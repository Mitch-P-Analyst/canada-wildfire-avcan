# streamlit_app/app.py


# ===================================================================
# Imports
# ===================================================================

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

# ===================================================================
# Components
# ===================================================================
from components.loaders import load_yaml_config
from components.loaders import fmt_int, fmt_num, fmt_pct 
from components.roadmap import roadmap_section

# -------------------------------------------------------------------
# Make repo imports reliable (so `from components...` works everywhere)
# -------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent              # streamlit_app/
REPO_ROOT = APP_DIR.parent                             # repo root
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AvCan Wildfire Explorer",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================================================================
# Constants
# ===================================================================
stage_a_cfg = load_yaml_config("stage_a.yaml")
stats = load_yaml_config("summary_stats.yaml")

thresholds = stage_a_cfg.get("thresholds", {}) or {}
calibration = stage_a_cfg.get("calibration", {}) or {}

data = stats.get("data", {}) or {}
nbac_stats = stats.get("nbac",{}) or {}
# Value Extraction 
# =================================================================

# ========== Thresholds =====================================
dnbr_min = thresholds.get("dnbr_min")          # e.g., 0.2
min_patch_area_ha = thresholds.get("min_patch_area_ha") # e.g., 10
dnbr_value = thresholds.get("dnbr_value")
pixel_conn = thresholds.get("connectivity")
scale_value = thresholds.get("scale")

# ========== Data =====================================
min_year = data.get("min_year")
max_year = data.get("max_year")
avg_fire_count_per_year = nbac_stats.get("avg_fires_per_year")
avg_burn_area_per_year_ha = nbac_stats.get("avg_burn_ha_per_year")
avg_burn_area_per_year_km = nbac_stats.get("avg_burn_km2_per_year")


# -------------------------------------------------------------------
# Landing / Overview page
# -------------------------------------------------------------------
st.title("Avalanche Canada Wildfire Explorer")

# st.info("Upate In Progress (Jan 5th). Address clarity structure and non-techincal communication")

st.markdown(f"""
The Canadian **National Burned Area Composite (NBAC)**, maintained by Natural Resources Canada, is a national geospatial dataset that maps and quantifies forest area burned each year across Canada. Compiled from provincial, territorial, and protected-area sources, NBAC is widely used to support analysis of wildfire impacts on ecosystems and landscapes.
            
According to NBAC, since **{min_year}** Canada has experienced an average of **{fmt_num(avg_fire_count_per_year,2)} fires per year**, burning approximately **{fmt_num(avg_burn_area_per_year_ha,2)} hectares** annually ({fmt_num(avg_burn_area_per_year_km,2)} km²). That is roughly **half the area of Nova Scotia every year**. Despite the scale of this size, the footprint of wildfire can be easy to miss on the ground, even for those living in close proximity or people traveling through mountain landscapes.

Many winter recreation users, such as skiers, snowboarders, and snowmobilers, are familiar with burned forests. Post-fire terrain, sometimes referred to as "Burnt Tree Zones", can create unique conditions for travel and enjoyable gladed riding when combined with favorable snow and stability. **Avalanche Canada (AvCan)** is a **non-profit organization** that provides public avalanche safety information and education, including regional avalanche forecasts and hazard bulletins informed by professional observations and community-submitted reports.

The initial objective of this **Avalanche Canada Wildfire Explorer** is to overlay NBAC-recorded wildfire perimeters with Avalanche Canada forecast regions to make wildfire impacts more tangible in the mountain environments used by the public. By pairing wildfire statistics with mapped recreation-relevant areas, this project aims to support awareness of wildfire presence in mountain communities and help users explore how these landscapes are changing over time. This dataset and workflow can be extended to support additional analyses, such as regional trends in fire frequency, burned area, severity, and ignition causes, with potential applications in research, planning, and risk communication.
            
""")



st.divider()


st.subheader("Application Structure")
st.write("Use the navigation links on the **left side of this application** to explore this project's pages.")
st.markdown(
    """
        
    ##### Explorer

    An interactive topographic map for exploring wildfire perimeters within Avalanche Canada (AvCan) forecast regions and viewing region-filtered summary statistics. In addition to NBAC fire perimeters, the Explorer includes a derived **Burn Severity Patches (Stage A)** layer, which highlights areas within AvCan-filtered fires that meet calibrated severity and minimum patch-size thresholds as potential **candidates for winter recreational use**. The methodology, calibration reference, and threshold logic used to generate these patches are documented on the Method page.

    Use the Explorer to navigate by region and year range, compare wildfire presence across backcountry-relevant areas, and review how fire activity and derived patch coverage vary within AvCan regions and subregions.

    ##### Method

    An overview of the analysis pipeline used to build this project, from raw NBAC wildfire perimeters to AvCan-filtered map layers and derived Burn Severity Patches. This page explains the key processing steps, calibrated thresholds, and assumptions used to identify patches, and documents the geospatial and analytical methods used throughout the workflow.
    
    ##### Data

    A catalogue of the datasets and app layers used in the AvCan Wildfire Explorer. This page describes what each layer represents, where it was sourced from, and how it is packaged for the application (formats, CRS, and key fields). It also hosts broader, multi-year summary statistics for each dataset and derived layer, providing national/project-wide context that complements the Explorer’s region-filtered summaries.
    """
)

st.divider()

roadmap_section()

st.markdown(
    """
    This application is informational and not intended for safety-critical decision-making.
    """
)
