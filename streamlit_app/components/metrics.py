# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd

from .loaders import load_yaml_config


# ===================================================================
# Metrics Function
# ===================================================================
def render_metrics_column(
    region: str,
    fires_f: gpd.GeoDataFrame,
    patches_f: gpd.GeoDataFrame,
    show_fires: bool,
    show_patches: bool,
) -> None:
    
    # Constants 
    # =================================================================
    stage_a_cfg = load_yaml_config("stage_a.yaml")
    
    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    dnbr_min = thresholds.get("dnbr_min")                 # e.g., 0.2
    min_patch_area_ha = thresholds.get("min_patch_area_ha")  # e.g., 10
    ref_gid = calibration.get("reference_gid")            # e.g., "1990_106"

    # Body 
    # =================================================================
    
    # ========== Header =====================================
    st.markdown("## Summary Statistics")
    region_s = (region or "").replace("_", " ").title()
    st.markdown(f"### Region: {region_s}")
    st.divider()

         # Layout: Map + Stats
    col_fires, col_A, col_B = st.columns([1, 1, 1], gap="medium")


    with col_fires:
        # Fires
        st.markdown("#### Fires")
        st.metric("Count", int(len(fires_f)) if (show_fires and fires_f is not None) else 0)

        if show_fires and fires_f is not None and not fires_f.empty and "Total Adjusted Area (ha)" in fires_f.columns:
            fires_ha = pd.to_numeric(fires_f["Total Adjusted Area (ha)"], errors="coerce").fillna(0).sum()
        else:
            fires_ha = 0

        st.metric("Hectares", f"{fires_ha:,.0f}")
        st.divider()
        # --- Fire causes breakdown (bullet list) ---
        st.markdown("**Fire Causes:**")

        if show_fires and fires_f is not None and (not fires_f.empty) and ("Cause" in fires_f.columns):
            vc = (
                fires_f["Cause"]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
                .replace({"": "Unknown"})
                .value_counts(dropna=False)
            )

            bullets = "\n".join([f"- {cause}: {count:,}" for cause, count in vc.items()])
            st.markdown(bullets)
        else:
            st.markdown("- N/A")

    with col_A:
        # Severity Patches
        st.markdown("#### Stage A: Severity Patches")
       
        st.metric("Count", int(len(patches_f)) if (show_patches and patches_f is not None) else 0)

        if show_patches and patches_f is not None and not patches_f.empty and "Patch Area (ha)" in patches_f.columns:
            patch_total_ha = pd.to_numeric(patches_f["Patch Area (ha)"], errors="coerce").fillna(0).sum()
        else:
            patch_total_ha = 0

        st.metric("Hectares", f"{patch_total_ha:,.0f}")
        st.divider()

          # --- YAML-driven caption (Stage A thresholds) ---
        parts = []
        if dnbr_min is not None:
            parts.append(f"dNBR ≥ {dnbr_min:g}")
        if min_patch_area_ha is not None:
            parts.append(f"min patch area ≥ {min_patch_area_ha:g} ha")

        if parts:
            suffix = f" (calibrated on Fire GID {ref_gid})" if ref_gid else ""
            bullets = "\n".join([f"- {p}" for p in parts])
            st.markdown(f"**Thresholds{suffix}:**\n{bullets}")

    with col_B:
        # Regrowth Patches
        st.markdown("#### Stage B: Regrowth Patches")
        st.metric("Count", 0)

        st.metric("Hectares", 0)
        st.divider()
        st.markdown("**Planned.**")
