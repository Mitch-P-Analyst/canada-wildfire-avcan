# ===================================================================
# Avalanche Canada Fire Data to Streamlit App Layers
# ===================================================================
 
# This notebook proceeds after using Google Earth Engine to assess Stage A Burn Severity Patches ( + Stage B Vegetation Regrowth) within AvCan Fires. 
# 

# ===================================================================
# Imports
# ===================================================================

# Operation Packages 
# =================================================================

import sys 
import pandas as pd
import geopandas as gpd
from pathlib import Path

import folium
# Visualisation Packages 
# =================================================================
# import plotly.express as px
# import plotly.graph_objects as go
# import matplotlib.pyplot as plt
# from shapely.geometry import Point

# ===================================================================
# Directories 
# ===================================================================

script_path = Path(__file__).resolve()
REPO_ROOT = script_path.parents[1]
data_dir = REPO_ROOT / 'data/'
docs_dir = REPO_ROOT / 'docs/'
raw_dir = data_dir / "raw"
analysis_dir = data_dir / 'processed' / 'analysis/'
stage_a2_dir = analysis_dir / "stage_A/stage_A2"
app_data_dir = data_dir / 'processed' / 'app/'
share_data_dir = data_dir / 'processed' / 'share/'


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

app_data_dir.mkdir(parents=True, exist_ok=True)
share_data_dir.mkdir(parents=True, exist_ok=True)
docs_dir.mkdir(parents=True, exist_ok=True)
# ===================================================================
# Helper Functions
# ===================================================================

def round_numeric_columns(df, decimals=2, exclude=None):
    exclude = set(exclude or [])
    num_cols = [c for c in df.select_dtypes(include="number").columns if c not in exclude]
    df[num_cols] = df[num_cols].round(decimals)
    return df







# ===================================================================
# Load Data
# ===================================================================

# Stage A Burn Severity Patches
# =================================================================


geojson_files = sorted(stage_a2_dir.glob("*.geojson"))
if not geojson_files:
    raise FileNotFoundError(f"No .geojson files found in: {stage_a2_dir}")

print(f"Loading {len(geojson_files)} Stage_A2 GeoJSON batch files...")

gdfs = []
for fp in geojson_files:
    gdf = gpd.read_file(fp)
    gdfs.append(gdf)

stage_A_polys = gpd.GeoDataFrame(
    pd.concat(gdfs, ignore_index=True),
    crs=gdfs[0].crs
)

print(f" Merged Stage_A patches: {stage_A_polys.shape} ")
print(f' Stage A Burn Severity patches loaded. CRS: {stage_A_polys.crs}\n')


# Safer de-dup: patch_id alone may not be globally unique
dedup_cols = [c for c in ["patch_id", "gid", "year"] if c in stage_A_polys.columns]
before = len(stage_A_polys)
stage_A_polys = stage_A_polys.drop_duplicates(subset=dedup_cols)
print(f"De-duped by {dedup_cols}: {before} -> {len(stage_A_polys)}")


# AvCan Fires 
# =================================================================

print(f'Loading all AvCan fires shapefile...')
avcan_fires_file = analysis_dir / 'avalanche_canada/fires/AvCan_fires_1990_2024.shp'

avcan_fires = gpd.read_file(avcan_fires_file)
print(f' AvCan fires loaded. CRS: {avcan_fires.crs}\n')

# AvCan Regions 
# =================================================================

print(f'Loading AvCan regions shapefile...')
avcan_path = analysis_dir / "avalanche_canada/regions/AvCan_cleaned_subregions.geojson"
avcan_regions= gpd.read_file(avcan_path)
print(f" AvCan Regions loaded. CRS: {avcan_regions.crs}\n")



# Dataframe Cleaning 
# =================================================================
print('Clean columns for visualisation.')

# ========== Columns =====================================

# ======= Drop Cols =======#
DROP_COLS_STAGE_A2 = [
    # aspect intermediate bands/stat outputs
    "asp_cos_max", "asp_cos_mean", "asp_cos_min", "asp_cos_stdDev",
    "asp_sin_max", "asp_sin_mean", "asp_sin_min", "asp_sin_stdDev",

    # redundant elevation stats (keep *_m fields)
    "elev_min", "elev_mean", "elev_max", "elev_stdDev",

    # redundant slope stats (keep slp_mn_deg / slp_std_dg / slp_mn_pct)
    "slp_min", "slp_mean", "slp_max", "slp_stdDev",
]

stage_A_polys = stage_A_polys.drop(columns=[c for c in DROP_COLS_STAGE_A2 if c in stage_A_polys.columns])

