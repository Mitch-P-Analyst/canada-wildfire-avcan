import streamlit as st
import pandas as pd
import geopandas as gpd


def render_metrics_column(
    region: str,
    fires_f: gpd.GeoDataFrame,
    patches_f: gpd.GeoDataFrame,
    show_fires: bool,
    show_patches: bool,
) -> None:
    # Header
    st.subheader("Summary")
    region_s = (region or "").replace("_", " ").title()
    st.markdown(f"**Region:** {region_s}")
    st.divider()

    # Fires
    st.markdown("#### Fires (filtered)")
    st.metric("Count", int(len(fires_f)) if (show_fires and fires_f is not None) else 0)

    if show_fires and fires_f is not None and not fires_f.empty and "Total Adjusted Area (ha)" in fires_f.columns:
        fires_ha = pd.to_numeric(fires_f["Total Adjusted Area (ha)"], errors="coerce").fillna(0).sum()
    else:
        fires_ha = 0

    st.metric("Hectares", f"{fires_ha:,.0f}")
    st.divider()

    # Patches
    st.markdown("#### Severity patches (filtered)")
    st.metric("Count", int(len(patches_f)) if (show_patches and patches_f is not None) else 0)

    if show_patches and patches_f is not None and not patches_f.empty and "Patch Area (ha)" in patches_f.columns:
        patch_total_ha = pd.to_numeric(patches_f["Patch Area (ha)"], errors="coerce").fillna(0).sum()
    else:
        patch_total_ha = 0

    st.metric("Hectares", f"{patch_total_ha:,.0f}")
