# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd

from .loaders import _kv , _bullet_list, _bullet_kv
from .loaders import load_yaml_config
from .loaders import fmt_int, fmt_num, fmt_pct, fmt_str


def _card():
    """Bordered card if supported; fallback otherwise."""
    try:
        return st.container(border=True)  # Streamlit newer versions
    except TypeError:
        return st.container()


# ===================================================================
# Map Layers Function
# ===================================================================
def map_layers_intro(
) -> None:

    # Constants 
    # =================================================================


    stage_a_cfg = load_yaml_config("stage_a.yaml")
    sum_stats = load_yaml_config("summary_stats.yaml")

    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    data = sum_stats.get("data", {}) or {}
    nbac = sum_stats.get("nbac", {}) or {}

    # ========== Value Extraction =====================================
    
    # ======= Thresholds =======#
    
    dnbr_min = thresholds.get("dnbr_min")          # e.g., 0.2
    min_patch_area_ha = thresholds.get("min_patch_area_ha") # e.g., 10
    dnbr_value = thresholds.get("dnbr_value")
    pixel_conn = thresholds.get("connectivity")
    scale_value = thresholds.get("scale")
    aspect_label = thresholds.get("aspect_label")

    # ========== NBAC Data =====================================
    min_year = data.get("min_year")
    max_year = data.get("max_year")
    avg_fire_count = nbac.get("avg_burn_ha_per_year")
    avg_burn_area_ha = nbac.get("avg_burn_ha_per_year")
    avg_burn_km = nbac.get("avg_burn_km2_per_year")
    total_burn_count = nbac.get("total_fires")
    total_burn_ha = nbac.get("total_burn_ha")
    total_burn_km = nbac.get("total_burn_km")

    # Header 
    # =================================================================
    st.markdown("### Map Layers")
    st.caption("All map layers, filters, and legend settings are available in the **left sidebar**.")

    # Regions 
    # =================================================================
    
    with st.expander("##### AvCan Region Perimeter", expanded=False):
        st.markdown(f"""
        All map layers shown below are filtered to the selected **AvCan forecasting region**. Use the **Region selector** in the sidebar to switch regions and explore nearby fires.
                    
        The AvCan Region Perimeter is indicated by a **thick black line**, representing the boundary used to filter displayed features.
                    
        Summary statistics update automatically based on the selected **region, year range, and enabled layers**.
                """)
        
    with st.expander("##### Fire Perimeters", expanded=False):
        st.markdown(f"""
        NBAC fires within the selected AvCan region are visualised with a default <span style='color:#F700FF;'>Pink Colour.</span> This colour can be changed in the **Legends** section of the sidebar. 
                    
        Use the **Year range** filter to adjust which fires are displayed and to update regional summary statistics for the selected period.
        
        Each fire perimeter includes the following metadata:
        """
        , unsafe_allow_html=True)
        fire_perim_list = [
        ("Region","The AvCan region the fire boundary resides in."),
        ("Subregion","The AvCan's subregion the fire boundary resides in."),
        ("Year", "The year the fire occurred."),
        ("Unique Fire ID (gid)","NBAC's assigned unique identification number"),
        ("Total Adjusted Area (ha)","NBAC’s calculated burned area (hectares).")
        ]
        _bullet_kv(fire_perim_list)
 
        
    with st.expander("##### Burn Severity Patches (Stage A)", expanded=False):
        st.markdown(f"""
        Stage A of this AvCan Wildfire Explorer computes custom, derived **Burn Severity Patches** within NBAC fire perimeters. These patches are visualised in an seperate map layer with default <span style='color:#ff5a00;'>Orange Colour</span> perimeters. This colour can be changed in the **Legends** section of the sidebar.
                    
        Burn severity patches represent post-fire areas that meet this project’s criteria as potential candidates for winter recreation (e.g., skiing, snowboarding, snowmobiling), sometimes referred to as “burnt tree zones.” This is intended as an exploratory layer to help highlight terrain for recreational use, not as an official Avalanche Canada product. For information on this layer's computation, refer to the **Method** page. 
        
        Each burn severity patch perimeter includes the following metadata:
        """, 
        unsafe_allow_html=True)
        patches_list = [
        ("Region","The AvCan region the fire boundary resides in."),
        ("Subregion","The AvCan's subregion the fire boundary resides in."),
        ("Patch ID", "An identifier assigned to the patch within the reference fire."),
        ("Aspect label","The most common aspect (cardinal direction) across pixels within the patch."),
        (f"Aspect Choerence (R)", f"A 0–1 score describing how consistent terrain aspect (slope-facing direction) is within the patch. Values near 1 indicate the patch largely faces a single direction (e.g., mostly north-facing), while values near 0 indicate a mix of aspects across the patch (highly variable terrain-facing directions). Patches with a R-value < {fmt_num(aspect_label,1)} are given a 'mixed' aspect label."), 
        ("Patch Area (ha)", "Area of the patch in hectares."),
        ("Mean Elevation (m)", "Average elevation of patch in metres."),
        ("Mean Slope Degree", "Average slope of the patch in degrees.")
        ]
        _bullet_kv(patches_list)