# ===================================================================
# Imports
# ===================================================================
import geopandas as gpd
import streamlit as st
from pathlib import Path

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

app_data_dir = REPO_ROOT / "data" / "processed" / "app"
app_data_dir.mkdir(parents=True, exist_ok=True)

# ===================================================================
# Helpers
# ===================================================================
def _ensure_wgs84(gdf: gpd.GeoDataFrame, name: str) -> gpd.GeoDataFrame:
    """Ensure GeoDataFrame is in EPSG:4326 for Folium/Leaflet."""
    if gdf is None or gdf.empty:
        return gdf
    if gdf.crs is None:
        raise ValueError(f"{name}: CRS is missing. App layers must have a defined CRS (expected EPSG:4326).")
    if gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    # drop empty geometries defensively
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    return gdf


# ===================================================================
# Load App Layers
# ===================================================================
@st.cache_data(show_spinner=False)
def load_app_layers(app_data_dir: Path, fires_mtime: float, patches_mtime: float, regions_mtime: float):
    fires   = gpd.read_parquet(app_data_dir / "Fires.parquet")
    patches = gpd.read_parquet(app_data_dir / "Stage_A_Severity_Patches.parquet")
    regions = gpd.read_parquet(app_data_dir / "Regions.parquet")

    fires   = _ensure_wgs84(fires, "Fires")
    patches = _ensure_wgs84(patches, "Stage A patches")
    regions = _ensure_wgs84(regions, "Regions")

    return fires, patches, regions
