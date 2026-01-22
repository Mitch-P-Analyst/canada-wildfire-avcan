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
from components.loaders import fmt_int, fmt_num, fmt_pct, fmt_str

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
    st.divider()

    st.markdown("## Overview")
    st.markdown("""
    This page documents the end-to-end workflow used to build the AvCan Wildfire Explorer map layers, from sourcing and cleaning NBAC fire perimeters, to intersecting fires with Avalanche Canada forecast regions, to generating Stage A Burn Severity Patches and exporting app-ready GeoParquet layers. It outlines the key processing steps, threshold logic, and calibration decisions that underpin the map layers and summary statistics shown in the Explorer.                
    """)

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
    min_patch_pixels = thresholds.get("min_patch_pixels")
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
    st.markdown("## Data Pipeline")
    st.markdown("""
            A high-level overview of the data pipeline used to produce the application’s map layers and summary statistics. 
            Reproducable project and indepth README overview can be accessed at the following link: [Avalanche Canada Wildfire Explorer Github Repository](https://github.com/Mitch-P-Analyst/canada-wildfire-avcan.git) 

            1. Download and process National Burn Area Composite (NBAC) file polygons.
                - `scripts/01_download_nbacs.py`
            2. Download Statistics Canada provinces and territories boundaries (2021)
                - `scripts/02_download_statscan_provinces.py`
            3. Clean and merge annual NBAC polygons into a single master fire-perimeter dataset
                - `scripts/03_clean_merge_nbac.py`
            4. Spatially overlay NBAC fire perimeters with AvCan forecasting regions and retain only fires within AvCan coverage.
                - `scripts/04_avcan_fires_overlay.py`
            5. Identify *Burn Severity Patches* withn AvCan fires with Google Earth Engine's python API. Looping through region/year and region/year/fireid arrangements.
                - `scripts/05_stage_a1.py`
            6. Compute and append applicable geographical metadata to stage A1's *Burn Severity Patches* with Google Earth Engine's python API.
                - `scripts/06_stage_a2.py`
            7. Compile and export batches of stage A2's Burn Severity Patches to Google Cloud Service and download to local.
                - `scripts/07_stage_a_ee_export.py`
            8. Build streamlit application-ready map explorer layers.
                - `scripts/08_build_app_layers.py`

            **Next Steps**
                
            9. Stage B1 | Forest Inventory.
                - Download Vegetation Resource Inventory (VRI) for each AvCan region. Overlaying patches with VRI inventory polygons, appending selected VRI attributes (e.g Canopy openness, species composition, density/biomass proxies)
            10. Stage B2 | Regrowth Vegetation.
                - Compute Normalised Difference Vegetation Index (NDVI) from post-fire year to current, assessing and callibrating a regrowth threshold for optimal patch candidates.
                """)
    
    st.divider()

    st.markdown("## Burn Severity Patches (Stage A)")
    st.markdown(f"""
    #### Objective 
    Identify and extract areas within AvCan fire polygons that meet callibrated thresholds. Identified areas are named "Burn Severity Zones" and candidates for winter recreational use.

    #### Reference calibration
    {fmt_str(ref_note)} Intended use of *Burn Severity Patches* is to identify candidate areas for winter recreational activities, sometimes referred to as *"burnt tree zones"*.  
    Calibration and resulting thresholds reference **{fmt_str(ref_region)}** fire GID **{fmt_str(ref_gid)}**, selected due to reported favourable winter recreational conditions.

    #### Thresholds 
    - Difference Normalised Burn Ratio (dNBR) minimum: **{fmt_num(dnbr_min,1)}**
    - Minimum connected patch area (ha): **{fmt_int(min_patch_area_ha)}**
    - Pixel connectivity: **{fmt_str(pixel_conn)}**

    #### Context
    
    **Difference Normalized Burn Ratio (dNBR)**

    dNBR is derived from the Normalized Burn Ratio (NBR), which is computed using the Near-Infrared (NIR) and Shortwave Infrared (SWIR) bands of satellite imagery. Wildfire typically reduces healthy vegetation (lower NIR reflectance) and increases exposed soil/char and surface dryness (higher SWIR reflectance). As a result, NBR and dNBR are widely used to map burn impacts and relative burn severity in forested landscapes.
    
    In this project, Burn Severity Patches (Stage A) are identified by applying a calibrated dNBR threshold (referenced to {fmt_str(ref_region)} fire ID {fmt_str(ref_gid)}) to extract comparable severity patches across fires within Avalanche Canada forecasting regions.

    dNBR is calculated using pre- and post-fire seasonal composites spanning **{fmt_str(time_start)} – {fmt_str(time_end)}** (one year before and one year after each fire year), from Landsat 5/7/8/9 composite imagery.
    

    **Minimum connected patch area and pixel connectivity**

    To reduce computational load within Google Earth Engine memory limits, and to focus on the largest candidate areas, Stage A applies a minimum patch area rule during patch identification. While Landsat imagery has a native 30m x 30m resolution, processing is performed at a coarser {fmt_str(scale_value)} scale during patch extraction to reduce computation and produce fewer, larger candidate patches.

    Pixels that meet or exceed the dNBR threshold are grouped into contiguous patches using {fmt_str(pixel_conn)} connectivity (pixels are connected through both cardinal and diagonal neighbours). A {fmt_int(min_patch_area_ha)} hectare minimum patch size is then applied at the {fmt_str(scale_value)} processing scale, this corresponds to approximately {fmt_str(min_patch_pixels)} connected pixels.

    **Computation**

    Burn Severity Patches are generated for each individual fire by applying a dNBR threshold (default dNBR ≥ {fmt_num(dnbr_min,2)}) to create a binary mask. Masked pixels are then grouped into connected patches using the pixel connectivity rules above, and patches smaller than the minimum area threshold are removed. The remaining patches form the final Burn Severity Patches layer, which is then converted to polygons clipped to the fire perimeter geometry.

    
    """)

    st.divider()

    st.markdown("## Regrowth Vegetation + Forest Inventory (Stage B - Planned)")
    st.markdown(f"""
    #### Objectives
                
    - Identify areas within Burn Severity Patches that show limited vegetation regrowth by a selected “current year” (e.g., 2025), using a calibrated regrowth threshold to highlight open terrain.
    - Intersect Burn Severity Patches with forest Vegetation Resource Inventory to characterize forest structure and composition within each patch.
                
    #### Data + Processes
                
    Landsat imagery for the Normalised Difference Vegetation Index (NDVI)
    - NDVI is a spectral index derived from red and near-infrared (NIR) reflectance and is used here as a proxy for vegetation greenness and post-fire recovery.
                
    Vegetation Resource Inventory (VRI) attributes to describe forest conditions within patches
    - Canopy openness / crown closure
    - Height / height class
    - Age / age class
    - Species composition
    - Density/biomass proxies
    - Non-tree vegetation descriptors

    #### Context
                
    Stage A Burn Severity Patches identifies areas within fire polygons that meet callibrated thresholds of burn severity and size to be candidates of "Burnt Tree Zones". However, Stage B Regrowth Vegetation + Forest Inventory aims to review the post-fire regrowth of these identified patches and use forest inventory data to assess the current status of identied patches for recreational use.
    
    """)

# ===================================================================
# Run Method Page Function
# ===================================================================
method_page()