# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd

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
    st.markdown("## Region Statistics")
    region_s = (region or "").replace("_", " ").title()
    st.caption(region_s)

    col_fires, col_A, col_B = st.columns(3, gap="medium")

    # =================================================================
    # Fires card
    # =================================================================
    with col_fires:
        with _card():
            st.markdown("#### Fires")

            fires_count = int(len(fires_f)) if (show_fires and fires_f is not None) else 0
            st.metric("Count", fires_count)

            if show_fires and fires_f is not None and not fires_f.empty and "Total Adjusted Area (ha)" in fires_f.columns:
                fires_ha = pd.to_numeric(fires_f["Total Adjusted Area (ha)"], errors="coerce").fillna(0).sum()
            else:
                fires_ha = 0
            st.metric("Area (ha)", f"{fires_ha:,.0f}")

            # Details (collapsed by default)
            with st.expander("Details", expanded=False):
                st.markdown("**Fire causes**")

                if show_fires and fires_f is not None and (not fires_f.empty) and ("Cause" in fires_f.columns):
                    vc = (
                        fires_f["Cause"]
                        .fillna("Unknown")
                        .astype(str)
                        .str.strip()
                        .replace({"": "Unknown"})
                        .value_counts(dropna=False)
                    )

                    df = vc.rename_axis("Cause").reset_index(name="Count")
                    total = int(df["Count"].sum()) or 1
                    df["Share"] = df["Count"] / total

                    st.dataframe(
                        df.style.format({"Count": "{:,}", "Share": "{:.0%}"}),
                        hide_index=True,
                        use_container_width=True,
                    )

                    # Optional small chart (only if not too many categories)
                    if len(df) <= 8:
                        st.bar_chart(df.set_index("Cause")["Count"], height=180)

                else:
                    st.caption("No fire-cause data available for the current selection.")

    # =================================================================
    # Stage A card
    # =================================================================
    with col_A:
        with _card():
            st.markdown("#### Stage A: Severity patches")

            a_count = int(len(patches_f)) if (show_patches and patches_f is not None) else 0
            st.metric("Count", a_count)

            if show_patches and patches_f is not None and not patches_f.empty and "Patch Area (ha)" in patches_f.columns:
                patch_total_ha = pd.to_numeric(patches_f["Patch Area (ha)"], errors="coerce").fillna(0).sum()
            else:
                patch_total_ha = 0
            st.metric("Area (ha)", f"{patch_total_ha:,.0f}")

            with st.expander("Details", expanded=False):
                st.markdown("**Stage A definition**")
                st.caption(
                    "Stage A patches are an exploratory layer identified by this project’s criteria "
                    "and are not an official Avalanche Canada product."
                )

                # Thresholds (clean formatting)
                st.markdown("**Thresholds**")
                if ref_gid:
                    st.caption(f"Calibrated on Fire GID {ref_gid}")

                parts = []
                if dnbr_min is not None:
                    parts.append(f"dNBR ≥ {dnbr_min:g}")
                if min_patch_area_ha is not None:
                    parts.append(f"Minimum patch area ≥ {min_patch_area_ha:g} ha")

                if parts:
                    st.markdown("\n".join([f"- {p}" for p in parts]))
                else:
                    st.caption("No thresholds found in stage_a.yaml.")

    # =================================================================
    # Stage B card
    # =================================================================
    with col_B:
        with _card():
            st.markdown("#### Stage B: Vegetation patches")

            # Use em dash to avoid implying a computed “0”
            # st.metric("Count", "—")
            # st.metric("Area (ha)", "—")

            st.info("Planned. This section will summarize Stage B criteria and outputs once implemented.")
