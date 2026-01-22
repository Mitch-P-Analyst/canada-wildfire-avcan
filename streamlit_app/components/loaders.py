# ===================================================================
# Imports
# ===================================================================
import geopandas as gpd
import streamlit as st
from pathlib import Path
import yaml  
from typing import Any, Dict

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parents[1]   # .../streamlit_app

app_data_dir = REPO_ROOT / "data" / "processed" / "app"
app_data_dir.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = APP_DIR / "config"

# ===================================================================
# YAML Configs
# ===================================================================
# @st.cache_data(show_spinner=False)
def load_yaml_config(filename: str) -> Dict[str, Any]:
    """Load a YAML config from streamlit_app/config/ with Streamlit caching."""
    path = CONFIG_DIR / filename
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        return {}
    return data

# Data loading 
# =================================================================

# ========== Integer values =====================================
def fmt_int(n):
    return "—" if n is None else f"{int(n):,}"

# ========== Float values =====================================
def fmt_num(x, decimals=0):
    return "—" if x is None else f"{x:,.{decimals}f}"

# ========== Percent values =====================================
def fmt_pct(x, decimals=1):
    return "—" if x is None else f"{x:.{decimals}%}"

# ========== String values =====================================
def fmt_str(s):
    # Handles None, NaN, and empty/whitespace-only strings
    if s is None:
        return "-"
    try:
        # catches pandas/numpy NaN without importing numpy
        if s != s:
            return "-"
    except Exception:
        pass

    s = str(s).strip()
    return "-" if s == "" else s





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
# Bullet Formatting
# ===================================================================
def _kv(label: str, value: str) -> None:
    st.markdown(f"**{label}:** {value}")

def _bullet_list(items: list[str]) -> None:
    st.markdown("\n".join([f"- {x}" for x in items]))

def _bullet_kv(items: list[tuple[str, str]]) -> None:
    st.markdown("\n".join([f"- **{k}:** {v}" for k, v in items]))


# ===================================================================
# Load App Layers
# ===================================================================
@st.cache_data(show_spinner=False)
def load_app_layers(app_data_dir: Path, fires_mtime: float, patches_mtime: float, regions_mtime: float):
    fires   = gpd.read_parquet(app_data_dir / "Fires.parquet")
    patches = gpd.read_parquet(app_data_dir / "Stage_A2_Burn_Severity_Patches.parquet")
    regions = gpd.read_parquet(app_data_dir / "Regions.parquet")

    fires   = _ensure_wgs84(fires, "Fires")
    patches = _ensure_wgs84(patches, "Stage A patches")
    regions = _ensure_wgs84(regions, "Regions")

    return fires, patches, regions

