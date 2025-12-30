# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
import streamlit as st

# ===================================================================
# Components
# ===================================================================
from components.loaders import load_yaml_config
from components.loaders import load_app_layers, app_data_dir

# ===================================================================
# Page Config
# ===================================================================
st.set_page_config(
    page_title="Data",
    page_icon="🔥",
    layout="wide",
)

# ===================================================================
# Helpers
# ===================================================================
def _bullet_list(items: list[str]) -> None:
    st.markdown("\n".join([f"- {x}" for x in items]))

def _kv(label: str, value: str) -> None:
    st.markdown(f"**{label}:** {value}")

# ===================================================================
# Data Page Function
# ===================================================================
def data_page() -> None:

    # Intro 
    # =================================================================
    st.title("Data")
    st.write(
        "This page describes the datasets used to produce the AvCan Wildfire Explorer, "
        "including both external sources and derived project layers."
    )
    st.divider()

   # Stage A config (derived layer metadata) 
   # =================================================================
    stage_a_cfg = load_yaml_config("stage_a.yaml") or {}
    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}
    stage_meta = stage_a_cfg.get("stage", {}) or {}

    dnbr_min = thresholds.get("dnbr_min")
    min_patch_area_ha = thresholds.get("min_patch_area_ha")
    connectivity = thresholds.get("connectivity") or thresholds.get("pixel_conn")  # support either key
    dnbr_value = thresholds.get("dnbr_value")

    ref_region = calibration.get("reference_region")
    ref_gid = calibration.get("reference_gid")
    time_start = calibration.get("time_start")
    time_end = calibration.get("time_end")
    ref_note = calibration.get("note")

   # Core Layers 
   # =================================================================
    st.markdown("## Core Explorer layers")

    # ========== App Layer Files =====================================
    st.markdown("### App files")
    st.caption("Processed layers loaded by the Streamlit app (GeoParquet, reprojected to WGS84 / EPSG:4326).")
    st.markdown("""
    - **Fires:** `data/processed/app/Fires.parquet`
    - **Stage A severity patches:** `data/processed/app/Stage_A_Severity_Patches.parquet`
    - **Regions:** `data/processed/app/Regions.parquet`
    - **Stage B regrowth patches (planned):** `data/processed/app/Stage_B_Regrowth_Patches.parquet`
    """)

    # ========== Data Lineage =====================================
    st.markdown("### Data lineage (raw → derived → app)")
    st.caption("High-level overview.")

    _bullet_list([
        "Raw: NBAC annual burned-area polygons (Natural Resources Canada / CWFIS).",
        "Raw: Avalanche Canada forecast polygons (regions/subregions).",
        "Python preprocessing: spatial overlay + labeling (NBAC ∩ AvCan) → exported as an Earth Engine table asset.",
        "Google Earth Engine: Stage A severity patches derived using dNBR + patch-size thresholds.",
        "Python post-processing: exported outputs normalized + saved as GeoParquet app layers (EPSG:4326).",
    ])

    st.markdown("**Key repo scripts/notebooks:**")
    _bullet_list([
        "`scripts/…` (NBAC ingest + AvCan overlay)",   # replace with your actual path
        "`notebooks/…` (export to GeoParquet / app layers)",  # replace with your actual path
    ])


    # Load Cached Layers (optional: quick transparency + QA)
    with st.expander("App layer summary (counts)", expanded=False):
        try:
            # Load Cached Layers 
            # =================================================================
            fires_path   = app_data_dir / "Fires.parquet"
            patches_path = app_data_dir / "Stage_A_Severity_Patches.parquet"
            regions_path = app_data_dir / "Regions.parquet"

            fires, patches, regions = load_app_layers(
                app_data_dir,
                fires_path.stat().st_mtime,
                patches_path.stat().st_mtime,
                regions_path.stat().st_mtime,
            )

            # ========== Region =====================================
            regions_sel = sorted(regions["Region"].dropna().unique().tolist()) if "Region" in regions.columns else []
            if not regions_sel:
                regions_sel = sorted(set(fires["Region"].dropna().unique()).union(set(patches["Region"].dropna().unique())))


            st.markdown(f"- **Fires:** {len(fires):,} rows")
            st.markdown(f"- **Stage A patches:** {len(patches):,} rows")
            st.markdown(f"- **Regions:** {len(regions_sel):,} rows")
            st.markdown("- **CRS:** `EPSG:4326` (WGS84 / web mapping)")
            st.caption(f"Further computation is on going to produce Stage A (and planned Stage B) analysis records for all {len(regions):,} AvCan regions.")
        except Exception as e:
            st.warning(f"Could not load app layers for summary counts. ({e})")

    st.markdown("### App Layers")
    st.caption("These are the primary layers shown on the interactive map and used for filtering and summary statistics.")

    # ========== NBAC Fires =====================================

    with st.expander("NBAC Fire Perimeters (Natural Resources Canada / CWFIS)", expanded=True):
        _kv("What it is", "National Burned Area Composite (NBAC): an annually updated national dataset of burned area polygons.")
        _kv("Publisher", "Natural Resources Canada – Canadian Forest Service (CWFIS)")
        _kv("Why it’s used", "Provides the fire perimeter geometry that is filtered to Avalanche Canada regions.")
        _kv("Temporal coverage", "Annual records (project currently uses the years processed into the app layers).")
        _kv("Downloaded as", "One ZIP file per year (NBAC burned area polygons).")
        _kv("Shipped to app as", "`data/processed/app/Fires.parquet` (GeoParquet; WGS84 / EPSG:4326)")
        st.markdown("**Source:** https://cwfis.cfs.nrcan.gc.ca")

    # ========== AvCan Regions =====================================
    
    with st.expander("Avalanche Canada Forecast Regions (forecast-polygons)", expanded=True):
        _kv("What it is", "Avalanche Canada (AvCan) forecast regions and subregions used for avalanche forecasting.")
        _kv("Publisher", "Avalanche Canada")
        _kv("Why it’s used", "Defines the spatial extent for filtering fires and presenting results in backcountry-relevant regions.")
        _kv("Downloaded as", "GeoJSON")
        _kv("Shipped to app as", "`data/processed/app/Regions.parquet` (GeoParquet; WGS84 / EPSG:4326)")
        st.markdown("**Source:** https://github.com/avalanche-canada/forecast-polygons")
        _bullet_list([
            "File: `canadian_subregions.geojson`",
        ])

    # ========== Stage A =====================================
    
    with st.expander("Stage A – Severity Patches (derived)", expanded=True):
        _kv("What it is", "Derived burn-severity patches clipped to AvCan regions, produced from satellite-based severity logic and minimum patch-size filtering.")
        _kv("Stage", f"{stage_meta.get('name', 'Stage A')}")
        _kv("Why it’s used", "Represents candidate ‘burn-zone’ patches based on calibrated severity and patch-size thresholds.")
        _kv("Calibration reference", f"{ref_region} / Fire ID {ref_gid}" if (ref_region or ref_gid) else "Defined in stage_a.yaml")
        _kv("Shipped to app as", "`data/processed/app/Stage_A_Severity_Patches.parquet` (GeoParquet; WGS84 / EPSG:4326)")

        if ref_note:
            _kv("Calibration note", ref_note)

        st.markdown("**Thresholds (from `stage_a.yaml`):**")
        t_items = []
        if dnbr_min is not None:
            t_items.append(f"dNBR ≥ {dnbr_min}")
        if min_patch_area_ha is not None:
            t_items.append(f"Minimum patch area ≥ {min_patch_area_ha} ha")
        if connectivity:
            t_items.append(f"Connectivity: {connectivity}")
        if dnbr_value:
            t_items.append(f"Severity class label: {dnbr_value}")
        _bullet_list(t_items if t_items else ["(No thresholds found in config)"])

        if time_start or time_end:
            _kv("Seasonal window used for composites", f"{time_start} to {time_end}".replace("_", " "))

        _kv("Produced in", "Google Earth Engine Console.")
        stage_A_items = [
        "[AvCan Region Fires (1990–2024) asset](https://code.earthengine.google.com/?asset=projects/wildfire-canada-475322/assets/AvCan_fires_1990_2024)",
        "[Stage A – Zone Severity script](https://code.earthengine.google.com/12944605af9b45be19b9321bd5a77f50)",
        "[Stage A – Export script](https://code.earthengine.google.com/916cd4802cc42e65f8b596f9932e46d8)",
        ]
        _bullet_list(stage_A_items)
    # ========== Stage B =====================================
    
    
    with st.expander("Stage B – Vegetation Regrowth Patches (planned)", expanded=False):
        st.write(
            "Stage B will filter Stage A patches based on indicators of vegetation recovery to prioritize "
            "more open-canopy / low-obstruction candidate zones."
        )
        st.markdown("**Planned inputs (options):**")
        _bullet_list([
            "Forest inventory attributes (e.g., canopy closure, height class, stand age class) where available",
            "Spectral indices (e.g., NDVI) as supporting evidence for greenness / vigor within a consistent seasonal window",
        ])
        st.markdown("**Planned output:** `data/processed/app/Stage_B_Regrowth_Patches.parquet` (to be added as a toggleable layer and summary metric).")

    st.divider()

   # Supporting / context layers 
   # =================================================================
    st.markdown("## Supporting / context datasets")
    st.caption("These datasets support preprocessing, validation, and cartographic context, but are not necessarily displayed as primary Explorer layers.")

    with st.expander("Statistics Canada – Provincial / Territorial boundaries (2021)", expanded=False):
        _kv("What it is", "Cartographic boundary file for provinces/territories (2021 Census).")
        _kv("Why it’s used", "Provides national context and can support sanity-check filtering / labeling.")
        _bullet_list(["File(s): `lpr_000b21a_e.zip` "])
        st.markdown("**Source:** https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?Year=21")

    with st.expander("Basemap tiles (OpenTopoMap / OSM attribution)", expanded=False):
        _kv("What it is", "Map tile basemap used for visualization.")
        _kv("Why it’s used", "Provides topographic context for backcountry terrain.")
        _bullet_list([
            "OpenTopoMap basemap (via Leaflet/Folium)",
            "Map data attribution: OpenStreetMap contributors",
        ])

    st.divider()

    # Limitations 
    # =================================================================
    st.markdown("## Notes and limitations")
    _bullet_list([
        "Stage A thresholds are calibrated to a reference fire and are intended as an initial heuristic; future work can broaden calibration across multiple representative fires.",
        "NDVI is a spectral proxy for greenness/vigor and does not directly measure canopy closure, height, or stand age.",
        "AvCan forecast regions are operational forecasting zones (not administrative boundaries).",
        "All layers are reprojected for web mapping (WGS84 / EPSG:4326) for consistent display in the app.",
    ])

# ===================================================================
# Run Data Page Function
# ===================================================================
data_page()
