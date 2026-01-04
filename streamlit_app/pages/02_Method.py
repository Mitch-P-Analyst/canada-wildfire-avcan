# 02_Method.py

# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


# ===================================================================
# Components
# ===================================================================
from components.loaders import load_yaml_config
from components.loaders import fmt

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ===================================================================
# Page Config
# ===================================================================
st.set_page_config(
    page_title="Method",
    page_icon="🔥",
    layout="wide"
)

# ===================================================================
# Method Function
# ===================================================================

def method_page() -> None:
    # ===================================================================
    # Introduction
    # ===================================================================
    st.title("Method & Processes")
    st.write("This page explains the analytical processes and method used to produce this AvCan Wildfire Explorer. ")
    st.divider()

    # ===================================================================
    # Constants
    # ===================================================================
    stage_a_cfg = load_yaml_config("stage_a.yaml")
    
    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    # Value Extraction 
    # =================================================================

    # ========== Thresholds =====================================
    dnbr_min = thresholds.get("dnbr_min")          # e.g., 0.2
    min_patch_area_ha = thresholds.get("min_patch_area_ha") # e.g., 10
    dnbr_value = thresholds.get("dnbr_value")
    pixel_conn = thresholds.get("connectivity")
    scale_value = thresholds.get("scale")

    # ========== Calibrations =====================================
    ref_region = calibration.get("reference_region").replace("_", " ")
    ref_gid = calibration.get("reference_gid")      # e.g., "1990_106"
    ref_note = calibration.get("note")
    time_start = calibration.get("time_start").replace("_", " ")
    time_end = calibration.get("time_end").replace("_", " ")

    # ===================================================================
    # Body
    # ===================================================================
    st.markdown("## Pipeline Overview")
    st.markdown("""
            1. Download and process National Burn Area Composite (NBAC) file polygons.
                - `scripts/01_download_nbacs.py`
            2. Download Statistics Canada provinces and territories boundaries (2021)
                - `scripts/02_download_statscan_provinces.py`
            3. Clean and merge NBAC file polygons into master file
                - `scripts/03_clean_merge_nbac.py`
            4. Overlay NBAC fires within AvCan regions. Filter for AvCan only fires.
                - `scripts/04_avcan_fires_overlay/py`
            5. Derive Stage A - Severity Patches through Google Earth Engine (dNBR and Minimum size thresholds).
                - [Stage A – Google Earth Engine Zone Severity script](https://code.earthengine.google.com/12944605af9b45be19b9321bd5a77f50)
            6. Build web application data layers. Summarize outputs for visualisation.
                - `scripts/05_build_app_layers.py`
            7. **Next Step** : Stage B - Identify Vegetation Regrowth (NVRI indice and VRI inventory) within Stage A Severity Patches.
            """)
    
    st.divider()

    st.markdown("## Stage A - Severity Patches")
    st.markdown(f"""
    **Objective**  
    Identify and extract areas within AvCan fire polygons that meet thresholds of *severe burn patches*.

    **Reference calibration**  
    {fmt(ref_note)} Intended use of *Severity Patches* is to identify candidate areas for winter recreational activities.  
    Calibration and resulting thresholds reference **{fmt(ref_region)}** fire ID **{fmt(ref_gid)}**, selected due to reported favourable winter recreational conditions.

    **Thresholds**
    - Difference Normalised Burn Ratio (dNBR) minimum: **{fmt(dnbr_min)}**
    - Minimum connected patch area (ha): **{fmt(min_patch_area_ha)}**
    - Pixel connectivity: **{fmt(pixel_conn)}**

    **Context**  
    dNBR (differenced Normalized Burn Ratio) is derived from the Normalized Burn Ratio index, which is computed from Landsat Near-Infrared (NIR) and Shortwave Infrared (SWIR) wavelength bands. Because wildfire typically reduces healthy vegetation (lower NIR reflectance) and increases exposed soil/char and dryness (higher SWIR reflectance), NBR and dNBR are commonly used to map burn impacts and relative burn severity in forested landscapes. Stage A applies a calibrated dNBR threshold (referenced to {fmt(ref_region)} fire ID {fmt(ref_gid)}) together with a minimum patch-size rule to identify comparable patches across AvCan fires.
    
    Stage A identifies Severity Patches by thresholding the dNBR layer at ≥ {fmt(dnbr_min)} to create a binary mask, then grouping masked pixels into connected areas using {fmt(pixel_conn)} (cardinal and diagonal adjacency). Patch size is approximated using connected pixel count at a {fmt(scale_value)} working scale, converting the 10 ha minimum area threshold to a minimum area size (≈ 49–50 connected pixels). Areas meeting or exceeding this minimum size are retained as the final **Severity Patches** mask and then converted to polygons within the fire perimeter geometry.

    This dNBR is calculated uses pre- and post-fire seasonal composites spanning **{fmt(time_start)} – {fmt(time_end)}** (one year before and after each fire year), from **Landsat 5/7/8/9** imagery.

    A coarser {fmt(scale_value)} processing scale is used during patch identifcation to reduce computational load and produce fewer, larger candidate patches.
    """)

    st.divider()

    st.markdown("## Stage B - Vegetation Regrowth (Planned)")
    st.markdown(f"""
    **Goal**
    Identify areas within **Stage A Severity Patches** that met a calibrated threshold for low levels of Vegetation Regrowth post-fire activity in a current year (2025) promoting open spaced areas.
                
    **Data + Processes**
                
    Vegetation Resource Inventories (VRI) assessing forest regrowth;
    - Canopy openness / crown closure
    - Height / height class
    - Age / age class
    - Species composition
    - Density/biomass proxies
    - Non-tree vegetation descriptors
                
    Landsat Specarel imagery for Normalised Difference Vegetation Indice (NDVI)
    - Spectral index computed from red and near-infrared reflectance to identify greenness/leaf and vegetation post-fire.
    """)

# ===================================================================
# Run Method Page Function
# ===================================================================
method_page()