# ===================================================================
# Imports
# ===================================================================
from datetime import datetime
import streamlit as st

# ===================================================================
# Components
# ===================================================================
from components.loaders import load_app_layers, app_data_dir
from components.loaders import _kv, _bullet_list, fmt_int, fmt_num, fmt_pct
from components.loaders import load_yaml_config
# ===================================================================
# Helpers
# ===================================================================

def _safe_nunique(df, col: str) -> int:
    if df is None or col not in df.columns:
        return 0
    return int(df[col].dropna().nunique())

def _safe_minmax_year(*dfs) -> tuple[int | None, int | None]:
    vals = []
    for df in dfs:
        if df is not None and "Year" in df.columns:
            s = df["Year"].dropna()
            if not s.empty:
                vals.append(int(s.min()))
                vals.append(int(s.max()))
    if not vals:
        return None, None
    return min(vals), max(vals)

# ===================================================================
# Roadmap Section Function
# ===================================================================
def roadmap_section() -> None:
    # Intro
    st.subheader("Project Roadmap")
    st.write("The current progress and planned steps for the Avalanche Canada Wildfire Explorer.")

    # ===================================================================
    # Constants
    # ===================================================================
    stage_a_cfg = load_yaml_config("stage_a.yaml")
    stats = load_yaml_config("summary_stats.yaml")

    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    data = stats.get("data", {}) or {}
    nbac_stats = stats.get("nbac",{}) or {}
    avcan_stats = stats.get("avcan", {}) or {}
    stage_a_stats = stats.get("stage_a", {}) or {}
    # Value Extraction 
    # =================================================================

    # ========== Data =====================================
    min_year = data.get("min_year")
    max_year = data.get("max_year")

    # ======= NBAC =======#
    avg_fire_count_per_year = nbac_stats.get("avg_fires_per_year")
    avg_burn_area_per_year_ha = nbac_stats.get("avg_burn_ha_per_year")
    avg_burn_area_per_year_km = nbac_stats.get("avg_burn_km2_per_year")

    # ======= Avcan =======#
    avcan_total_fires = avcan_stats.get("total_fires")

    # ======= Burn Severity Patches =======#
    A_total_patches = stage_a_stats.get("total_patches")

    # -----------------------------------------------------------------
    # CURRENT STATUS
    # -----------------------------------------------------------------
    st.markdown("#### Current Project Status")

    with st.expander("Burn Severity Patches (Stage A)", expanded=True):
        try:
            fires_path   = app_data_dir / "Fires.parquet"
            patches_path = app_data_dir / "Stage_A2_Burn_Severity_Patches.parquet"
            regions_path = app_data_dir / "Regions.parquet"

            fires_mtime   = fires_path.stat().st_mtime
            patches_mtime = patches_path.stat().st_mtime
            regions_mtime = regions_path.stat().st_mtime

            fires, patches, regions = load_app_layers(
                app_data_dir,
                fires_mtime,
                patches_mtime,
                regions_mtime,
            )

            # Totals (prefer unique names, not raw row counts)
            total_regions = regions["Region"].nunique()

            # “Computed regions” should reflect where Stage A patches exist
            regions_sel = sorted(regions["Region"].dropna().unique().tolist()) if "Region" in regions.columns else []
            if not regions_sel:
                regions_sel = sorted(set(fires["Region"].dropna().unique()).union(set(patches["Region"].dropna().unique())))

            computed_regions = len(regions_sel)
            coverage_pct = (computed_regions / total_regions * 100) if total_regions else 0.0

            y_min, y_max = _safe_minmax_year(fires, patches)

            last_updated_epoch = max([fires_mtime, patches_mtime, regions_mtime])
            last_updated = datetime.fromtimestamp(last_updated_epoch).strftime("%Y-%m-%d")

            # At-a-glance metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Avcan regions covered", f"{computed_regions}/{total_regions}", f"{coverage_pct:.0f}%")
            c2.metric("Fires loaded", f"{avcan_total_fires:,}")
            c3.metric("Stage A patches", f"{A_total_patches:,}")
            c4.metric("Last updated", last_updated)

            # Optional detail line
            if y_min is not None and y_max is not None:
                _kv("Years covered", f"{y_min}–{y_max}")

            st.markdown(
                "Burn Severity Patches are now successfully generated for all 22 Avcan foresting regions."
            )

        except Exception as e:
            st.warning(f"Could not load app layer data. ({e})")
            st.markdown(
                "Stage A severity patches have been calibrated and generated for a subset of Avalanche Canada regions. "
                "Additional processing in Google Earth Engine will expand coverage over time."
            )

    # -----------------------------------------------------------------
    # NEXT STAGES
    # -----------------------------------------------------------------
    st.markdown("#### Next Stages")

    with st.expander("Regrowth Vegetation + Forest Inventory (Stage B - Planned)", expanded=False):
        st.markdown("""
        A **Normalized Difference Vegetation Index (NDVI)** time-series will be computed on Stage A's Burn Severity Patches from each post-fire year to the current year. This assessment will aim to **calculate the amount of vegetation regrowth since fire occurance**.
                    
        Additionally, this project plans to integrate vegetation inventory data (specifically the British Columbia **Vegetation Resources Inventory (VRI)** ) to characterize applicable Stage A Burn Severity Patches with forest stand-structure attributes derived from the inventory's aerial photo interpretation and supporting field data. Potential stand-structure descriptors that may help interpret post-fire canopy conditions include canopy closure/openness, stand height, species composition, biomass proxies, and sparsity/openness classes.
        
        For further information on techinical method and planned analytical processes can be found on the **Method** page.
                                """)

    with st.expander("Validation (Planned)", expanded=False):
        validation_list = [
            "Validate Stage A + Stage B against 2–3 reference fires (ideally across different regions) to verify thresholds and expected patterns."
        ]
        _bullet_list(validation_list)

    with st.expander("Streamlit Performance + UX (Ongoing)", expanded=False):
        performance_list = [
            "Cache loaded layers and derived summaries to reduce page latency.",
            "Differentiate Stage A vs Stage B clearly with toggles, legends, and consistent naming."
        ]
        _bullet_list(performance_list)

    with st.expander("Potential Plans (Future)", expanded=False):
        future_list = [
            "Add average monthly snowpack depth summaries for Stage A + Stage B patches (context for terrain/snow response post-fire).",
            "Add a **Forest Service Roads** map layer for insight to accessability of identified Stage A + B patches.",
            "Add a selector and **export feature** to download polygon perimeter coordinates for chosen burn-severity patches and/or fire perimeters, enabling field navigation and planning in Google Earth, Gaia GPS, and Strava/FatMap."
        ]
        _bullet_list(future_list)


