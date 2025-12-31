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
data_dir = REPO_ROOT / 'data/'
processed_dir = data_dir / 'processed' / 'analysis/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

aoi_out = processed_dir / 'avalanche_canada/regions/aoi'
aoi_out.mkdir(parents=True, exist_ok=True)

# ===================================================================
# Helper Functions
# ===================================================================


def zip_shapefile_components(files, zip_path):
    """
    Create a ZIP archive containing all given shapefile component files.

    Parameters
    ----------
    files : Iterable[Path]
        Paths to the component files (.shp, .shx, .dbf, .prj, etc.).
    zip_path : Path or str
        Full path (including .zip filename) where the archive will be written.
    """
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            f = Path(f)
            # Store just the filename inside the archive
            zf.write(f, arcname=f.name)


# ===================================================================
# Files
# ===================================================================

# Avalanche Canada polygons (GeoJSON)
# =================================================================
print(f'Loading Avalanche Canada (AvCan) regions shapefile...')
avcan_path = REPO_ROOT / "data/processed/analysis/avalanche_canada/regions/AvCan_cleaned_subregions.geojson"
avcan_shapes = gpd.read_file(avcan_path)
print(f" Avalanche Canada Regions loaded. {avcan_shapes.crs}\n")


# 1) Subset to your target region
sea_to_sky = avcan_shapes.loc[avcan_shapes["region"] == "Sea_To_Sky"].copy()

# 2) Reproject to BC Albers (meters) to match the portal setting
sea_to_sky = sea_to_sky.to_crs(epsg=3005)

# 3) Ensure valid geometries (recommended before union)
# If you're on GeoPandas >= 0.12 + Shapely >= 2, make_valid exists
try:
    sea_to_sky["geometry"] = sea_to_sky["geometry"].make_valid()
except Exception:
    # Fallback that often fixes minor issues
    sea_to_sky["geometry"] = sea_to_sky["geometry"].buffer(0)

# 4) Dissolve/union into a single geometry (one-row GeoDataFrame)
# Option A: dissolve by the region field
aoi = sea_to_sky.dissolve(by="region", as_index=False)

# Keep a minimal schema for AOI upload
aoi = aoi[["region", "geometry"]].rename(columns={"region": "name"})


# AvCan Regions 
# =================================================================

# ========== Shapefile Export =====================================

print('\nExporting Shapefile...')

aoi_name = "AOI_Sea_To_Sky"
shp_path = aoi_out / f"{aoi_name}.shp"



try:
    aoi.to_file(shp_path, driver="ESRI Shapefile")
    print(f' Shapefile export successful: {shp_path}')
except Exception as e:
    raise RuntimeError(f' AOI regions Shapefile failed to export: {e}\n')

# ========== Zipped Shapefile Export =====================================
# All components of the shapefile
aoi_shp_files = list(aoi_out.glob(f"{aoi_name}.*"))


# Choose the zip filename (same stem as shapefile components)
zip_name = aoi_out / f"{aoi_name}.zip"

print("\nZipping AvCan regions shapefiles...")
zip_shapefile_components(aoi_shp_files, zip_name)
print(f" Created archive: {zip_name}")



print("\n")
print("AOI bounds (EPSG:3005):", aoi.total_bounds)
print("AOI bounds (EPSG:4326):", aoi.to_crs(4326).total_bounds)


# ===================================================================
# Py File Complete
# ===================================================================
print('\nPy File Complete.')

