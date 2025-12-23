# 02_Method.py

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

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Method",
    page_icon="🔥",
    layout="wide"
)

def method_page() -> None:
    st.title("Method & Processes")
    st.write("This page explains the analytical processes and method used to produce this AvCan Wildfire Explorer. ")

    st.divider()

    st.markdown("## Pipeline Overview")
    st.markdown(
        "1. Download and process National Burn Area Composite (NBAC) file polygons." \
        "2. Download Avalanche Canada (AvCan) region and subregion polygons." \
        "3. Overlay NBAC fires within AvCan regions. Filter for AvCan only fires." \
        "4. Derive Stage A - Severity Patches through Google Earth Engine (dNBR and Minimum size thresholds)." \
        "5. Summarize Outputs for visualisation." \
        "6. **Next Step** : Stage B - Identify Vegetation Regrowth (NVRI indice) within Stage A Severity Patches")
    
    st.divider()
    