# ======= Rename Cols =======#
RENAME_MAP = {
    # Shared / join keys
    "year": "Year",
    "region": "Region",
    "subregion": "Subregion",

    # IDs
    "gid": "Unique Fire ID (gid)",
    "fireid": "FireID",
    "patch_id": "Patch ID",
    

    # Fire attributes (from avcan_fires)
    "tot_adj_ha": "Total Adjusted Area (ha)",
    "cause": "Cause",
    "subreg_ha": "Subregion Area (ha)",
    "prov_terr": "Province/Territory",

    # Stage A2 patch attributes
    "natpark": "National Park",
    "scenario": "Scenario",
    "id": "ee_feature_id",

    "patch_area_ha": "Patch Area (ha)",
    "patch_area_m2": "Patch Area (m2)",

    "elev_min_m": "Min Elevation (m)",
    "elev_mean_m": "Mean Elevation (m)",
    "elev_max_m": "Max Elevation (m)",
    "elev_relief_m": "Elevation Relief (m)",

    "slp_mn_deg": "Mean Slope Degree",
    "slp_std_dg": "Slope Std Dev (deg)",
    "slp_mn_pct": "Slope Mean Percentage",

    "aspect_mean_deg": "Aspect Mean (deg)",
    "aspect_R": "Aspect Coherence (R)",
    "aspect_cardinal_mean": "Majority Cardinal Direction",
    "aspect_label": "Aspect Label",
}


# ======= Apply Renaming =======#
avcan_fires = avcan_fires.rename(columns=RENAME_MAP)
stage_A_polys = stage_A_polys.rename(columns=RENAME_MAP)
avcan_regions = avcan_regions.rename(columns=RENAME_MAP)
print(' Renamed.')
# ======= Round Numeric Columns =======#
avcan_fires = round_numeric_columns(avcan_fires, 2, exclude=["FireID","Unique Fire ID (gid)","Patch ID"])
stage_A_polys = round_numeric_columns(stage_A_polys, 2, exclude=["FireID","Unique Fire ID (gid)","Patch ID"])
avcan_regions = round_numeric_columns(avcan_regions, 2, exclude=["FireID","Unique Fire ID (gid)","Patch ID"])
print(' Numeric Rounding.')

# ======= Stage A Unique IDs =======#
stage_A_polys["Patch_Unique_Id"] = (
    stage_A_polys["Unique Fire ID (gid)"].astype(str) + "_" +
    stage_A_polys["Patch ID"].astype(str)
)
print(' Unique ID computed')


# Masking
# =================================================================
print('Identify AvCan regions + years of interest from Earth Engine analysis.')

# ========== Creation =====================================

# ======= Regions =======#
regions = sorted(stage_A_polys["Region"].dropna().unique().tolist())
subregions = sorted(stage_A_polys["Subregion"].dropna().unique().tolist())

# ======= Year Ranges =======#
min_year = int(stage_A_polys["Year"].min())
max_year = int(stage_A_polys["Year"].max())

stage_A_polys = stage_A_polys[
    stage_A_polys["Region"].isin(regions) &
    stage_A_polys["Year"].between(min_year, max_year, inclusive="both")
].copy()



# ========== Applying =====================================
print('Filter by Masks.')

# ======= AvCan Regions =======#
avcan_reg_sel = avcan_regions[avcan_regions["Region"].isin(regions)].copy()

# CRS alignment (only if both have CRS)
if stage_A_polys.crs is None:
    raise ValueError("Stage_A2 GeoJSONs have no CRS. Set it before reprojecting.")
if avcan_reg_sel.crs is not None and avcan_reg_sel.crs != stage_A_polys.crs:
    stage_A_polys = stage_A_polys.to_crs(avcan_reg_sel.crs)

# ======= AvCan Fires =======#

# ==== Years Mask ====#
mask_year = avcan_fires["Year"].between(min_year, max_year, inclusive="both")   # Min + Max year of Stage A Polygons

# ==== Regions Mask ====#
mask_region = avcan_fires["Region"].isin(regions)    # Regions from Stage A Severity Patch Fires

# ==== Apply Masks ====#
avcan_fires_sel = avcan_fires[mask_region & mask_year].copy()



# ========== CRS =====================================
# Make WGS84 (lat/lon) copies of fires for mapping

print('CRS Mapping.')

# Avcan Fires
avcan_fires_sel_ll = avcan_fires_sel.to_crs(epsg=4326)   
print(" AvCan Fires CRS for mapping:", avcan_fires_sel_ll.crs)

