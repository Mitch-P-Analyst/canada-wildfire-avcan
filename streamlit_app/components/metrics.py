# ===================================================================
# Imports
# ===================================================================
import streamlit as st
import pandas as pd
import geopandas as gpd
import altair as alt

from .loaders import load_yaml_config

# ===================================================================
# Helper Functions
# ===================================================================
def _card():
    """Bordered card if supported; fallback otherwise."""
    try:
        return st.container(border=True)  # Streamlit newer versions
    except TypeError:
        return st.container()
    
def pct_bar(p: float | None, height_px: int = 10) -> None:
    """Gradient progress bar (yellow→orange) with the fill clipped to percentage."""
    if p is None:
        p = 0.0
    p = max(0.0, min(1.0, float(p)))
    pct = p * 100

    st.markdown(
        f"""
        <div style="
            width:100%;
            height:{height_px}px;
            background: rgba(255,255,255,0.10);
            border-radius: 999px;
            overflow:hidden;
        ">
          <div style="
              width:{pct:.1f}%;
              height:{height_px}px;
              background: linear-gradient(90deg, #FFD54A 0%, #FF8C00 100%);
              border-radius: 999px;
          "></div>
        </div>
        """,
        unsafe_allow_html=True,
    )



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
    st.markdown("#### Layer Totals")

    col_fires, col_A, col_B = st.columns(3, gap="medium")

    # =================================================================
    # Fires card
    # =================================================================
    with col_fires:
        with _card():
            st.markdown("##### Fires")
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
            st.markdown("##### Burn Severity Patches")
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
            st.markdown("##### Regrowth Vegetation + Forest Inventory")
            st.caption("(Stage B)")

            # Use em dash to avoid implying a computed “0”
            # st.metric("Count", "—")
            # st.metric("Area (ha)", "—")

            st.info("Planned. This section will summarize Stage B statistics once implemented.")

    st.markdown("#### Fire Causes")

    CAUSE_ORDER = ["Human", "Natural", "Undetermined"]  # fixed display order

    if show_fires and fires_f is not None and (not fires_f.empty) and ("Cause" in fires_f.columns):

            # Normalize cause strings
            s = (
                fires_f["Cause"]
                .fillna("Undetermined")
                .astype(str)
                .str.strip()
                .replace({"": "Undetermined", "Unknown": "Undetermined"})
            )

            # Count and force all categories to exist (0 if missing)
            counts = s.value_counts(dropna=False).reindex(CAUSE_ORDER, fill_value=0)

            causes_df = counts.rename_axis("Cause").reset_index(name="Count")
            total = int(counts.sum()) or 1
            causes_df["Share"] = causes_df["Count"] / total

    else:
            # If layer is off / no data, still show cards with zeros
            causes_df = pd.DataFrame({"Cause": CAUSE_ORDER, "Count": [0, 0, 0], "Share": [0.0, 0.0, 0.0]})
            total = 0

    # ---- render cards (always 3) ----
    cols = st.columns(3, gap="medium")

    for col, cause in zip(cols, CAUSE_ORDER):
            row = causes_df.loc[causes_df["Cause"].eq(cause)].iloc[0]
            count = int(row["Count"])
            share = float(row["Share"])

            with col:
                with _card():
                    st.markdown(f"##### {cause}")
                    st.metric("Fires", f"{count:,}")
                    st.caption(f"{share:.1%} of fires" if total > 0 else "—")
                    pct_bar(share, height_px=10)  # your yellow→orange gradient bar
