#-- Packages --#

#--- Operational ---#
import os
import sys 
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import json
import re
import zipfile
import shutil

#--- Visualisations ---#
import plotly.express as px
import plotly.graph_objects as go

#-- Directories --#
REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / 'data/'
processed_dir = data_dir / 'processed/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


#-- Helper Functions --#
def extract_max_year(path):
    """
    Identify shapefile with latest year of available data
    """
    years = re.findall(r"\d{4}", path.stem)
    return max(map(int, years)) if years else -1



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


#-- Files --#

# Avalanche Canada polygons (GeoJSON)
print(f'Loading Avalanche Canada (AvCan) regions shapefile...')
avcan_path = REPO_ROOT / "data/external/avalanche_canada/canadian_subregions.geojson"
avcan_shapes = gpd.read_file(avcan_path)
print(f" Avalanche Canada Regions loaded. {avcan_shapes.crs}\n")

# NBAC / BC fire perimeters 
fires_dir = REPO_ROOT / "data/processed/national_canadian_fires"



#-------------------------------------------------#
# If desire manual selection of fires year range, manipulate this comment block

shp_files = list(fires_dir.glob("*.shp"))

if not shp_files:
    raise FileNotFoundError(f"No shapefiles found in {fires_dir}\n")

fires_path = max(shp_files, key=extract_max_year)

# fires_path = fires_dir / "Canada_fires_2009_2024.shp"
#-------------------------------------------------#



print(f"Loading latest Canada fires shapefile... \n File name: {fires_path.name}")
canada_fires = gpd.read_file(fires_path)
print(f" National Canada Fires loaded. {canada_fires.crs}\n")


# Stats Canada Province / Territories boundaries
print(f'Loading Stats Canada Province + Territory boundaries shapefile...')
provinces = gpd.read_file(REPO_ROOT / "data/external/stats_canada/boundaries/lpr_000b21a_e.shp")
print(f" Canadian Province / Territory boundaries loaded. {provinces.crs}\n")



#-- Aggregations --#

# AvCanada Ski Regions
print('Isolate all AvCan regions.')
avcan_cleaning = avcan_shapes.copy()
print('AvCan cleaning...')
colnames = {
    'polygon_name':'subregion',
    'reference_region':'region'
}
avcan_cleaning = avcan_cleaning.rename(columns=colnames)
regions = avcan_cleaning[["region","subregion", "geometry"]]   # adjust column names as needed


print(" Classifying AvCan subregions to Canadian Province / Territory...")

# 1) Project to a projected CRS
regions_proj   = regions.to_crs(3347)
provinces_proj = provinces.to_crs(3347)   # StatsCan is already 3347, but this is safe

# 2) Use centroids for the spatial join
regions_centroids = regions_proj.copy()
regions_centroids["geometry"] = regions_centroids.geometry.centroid

print("  Joining subregion *centroids* to province/territory polygons...")
regions_with_admin = gpd.sjoin(
    regions_centroids,
    provinces_proj[["PRENAME", "geometry"]].rename(columns={"PRENAME": "prov_terr"}),
    how="left",
    predicate="within"
).drop(columns="index_right")

# 3) Restore original subregion polygons as the geometry
regions_with_admin = regions_with_admin.set_geometry(regions_proj.geometry)

print(" Cleaning region and subregion naming structure.")
# Normalize region / subregion names: "South Coast Inland" -> "South_Coast_Inland",
# "North-Coast" -> "North_Coast", etc.
for col in ["region", "subregion"]:
    regions_with_admin[col] = (
        regions_with_admin[col]
        .astype(str)                      # just in case
        .str.strip()                      # remove leading/trailing spaces
        .str.replace(r"[ \-]+", "_", regex=True)  # spaces or '-' -> '_'
    )


# 4) Make this your cleaned AvCan layer
avcan_clean = regions_with_admin[["region", "subregion", "prov_terr", "geometry"]].copy()



print("AvCan regions cleaned.")

missing = avcan_clean[avcan_clean["prov_terr"].isna()][["region", "subregion"]]
if missing.empty:
    print(" All subregions have a province/territory.")
else:
    print(" Subregions with no province/territory match:\n", missing)



print('\nOverlaying Canadian fires with respective AvCan subregions..')
# 1) Make sure both layers share the same projected CRS
analysis_crs = regions_with_admin.crs  # this should be EPSG:3347

