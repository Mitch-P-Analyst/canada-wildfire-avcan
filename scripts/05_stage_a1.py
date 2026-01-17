
# ===================================================================
# Imports
# ===================================================================
import re
import time
from typing import Dict, Tuple, List, Optional, Set, Literal
import ee
from dataclasses import dataclass
import json
import sys
from pathlib import Path

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / 'data/'
analysis_dir = data_dir / 'processed' / 'analysis/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

    

# ===================================================================
# Configs
# ===================================================================

NO_FIRES_JSON = analysis_dir / "stage_A/stage_A1/stage_A1_no_fires_jobs.json"

# Google Earth Engine  
# =================================================================
AVCAN_TABLE_ID = "projects/wildfire-canada-475322/assets/AvCan_Wildfire_Explorer/AvCan_fires_1990_2024"
OUT_FOLDER     = "projects/wildfire-canada-475322/assets/AvCan_Wildfire_Explorer/Stage_A1"

PROJECT_ID = "wildfire-canada-475322"

print('Py file 04_avcan_fires_overlay output file uploaded to Google Earth Engine as cloud asset.')
print(f" {AVCAN_TABLE_ID}")

# ===================================================================
# EE Initialize
# ===================================================================
print("\nInitializing Google Earth Engine...")
ee.Initialize(project=PROJECT_ID)
print(" Complete.\n")

# ===================================================================
# Inputs
# ===================================================================

# Parameters 
# =================================================================
YEARS = list(range(2008, 2025))  # Last list item is exclusive

MAXIMUM_TASKS_ACTIVE = 6             # READY + RUNNING combined
SLEEP_BETWEEN_SUBMISSIONS = 2    # Seconds
print(f"""\n
Assessment Parameters
    Max Active Tasks: {MAXIMUM_TASKS_ACTIVE}
    Sleep seconds: {SLEEP_BETWEEN_SUBMISSIONS}
    Date Range: {YEARS})

    """)


# ========== Processing =====================================

# ======= Earth Engine Memory Mitigation Parameters =======#
# If Google EE memory limitations are apparent, adjust imagery processing parameters below.

# Polygon simplification (meters). Try increasing first for memory failures.
SIMPLIFY_M = 60   # retry ladder: 60 → 90 → 120 → 250

# EE tileScale (server-side chunking). Increase if simplification is insufficient.
TILESCALE_VECT = 4     # retry ladder: 4 → 8 → 16 MAX

# sampling scale used during raster → vector polygonization (reduceToVectors) in meters. Adjust last.
VECT_SCALE = 45  # retry ladder: 30 → 45 → 60 → 90 MAX

# ======= Constants =======#
CLOUD_COVER_MAX = 60
HIGH_THR = 0.20
MIN_PATCH_HA = 10.0
MAX_PATCH_PIX = round(((MIN_PATCH_HA * 1e4) / (VECT_SCALE * VECT_SCALE)),2)
MAX_PATCH_SIZE_PIX = 1024
EIGHT_CONNECTED = True

print(f"""
Google EE Memory Mitation Parameters.
    Polygon Vectorisation: {SIMPLIFY_M}
    Tilescale: {TILESCALE_VECT}
    Processing scale: {VECT_SCALE}
      
Landsat Imagery processing parameters.
    Image composite cloud cover maximum: {CLOUD_COVER_MAX}

Patches parameters.
    dNBR Threshold: {HIGH_THR}
    Minimum patch area (ha): {MIN_PATCH_HA}
    Minimum patch size (pixels): {MAX_PATCH_PIX}
    Maximum patch size (pixels): {MAX_PATCH_SIZE_PIX}
    8-neighbour Pixel connectivity: {EIGHT_CONNECTED}
      """)


# ===================================================================
# Function Helpers
# ===================================================================
def sanitize_name(s: str) -> str:
    """
    Verify region / subregion names in uniform format meeting Google EE requirements.
    """
    return re.sub(r"[^0-9A-Za-z_]+", "_", str(s))

def asset_exists(asset_id: str) -> bool:
    """
    Verify if region / subregion / year candidate fires already analyzed and present in Google EE assets folder.
    
    asset_id: Candidate asset name 
    return: bool TRUE/FALSE
    """
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False

