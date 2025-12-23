# ===================================================================
# Avalanche Canada Fire Data to Streamlit App Layers
# ===================================================================
 
# This notebook proceeds after using Google Earth Engine to assess Stage A Severity Patches ( + Stage B Vegetation Regrowth) within AvCan Fires. 
# 

# ===================================================================
# Imports
# ===================================================================

# Operation Packages 
# =================================================================
import os
import sys 
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import json
import re
import geopandas as gpd
import folium

# Visualisation Packages 
# =================================================================
import plotly.express as px
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from shapely.geometry import Point

# ===================================================================
# Directories 
# ===================================================================

nb_dir = Path.cwd()
REPO_ROOT = nb_dir.parent
data_dir = REPO_ROOT / 'data/'
docs_dir = REPO_ROOT / 'docs/'
processed_dir = data_dir / 'processed' / 'analysis/'
app_data_dir = data_dir / 'processed' / 'app/'
share_data_dir = data_dir / 'processed' / 'share/'


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ===================================================================
# Helper Functions
# ===================================================================

def round_numeric_columns(df, decimals=2):
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].round(decimals)
    return df



# ===================================================================
# Load Data
# ===================================================================

print(f'Loading Stage A Severity Patches shapefiles...')
stage_A_shp = processed_dir / 'stage_A/AvCan_Stage_A/AvCan_Stage_A_all_regions_SHP.shp'
stage_A_polys = gpd.read_file(stage_A_shp)
print(f' Stage A Severity patches loaded. {stage_A_polys.crs}\n')

print(f'Loading all AvCan fires shapefile...')
avcan_fires_file = processed_dir / 'avalanche_canada_fires/shapefiles/AvCan_fires_1990_2024.shp'
avcan_fires = gpd.read_file(avcan_fires_file)
print(f' AvCan fires loaded. {avcan_fires.crs}\n')


print(f'Loading AvCan regions shapefile...')
avcan_path = processed_dir / "avalanche_canada_fires/AvCan_cleaned_subregions.geojson"
avcan_regions= gpd.read_file(avcan_path)
print(f" AvCan Regions loaded. {avcan_regions.crs}\n")


# Masking
# =================================================================
print('Identify AvCan regions + years of interest from Earth Engine analysis.')

# ========== Creation =====================================

# ======= Regions =======#
subregions = list(stage_A_polys['subregion'].unique())
regions = list(stage_A_polys['region'].unique())

# ======= Year Ranges =======#
min_year = int(stage_A_polys["year"].min())
max_year = int(stage_A_polys["year"].max())


# ========== Applying =====================================
print('Filter by Masks.')

# ======= AvCan Regions =======#
avcan_reg_sel = avcan_regions[avcan_regions["region"].isin(regions)]

# 3. Make sure CRS match 
if avcan_reg_sel.crs != stage_A_polys.crs:
    severe_burn = stage_A_polys.to_crs(avcan_reg_sel.crs)

# ======= AvCan Fires =======#

# ==== Years Mask ====#
mask_year = avcan_fires["year"].between(min_year, max_year, inclusive="both")   # Min + Max year of Stage A Polygons

# ==== Regions Mask ====#
mask_region = avcan_fires["region"].isin(regions)    # Regions from Stage A Severity Patch Fires

# ==== Apply Masks ====#
avcan_fires_sel = avcan_fires[mask_region & mask_year]



# Dataframe Cleaning 
# =================================================================
print('Clean columns for visualisation.')

# ========== Columns =====================================

RENAME_MAP = {
    # Shared Dfs
    'year':'Year',
    'region':'Region',
    'subregion':'Subregion',

    # AvCan Fires
    'tot_adj_ha':'Total Adjusted Area (ha)',
    'gid':'Unique Fire ID (gid)',
    'fireid':'FireID',
    'cause':'Cause',
    'subreg_ha':'Subregion Area (ha)',
    'prov_terr': 'Province/Territory',

    # Stage A Burns
    'slp_mn_pct' : 'Slope Mean Percentage',
    'natpark': 'National Park',
    'gid': 'Unique Fire ID (gid)',
    'aspect_car' : 'Majority Cardinal Direction',
    'patch_id': 'Patch ID',
    'patch_area': 'Patch Area (ha)' , 
    'elev_min_m' : 'Min Elevation (m)',
    'subregion': 'Subregion',
    'elev_mean_' : 'Mean Elevation (m)',
    'aspect_mea': 'figure this out',
    'region':'Region',
    'elev_max_m': 'Max Elevation (m)',
    'slp_mn_deg' : 'Mean Slope Degree',

}

# ======= Apply Renaming =======#
avcan_fires_sel = avcan_fires_sel.rename(columns=RENAME_MAP)
stage_A_polys = stage_A_polys.rename(columns=RENAME_MAP)
avcan_reg_sel = avcan_reg_sel.rename(columns=RENAME_MAP)
print(' Renamed.')
# ======= Round Numeric Columns =======#
avcan_fires_sel = round_numeric_columns(avcan_fires_sel, 2)
stage_A_polys = round_numeric_columns(stage_A_polys, 2)
avcan_reg_sel = round_numeric_columns(avcan_reg_sel, 2)
print(' Numeric Rounding.')


