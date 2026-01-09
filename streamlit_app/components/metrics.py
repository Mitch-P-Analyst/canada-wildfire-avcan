# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd
import altair as alt

from .loaders import load_yaml_config


def _card():
    """Bordered card if supported; fallback otherwise."""
    try:
        return st.container(border=True)  # Streamlit newer versions
    except TypeError:
        return st.container()


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

    # -----------------------------
    # Config (Stage A thresholds)
    # -----------------------------
    stage_a_cfg = load_yaml_config("stage_a.yaml")
    thresholds = stage_a_cfg.get("thresholds", {}) or {}
    calibration = stage_a_cfg.get("calibration", {}) or {}

    dnbr_min = thresholds.get("dnbr_min")
    min_patch_area_ha = thresholds.get("min_patch_area_ha")
    ref_gid = calibration.get("reference_gid")

    # -----------------------------
    # Header
    # -----------------------------
    st.markdown("### Region Statistics")
    region_s = (region or "").replace("_", " ").title()
    st.markdown(f"Filtered region: **{region_s}**")

    col_fires, col_A, col_B = st.columns(3, gap="medium")

    # =================================================================
    # Fires card
    # =================================================================
    with col_fires:
        with _card():
            st.markdown("#### Fires")
            st.caption("NBAC Data")

            fires_count = int(len(fires_f)) if (show_fires and fires_f is not None) else 0
            st.metric("Count", fires_count)

            if show_fires and fires_f is not None and not fires_f.empty and "Total Adjusted Area (ha)" in fires_f.columns:
                fires_ha = pd.to_numeric(fires_f["Total Adjusted Area (ha)"], errors="coerce").fillna(0).sum()
            else:
                fires_ha = 0
            st.metric("Area (ha)", f"{fires_ha:,.0f}")

    # =================================================================
    # Stage A card
    # =================================================================
    with col_A:
        with _card():
            st.markdown("#### Burn Severity Patches")
            st.caption("(Stage A)")

            a_count = int(len(patches_f)) if (show_patches and patches_f is not None) else 0
            st.metric("Count", a_count)

            if show_patches and patches_f is not None and not patches_f.empty and "Patch Area (ha)" in patches_f.columns:
                patch_total_ha = pd.to_numeric(patches_f["Patch Area (ha)"], errors="coerce").fillna(0).sum()
            else:
                patch_total_ha = 0
            st.metric("Area (ha)", f"{patch_total_ha:,.0f}")

    # =================================================================
    # Stage B card
    # =================================================================
    with col_B:
        with _card():
            st.markdown("#### Regrowth Vegetation + Forest Inventory")
            st.caption("(Stage B)")

            # Use em dash to avoid implying a computed “0”
            # st.metric("Count", "—")
            # st.metric("Area (ha)", "—")

            st.info("Planned. This section will summarize Stage B criteria and outputs once implemented.")

    st.markdown("#### Fire Causes")

    if show_fires and fires_f is not None and (not fires_f.empty) and ("Cause" in fires_f.columns):
        vc = (
            fires_f["Cause"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace({"": "Unknown"})
            .value_counts(dropna=False)
        )

        causes_df = vc.rename_axis("Cause").reset_index(name="Count")
        total = int(causes_df["Count"].sum()) or 1
        causes_df["Share"] = causes_df["Count"] / total

        
        chart = (
            alt.Chart(causes_df)
            .mark_bar(
                color="#ffcc00de"
            )
            .encode(
                x=alt.X("Cause:N", sort="-y", axis=alt.Axis(labelAngle=45)),
                y=alt.Y("Count:Q"),
                tooltip=[
                    alt.Tooltip("Cause:N", title="Cause"),
                    alt.Tooltip("Count:Q", title="Count"),
                    alt.Tooltip("Share:Q", title="Share", format=".1%"),  # percent formatting
                ],
            )
        )

        st.altair_chart(chart, use_container_width=True)


    else:
        st.caption("No fire-cause data available for the current selection.")