def active_task_count() -> int:
    """
    Count of Google EE tasks in operational status. 
    """
    states = {"READY", "RUNNING"}
    n = 0

    for t in ee.batch.Task.list():
        try:
            st = t.status()
        except Exception as e:
            # Common EE polling failure: Operation not found (404)
            msg = str(e).lower()
            if "operation" in msg and "not found" in msg:
                continue
            # If it's something else transient, you can also just skip
            # or re-raise. I recommend skip to keep long runs alive.
            continue

        if st.get("state") in states:
            n += 1

    return n


def is_empty_table_error(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        ("empty" in m and "table" in m) or
        ("no features" in m) or
        ("0 features" in m) or
        ("collection is empty" in m)
    )

JobKey = Tuple[str, str, int, Optional[int]]  # (region, subregion, year, fireid)


NoFireKey = Tuple[str, str, int]  # region, subregion, year

def load_no_fire_cache(path: Path) -> Set[NoFireKey]:
    if not path.exists():
        return set()
    with open(path, "r") as f:
        rows = json.load(f)
    out: Set[NoFireKey] = set()
    for r in rows:
        out.add((r["region"], r["subregion"], int(r["year"])))
    return out

def save_no_fire_cache(path: Path, keys: Set[NoFireKey]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"region": r, "subregion": s, "year": y} for (r, s, y) in sorted(keys)]
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


@dataclass
class FailedJob:
    region: str
    subregion: str
    year: int
    fireid: Optional[int]
    state: str
    error: str

# ========== Expand aggregates to per-fire jobs =====================================
def expand_failed_to_fireid_jobs(
    avcan_fc: ee.FeatureCollection,
    failed: List[FailedJob],
    limit_per_group: Optional[int] = None,
    debug: bool = True,
) -> List[JobKey]:
    # ONLY expand aggregate failures (fireid is None)
    groups = sorted({(j.region, j.subregion, j.year) for j in failed if j.fireid is None})

    expanded: List[JobKey] = []
    for region, subregion, year in groups:
        fc = (avcan_fc
              .filter(ee.Filter.eq("region", region))
              .filter(ee.Filter.eq("subregion", subregion))
              .filter(ee.Filter.eq("year", year)))

        n = fc.size().getInfo()
        if n == 0:
            if debug:
                print(f"[RETRY-SKIP no fires] {region}-{subregion}-{year}")
            continue

        fireids = fc.aggregate_array("fireid").getInfo()
        fireids = [int(fid) for fid in fireids if fid is not None]

        if limit_per_group is not None:
            fireids = fireids[:limit_per_group]

        if debug:
            print(f"[RETRY-EXPAND] {region}-{subregion}-{year}: {len(fireids)} fireids")

        expanded.extend([(region, subregion, year, fid) for fid in fireids])

    return expanded

# ===================================================================
# Constants
# ===================================================================
SubmitStatus = Literal["SUBMITTED", "SKIP_EXISTS", "SKIP_NO_FIRES"]

# ===================================================================
# Landsat Collections
# ===================================================================
ls5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2")
ls7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
ls8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
ls9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")

dummy_nbr = ee.Image.constant(0).rename("NBR").toFloat()

def mask_landsat_sr(img: ee.Image) -> ee.Image:
    qa = img.select("QA_PIXEL")
    cloud = qa.bitwiseAnd(1 << 3).eq(0)
    shadow = qa.bitwiseAnd(1 << 4).eq(0)
    snow = qa.bitwiseAnd(1 << 5).eq(0)
    return img.updateMask(cloud.And(shadow).And(snow)).copyProperties(img, img.propertyNames())

def add_nbr_57(img: ee.Image) -> ee.Image:
    return img.addBands(img.normalizedDifference(["SR_B4", "SR_B7"]).rename("NBR")).copyProperties(img, img.propertyNames())

def add_nbr_89(img: ee.Image) -> ee.Image:
    return img.addBands(img.normalizedDifference(["SR_B5", "SR_B7"]).rename("NBR")).copyProperties(img, img.propertyNames())

