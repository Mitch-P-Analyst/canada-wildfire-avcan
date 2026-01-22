# streamlit_app/components/sidebar.py
import streamlit as st

def sidebar_controls(regions_sel, y_min, y_max):
    with st.sidebar:
        st.header("Filters")

        region = st.selectbox("Region", options=regions_sel, index=0)
        year_range = st.slider("Year range", min_value=y_min, max_value=y_max, value=(y_min, y_max), step=1)

        st.divider()
        st.subheader("Toggle Layers")
        show_region = st.checkbox("AvCan Region Perimeter", value=True)
        show_fires = st.checkbox("Fire Perimeters", value=True)
        show_patches = st.checkbox("Burn Severity Patches", value=True)

        st.divider()
        st.subheader("Legend")
        color_fires = st.color_picker("Fire perimeter", value="#F700FF")
        color_patches = st.color_picker("Burn Severity patches", value="#ff5a00")

        st.divider()
        st.subheader("Performance")
        simplify = st.checkbox("Simplify geometries (faster)", value=False)
        tol_m = st.slider("Simplification tolerance (meters)", 0, 250, 30, 10) if simplify else 0

    return {
        "region": region,
        "year_range": year_range,
        "show_fires": show_fires,
        "show_patches": show_patches,
        "show_region": show_region,
        "color_fires": color_fires,
        "color_patches": color_patches,
        "simplify": simplify,
        "tol_m": tol_m,
    }
