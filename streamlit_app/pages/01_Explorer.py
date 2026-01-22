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
    page_title="Avalanche Canada Wildfire Explorer",
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
from components.loaders import load_yaml_config, fmt_int, fmt_num, fmt_pct, fmt_str
from components.map_layers import map_layers_intro

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
# Constants
# ===================================================================
stage_a_cfg = load_yaml_config("stage_a.yaml")
sum_stats = load_yaml_config("summary_stats.yaml")

thresholds = stage_a_cfg.get("thresholds", {}) or {}
calibration = stage_a_cfg.get("calibration", {}) or {}

data = sum_stats.get("data", {}) or {}
nbac = sum_stats.get("nbac", {}) or {}

# Value Extraction 
# =================================================================

# ========== Thresholds =====================================
dnbr_min = thresholds.get("dnbr_min")          # e.g., 0.2
min_patch_area_ha = thresholds.get("min_patch_area_ha") # e.g., 10
dnbr_value = thresholds.get("dnbr_value")
pixel_conn = thresholds.get("connectivity")
scale_value = thresholds.get("scale")

# ========== NBAC Data =====================================
min_year = data.get("min_year")
max_year = data.get("max_year")
avg_fire_count = nbac.get("avg_burn_ha_per_year")
avg_burn_area_ha = nbac.get("avg_burn_ha_per_year")
avg_burn_km = nbac.get("avg_burn_km2_per_year")
total_burn_count = nbac.get("total_fires")
total_burn_ha = nbac.get("total_burn_ha")
total_burn_km = nbac.get("total_burn_km")


# ===================================================================
# Body
# ===================================================================
def mapp_application() -> None:
    st.title("Wildfire Explorer")
   
    st.caption("Note: This Explorer is an informational mapping and analysis tool. The Burn Severity Patches (Stage A) layer is a screening heuristic that highlights candidate areas for follow-on verification (e.g., with current imagery, local knowledge, and appropriate professional guidance). It is not a safety product and must not be used for route selection, terrain selection, or trip planning decisions.")
    st.divider()
    # Load Cached Layers 
    # =================================================================
    fires_path   = app_data_dir / "Fires.parquet"
    patches_path = app_data_dir / "Stage_A2_Burn_Severity_Patches.parquet"
    regions_path = app_data_dir / "Regions.parquet"

    fires, patches, regions = load_app_layers(
        app_data_dir,
        fires_path.stat().st_mtime,
        patches_path.stat().st_mtime,
        regions_path.stat().st_mtime,
    )
    
    # ========== Overview =====================================
    st.markdown("## Overview")
    st.markdown(f"""
    After combining annual NBAC wildfire-perimeter data from {min_year} to {max_year}, summary statistics indicate that Canada recorded {fmt_num(total_burn_count)} fires and {fmt_num(total_burn_ha,2)} hectares burned over this {(max_year - min_year) + 1}-year period, an impact that is difficult to interpret at a national scale.
    
    This Wildfire Explorer improves local interpretability by overlaying NBAC wildfire perimeters onto Avalanche Canada (AvCan) forecast regions within an interactive topographic map. Use the region and year filters to explore where wildfires have occurred across mountainous landscapes and how wildfire presence varies by AvCan region and subregion. The goal is to support clearer communication of wildfire footprint and landscape change over time.
    
                
                """)
    
    # ========== Map Layers =====================================
    map_layers_intro()
    
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

    # Summary Stats 
    # =================================================================
    render_metrics_column(
        region=region,
        fires_f=fires_f,
        patches_f=patches_f,
        show_fires=ui["show_fires"],
        show_patches=ui["show_patches"],
    )
    st.divider()
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
    st.markdown("## Wildfire Explorer")
    st_folium(
        m,
        key="map",
        height=700,
        width=None,
        returned_objects=[],   # critical if your streamlit-folium version supports it
    )



# ===================================================================
# Apply Mapp Application Function
# ===================================================================
mapp_application()