# ===================================================================
# Main Function
# ===================================================================
def run_stage_a1(avcan_fc: ee.FeatureCollection, region: str, subregion: str, fire_year: int, fireid: Optional[int] = None) -> ee.FeatureCollection:
    empty_fc = ee.FeatureCollection([])
    """
    Primary Stage_A1 function. Perform dNBR across designated pre/post fire years for region-subregion and year input. 

    avcan_fc: AvCan fires uploaded Google EE cloud asset
    region: AvCan region
    subregion: AvCan subregion
    fire_year: Individual year
    """

    # Fires 
    # =================================================================
    
    # ========== Extract fire geometry of input variables =====================================
    fires = (avcan_fc
             .filter(ee.Filter.eq("region", region))
             .filter(ee.Filter.eq("subregion", subregion))
             .filter(ee.Filter.eq("year", fire_year)))
    if fireid is not None:
        fires = fires.filter(ee.Filter.eq("fireid", fireid))
    # ========== Per fire analysis  =====================================
    def per_fire(fire: ee.Feature) -> ee.FeatureCollection:
        geom = fire.geometry().simplify(SIMPLIFY_M)

        # ======= dNBR dates =======#
        pre_start  = ee.Date.fromYMD(fire_year - 1, 6, 1)
        pre_end    = ee.Date.fromYMD(fire_year - 1, 10, 31)
        post_start = ee.Date.fromYMD(fire_year + 1, 6, 1)
        post_end   = ee.Date.fromYMD(fire_year + 1, 10, 31)

        # ======= Landsat imagery composites =======#
        
        # ==== Landsat 5 + 7 ====#
        ls57 = (ls5.merge(ls7)
                .filterBounds(geom)
                .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
                .map(mask_landsat_sr)
                .map(add_nbr_57))

        # ==== Landsat 8 + 9 ====#
        ls89 = (ls8.merge(ls9)
                .filterBounds(geom)
                .filter(ee.Filter.lt("CLOUD_COVER", CLOUD_COVER_MAX))
                .map(mask_landsat_sr)
                .map(add_nbr_89))

        # ==== Compile all Landsat ====#
        ls = ls57.merge(ls89)

        pre_col  = ls.filterDate(pre_start, pre_end).select("NBR")
        post_col = ls.filterDate(post_start, post_end).select("NBR")

        pre_safe = ee.ImageCollection(ee.Algorithms.If(pre_col.size().gt(0), pre_col, ee.ImageCollection([dummy_nbr])))
        post_safe = ee.ImageCollection(ee.Algorithms.If(post_col.size().gt(0), post_col, ee.ImageCollection([dummy_nbr])))

        pre = pre_safe.median()
        post = post_safe.median()
        dnbr = pre.subtract(post).rename("dNBR")

        # ========== dNBR Mask =====================================
        mask = dnbr.gte(HIGH_THR)   # Callibrated minimum dNBR threshold

        min_patch_pixels = (ee.Number(MIN_PATCH_HA)
                            .multiply(1e4)
                            .divide(VECT_SCALE * VECT_SCALE))   # Callibrated minimum patch size 

        patch_pix = mask.connectedPixelCount(
            maxSize=MAX_PATCH_SIZE_PIX,
            eightConnected=EIGHT_CONNECTED
        )
        # ======= Filter dNBR Mask =======#
        big_mask = mask.updateMask(patch_pix.gte(min_patch_pixels)) # Minimum patch sizes by pixel-neighbour connected

        # ======= Extract dNBR patch vectors as polygons =======#
        polys = big_mask.selfMask().reduceToVectors(
            geometry=geom,
            scale=VECT_SCALE,
            geometryType="polygon",
            eightConnected=True,
            maxPixels=1e10,
            tileScale=TILESCALE_VECT
        )

        # ========== Patch Metadata =====================================
        fire_props = fire.toDictionary(["gid", "fireid", "year", "natpark", "region", "subregion"])

        patches = polys.map(lambda ft: ee.Feature(ee.Feature(ft).geometry()).set(fire_props))

        n = patches.size()

        # ======= Assign IDs + calculate area =======#
        def make_with_ids() -> ee.FeatureCollection:
            """
            Assign ID to each identified Burn Severity Patch in fire + calculate patch area
            """
            lst = patches.toList(n)
            idxs = ee.List.sequence(0, n.subtract(1))
            fc = ee.FeatureCollection(idxs.map(lambda i:
                ee.Feature(lst.get(i)).set({
                    "patch_id": ee.Number(i).add(1),
                    "patch_area_ha": ee.Feature(lst.get(i)).geometry().area(maxError=10).divide(1e4),
                    "scenario": "direct_post"
                })
            ))
            return fc

        return ee.FeatureCollection(ee.Algorithms.If(n.eq(0), empty_fc, make_with_ids()))

    per_fire_fc = fires.map(per_fire)  # returns a "collection of collections"
    return ee.FeatureCollection(per_fire_fc).flatten()


