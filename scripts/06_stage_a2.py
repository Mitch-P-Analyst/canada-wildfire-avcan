# ===================================================================
# Overview
# ===================================================================

"""
Stage_A2: Enrich Stage_A1 patch FeatureCollections with terrain-derived metadata.

- Inputs:  FeatureCollection assets in a Stage_A1 folder
- Outputs: FeatureCollection assets in a Stage_A2 folder

Adds:
  - patch area
  - elevation min/max/mean/relief
  - slope mean/std + mean pct
  - circular mean aspect (deg)
  - aspect coherence R (0..1)
  - aspect label: cardinal if R is high, else "Mixed"
"""

# ===================================================================
# Imports
# ===================================================================
import time
import ee
from pathlib import Path
import sys

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / 'data/'
analysis_dir = data_dir / 'processed' / 'analysis/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

    

# ===================================================================
# Components
# ===================================================================
from src.config_utils import read_yaml, pause

# ===================================================================
# Configs
# ===================================================================

# Google Earth Engine 
# =================================================================
ee_yaml_path = REPO_ROOT / "scripts/config/google_ee.yaml"
ee_yaml = read_yaml(ee_yaml_path, strict=True)


# ========== YAML Values =====================================
ee_project = ee_yaml.get("earth_engine", {}) or {}
overrides = ee_yaml.get("overrides", {}) or {}
params = ee_yaml.get("parameters", {}) or {}
thresholds = ee_yaml.get("thresholds", {}) or {}
proc = ee_yaml.get("processing", {}) or {}
docs = ee_yaml.get("docs", {}) or {}


# ======= EE Setup =======#
ee_project_id = ee_project.get("project_id")
if not ee_project_id:
    raise ValueError("Missing earth_engine.project_id in google_ee.yaml")


# ========== YAML Values =====================================

# ======= Parameters =======#
MAX_ACTIVE_TASKS = int(params.get("maximum_tasks_active", 6))   # READY + RUNNING combined
SLEEP_BETWEEN_SUBMISSIONS = int(params.get("submission_sleep", 2))  # Seconds

# ======= Thresholds =======#

# Assess mean cardinal direction/aspect of identified Burn Severity patch
ASPECT_R_THRESHOLD = float(thresholds.get("r_threshold", 0.60))  # mean aspect is shown only if coherence is sufficiently high

ASPECT_MIXED_LABEL = docs.get("mixed_label", "Mixed")
# ======= Processing =======#

# ==== Memory Mitigation ====#
# If Google EE memory limitations are apparent, adjust imagery processing variables.
# ===========================#

# EE tileScale (server-side chunking). Increase if simplification is insufficient.
TILESCALE_VECT = int(proc.get("tile_scale", 4))     # retry ladder: 4 → 8 → 16 MAX

# sampling scale used during zonal statistics (reduceRegions) over DEM/slope/aspect.
SCALE_M = int(proc.get("scale_m", 30))     # retry ladder: 30 → 45 → 60

