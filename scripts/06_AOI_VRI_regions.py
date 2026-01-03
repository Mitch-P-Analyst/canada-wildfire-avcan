# ===================================================================
# Packages
# ===================================================================

from pathlib import Path
import geopandas as gpd
import zipfile
import sys

# ===================================================================
# Directories
# ===================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / "data"
analysis_dir = data_dir / "processed" / "analysis"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

aoi_out = analysis_dir / "avalanche_canada" / "regions" / "aoi"
aoi_out.mkdir(parents=True, exist_ok=True)

# ===================================================================
# Helper Functions
# ===================================================================

def zip_shapefile_components(files, zip_path):
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            f = Path(f)
            zf.write(f, arcname=f.name)

def normalize_region(val: object) -> str:
    """
    Normalize region identifiers so matching is resilient:
    - cast to str
    - strip
    - replace spaces/hyphens with underscores
    - collapse double underscores
    """
    s = str(val).strip()
    s = s.replace(" ", "_").replace("-", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s

def find_region_column(gdf: gpd.GeoDataFrame) -> str:
    """
    Try common region field names; fail fast with a clear message.
    """
    candidates = ["region", "Region", "REGION", "avcan_reg", "AvCan_Reg"]
    for c in candidates:
        if c in gdf.columns:
            return c
    raise KeyError(
        f"Could not find a region column in stage_A_polys. "
        f"Available columns: {list(gdf.columns)}"
    )

# ===================================================================
# Files
# ===================================================================

print("Loading Avalanche Canada (AvCan) regions file...")
avcan_path = analysis_dir / "avalanche_canada" / "regions" / "AvCan_cleaned_subregions.geojson"
avcan_shapes = gpd.read_file(avcan_path)
print(f" AvCan regions loaded. CRS: {avcan_shapes.crs}\n")

print("Loading Stage A Severity Patches shapefile...")
stage_A_shp = analysis_dir / "stage_A" / "AvCan_Stage_A" / "AvCan_Stage_A_all_regions_SHP.shp"
stage_A_polys = gpd.read_file(stage_A_shp)
print(f" Stage A patches loaded. CRS: {stage_A_polys.crs}\n")

# ===================================================================
# Determine regions to process (from Stage A)
# ===================================================================

stage_region_col = find_region_column(stage_A_polys)

regions_stage = (
    stage_A_polys[stage_region_col]
    .dropna()
    .astype(str)
    .map(normalize_region)
    .unique()
)

regions_stage = sorted(regions_stage)
print(f"Regions found in Stage A: {len(regions_stage)}")
# print(regions_stage)  # uncomment if you want to see them

# ===================================================================
# Prep AvCan shapes once (efficiency)
# ===================================================================

# Make a normalized join key for AvCan regions too
if "region" not in avcan_shapes.columns:
    raise KeyError(
        f"Expected 'region' column in AvCan shapes. Available columns: {list(avcan_shapes.columns)}"
    )

avcan_shapes = avcan_shapes.copy()
avcan_shapes["region_norm"] = avcan_shapes["region"].map(normalize_region)

# Reproject once (meters) and fix geometries once
avcan_3005 = avcan_shapes.to_crs(epsg=3005)

try:
    avcan_3005["geometry"] = avcan_3005["geometry"].make_valid()
except Exception:
    avcan_3005["geometry"] = avcan_3005["geometry"].buffer(0)

# ===================================================================
# Loop: build + export AOI for each Stage A region
# ===================================================================

bounds_rows = []

print("\nExporting AOIs per region...\n")

for region_norm in regions_stage:
    # 1) Subset AvCan polygons to this region
    aoi_region = avcan_3005.loc[avcan_3005["region_norm"] == region_norm].copy()

    if aoi_region.empty:
        print(f"[WARN] Region '{region_norm}' exists in Stage A but not found in AvCan shapes. Skipping.")
        continue

    # Pick a clean label for output (use the AvCan canonical 'region' value)
    region_label = str(aoi_region["region"].iloc[0])

    # 2) Dissolve into a single geometry
    aoi = aoi_region.dissolve(by="region_norm", as_index=False)

    # 3) Minimal schema for shapefile upload
    aoi = aoi[["geometry"]].copy()
    aoi["name"] = region_label
    aoi = aoi[["name", "geometry"]]

    # 4) Export shapefile + zip
    aoi_name = f"AOI_{region_norm}"  # region_norm is already filename-safe
    shp_path = aoi_out / f"{aoi_name}.shp"

    try:
        aoi.to_file(shp_path, driver="ESRI Shapefile")
        print(f" Shapefile export successful: {shp_path}")
    except Exception as e:
        raise RuntimeError(f" AOI Shapefile failed for region '{region_norm}': {e}\n")

    aoi_shp_files = list(aoi_out.glob(f"{aoi_name}.*"))
    zip_path = aoi_out / f"{aoi_name}.zip"

    print(f" Zipping components -> {zip_path.name}")
    zip_shapefile_components(aoi_shp_files, zip_path)

    # 5) Bounds reporting (and optional CSV summary)
    b3005 = aoi.total_bounds
    b4326 = aoi.to_crs(4326).total_bounds

    print(f" AOI bounds (EPSG:3005): {b3005}")
    print(f" AOI bounds (EPSG:4326): {b4326}\n")

    bounds_rows.append({
        "region_norm": region_norm,
        "region_label": region_label,
        "minx_3005": b3005[0], "miny_3005": b3005[1], "maxx_3005": b3005[2], "maxy_3005": b3005[3],
        "minlon_4326": b4326[0], "minlat_4326": b4326[1], "maxlon_4326": b4326[2], "maxlat_4326": b4326[3],
        "shp_path": str(shp_path),
        "zip_path": str(zip_path),
    })

# Optional: write bounds summary table
if bounds_rows:
    import pandas as pd
    bounds_csv = aoi_out / "aoi_bounds_summary.csv"
    pd.DataFrame(bounds_rows).to_csv(bounds_csv, index=False)
    print(f"Bounds summary written: {bounds_csv}")

print("\nPy File Complete.")