# ===================================================================
# Region/Subregion Selection
# ===================================================================
avcan = ee.FeatureCollection(AVCAN_TABLE_ID)

regions = avcan.aggregate_array("region").distinct().getInfo()

# Region Selection 
# =================================================================

# ========== All Regions =====================================
# regions = [r for r in regions if r in set(regions)]
# print(f"Running regions ({len(regions)}): {regions}")

# ======= Specifc Region Selection =====================================

SPECIFIC_REGION = [
    "Cariboos",
    "Kootenay_Boundary",
    "North_Columbia",
    "South_Columbia",
    "Purcells",
    "South_Coast_Inland"
]
print('\nSpecifc region(s) selection in place.')

regions = [r for r in regions if r in set(SPECIFIC_REGION)]
print(f"Running regions ({len(regions)}): {regions}")

# Subregion Seleciton 
# =================================================================

# ========== All Subregions =====================================

# subregions_by_region: Dict[str, List[str]] = {}
# for r in regions:
#     subs = (
#         avcan.filter(ee.Filter.eq("region", r))
#                 .aggregate_array("subregion")
#                 .distinct()
#                 .getInfo()
#                 )
#     subregions_by_region[r] = [s for s in subs if s is not None]

# ======= Specific Subregion Selection =======#

print("\nSpecifc subregion(s) selection in place.")
subregions_by_region: Dict[str, List[str]] = {}
for r in regions:
    specific_sub = [
        "Quesnel",
        "South_Okanagan",
        "Jordan",
        "St.Mary",
        "Harrison_Fraser",
        "Gold",
        "Central_Selkirk",
        "Stein"
    ]
    subregions_by_region[r] = [s for s in specific_sub]



# ===================================================================
# Google EE task submission
# ===================================================================

def submit_job(
    region: str,
    subregion: str,
    year: int,
    skip_existing: bool,
    fireid: Optional[int] = None
    ) -> Tuple[SubmitStatus, Optional[ee.batch.Task]]:

    """
    Submit active Google EE task for identified region, subregion, year
    
    :param region: Description
    :type region: str
    :param subregion: Description
    :type subregion: str
    :param year: Description
    :type year: int
    :param skip_existing: Description
    :type skip_existing: bool
    :return: Description
    :rtype: Task | None
    """


    # Structured asset outputs
    suffix = f"{year}" if fireid is None else f"{year}_fireid{fireid}"
    asset_name = f"Stage_A1_Patches_{sanitize_name(region)}_{sanitize_name(subregion)}_{suffix}"
    asset_id = f"{OUT_FOLDER}/{asset_name}"

    if skip_existing and asset_exists(asset_id):
        print(f"[SKIP exists] {asset_name}")
        return ("SKIP_EXISTS", None)
    
    # AvCan Fires 
    # =================================================================

    fires_fc = (avcan
        .filter(ee.Filter.eq("region", region))
        .filter(ee.Filter.eq("subregion", subregion))
        .filter(ee.Filter.eq("year", year))
    )
    if fireid is not None:
        fires_fc = fires_fc.filter(ee.Filter.eq("fireid", fireid))

    fires_n = fires_fc.size().getInfo()
    if fires_n == 0:
        print(f"[SKIP no fires] {asset_name}")
        return ("SKIP_NO_FIRES", None)
    
    # ========== Debuging =====================================
    
    # ======= list fireids in this job =======#
    DEBUG = False  # set False for full production runs
    if DEBUG:
        fireids = fires_fc.aggregate_array("fireid").getInfo()
        print(f"[INFO] fireids for {region}-{subregion}-{year} ({len(fireids)}): {fireids}")

        # ======= show largest fires first (by area)  =======#
        fires_debug = (fires_fc
        .map(lambda f: f.set("area_ha", f.geometry().area(10).divide(1e4)))
        .sort("area_ha", False)
    )

        top = fires_debug.limit(5).getInfo()["features"]
        print(f"[INFO] Top 5 fires by area for {region}-{subregion}-{year}:")
        for feat in top:
            props = feat["properties"]
            print(f"  fireid={props.get('fireid')}  area_ha={float(props.get('area_ha', 0)):.1f}")


    # ========== Resume =====================================

    fc = run_stage_a1(avcan, region, subregion, year, fireid=fireid)

    task = ee.batch.Export.table.toAsset(
        collection=fc,
        description=asset_name,
        assetId=asset_id
    )
    task.start()
    print(f"[SUBMIT] {asset_name} (fires={fires_n})")
    return ("SUBMITTED", task)