# ======= Constants =======#
ASPECT_LABELS = ee.List(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
PI = ee.Number(3.141592653589793)

# Directories 
# =================================================================
PROJECT_ID = ee_project_id

IN_FOLDER = f"projects/{ee_project_id}/assets/AvCan_Wildfire_Explorer/Stage_A1"
OUT_FOLDER = f"projects/{ee_project_id}/assets/AvCan_Wildfire_Explorer/Stage_A2"

# ===================================================================
# EE Initialize
# ===================================================================
print("\nInitializing Google Earth Engine...")
print(f" EE Project: {PROJECT_ID}")
ee.Initialize(project=PROJECT_ID)
print(" Complete.\n")
pause(1)
print(f"Input asset folder (Stage A1): {IN_FOLDER}")
pause(2)
print(f"Output asset folder (Stage A2): {OUT_FOLDER}")
pause(2)

# ===================================================================
# Inputs
# ===================================================================

print(f"""\n
Assessment Parameters
    Max Active Tasks: {MAX_ACTIVE_TASKS}
    Sleep seconds: {SLEEP_BETWEEN_SUBMISSIONS}
    """)
pause(2.5)


print(f"""
Google EE Memory Mitation Parameters.
    Tilescale: {TILESCALE_VECT}
    Sampling scale: {SCALE_M}
    """)
pause(2.5)
print(f"""
Thresholds.
    To assess mean cardinal direction/aspect.
        minimum mean threshold: {ASPECT_R_THRESHOLD}
    Otherwise: {ASPECT_MIXED_LABEL}

    """)
pause(2.5)

# ===================================================================
# Helper Functions
# ===================================================================
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
            continue

        if st.get("state") in states:
            n += 1

    return n



def poll_active(active: dict, poll_seconds: int) -> None:
    """
    Poll tasks submitted.

    active is keyed by tid and stores a dict:
      {
        "task": ee.batch.Task,
        "base": str,
        "out_asset_id": str,
      }
    """
    done = []

    for tid, rec in list(active.items()):
        task = rec["task"]
        base = rec["base"]
        out_asset_id = rec["out_asset_id"]

        try:
            st = task.status()
        except Exception as e:
            # If EE can't find operation, treat as "done" and drop it to avoid infinite blocking
            msg = str(e).lower()
            if "operation" in msg and "not found" in msg:
                print(f"[WARN] {tid} :: {base} status unavailable (operation not found). Dropping.")
                done.append(tid)
            continue

        state = st.get("state")
        if state in ("READY", "RUNNING"):
            continue

        if state == "COMPLETED":
            print(f"[OK] {tid} :: -> {out_asset_id}")
        else:
            print(f"[FAIL] {tid} :: -> {out_asset_id} :: {state} :: {st.get('error_message','')}")
        done.append(tid)

    for tid in done:
        active.pop(tid, None)

    if active:
        time.sleep(poll_seconds)


def list_table_assets(parent_folder: str) -> list[str]:
    """
    Returns asset IDs of TABLE assets under the parent folder.
    Uses ee.data.listAssets (preferred) with fallback to ee.data.getList.
    """
    try:
        resp = ee.data.listAssets({"parent": parent_folder})
        assets = resp.get("assets", [])
        return [a["id"] for a in assets if a.get("type") == "TABLE"]
    except Exception:
        assets = ee.data.getList({"id": parent_folder})
        return [a["id"] for a in assets if a.get("type") == "Table"]


def asset_exists(asset_id: str) -> bool:
    """
    Assess existance of asset.

    asset_id: str
    rtype: bool
    """
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False


def ensure_folder(folder_id: str) -> None:
    """
    Ensure existance of folder structure
    
    folder_id: str
    """
    if asset_exists(folder_id):
        return
    print(f"Creating output folder: {folder_id}")
    ee.data.createAsset({"type": "FOLDER"}, folder_id)

# ===================================================================
# Terrain Sources
# ===================================================================

# 1) SRTM (good where available, but masked north of ~60N)
srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")  # meters

# 2) Global 30 m DEM (fills gaps in the far north)
glo30 = (
    ee.ImageCollection("COPERNICUS/DEM/GLO30")
    .select("DEM")
    .mosaic()
)

# 3) Use SRTM where it exists; fall back to GLO30 where SRTM is masked
dem = srtm.unmask(glo30).rename("elevation")    # meters

terrain = ee.Algorithms.Terrain(dem)
slope   = terrain.select("slope")    # degrees
aspect  = terrain.select("aspect")   # degrees from north

# ===================================================================
# Main Function - Enrich Asset
# ===================================================================
def enrich_fc_with_terrain(fc: ee.FeatureCollection) -> ee.FeatureCollection:
    """
    Calculate and add terrain metadata to Stage A1 input.

    Adds:
      patch_area_m2, patch_area_ha
      elev_min_m, elev_max_m, elev_mean_m, elev_relief_m
      slp_mn_deg, slp_std_dg, slp_mn_pct
      aspect_mean_deg, aspect_R
      aspect_cardinal_mean, aspect_label
      scenario
    """
    # Add Area 
    # =================================================================
    def add_area(ft: ee.Feature) -> ee.Feature:
        """
        Calculate area for polygon asset
        
        ft: ee.Feature
        return: ee.Feature
        return:
            "patch_area_m2"
            "patch_area_ha"
        """
        g = ft.geometry()
        a_m2 = g.area(maxError=10)
        return ft.set({
            "patch_area_m2": a_m2,
            "patch_area_ha": ee.Number(a_m2).divide(1e4),
        })

    fc = fc.map(add_area)

    # ========= Aspect circular stats (why sin/cos?) =====================
    # Aspect is a circular variable (0° == 360°), so you cannot take a normal mean in degrees.
    # Convert aspect (deg) -> radians, then to unit-vector components: sin(theta), cos(theta).
    # Later we reduce (mean) these components per polygon and recover the circular mean angle with atan2(mean_sin, mean_cos),
    # plus a coherence score R = sqrt(mean_sin^2 + mean_cos^2) indicating how consistent aspect is within the patch.
    aspect_rad = aspect.multiply(PI.divide(180))
    asp_sin = aspect_rad.sin().rename("asp_sin")
    asp_cos = aspect_rad.cos().rename("asp_cos")

    # Singular reduce regions 
    # =================================================================

    # ========== Concat image into singular multiband-image ===========
    img = ee.Image.cat([
        # Produce 4 pixel bands for analysis
        dem.rename("elev"),     # Terrain elevation of pixels in image geometry
        slope.rename("slp"),    # Terrain slope of pixels in image geometry
        asp_sin,                # Aspect_sin
        asp_cos,                # Aspect_cos
    ])

    # ========== Pixel reducer: minMax + mean + standard deviation ===========
    reducer = (
        ee.Reducer.minMax()         # Min + Max computation
        .combine(ee.Reducer.mean(), sharedInputs=True)  # Mean computation
        .combine(ee.Reducer.stdDev(), sharedInputs=True)    # Standard deviation computation
    )

    # ========== Calculate feature collection stats ==============================
    fc_stats = img.reduceRegions(
        # Apply reduction calculations on the "img" variable 4 pixel bands
        collection=fc,              # Stage A1 feature collection geometry
        reducer=reducer,            # minMax + mean + standard deviation 
        scale=SCALE_M,
        tileScale=TILESCALE_VECT,
        maxPixelsPerRegion=1e9,
    )
            # fc_stats output are computations from the reducer upon the 4 pixel bands of geometry input.

    # Derive Outputs 
    # =================================================================
    def add_derived(ft: ee.Feature) -> ee.Feature:
        """
        Calculates metadata from the reducer-generated per-feature statistics attached to each feature in fc_stats
        
        return:
            "elev_min_m" :: Minimum patch elevation (m)
            "elev_max_m" :: Maximum patch elevation (m)
            "elev_mean_m" :: Mean patch elevation (m)   
            "elev_relief_m" :: Elevation change (m)
            "slp_mn_deg" :: Mean slope degree
            "slp_std_dg" :: slope degree standard deviation
            "slp_mn_pct" :: Mean slope percent
            "aspect_mean_deg" :: Mean aspect degree
            "aspect_R" :: Aspect confidence
            "aspect_cardinal_mean" :: Mean aspect cardinal direction
            "aspect_label" :: Derived aspect label
            "scenario": "direct_post"
        """
        # ========== Elevation =====================================
        elev_min = ee.Number(ft.get("elev_min"))
        elev_max = ee.Number(ft.get("elev_max"))
        elev_mean = ee.Number(ft.get("elev_mean"))
        elev_relief = elev_max.subtract(elev_min)

        # ========== Slope =====================================
        slp_mean = ee.Number(ft.get("slp_mean"))
        slp_std = ee.Number(ft.get("slp_stdDev"))
        slp_mean_pct = slp_mean.multiply(PI.divide(180)).tan().multiply(100)

        # ========== Aspect =====================================
        # reducer outputs: mean(sin(aspect)) and mean(cos(aspect)) per polygon
        sin_mean = ee.Number(ft.get("asp_sin_mean"))
        cos_mean = ee.Number(ft.get("asp_cos_mean"))

        # ======= Circular mean =======#
        # Recover the mean direction from mean unit-vector components (circular stats)
        mean_rad = cos_mean.atan2(sin_mean)  # Earth Engine: x.atan2(y) returns atan2(y, x)
        mean_deg = (                         # radians -> degrees, normalized to [0, 360)
            mean_rad.multiply(180).divide(PI)
            .add(360)
            .mod(360)
        )

        # ======= Mean-derived cardinal direction (8-way) =======#
        # Bin angle into 8 compass sectors:
        # - +22.5 centers the bins on N, NE, E, ...
        # - /45 gives sector index, floor -> integer, mod 8 wraps
        idx = mean_deg.add(22.5).divide(45).floor().mod(8).toInt()
        cardinal_mean = ee.String(ASPECT_LABELS.get(idx))  # ["N","NE","E","SE","S","SW","W","NW"]

        # ======= Aspect coherence R (0..1) =======#
        # Magnitude of the mean resultant vector:
        # - near 1: aspects are consistent (single direction meaningful)
        # - near 0: aspects are mixed/variable
        aspect_R = sin_mean.pow(2).add(cos_mean.pow(2)).sqrt()

        # If coherence is low, label as mixed/variable; otherwise use 8-way cardinal
        aspect_label = ee.String(
            ee.Algorithms.If(
                aspect_R.gte(ASPECT_R_THRESHOLD),
                cardinal_mean,
                ee.String(ASPECT_MIXED_LABEL),
            )
        )


        return ft.set({
            "elev_min_m": elev_min,
            "elev_max_m": elev_max,
            "elev_mean_m": elev_mean,
            "elev_relief_m": elev_relief,
            "slp_mn_deg": slp_mean,
            "slp_std_dg": slp_std,
            "slp_mn_pct": slp_mean_pct,

            "aspect_mean_deg": mean_deg,
            "aspect_R": aspect_R,
            "aspect_cardinal_mean": cardinal_mean,
            "aspect_label": aspect_label,

            "scenario": "direct_post",
        })

    return fc_stats.map(add_derived)


# ===================================================================
# Export Driver
# ===================================================================
def export_stage_a2_for_asset(in_asset_id: str, active: dict, poll_seconds: int) -> None:
    """
    Docstring for export_stage_a2_for_asset
    
    :param in_asset_id: Description
    :type in_asset_id: str
    :param active: Description
    :type active: dict
    :param poll_seconds: Description
    :type poll_seconds: int
    """
    # ========== Variables =====================================

    base_in = in_asset_id.split("/")[-1]

    # Rename output basename: Stage_A1_*  ->  Stage_A2_*
    if base_in.startswith("Stage_A1_"):
        base_out = base_in.replace("Stage_A1_", "Stage_A2_", 1)
    elif base_in.startswith("Stage_A1"):
        base_out = base_in.replace("Stage_A1", "Stage_A2", 1)
    else:
        # Fallback (in case any asset doesn't follow the expected naming)
        base_out = f"Stage_A2_{base_in}"

    out_asset_id = f"{OUT_FOLDER}/{base_out}"


    if asset_exists(out_asset_id):
        # Skip already computed assets
        print(f"Skipping (exists): {out_asset_id}")
        return

    # ========== Assets =====================================

    fc_in = ee.FeatureCollection(in_asset_id)   # Stage_A1 asset
    fc_out = enrich_fc_with_terrain(fc_in)      # Stage_A2 asset

    task = ee.batch.Export.table.toAsset(
        collection=fc_out,
        description=base_out,
        assetId=out_asset_id,
    )

    # ========== Throttling =====================================
    # Local throttling: only tasks we started in THIS run
    while len(active) >= MAX_ACTIVE_TASKS:
        poll_active(active, poll_seconds)

    task.start()
    st0 = task.status()
    tid = st0.get("id") or st0.get("name") or f"unknown_{time.time()}"

    # ========== Record Metadata =====================================
    # Store metadata so OK/FAIL logs are attributable
    active[tid] = {
    "task": task,
    "base": base_out,
    "out_asset_id": out_asset_id,
}
    print(f"[SUBMIT] {tid} :: {base_out}  ->  {out_asset_id}")

    time.sleep(SLEEP_BETWEEN_SUBMISSIONS)

# ===================================================================
# Main
# ===================================================================
def main() -> None:
    ensure_folder(OUT_FOLDER)

    assets = list_table_assets(IN_FOLDER)
    # # ===================================================================
    # # --- ONLY run the two Yukon failures ---
    # # ===================================================================
    # ONLY_BASENAMES = {
    #     "Stage_A1_Patches_Yukon_Wheaton_1998",
    #     "Stage_A1_Patches_Yukon_Wheaton_2003",
    # }
    # assets = [a for a in assets if a.split("/")[-1] in ONLY_BASENAMES]

    # print(f"Filtered to {len(assets)} assets:\n" + "\n".join(assets) + "\n")
    # # =================================================================
    print(f"Found {len(assets)} TABLE assets in:\n  {IN_FOLDER}\n")

    active = {}
    poll_seconds = 30

    for i, aid in enumerate(sorted(assets), start=1):
        print(f"[{i}/{len(assets)}] Processing: {aid}")
        export_stage_a2_for_asset(aid, active, poll_seconds)

    # Drain remaining tasks
    while active:
        poll_active(active, poll_seconds)

    print("\nSubmitted all exports.")


if __name__ == "__main__":
    main()
