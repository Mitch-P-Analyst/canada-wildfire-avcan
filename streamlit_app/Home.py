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
from components.loaders import fmt
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
nbac_cfg = load_yaml_config("nbac_stats.yaml")

thresholds = stage_a_cfg.get("thresholds", {}) or {}
calibration = stage_a_cfg.get("calibration", {}) or {}

data = nbac_cfg.get("data", {}) or {}

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
avg_fire_count = data.get("avg_fire_count")
avg_burn_area_ha = data.get("avg_burn_ha")
avg_burn_km = data.get("avg_burn_km")


# -------------------------------------------------------------------
# Landing / Overview page
# -------------------------------------------------------------------
st.title("Avalanche Canada Wildfire Explorer")

st.info("Upate In Progress (Jan 5th). Address clarity structure and non-techincal communication")

st.markdown(f"""
The Canadian **National Burned Area Composite (NBAC)**, maintained by Natural Resources Canada, is a national geospatial dataset that maps and quantifies forest area burned each year across Canada. Compiled from provincial, territorial, and protected-area sources, NBAC is widely used to support analysis of wildfire impacts on ecosystems and landscapes.
            
According to NBAC, since **{fmt(min_year)}** Canada has experienced an average of **{fmt(avg_fire_count)} fires per year**, burning approximately **{fmt(avg_burn_area_ha)} hectares** annually ({fmt(avg_burn_km)}). That is roughly **half the area of Nova Scotia every year**. Despite the scale of this size, the footprint of wildfire can be easy to miss on the ground, even for those living in close proximity or people traveling through mountain landscapes.

Many winter recreation users, such as skiers, snowboarders, and snowmobilers, are familiar with burned forests. Post-fire terrain can create unique conditions for travel and, in some contexts, enjoyable gladed riding when combined with favorable snow and stability. **Avalanche Canada (AvCan)** is a **non-profit organization** that provides public avalanche safety information and education, including regional avalanche forecasts and hazard bulletins informed by professional observations and community-submitted reports.

The initial objective of this **Avalanche Canada Wildfire Explorer** is to overlay NBAC-recorded wildfire perimeters with Avalanche Canada forecast regions to make wildfire impacts more tangible in the mountain environments used by the public. By pairing wildfire statistics with mapped recreation-relevant areas, this project aims to support awareness of wildfire presence in mountain communities and help users explore how these landscapes are changing over time. This dataset and workflow can be extended to support additional analyses, such as regional trends in fire frequency, burned area, severity, and ignition causes, with potential applications in research, planning, and risk communication.
            
""")



st.divider()


st.subheader("Project Structure")
st.write("Using the navigation links on the **left side of this application**, explore this project's pages to observe the interactive topographical map and learn about the data.")
st.markdown(
    """
        
    ##### Explorer

    An interactive topographical map has been built to visualise fire perimeters in filtered AvCan regions and communicate statstical findings. An additional map layer named **burn-severity patches** has been produced, which identifies areas within filtered fires that meet calibrated thresholds as **candidates for winter recreational uses.** The burn-severity patches identifed are derived from a calibrated fire severity and minimum patch-size logic further explained in technical terms on the **Method Page** of this application. 

    Explore this interactive map to learn about and view wildfire presence, statistics and identified regions within Avalanche Canada forecasting regions.
    
    ##### Method

    A pipeline overview of the analysis and strucutre of this data project. Along with techinical breakdowns of the analysed data from NBAC and derived map layers of Burn Severity Patches. Discussing the analytical processes and methods used in creating and implementing calibrations. 
    
    ##### Data

    Descriptive explanation of datasets used to produce the AvCan Wildfire Explorer project, including both external sources and derived project layers. 
    """
)

st.divider()

roadmap_section()

st.subheader("Data Sources")
st.markdown(
    """
    - **NBAC (National Burn Area Composite):** wildfire perimeter dataset  
    - **Avalanche Canada regions:** forecasting region boundaries  
    - **Statistics Canada boundaries:** provincial/territorial context

    This application is informational and not intended for safety-critical decision-making.
    """
)

# Optional: show where app expects data to exist (helps debugging)
with st.expander("App data location (debug)", expanded=False):
    st.code(str(REPO_ROOT / "data" / "processed" / "app"))
    st.write("Expected files:")
    st.code(
        "\n".join(
            [
                "Fires.parquet",
                "Regions.parquet",
                "Stage_A_Severity_Patches.parquet",
            ]
        )
    )
