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

def fmt_int(n):
    return "—" if n is None else f"{int(n):,}"

def fmt_num(x, decimals=0):
    return "—" if x is None else f"{x:,.{decimals}f}"


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
    st.info("Upate In Progress (Jan 19th). Updating pipeline structure and summary statistics")
    st.divider()

   # Stage A config (derived layer metadata) 
   # =================================================================
    stage_a_cfg = load_yaml_config("stage_a.yaml") or {}
    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}
    stage_meta = stage_a_cfg.get("stage", {}) or {}

    dnbr_min = thresholds.get("dnbr_min")
    min_patch_area_ha = thresholds.get("min_patch_area_ha")
    min_patch_pixel = thresholds.get("min_patch_pixels")
    connectivity = thresholds.get("connectivity") or thresholds.get("pixel_conn")  # support either key
    dnbr_value = thresholds.get("dnbr_value")

    ref_region = calibration.get("reference_region")
    ref_gid = calibration.get("reference_gid")
    time_start = calibration.get("time_start")
    time_end = calibration.get("time_end")
    ref_note = calibration.get("note")

   # Summary stats data
   # =================================================================
    stats = load_yaml_config("summary_stats.yaml") or {}
    data = stats.get("data",{}) or {}
    nbac = stats.get("nbac",{}) or {}
    avcan = stats.get("avcan",{}) or {}
    stage_a_data = stats.get("stage_a",{}) or {}

    # ========== All Data =====================================
    min_year = data.get("min_year")
    max_year = data.get("max_year")
    n_years = data.get("n_years")

    # ========== nbac =====================================
    nbac_total_fires = nbac.get("total_fires")
    nbac_avg_fires_per_year = nbac.get("avg_fires_per_year")
    nbac_burn_ha = nbac.get("total_burn_ha")
    nbac_burn_km = nbac.get("total_burn_km2")
    nbac_avg_burn_ha_per_year = nbac.get("avg_burn_ha_per_year")
    nbac_avg_fire_burn_ha = nbac.get("avg_fire_burn_ha")
    nbac_avg_fire_burn_km = nbac.get("avg_fire_burn_km2")
    nbac_largest_id = nbac.get("largest_fire_id")
    nbac_largest_fire_prov = nbac.get("largest_fire_province")
    nbac_largest_fire_burn_ha = nbac.get("largest_fire_burn_ha")

    # ========== avcan =====================================
    avcan_total_fires = avcan.get("total_fires")
    avcan_avg_fires_per_year = avcan.get("avg_fires_per_year")
    avcan_median_fires_per_year = avcan.get("median_fires_per_year")
    avcan_total_burn_ha = avcan.get("total_burn_ha")
    avcan_total_burn_km = avcan.get("total_burn_km2")
    avcan_avg_burn_ha_per_year  = avcan.get("avg_burn_ha_per_year")
    avcan_avg_burn_km_per_year  = avcan.get("avg_burn_km2_per_year")
    avcan_median_burn_ha_per_year   = avcan.get("median_burn_ha_per_year")
    avcan_median_burn_km_per_year   = avcan.get("median_burn_km2_per_year")
    avcan_largest_id = avcan.get("largest_fire_id")
    avcan_largest_fire_prov = avcan.get("largest_fire_province")
    avcan_lagest_fire_region    = avcan.get("largest_fire_regions")
    avcan_largest_fire_burn_ha  = avcan.get("largest_fire_burn_ha")
    avcan_largest_fire_burn_km  = avcan.get("largest_fire_burn_km2")
    avcan_avg_fire_burn_ha = avcan.get("avg_burn_ha_per_fire_ha")
    avcan_avg_fire_burn_km = avcan.get("avg_burn_ha_per_fire_km2")
    avcan_median_fire_burn_ha  = avcan.get("median_burn_per_fire_ha")
    avcan_median_fire_burn_km = avcan.get("median_burn_per_fire_km2")
    avcan_90_percentile_burn_ha = avcan.get("p90_burn_ha_per_fire")
    avcan_95_percentile_burn_ha = avcan.get("p95_burn_ha_per_fire")

    # ========== stage_A =====================================
    A_total_patches = stage_a_data.get("total_patches")
    A_total_fires_w_patches = stage_a_data.get("total_fires_with_patches")
    A_avg_patches_per_fire_w_patches    = stage_a_data.get("avg_patches_per_fire_with_patches")
    A_median_patches_per_fire_w_patches = stage_a_data.get("median_patches_per_fire_with_patches")
    A_90_percentile_patches_per_fire_w_patches  = stage_a_data.get("p90_patches_per_fire_with_patches")
    A_avg_patches_per_avcan_fire    = stage_a_data.get("avg_patches_per_avcan_fire")
    A_total_patch_ha    = stage_a_data.get("total_patch_ha")
    A_avg_patch_ha  = stage_a_data.get("avg_patch_ha")
    A_median_patch_ha   = stage_a_data.get("median_patch_ha")
    A_90_percentile_patch_ha    = stage_a_data.get("p90_patch_ha")
    A_95_percentile_patch_ha    = stage_a_data.get("p95_patch_ha")
    A_largest_patch_id  = stage_a_data.get("largest_patch_id")
    A_largest_patch_region  = stage_a_data.get("largest_patch_region")
    A_largest_patch_subregion   = stage_a_data.get("largest_patch_subregion")
    A_largest_patch_ha  = stage_a_data.get("largest_patch_ha")
    A_largest_patch_km  = stage_a_data.get("largest_patch_km2")
    # ======= Coverage =======#
    A_pct_avcan_fires_w_patches = stage_a_data.get("pct_avcan_fires_with_patches")
    A_pct_avcan_burn_in_patches = stage_a_data.get("pct_avcan_burn_in_patches")
    A_patches_per_1000ha_burned = stage_a_data.get("patches_per_1000ha_burned")
    A_max_patch_year    = stage_a_data.get("max_patch_year")
    A_max_patch_year_ha = stage_a_data.get("max_patch_year_ha")
    A_top_region_patch_ha   = stage_a_data.get("top_region_by_patch_ha")
    A_top_region_patch_share    = stage_a_data.get("top_region_patch_share")
    # ======= Terrain =======#
    A_patch_mixed_aspect_pct    = stage_a_data.get("pct_patches_mixed_aspect")
    A_aspect_R_median   = stage_a_data.get("aspect_R_median")
    A_median_slope_deg  = stage_a_data.get("slope_mean_deg_median")
    A_median_elevation  = stage_a_data.get("elev_mean_m_median")
    
    

   # Core Layers 
   # =================================================================
    st.markdown("## Core Explorer layers")

    # ========== App Layer Files =====================================
    st.markdown("### App files")
    st.caption("Processed layers loaded by the Streamlit app (GeoParquet, reprojected to WGS84 / EPSG:4326).")
    st.markdown("""
    - **AvCan Region Perimeters:** `data/processed/app/Regions.parquet`
    - **Fire Perimeters:** `data/processed/app/Fires.parquet`
    - **Burn Severity Patches (Stage A):** `data/processed/app/Stage_A2_Burn_Severity_Patches.parquet`
    - **Regrowth Vegetation + Forest Inventory (Stage B - planned):** `data/processed/app/Stage_B_Regrowth_Patches.parquet`
    """)

    # ========== Data Lineage =====================================
    st.markdown("### Data lineage (raw → derived → app)")
    st.caption("High-level overview.")

    _bullet_list([
        "Raw: NBAC annual burned-area polygons (Natural Resources Canada / CWFIS).",
        "Raw: Avalanche Canada forecast polygons (regions/subregions).",
        "Python preprocessing: spatial overlay + labeling (NBAC + AvCan) → exported as an Earth Engine table asset.",
        "Google Earth Engine Python API: Stage A severity patches derived using dNBR + patch-size thresholds.",
        "Python post-processing: exported outputs normalized + saved as GeoParquet app layers (EPSG:4326).",
    ])

    # ========== Summary Statistics =====================================
    
    st.markdown("### Data Summary Statistics**")
    st.markdown(f"""
    The following data encompass summary statistics for {n_years} years, between {min_year} → {max_year}, for all datasets cleaned and computed throughout this proejct.
                """)

    # ======= NBAC =======#
    with st.expander("NBAC Fires",expanded=False):
        _kv("Total fires",fmt_int(nbac_total_fires))
        _kv("Average fires per year", fmt_num(nbac_avg_fires_per_year,2))
        _kv("Total burn",f"{fmt_num(nbac_burn_ha,2)} ha ({fmt_num(nbac_burn_km,2)} km²)")
        _kv("Average burn per year", f"{fmt_num(nbac_avg_burn_ha_per_year,2)} ha ({fmt_num(nbac_burn_km,2)} km²)")
        _kv("Average fire burn",f"{fmt_num(nbac_avg_fire_burn_ha,2)} ha ({fmt_num(nbac_avg_fire_burn_km,2)} km²)")
        _kv("Largest fire",f"Unique ID {nbac_largest_id} in {nbac_largest_fire_prov}")
        _kv("Largest fire burn (ha)", fmt_num(nbac_largest_fire_burn_ha,2))

    # ======= Avcan =======#
    with st.expander("Avalance Canada Fires",expanded = False):
        _kv("Total fires",fmt_int(avcan_total_fires))
        _kv("Average fires per year",fmt_num(avcan_avg_fires_per_year,2))
        _kv("Median fires per year",fmt_num(avcan_median_fires_per_year,2))
        _kv("Total burn",f"{fmt_num(avcan_total_burn_ha,2)} ha ({fmt_num(avcan_total_burn_km,2)} km²)")
        _kv("Average burn per year",f"{fmt_num(avcan_avg_burn_ha_per_year,2)} ha ({fmt_num(avcan_avg_burn_km_per_year,2)} km²)")
        _kv("Median burn per year",f"{fmt_num(avcan_median_burn_ha_per_year,2)} ha ({fmt_num(avcan_median_burn_km_per_year,2)} km²)")
        _kv("Average fire burn",f"{fmt_num(avcan_avg_fire_burn_ha,2)} ha ({fmt_num(avcan_avg_fire_burn_km,2)} km²)")
        _kv("Median fire burn",f"{fmt_num(avcan_median_fire_burn_ha,2)} ha ({fmt_num(avcan_median_fire_burn_km,2)} km²)")
        _kv("Largest fire",f"Unique ID {avcan_largest_id} in {avcan_lagest_fire_region}")
        _kv("Largest fire burn",f"{fmt_num(avcan_largest_fire_burn_ha,2)} ha ({fmt_num(avcan_largest_fire_burn_km,2)} km²)")

    
    
    # App Layers 
    # =================================================================
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
        _kv("What it is", "Avalanche forecasting region geometry boundaries.")
        _kv("Publisher", "Avalanche Canada")
        _kv("Why it’s used", "Defines the spatial extent for filtering fires and presenting results in backcountry-relevant regions.")
        _kv("Downloaded as", "GeoJSON")
        _kv("Shipped to app as", "`data/processed/app/Regions.parquet` (GeoParquet; WGS84 / EPSG:4326)")
        st.markdown("**Source:** https://github.com/avalanche-canada/forecast-polygons")
        _bullet_list([
            "File: `canadian_subregions.geojson`",
        ])

    # ========== Stage A =====================================
    
    with st.expander("Burn Severity Patches (Stage A)", expanded=True):
        _kv("What it is", "Derived burn-severity patches clipped to AvCan regions, produced from satellite-based severity logic and minimum patch-size filtering.")
        _kv("Why it’s used", "Represents candidate ‘burnt tree zone’ patches based on calibrated severity and patch-size thresholds.")
        _kv("Calibration reference", f"{ref_region} / Fire ID {ref_gid}" if (ref_region or ref_gid) else "Defined in stage_a.yaml")
        _kv("Shipped to app as", "`data/processed/app/Stage_A2_Burn_Severity_Patches.parquet` (GeoParquet; WGS84 / EPSG:4326)")

        if ref_note:
            _kv("Calibration note", ref_note)

        st.markdown("**Thresholds (from `stage_a.yaml`):**")
        t_items = []
        if dnbr_min is not None:
            t_items.append(f"Difference Normalized Burn Ratio (dNBR) ≥ {dnbr_min}")
        if min_patch_area_ha and min_patch_pixel is not None:
            t_items.append(f"Minimum patch area ≥ {min_patch_area_ha} ha / {min_patch_pixel} pixels ")
        if connectivity is not None:
            t_items.append(f"Pixel Connectivity: {connectivity}")
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
    
    
    with st.expander("Regrowth Vegetation + Forest Inventory (Stage B - Planned)", expanded=False):
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