# ========== CRS =====================================
# Make WGS84 (lat/lon) copies of fires for mapping

print('CRS Mapping.')

# Avcan Fires
avcan_fires_sel_ll = avcan_fires_sel.to_crs(epsg=4326)   
print(" AvCan Fires CRS for mapping:", avcan_fires_sel_ll.crs)

# Stage A Severity Patches
stage_A_polys_ll = stage_A_polys.to_crs(epsg=4326)  
print(" Stage A Severity Patches CRS for mapping:", stage_A_polys_ll.crs)

# AvCan Regions
avcan_reg_sel_ll = avcan_reg_sel.to_crs(epsg=4326)   
print(" AvCan Regions CRS for mapping:", avcan_reg_sel_ll.crs)


# ===================================================================
# GeoPandas Explore Map for Docs
# ===================================================================

centroid = stage_A_polys_ll.iloc[0].geometry.centroid
center = [centroid.y, centroid.x]   # [lat, lon]

m = avcan_reg_sel_ll.explore(
    tiles="OpenTopoMap",  # or "OpenStreetMap", "Stamen Terrain", ...
    style_kwds=dict(color="black", weight=2, fill=False),
    name="AvCan Regions",
    location=center,   # <- initial centre
    zoom_start=14,     # <- tweak until it feels right
    width=900,
    height=600,
)

fire_cols = ["Region","Subregion","Unique Fire ID (gid)","Year","Total Adjusted Area (ha)"]

avcan_fires_sel_ll.explore(
    m=m,
    color="orange",
    name="Fire Polygon",
    tooltip=fire_cols,
    popup=fire_cols
)

stage_A_cols = ["Region","Subregion","Unique Fire ID (gid)", "Patch ID", "Year", "Majority Cardinal Direction","Patch Area (ha)", "Mean Elevation (m)","Mean Slope Degree"]  # whatever you want visible
stage_A_polys_ll.explore(
    m=m,
    color="red",
    name="Stage A burn patches",
    tooltip=stage_A_cols,   # shown on hover
    popup=stage_A_cols      # shown on click
    
)
page_title = "Stage A Severity Patches"

m.get_root().html.add_child(
    folium.Element(f"<title>{page_title}</title>")
)

m.save(REPO_ROOT / f"docs/Stage_A_Zone_Severity.html")


# ===================================================================
# PY File Summary
# ===================================================================


sel_regions = stage_A_polys_ll['Region'].unique()

print(f"\nBelow is the number of polygons for each layer for the assessed AvCan regions: {sel_regions}")

print(f" Number of Fires across years {avcan_fires_sel_ll['Year'].min()} - {avcan_fires_sel_ll['Year'].max()}: {avcan_fires_sel_ll.shape[0]} ")
print(f" Number of Stage A Severity Patches across years {stage_A_polys_ll['Year'].min()} - {stage_A_polys_ll['Year'].max()}: {stage_A_polys_ll.shape[0]}")


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
    stage_A_polys_ll.to_file(gpkg_path, layer="patches_stage_a", driver="GPKG")
    avcan_reg_sel_ll.to_file(gpkg_path, layer="regions", driver="GPKG")
    print(f' GeoPackage export successful: {gpkg_path}')
except Exception as e:
    raise RuntimeError(f'GeoPackage failed to export: {e}')


# GeoParaquet
# =================================================================

print(f"\nExporting GeoParaquet")

# ======= Stage A Severity Patches =======#

patches_path_paraquet = app_data_dir / 'Stage_A_Severity_Patches.parquet'
try:
    stage_A_polys_ll.to_parquet(patches_path_paraquet, index=False, compression="zstd")
    print(f'Stage A Severity Patches Paraquet file export successful: {patches_path_paraquet}')
except Exception as e:
    raise RuntimeError(f'Stage A Severity Patches Paraquet file failed to export: {e}')

# ======= AvCan Fires =======#
fires_path_paraquet = app_data_dir / 'Fires.parquet'

try:
    avcan_fires_sel_ll.to_parquet(fires_path_paraquet, index=False, compression="zstd")
    print(f'AvCan Fires Paraquet file export successful: {fires_path_paraquet}')
except Exception as e:
    raise RuntimeError(f'AvCan Fires Paraquet file failed to export: {e}')

# ======= AvCan Regions =======#
avcan_regions_paraquet = app_data_dir / "Regions.parquet"

try:
    avcan_reg_sel_ll.to_parquet(avcan_regions_paraquet, index=False, compression="zstd")
    print(f'AvCan Regions Paraquet file export successful: {avcan_regions_paraquet}')
except Exception as e:
    raise RuntimeError(f'AvCan Regions Paraquet file failed to export: {e}')


print(f"\nPy File complete.")


