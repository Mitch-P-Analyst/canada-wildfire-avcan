# streamlit_app/pages/01_Explorer.py

# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import yaml

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AvCan Wildfire Explorer",
    page_icon="🔥",
    layout="wide"
)

# ===================================================================
# Components
# ===================================================================
from components.loaders import load_app_layers, app_data_dir
from components.sidebar import sidebar_controls
from components.folium_map import build_folium_map
from components.metrics import render_metrics_column

# ===================================================================
# Helper Functions
# ===================================================================
def _safe_year_limits(fires_df, patches_df):
    years = []
    if fires_df is not None and not fires_df.empty and "Year" in fires_df.columns:
        y = pd.to_numeric(fires_df["Year"], errors="coerce").dropna()
        if not y.empty:
            years.append((int(y.min()), int(y.max())))
    if patches_df is not None and not patches_df.empty and "Year" in patches_df.columns:
        y = pd.to_numeric(patches_df["Year"], errors="coerce").dropna()
        if not y.empty:
            years.append((int(y.min()), int(y.max())))
    if not years:
        return 1990, 2024
    return min(a for a, _ in years), max(b for _, b in years)


# ===================================================================
# Body
# ===================================================================
def mapp_application() -> None:
    st.title("AvCan Wildfire Severity Explorer")
    st.caption("Interactive map of wildfire perimeters and Stage A burn-severity patches within Avalanche Canada regions.")
    st.divider()
    # Load Cached Layers 
    # =================================================================
    fires_path   = app_data_dir / "Fires.parquet"
    patches_path = app_data_dir / "Stage_A_Severity_Patches.parquet"
    regions_path = app_data_dir / "Regions.parquet"

    fires, patches, regions = load_app_layers(
        app_data_dir,
        fires_path.stat().st_mtime,
        patches_path.stat().st_mtime,
        regions_path.stat().st_mtime,
    )
    
    # Instructions 
    # =================================================================
    st.markdown("## Instructions")
    st.markdown("Below is a topographical map exploring wildfires within Avalanche Canada forecast regions. " \
    "This map aims to illustrate not only the wildfires within recreational backcountry areas, but communicate identifed areas that meet conditions for favourable **winter recreation (skiing, snowmobiling, etc) as a result of wildfire impact." \
    "" \
    "**Controls**" \
    "The user-interface on the left-portion of this application includes filters and customise legends to observed wildfires. Modify layer appearances and visibility to navigate the map.")
    
    st.divider()

    # Filters
    # =================================================================

    # ========== Region =====================================
    regions_sel = sorted(regions["Region"].dropna().unique().tolist()) if "Region" in regions.columns else []
    if not regions_sel:
        regions_sel = sorted(set(fires["Region"].dropna().unique()).union(set(patches["Region"].dropna().unique())))

    # ========== Year Range =====================================
    y_min, y_max = _safe_year_limits(fires, patches)

    # ========== Sidebar Controls =====================================    
    ui = sidebar_controls(regions_sel, y_min, y_max)
    region = ui["region"]
    y0, y1 = ui["year_range"]

    # ========== Apply Filters =====================================
    fires_r = fires[fires["Region"] == region] if "Region" in fires.columns else fires.iloc[0:0]
    patches_r = patches[patches["Region"] == region] if "Region" in patches.columns else patches.iloc[0:0]
    region_f = regions[regions["Region"] == region] if "Region" in regions.columns else regions.iloc[0:0]

    fires_f = fires_r[pd.to_numeric(fires_r["Year"], errors="coerce").between(y0, y1, inclusive="both")].copy() if not fires_r.empty else fires_r
    patches_f = patches_r[pd.to_numeric(patches_r["Year"], errors="coerce").between(y0, y1, inclusive="both")].copy() if not patches_r.empty else patches_r
    
    # Bounds 
    # =================================================================
    if region_f is not None and not region_f.empty:
        minx, miny, maxx, maxy = region_f.total_bounds
        center = ((miny + maxy) / 2.0, (minx + maxx) / 2.0)
        bounds = [minx, miny, maxx, maxy]
    else:
        center = (54.5, -125.0)
        bounds = None

    st.session_state.setdefault("prev_region", None)
    region_changed = (st.session_state.prev_region != region)
    st.session_state.prev_region = region

    # Map Building
    # =================================================================    
    m = build_folium_map(
        start_location=center,
        start_zoom=11,
        region_gdf=region_f,
        fires_gdf=fires_f,
        patches_gdf=patches_f,
        show_fires=ui["show_fires"],
        show_patches=ui["show_patches"],
        show_region=ui["show_region"],
        color_fires=ui["color_fires"],
        color_patches=ui["color_patches"],
        bounds=bounds,
        fit_bounds=(bounds is not None and region_changed),
    )

    # ========== Apply Map =====================================
    st_folium(
        m,
        key="map",
        height=700,
        width=None,
        returned_objects=[],   # critical if your streamlit-folium version supports it
    )

    # Summary Stats 
    # =================================================================
    render_metrics_column(
        region=region,
        fires_f=fires_f,
        patches_f=patches_f,
        show_fires=ui["show_fires"],
        show_patches=ui["show_patches"],
    )


# ===================================================================
# Apply Mapp Application Function
# ===================================================================
mapp_application()
