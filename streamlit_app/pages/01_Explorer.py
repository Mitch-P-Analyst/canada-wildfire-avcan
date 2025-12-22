# streamlit_app/pages/01_Explorer.py

# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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

    # --- Load layers (cached) ---
    fires_path   = app_data_dir / "Fires.parquet"
    patches_path = app_data_dir / "Stage_A_Severity_Patches.parquet"
    regions_path = app_data_dir / "Regions.parquet"

    fires, patches, regions = load_app_layers(
        app_data_dir,
        fires_path.stat().st_mtime,
        patches_path.stat().st_mtime,
        regions_path.stat().st_mtime,
    )

    # --- Region list (prefer regions layer) ---
    regions_sel = sorted(regions["Region"].dropna().unique().tolist()) if "Region" in regions.columns else []
    if not regions_sel:
        regions_sel = sorted(set(fires["Region"].dropna().unique()).union(set(patches["Region"].dropna().unique())))

    # Global year bounds (avoids region-selection circularity)
    y_min, y_max = _safe_year_limits(fires, patches)

    # --- Sidebar controls ---
    ui = sidebar_controls(regions_sel, y_min, y_max)
    region = ui["region"]
    y0, y1 = ui["year_range"]

    # --- Filter to region + year ---
    fires_r = fires[fires["Region"] == region] if "Region" in fires.columns else fires.iloc[0:0]
    patches_r = patches[patches["Region"] == region] if "Region" in patches.columns else patches.iloc[0:0]
    region_f = regions[regions["Region"] == region] if "Region" in regions.columns else regions.iloc[0:0]

    fires_f = fires_r[pd.to_numeric(fires_r["Year"], errors="coerce").between(y0, y1, inclusive="both")].copy() if not fires_r.empty else fires_r
    patches_f = patches_r[pd.to_numeric(patches_r["Year"], errors="coerce").between(y0, y1, inclusive="both")].copy() if not patches_r.empty else patches_r

    # --- Compute region bounds/center for map ---
    if region_f is not None and not region_f.empty:
        minx, miny, maxx, maxy = region_f.total_bounds
        center = ((miny + maxy) / 2.0, (minx + maxx) / 2.0)
        bounds = [minx, miny, maxx, maxy]
    else:
        center = (54.5, -125.0)
        bounds = None

    # --- View state persistence ---
    if "prev_region" not in st.session_state:
        st.session_state.prev_region = None
    if "map_center" not in st.session_state:
        st.session_state.map_center = None
    if "map_zoom" not in st.session_state:
        st.session_state.map_zoom = 11

    region_changed = (st.session_state.prev_region != region)
    st.session_state.prev_region = region

    start_location = st.session_state.map_center if (st.session_state.map_center and not region_changed) else center
    start_zoom = st.session_state.map_zoom if (st.session_state.map_center and not region_changed) else 11

    # Layout: Map + Stats
    col_map, col_stats = st.columns([2.2, 0.8], gap="medium")


    with col_stats:
        # inside your stats column:
        render_metrics_column(
            region=region,
            fires_f=fires_f,
            patches_f=patches_f,
            show_fires=ui["show_fires"],
            show_patches=ui["show_patches"],
        )

    # --- Build the folium map (component) ---
    with col_map:
        m = build_folium_map(
            start_location=start_location,
            start_zoom=start_zoom,
            region_gdf=region_f,
            fires_gdf=fires_f,
            patches_gdf=patches_f,
            show_fires=ui["show_fires"],
            show_patches=ui["show_patches"],
            show_region=ui["show_region"],
            color_fires=ui["color_fires"],
            color_patches=ui["color_patches"],
            bounds=bounds,
            fit_bounds=(bounds is not None and (region_changed or st.session_state.map_center is None)),
        )

        out = st_folium(m, key="map", width=None, height=700)

        # Persist latest pan/zoom
        if out:
            c = out.get("center")
            z = out.get("zoom")
            if isinstance(c, dict) and "lat" in c and "lng" in c:
                st.session_state.map_center = [c["lat"], c["lng"]]
            if isinstance(z, (int, float)):
                st.session_state.map_zoom = int(z)


mapp_application()