# ===================================================================
# Run all Jobs
# ===================================================================


def run_all_jobs(
    jobs: List[JobKey],
    max_active_tasks: int,
    poll_seconds: int,
    sleep_between_submissions: int,
    skip_existing: bool,
    no_fire_cache_path: Path
    ):

    active: Dict[str, Tuple[ee.batch.Task, JobKey]] = {}
    results = {
        "COMPLETED": [],
        "SKIP_EXISTS": [],
        "SKIP_NO_FIRES": [],
        "SKIP_EMPTY": [],
        "FAILED_OTHER": [],
        "UNKNOWN_STATUS": []
    }

    # load prior "no fires" knowledge
    known_no_fires = load_no_fire_cache(no_fire_cache_path)

    queue = list(jobs)

    def poll_active():
        done_ids = []
        for tid, (task, job) in list(active.items()):
            try:
                st = task.status()
            except Exception as e:
                msg = str(e).lower()

                # EE sometimes returns 404 for old/stale operations:
                # "Operation ... not found."
                if "operation" in msg and "not found" in msg:
                    results["UNKNOWN_STATUS"].append(
                        FailedJob(
                            region=job[0],
                            subregion=job[1],
                            year=job[2],
                            fireid=job[3],
                            state="UNKNOWN",
                            error="Operation not found"
                        )
                    )


                    print(f"[WARN] {job} :: status unavailable (operation not found). Dropping from active.")
                    done_ids.append(tid)
                    continue

                # Any other transient error: skip this task for this poll cycle
                print(f"[WARN] {job} :: status check failed this cycle: {e}")
                continue

            state = st.get("state")
            err = st.get("error_message", "") or ""


            if state in ("READY", "RUNNING"):
                continue

            if state == "COMPLETED":
                results["COMPLETED"].append(job)
                print(f"[OK] {job}")
                done_ids.append(tid)
                continue

            if is_empty_table_error(err):
                results["SKIP_EMPTY"].append(job)
                print(f"[EMPTY] {job}")
            else:
                results["FAILED_OTHER"].append(
                    FailedJob(
                        region=job[0],
                        subregion=job[1],
                        year=job[2],
                        fireid=job[3],
                        state=state,
                        error=err
                    )
                )
                print(f"[FAIL] {job} :: {state} :: {err}")


            done_ids.append(tid)

        for tid in done_ids:
            active.pop(tid, None)

    while queue or active:
        while queue and len(active) < max_active_tasks:
            job = queue.pop(0)
            region, subregion, year, fireid = job  # because ALWAYS 4-tuple


            # skip cached no-fires applies ONLY to aggregate jobs
            if fireid is None and (region, subregion, year) in known_no_fires:
                results["SKIP_NO_FIRES"].append(job)
                print(f"[SKIP cached no-fires] {job}")
                continue

            # 2) enforce max active tasks
            while len(active) >= max_active_tasks:
                time.sleep(poll_seconds)
                poll_active()

            status, task = submit_job(region, subregion, year, skip_existing, fireid=fireid)

            if status == "SKIP_EXISTS":
                results["SKIP_EXISTS"].append(job)
                time.sleep(sleep_between_submissions)
                continue

            if status == "SKIP_NO_FIRES":
                results["SKIP_NO_FIRES"].append(job)
                # cache ONLY if this was an aggregate job
                if fireid is None:
                    known_no_fires.add((region, subregion, year))   # learn it for this run + future runs
                time.sleep(sleep_between_submissions)
                continue

            # SUBMITTED
            if task is None:
                results["FAILED_OTHER"].append(FailedJob(region, subregion, year, fireid, "SUBMIT_ERROR", "Task was None after SUBMITTED"))
                continue
            tid = task.status().get("id") or f"unknown_{time.time()}"

            active[tid] = (task, job)
            time.sleep(sleep_between_submissions)

        if active:
            time.sleep(poll_seconds)
            poll_active()

    # persist learned no-fires at end
    save_no_fire_cache(no_fire_cache_path, known_no_fires)
    print(f"[WRITE] {no_fire_cache_path} (cached no-fires={len(known_no_fires)})")

    return results