if canada_fires.crs != analysis_crs:
    canada_fires = canada_fires.to_crs(analysis_crs)
    
print(f' NBAC fires CRS: {canada_fires.crs}')
print(f' AvCan regions CRS: {regions_with_admin.crs}')

# Optional: drop with errors="ignore" in case prov_terr isn't there
canada_fires = canada_fires.drop(columns="prov_terr", errors="ignore")

# Overlay BcFires to respective AvCanada Ski Regions
print(' Splitting fires across AvCan subregions...')
fire_stats = gpd.overlay(
    canada_fires,
    regions_with_admin,
    how="intersection"   # intersection of fire and region polygons. Cutting fires by region borders
)
print(f' Overlay complete.')


# fire_stats is already projected => no need for extra CRS logic
print(f"""Convert fires_region variable CRS type to projected coordinates.
    Projected CRS type: {fire_stats.crs} (metres)
    Projected CRS name: {fire_stats.crs.name}\n
""")


print('Calculating area burned (ha) for each AvCan subregion split fire.')
# Create hectare area for each AvCanada Ski Region
fire_stats["subreg_ha"] = fire_stats.geometry.area / 10_000
fire_stats = fire_stats.rename(columns={'adj_ha':'tot_adj_ha'})
print(f' Individual fire per region burn = fire.geometry.area / 10_000 = "subreg_ha')

print(f' NBAC Total Region adjusted burn = "tot_adj_ha"\n')

print(f'Individual Fire Statistics DF complete. \n')



#--- AvCan Fires Exports ---#
print(f'Beginning Export procedure.')

# Identify year range (cast to int to avoid "2014.0")
AvCan_fires_year_min = int(fire_stats['year'].min())
AvCan_fires_year_max = int(fire_stats['year'].max())


# Output folder
out_dir = processed_dir / 'avalanche_canada_fires/'
shapefiles_out_dir = processed_dir / 'avalanche_canada_fires/shapefiles/'
out_dir.mkdir(parents=True, exist_ok=True)

#---- AvCan Fires Export -----#

# ---- GeoJSON export ---- #
AvCan_fires_path_geojson = out_dir / f"AvCan_fires_{AvCan_fires_year_min}_{AvCan_fires_year_max}.geojson"
print('Exporting AvCan fires GeoJSON...')

try:
    fire_stats.to_file(AvCan_fires_path_geojson, driver="GeoJSON")
    print(f'AvCan GeoJSON export successful: {AvCan_fires_path_geojson}')
except Exception as e:
    raise RuntimeError(f'AvCan fires GeoJSON failed to export: {e}')

# ---- Shapefile export ---- #
AvCan_fires_path_shp = shapefiles_out_dir / f"AvCan_fires_{AvCan_fires_year_min}_{AvCan_fires_year_max}.shp"
print('Exporting AvCan fires Shapefile...')

try:
    fire_stats.to_file(AvCan_fires_path_shp, driver="ESRI Shapefile")
    print(f'Shapefile export successful: {AvCan_fires_path_shp}')
except Exception as e:
    raise RuntimeError(f'AvCan fires Shapefile failed to export: {e}\n')

# ---- Zipped Shapefile export ---- #

# All components of the shapefile
output_shp_files = list(shapefiles_out_dir.glob(f"AvCan_fires_{AvCan_fires_year_min}_{AvCan_fires_year_max}.*"))


# Choose the zip filename (same stem as shapefile components)
zip_name = shapefiles_out_dir / f"AvCan_fires_{AvCan_fires_year_min}_{AvCan_fires_year_max}.zip"

print("Zipping AvCan shapefiles...")
zip_shapefile_components(output_shp_files, zip_name)
print(f"Created archive: {zip_name}")


#--- AvCan Regions Export ---#

# ---- GeoJSON export ---- #
AvCan_regions_path_geojson = out_dir / f"AvCan_cleaned_subregions.geojson"
print('Exporting AvCan subregions GeoJSON...')

try:
    avcan_clean.to_file(AvCan_regions_path_geojson, driver="GeoJSON")
    print(f'AvCan cleaned subregions GeoJSON export successful: {AvCan_regions_path_geojson}')
except Exception as e:
    raise RuntimeError(f'AvCan cleaned subregions GeoJSON failed to export: {e}')


print('\nPy file complete.')