# Stage A2 Burn Severity Patches
stage_A_polys_ll = stage_A_polys.to_crs(epsg=4326)  
print(" Stage A2 Severity Patches CRS for mapping:", stage_A_polys_ll.crs)

# AvCan Regions
avcan_reg_sel_ll = avcan_reg_sel.to_crs(epsg=4326)   
print(" AvCan Regions CRS for mapping:", avcan_reg_sel_ll.crs)


# ===================================================================
# GeoPandas Explore Map for Docs
# ===================================================================
if stage_A_polys_ll.empty:
    raise RuntimeError("stage_A_polys_ll is empty; cannot create map.")
centroid = stage_A_polys_ll.iloc[0].geometry.centroid
center = [centroid.y, centroid.x]   # [lat, lon]


fire_cols = ["Region", "Subregion", "Unique Fire ID (gid)", "Year", "Total Adjusted Area (ha)"]
stage_A_cols = [
    "Region", "Subregion", "Unique Fire ID (gid)", "Patch ID", "Year",
    "Majority Cardinal Direction", "Aspect Coherence (R)",
    "Patch Area (ha)", "Mean Elevation (m)", "Mean Slope Degree"
]

fire_cols = [c for c in fire_cols if c in avcan_fires_sel_ll.columns]
stage_A_cols = [c for c in stage_A_cols if c in stage_A_polys_ll.columns]

m = avcan_reg_sel_ll.explore(
    tiles="OpenTopoMap",  # or "OpenStreetMap", "Stamen Terrain", ...
    style_kwds=dict(color="black", weight=2, fill=False),
    name="AvCan Regions",
    location=center,   # <- initial centre
    zoom_start=14,     # <- tweak until it feels right
    width=900,
    height=600,
)



avcan_fires_sel_ll.explore(
    m=m,
    color="orange",
    name="Fire Polygon",
    tooltip=fire_cols,
    popup=fire_cols
)



stage_A_polys_ll.explore(
    m=m,
    color="red",
    name="Stage A Burn Severity Patches",
    tooltip=stage_A_cols,   # shown on hover
    popup=stage_A_cols      # shown on click
    
)
page_title = "Stage A2 Burn Severity Patches"

m.get_root().html.add_child(
    folium.Element(f"<title>{page_title}</title>")
)

m.save(docs_dir / "Stage_A2_Burn_Severity_Patches.html")


# ===================================================================
# PY File Summary
# ===================================================================


# ===================================================================
# Export App Layers
# ===================================================================

print('\nExport App Layers.\n')

# Export to GeoPackage
# =================================================================
# Driver='GPKG'

print('Exporting Singular GeoPackage File...')

gpkg_path = share_data_dir / "avcan_layers.gpkg"
try:
    avcan_fires_sel_ll.to_file(gpkg_path, layer="fires", driver="GPKG")
    stage_A_polys_ll.to_file(gpkg_path, layer="patches_stage_a2", driver="GPKG")
    avcan_reg_sel_ll.to_file(gpkg_path, layer="regions", driver="GPKG")
    print(f' GeoPackage export successful: {gpkg_path}')
except Exception as e:
    raise RuntimeError(f'GeoPackage failed to export: {e}')


# GeoParquet
# =================================================================

print(f"\nExporting GeoParquet")

# ======= Stage A Burn Severity Patches =======#

patches_path_parquet = app_data_dir / 'Stage_A2_Burn_Severity_Patches.parquet'
try:
    stage_A_polys_ll.to_parquet(patches_path_parquet, index=False, compression="zstd")
    print(f'Stage A2 Burn Severity Patches parquet file export successful: {patches_path_parquet}')
except Exception as e:
    raise RuntimeError(f'Stage A2 Burn Severity Patches parquet file failed to export: {e}')

# ======= AvCan Fires =======#
fires_path_parquet = app_data_dir / 'Fires.parquet'

try:
    avcan_fires_sel_ll.to_parquet(fires_path_parquet, index=False, compression="zstd")
    print(f'AvCan Fires parquet file export successful: {fires_path_parquet}')
except Exception as e:
    raise RuntimeError(f'AvCan Fires parquet file failed to export: {e}')

# ======= AvCan Regions =======#
avcan_regions_parquet = app_data_dir / "Regions.parquet"

try:
    avcan_reg_sel_ll.to_parquet(avcan_regions_parquet, index=False, compression="zstd")
    print(f'AvCan Regions parquet file export successful: {avcan_regions_parquet}')
except Exception as e:
    raise RuntimeError(f'AvCan Regions parquet file failed to export: {e}')


print(f"\nPy File complete.")


