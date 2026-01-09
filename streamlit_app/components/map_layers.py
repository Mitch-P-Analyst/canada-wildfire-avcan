# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd

from .loaders import load_yaml_config


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
    nbac_cfg = load_yaml_config("nbac_stats.yaml")

    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    data = nbac_cfg.get("data", {}) or {}

    # ========== Value Extraction =====================================
    
    # ======= Thresholds =======#
    
    dnbr_min = thresholds.get("dnbr_min")          # e.g., 0.2
    min_patch_area_ha = thresholds.get("min_patch_area_ha") # e.g., 10
    dnbr_value = thresholds.get("dnbr_value")
    pixel_conn = thresholds.get("connectivity")
    scale_value = thresholds.get("scale")

    # ======= Data =======#

    min_year = data.get("min_year")
    max_year = data.get("max_year")
    avg_fire_count = data.get("avg_fire_count")
    avg_burn_area_ha = data.get("avg_burn_ha")
    avg_burn_km = data.get("avg_burn_km")
    total_burn_count = data.get("total_fire_count")
    total_burn_ha = data.get("total_burn_ha")
    total_burn_km = data.get("total_burn_km")

    # Header 
    # =================================================================
    st.markdown("### Map Layers")
    st.caption("All map layers, filters and legend customisations can be found on the **left side of this application**.")

    # Regions 
    # =================================================================
    
    with st.expander("##### AvCan Region Perimeter", expanded=False):
        st.markdown(f"""
        Presented wildfires in the map below will be filtered to a chosen **AvCan Forecasting Region**. In the sidebar, select from the available regions to observe proximate fires. 
                    
        The AvCan Region Perimeter is indicated by a **thick black line**, outlining the forecasting region and boundary for filtered fires.
                    
        Your chosen region will compile summary statistics above the topographical map of relevant details of presented map layers.
                """)
        
    with st.expander("##### Fire Perimeters", expanded=False):
        st.markdown(f"""
        NBAC fires within the chosen AvCan Region Perimeter are visualised with a default <span style='color:#ffce00;'>Yellow Colour.</span> This colour can be modified in the **Legends** section of the sidebar. 
                    
        The date range of presented fires can be modified in the **filters** section, to visualise and receive regional summary statistics of specific time periods.
                    
        Each fire perimeter includes the following metadata:
        - **Region**: The AvCan region the fire boundary resides in.
        - **Subregion**: The AvCan's subregion the fire boundary resides in.
        - **Yea**: The year of fire occurance.
        - **Unique Fire ID (gid)**: NBAC's assigned unique identification number
        - **Total Adjusted Area (ha)**: NBAC's total calculated hecteras burned.
                   """, unsafe_allow_html=True)
        
    with st.expander("##### Burn Severity Patches (Stage A)", expanded=False):
        st.markdown(f"""
        Stage A of this AvCan wildfire explorer computes custom derived **burn severity patches** within NBAC fire perimeters. These are visualised in an seperate map layer with default <span style='color:#ff5a00;'>Orange Colour</span> perimeters. This colour can be modified in the **Legends** section of the sidebar. 
                    
        Burn severity patches are post-fire areas identified by this project’s criteria as candidates for winter recreation (e.g., skiing, snowboarding snowmobiling) as commonly known "Burnt Tree Zones". This layer is intended as an exploratory layer to help highlight terrain for recreational use, not as an official Avalanche Canada product. For information on this layer's computation, refer to the **Method** page of this application. 
        
        Each burn severity patch perimeter includes the following metadata:
        - **Region**: The AvCan region the fire boundary resides in.
        - **Subregion**: The AvCan's subregion the fire boundary resides in.
        - **Yea**: The year of the fire occurance.
        - **Patch ID**: A patch assigned ID within the reference fire.
        - **Majority Cardinal Direction**: Within the identified patch, the most common cardinal direction per pixel.
        - **Patch Area (ha)**: Hectare area of identified patch.
        - **Mean Elevation (m)**: Average elevation of patch in metres.
        - **Mean Slope Degree**: Average gradient of patch.
                    """, unsafe_allow_html=True)
        
