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
from components.loaders import fmt_int, fmt_num, fmt_pct , _kv, _bullet_list, _bullet_kv

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


# ===================================================================
# Data Page Function
# ===================================================================
def data_page() -> None:

    # Intro 
    # =================================================================
    st.title("Data")
    # st.info("Upate In Progress (Jan 19th). Updating pipeline structure and summary statistics")
    st.divider()

    st.markdown("## Overview")
    st.markdown("This page documents the datasets and map layers used by the AvCan Wildfire Explorer. It describes what each layer represents, where it was sourced from, and how it is packaged for the application. It also provides project-wide summary statistics for each core dataset to complement the region-filtered metrics shown in the Explorer.")

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
    nbac_largest_fire_burn_km = nbac.get("largest_fire_burn_km2")
    nbac_natural_cause = nbac.get("natural_cause")
    nbac_human_cause = nbac.get("human_cause")
    nbac_undetermined_cause = nbac.get("undetermined_cause")

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
    avcan_natural_cause = avcan.get("natural_cause")
    avcan_human_cause = avcan.get("human_cause")
    avcan_undetermined_cause = avcan.get("undetermined_cause")

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
    
    
    # Datasets 
    # =================================================================
    st.markdown("## Dataset summary")
    
    # ========== Summary Statistics =====================================
    
    st.markdown("### Summary Statistics")
    st.caption(f"""
    Summary statistics of the available {n_years} years ({min_year} → {max_year}) for the accessed and derived datasets computed throughout this project.
                """)

    # ======= NBAC =======#
    with st.expander("NBAC Fires",expanded=False):
        nbac_fires_list = [
        ("Total fires",fmt_int(nbac_total_fires)),
        ("Average fires per year", fmt_num(nbac_avg_fires_per_year,2)),
        ("Total burn area",f"{fmt_num(nbac_burn_ha,2)} ha ({fmt_num(nbac_burn_km,2)} km²)"),
        ("Average burn area per year", f"{fmt_num(nbac_avg_burn_ha_per_year,2)} ha ({fmt_num(nbac_burn_km,2)} km²)"),
        ("Average fire burn area",f"{fmt_num(nbac_avg_fire_burn_ha,2)} ha ({fmt_num(nbac_avg_fire_burn_km,2)} km²)"),
        ("Largest fire",f"Unique ID {nbac_largest_id} in {nbac_largest_fire_prov}"),
        ("Largest fire burn area",f"{fmt_num(nbac_largest_fire_burn_ha,2)} ha ({fmt_num(nbac_largest_fire_burn_km,2)} km²)"),
        ("Natural caused", fmt_pct(nbac_natural_cause,2)),
        ("Human caused", fmt_pct(nbac_human_cause,2)),
        ("Undetermined caused", fmt_pct(nbac_undetermined_cause,2))
        ]
        
        _bullet_kv(nbac_fires_list)

    # ======= Avcan =======#
    with st.expander("Avalanche Canada Fires",expanded = False):
        regions_str = ", ".join(avcan_lagest_fire_region)  # "Jasper" or "Region A, Region B"
        avcan_fires_list = [
        ("Total fires",fmt_int(avcan_total_fires)),
        ("Average fires per year",fmt_num(avcan_avg_fires_per_year,2)),
        ("Median fires per year",fmt_num(avcan_median_fires_per_year,2)),
        ("Total burn area",f"{fmt_num(avcan_total_burn_ha,2)} ha ({fmt_num(avcan_total_burn_km,2)} km²)"),
        ("Average burn area per year",f"{fmt_num(avcan_avg_burn_ha_per_year,2)} ha ({fmt_num(avcan_avg_burn_km_per_year,2)} km²)"),
        ("Median burn area per year",f"{fmt_num(avcan_median_burn_ha_per_year,2)} ha ({fmt_num(avcan_median_burn_km_per_year,2)} km²)"),
        ("Average fire burn area",f"{fmt_num(avcan_avg_fire_burn_ha,2)} ha ({fmt_num(avcan_avg_fire_burn_km,2)} km²)"),
        ("Median fire burn area",f"{fmt_num(avcan_median_fire_burn_ha,2)} ha ({fmt_num(avcan_median_fire_burn_km,2)} km²)"),
    
        ("Largest fire",f"Unique ID {avcan_largest_id} in {regions_str}"),
        ("Largest fire burn area",f"{fmt_num(avcan_largest_fire_burn_ha,2)} ha ({fmt_num(avcan_largest_fire_burn_km,2)} km²)"),

        ("Natural caused", fmt_pct(avcan_natural_cause,2)),
        ("Human caused", fmt_pct(avcan_human_cause,2)),
        ("Undetermined caused", fmt_pct(avcan_undetermined_cause,2))
        ]
        _bullet_kv(avcan_fires_list)

    # ======= Stage A =======#
    with st.expander("Burn Severity Patches (Stage A)", expanded=False):
        stage_a_list = [
        ("Total patches",fmt_int(A_total_patches)),
        ("Total fires with patches",fmt_int(A_total_fires_w_patches)),
        ("Average patches per Stage A fire (fires with patches)",fmt_num(A_avg_patches_per_fire_w_patches,2)),
        ("Median patches per Stage A fire (fires with patches)",fmt_num(A_median_patches_per_fire_w_patches,2)),
        ("Average patches per AvCan fire (All Avcan fires)",fmt_num(A_avg_patches_per_avcan_fire,2)),
        ("Total patches burn area",f"{fmt_num(A_total_patch_ha,2)} ha"),
        ("Average patch burn area",f"{fmt_num(A_avg_patch_ha,2)} ha"),
        ("Median patch burn area", f"{fmt_num(A_median_patch_ha,2)} ha"),
        ("95th percentile patch burn area", f"{fmt_num(A_95_percentile_patch_ha,2)} ha"),
        ("Largest patch", f"Unique ID {A_largest_patch_id} in {A_largest_patch_region}"),
        ("Largest patch burn area",f"{fmt_num(A_largest_patch_ha,2)} ha ({fmt_num(A_largest_patch_km,2)} km²)"),
        ("Median of elevation means",f"{fmt_num(A_median_elevation,2)} m"),
        ("Median of slope degree means",f"{fmt_num(A_median_slope_deg,2)}%"),

        ("Percentage of Avcan fires with Burn Severity Patches",f"{fmt_pct(A_pct_avcan_fires_w_patches,2)}"),
        ("Percentage of Avcan fire burn area identified as Burn Severity Patches",f"{fmt_pct(A_pct_avcan_burn_in_patches,2)}"),
        ("Fire year that produced the highest number of patches",f" {A_max_patch_year} with {fmt_num(A_max_patch_year_ha)} ha burned"),
        ("Region with largest patches burn area",f"{A_top_region_patch_ha}"),

        ("Percentage of patches with mixed aspect", fmt_pct(A_patch_mixed_aspect_pct,2))
        ]
        _bullet_kv(stage_a_list)
    
    st.divider()
   # Core Layers 
   # =================================================================
    st.markdown("## Explorer Layers")

    # ========== App Layer Files =====================================
    st.markdown("### App files")
    st.caption("Primary layers displayed in the Explorer and used for filtering and summary statistics.")
    st.markdown("""
    - **AvCan Region Perimeters:** `data/processed/app/Regions.parquet`
    - **Fire Perimeters:** `data/processed/app/Fires.parquet`
    - **Burn Severity Patches (Stage A):** `data/processed/app/Stage_A2_Burn_Severity_Patches.parquet`
    """)

    # App Layers 
    # =================================================================
    st.markdown("### Layer Descriptions")
    st.caption("The primary layers shown on the interactive map and used for filtering and summary statistics.")
    
    # ========== NBAC Fires =====================================

    with st.expander("NBAC Fire Perimeters (Natural Resources Canada / CWFIS)", expanded=True):
        _kv("What it is", "National Burned Area Composite (NBAC): an annually updated national dataset of burned area polygons.")
        _kv("Publisher", "Natural Resources Canada – Canadian Forest Service (CWFIS)")
        _kv("Why it’s used", "Provides the fire perimeter geometry that is filtered to Avalanche Canada regions.")
        _kv("Temporal coverage", "Annual records (project currently uses the years processed into the app layers).")
        _kv("Downloaded as", "One ZIP file per year (NBAC burned area polygons).")
        _kv("Transformed", "NBAC fire perimeters were intersected with Avalanche Canada forecast regions and split by subregions to create an AvCan-filtered fire-perimeter layer (NBAC fires within AvCan regions only).")
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
        _kv("What it is", "Stage A is a **screening heuristic** that identifies post-fire polygons that meet a calibrated Landsat spectral severity threshold and exceed a minimum patch size threshold. The patches are then enriched with terrain metadata (elevation, slope, and aspect variability)")
        _kv("How to interpret","These patches are **candidates for follow-on verification**, not a confirmation of “open trees,” “good skiing,” or safety. The layer can be used to support exploratory mapping and analysis of landscape change, and to guide where deeper review may be worthwhile (e.g., reviewing current satellite imagery, consulting local knowledge, land managers, and professional guides).")
        _kv("Why it’s used", "Highlights post-fire patches meeting configured severity and patch-size thresholds as **candidates for follow-on verification** (exploratory screening layer; not a suitability or safety layer).")
        _kv("Calibration and limitations",f"Stage A thresholds are calibrated as a practical, repeatable approach to highlight potential canopy-loss conditions using widely used spectral proxies. Calibration is anchored to a reference fire and region ({ref_region} / Fire ID {ref_gid}" if (ref_region or ref_gid) else 'Defined in stage_a.yaml'"). Results are sensitive to Landsat spatial resolution, seasonal composite window, regional vegetation differences, and timing of post-fire imagery. dNBR is a severity proxy and is not a direct measurement of canopy openness, hazard, access, or suitability.")
        _kv("Shipped to app as", "`data/processed/app/Stage_A2_Burn_Severity_Patches.parquet` (GeoParquet; WGS84 / EPSG:4326)")
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

        _kv("Produced with", "Google Earth Engine python API.")
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
        st.markdown("**Planned output:** `data/processed/app/Stage_B_Regrowth_Patches.parquet`")

    st.divider()

   # Supporting / context layers 
   # =================================================================
    st.markdown("## Supporting and Context Datasets")
    st.caption("These datasets support preprocessing, validation, and cartographic context, but are not necessarily displayed as primary Explorer layers.")

    with st.expander("Provincial / Territorial boundaries (2021)", expanded=False):
        _kv("What it is", "Cartographic boundary file for provinces/territories (2021 Census).")
        _kv("Publisher", "Statistics Canada")
        _kv("Why it’s used", "Provides national context and can support sanity-check filtering / labeling during Avcan/NBAC overlay.")
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

# ===================================================================
# Run Data Page Function
# ===================================================================
data_page()
