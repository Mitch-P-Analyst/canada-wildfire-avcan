# streamlit_app/app.py

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


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


# -------------------------------------------------------------------
# Landing / Overview page
# -------------------------------------------------------------------
st.title("Avalanche Canada Wildfire Explorer")


st.write(
    "This Streamlit application visualizes wildfire perimeters recorded in the National Burn Area Composite (NBAC) "
    "within Avalanche Canada (AvCan) forecasting regions. It is designed to support exploration of historical fires "
    "and the identification of candidate burn-severity patches relevant to winter backcountry recreation.")
    
st.write(
    "Identifcation of fires within recreational backcountry areas is an opportunity to raise wildfire awareness to users of local environments, "
    "providing insights to natural events and human involvement. Simultanously, provide opportunties to explore landscapes for adventure activities, promoting outdoor recreation."


)

st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Current pipeline status")
    st.markdown(
        """
        **Stage A (available now):**  
        Burn-severity *patches* derived using a calibrated fire severity and minimum patch-size logic.  
        Calibration is anchored to observed on-the-ground patch scale and severity from the **South Coast Inland fire ID 1990–106**.

        **Stage B (planned):**  
        Apply **NVRI vegetation regrowth** since fire date to present to remove regenerated areas and isolate more durable
        candidate “burn zones” for winter recreation.
        
        Identify forest regrowth with applicable Vegetation Resource Inventories (VRI), such as Canopy openness, Height, Age, Species composition and more.
        """
    )

with col2:
    st.subheader("How to use")
    st.markdown(
        """
        - Open the **Explorer** page (left navigation) to view the interactive map.  
        - Filter by **Region** and **Year range**.  
        - Toggle layers (fires / severity patches / region boundary).  
        - Use the summary metrics to interpret the filtered selection.
        """
    )

st.divider()

st.subheader("Data sources")
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