# ===================================================================
# Build Task Job List
# ===================================================================


jobs: List[JobKey] = [(r, s, y, None) for r in regions for s in subregions_by_region[r] for y in YEARS]

# Specific Job List 
# =================================================================


# Clearwater_2021 = [1205, 1233, 1275, 1323, 1325, 1650, 1665, 1809, 2526, 2589, 2644, 2652, 2723]
# Clearwater_2024 = [201, 213, 242, 1166, 1167, 1169, 1173, 1174, 1177, 1180, 1181, 1182, 1183, 1184, 1186, 1187, 1188, 1190, 1194, 1195]

# region = "Cariboos"
# subregion = "Clearwater"

# specific_jobs: List[JobKey] = []

# for job_id in Clearwater_2021:
#     specific_jobs.append((region, subregion, 2021, job_id))

# for job_id in Clearwater_2024:
#     specific_jobs.append((region, subregion, 2024, job_id))

# jobs: List[JobKey] = specific_jobs
# Run Jobs 
# =================================================================


results = run_all_jobs(
    jobs=jobs,
    max_active_tasks=MAXIMUM_TASKS_ACTIVE,
    poll_seconds=30,
    sleep_between_submissions=SLEEP_BETWEEN_SUBMISSIONS,
    skip_existing=True,
    no_fire_cache_path=NO_FIRES_JSON
)

# ===================================================================
# Finish
# ===================================================================
print("\n=== SUMMARY ===")
for k, v in results.items():
    print(f"{k}: {len(v)}")

# Export Failed / Unknown Jobs
# =================================================================
FAILED_JSON  = analysis_dir / "stage_A/stage_A1/stage_A1_failed_jobs.json"
UNKNOWN_JSON = analysis_dir / "stage_A/stage_A1/stage_A1_unknown_status_jobs.json"


# Ensure output directory exists
FAILED_JSON.parent.mkdir(parents=True, exist_ok=True)

# ========== Failed Other =====================================

with open(FAILED_JSON, "w") as f:
    json.dump(
        [j.__dict__ for j in results["FAILED_OTHER"]],
        f,
        indent=2
    )
print(f"[WRITE] {FAILED_JSON}")

# ========== Failed Unknown Status =====================================
with open(UNKNOWN_JSON, "w") as f:
    json.dump(
        [j.__dict__ for j in results["UNKNOWN_STATUS"]],
        f,
        indent=2
    )
print(f"[WRITE] {UNKNOWN_JSON}")

# ===================================================================
# Retry pass: expand aggregate FAILED_OTHER into per-fire jobs
# ===================================================================

failed_other: List[FailedJob] = results["FAILED_OTHER"]

if failed_other:
    print(f"\nRetrying FAILED_OTHER by expanding to per-fireid jobs...\n")

    retry_jobs: List[JobKey] = expand_failed_to_fireid_jobs(avcan, failed_other, debug=True)

    if retry_jobs:
        retry_results = run_all_jobs(
            jobs=retry_jobs,
            max_active_tasks=MAXIMUM_TASKS_ACTIVE,
            poll_seconds=30,
            sleep_between_submissions=SLEEP_BETWEEN_SUBMISSIONS,
            skip_existing=False,
            no_fire_cache_path=NO_FIRES_JSON,
        )
else:
    print("\nNo FAILED_OTHER jobs to retry.\n")


print("\nPy File Complete.")
