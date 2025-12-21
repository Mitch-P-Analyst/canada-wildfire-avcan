#-- Packages --#

from pathlib import Path
import re
import requests
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

#-- Directories --#

REPO_ROOT = Path(__file__).resolve().parent.parent

app_data = REPO_ROOT / "data" / "processed" / "app"
app_data.mkdir(parents=True, exist_ok=True)

#-- Constants --#
Stage_A_Fires_path = app_data / "Stage_A_Fires.GPKG"
Stage_A_Patches_path = app_data / "Stage_A_Patches.GPKG"
Stage_A_Avcan_Regions_path = app_data / "AvCan_Regions.GPKG"

#-- Helper Functions --#

def _to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure WGS84 for web mapping."""
    if gdf.crs is None:
        # If you know the correct CRS, set it here instead of guessing.
        # gdf = gdf.set_crs("EPSG:XXXX", allow_override=True)
        pass
    if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def load_layers():
    fires = gpd.read_file( Stage_A_Fires_path, layer="Stage A Fires")
    patches = gpd.read_file(Stage_A_Patches_path, layer="Stage A Patches")
    regions = gpd.read_file(Stage_A_Avcan_Regions_path, layer="Stage A AvCan Regions")

    fires = _to_wgs84((fires))
    patches = _to_wgs84((patches))
    regions = _to_wgs84((regions))

    # drop empty geometries defensively
    fires = fires[~fires.geometry.is_empty & fires.geometry.notna()].copy()
    patches = patches[~patches.geometry.is_empty & patches.geometry.notna()].copy()
    regions = regions[~regions.geometry.is_empty & regions.geometry.notna()].copy()

    return fires, patches, regions


def bounds_center(gdf_list):
    """Compute a center from combined bounds."""
    bounds = None
    for gdf in gdf_list:
        if gdf is None or gdf.empty:
            continue
        b = gdf.total_bounds  # [minx, miny, maxx, maxy]
        if bounds is None:
            bounds = b
        else:
            bounds = [
                min(bounds[0], b[0]),
                min(bounds[1], b[1]),
                max(bounds[2], b[2]),
                max(bounds[3], b[3]),
            ]
    if bounds is None:
        return (54.5, -125.0), None  # fallback (BC-ish)
    center = ((bounds[1] + bounds[3]) / 2.0, (bounds[0] + bounds[2]) / 2.0)
    return center, bounds


#-- Body --#
def configure_page() -> None:
    st.set_page_config(page_title="Avalanche Canada Wildfire Explorer", layout="wide")

def configure_overview() -> None:
    st.markdown("# Avalanche Canada Wildfire Explorer")
    st.markdown("This Streamlit application generates a topographical map of forest fires recorded in the National Burn Area Composite (NBAC) by the Canadian Wildland Fire Information System, overlayed within Avalanche Canada (AvCan) forecasting regions, to communicate both awareness of forest fires within popular backcountry recreational areas and identify 'Burn Zones' applicable to recreational use in winter conditions.")
    st.divider()
    st.markdown("## Base Data")
    st.markdown("### AvCan Regions")
    st.markdown("Fires displayed below are filtered by selected Avalanache Canada forecasting region. This can be manipulated in the sidebar to the left of this page.")
    st.markdown("### Fire Perimeters")
    st.markdown("All fire polygons displayed are overlayed within regions with local projected coordinate reference systems and split across **AvCan subregions**.")
    st.divider()
    st.markdown("## Analysis")
    st.markdown("### Stage A")
    st.markdown("**Severity Patches** is the first stage in this analysis project to provide tanglible evidence of 'Burn Zones' in backcountry recreational areas. From reports of ")
    st.divider()
    
#--- UI --- #
def mapp_application() -> None:
    st.title("AvCan Wildfire Severity Explorer")
    st.caption("Interactive map of wildfire perimeters and Stage A burn-severity patches within Avalanche Canada regions.")


    fires, patches, regions = load_layers()

    # Derive regions list from available data
    regions_sel = sorted(set(fires["Region"].dropna().unique()).union(set(patches["Region"].dropna().unique())))

    with st.sidebar:
        st.header("Filters")

        region = st.selectbox("Region", options=regions_sel, index=0)

        # Year range from layers for that region
        fires_r = fires[fires["Region"] == region]
        patches_r = patches[patches["Region"] == region]
        region_f = regions[regions["Region"] == region]

        y_min = int(min(fires_r["Year"].min(skipna=True), patches_r["Year"].min(skipna=True)))
        y_max = int(max(fires_r["Year"].max(skipna=True), patches_r["Year"].max(skipna=True)))

        year_range = st.slider("Year range", min_value=y_min, max_value=y_max, value=(y_min, y_max), step=1)

        st.divider()
        st.subheader("Toggle Layers")
        show_fires = st.checkbox("Fire perimeters", value=True)
        show_patches = st.checkbox("Severity patches", value=True)
        show_region = st.checkbox("Region perimeter", value= True)

        st.divider()
        st.subheader("Legend")
        color_fires = st.color_picker(label="Fire perimeter", value= "#ffce00",label_visibility="visible")
        color_patches = st.color_picker(label="Severity patches", value= "#ff5a00",label_visibility="visible")
        st.write("Modify the colors presented on the map.")

        st.divider()
        st.subheader("Performance")
        simplify = st.checkbox("Simplify geometries (faster)", value=False)
        tol = st.slider("Simplification tolerance (degrees)", 0.0000, 0.0100, 0.0010, 0.0005) if simplify else 0.0

        st.divider()
        st.subheader("Context")
        st.write(
            "Stage A 'Severity patches' represent burned forest areas that meet an identified minimum patch size (≥10 ha) "
            "and dNBR severity threshold of 0.2, summarized by fire year."
        )
        st.write("This map is informational and not intended for safety-critical decision-making.")

    # Apply filters
    y0, y1 = year_range
    fires_f = fires_r[fires_r["Year"].between(y0, y1, inclusive="both")].copy()
    patches_f = patches_r[patches_r["Year"].between(y0, y1, inclusive="both")].copy()

    if simplify and tol > 0:
        fires_f["geometry"] = fires_f.geometry.simplify(tol, preserve_topology=True)
        patches_f["geometry"] = patches_f.geometry.simplify(tol, preserve_topology=True)
        region_f["geometry"] = region_f.geometry.simplify(tol, preserve_topology=True)

    # Layout: Map + Stats
    col_map, col_stats = st.columns([2.2, 0.8], gap="medium")

    with col_stats:
        # Header
        st.subheader("Summary")
        region_s = region.replace("_", " ").title()
        st.markdown(f"**Region:** {region_s}")
        st.divider()
    

        # Region fires
        st.markdown("#### Fires (filtered)")
        st.metric("Count", int(len(fires_f)) if show_fires else 0)
        fires_ha = fires_f["Total Adjusted Area (ha)"].astype(float).fillna(0).sum()
        st.metric("Hectares", f"{fires_ha:,.0f}" if show_fires else "0")
        st.divider()

        # Severity Patches
        st.markdown("#### Severity patches (filtered)")
        st.metric("Count", int(len(patches_f)) if show_patches else 0)
        patch_area_col = "Patch Area (ha)"
        patch_total_ha = patches_f[patch_area_col].astype(float).fillna(0).sum()
        st.metric("Hectares", f"{patch_total_ha:,.0f}" if show_patches else "0")
        
        st.caption("Tip: add “Total patch area (ha)” by computing area in a projected CRS (e.g., EPSG:3005).")

    with col_map:
        center, bnds = bounds_center([region_f])

        # --- Map view state ---
        if "map_center" not in st.session_state:
            st.session_state.map_center = None
        if "map_zoom" not in st.session_state:
            st.session_state.map_zoom = 11
        if "prev_region" not in st.session_state:
            st.session_state.prev_region = None

        region_changed = (st.session_state.prev_region != region)
        st.session_state.prev_region = region

        # Pull prior map view from the component state BEFORE rebuilding the map
        prev_map = st.session_state.get("map")  # because key="map" in st_folium

        if prev_map and not region_changed:
            prev_center = prev_map.get("center")
            prev_zoom = prev_map.get("zoom")

            # center can be dict {"lat":..,"lng":..} or list/tuple [lat,lng] depending on version
            if isinstance(prev_center, dict) and "lat" in prev_center and "lng" in prev_center:
                st.session_state.map_center = [prev_center["lat"], prev_center["lng"]]
            elif isinstance(prev_center, (list, tuple)) and len(prev_center) == 2:
                st.session_state.map_center = [prev_center[0], prev_center[1]]

            if isinstance(prev_zoom, (int, float)):
                st.session_state.map_zoom = int(prev_zoom)

                
        # If user has already panned/zoomed and region didn't change, keep that view
        start_location = st.session_state.map_center if (st.session_state.map_center and not region_changed) else center
        start_zoom = st.session_state.map_zoom if (st.session_state.map_center and not region_changed) else 11

        m = folium.Map(location=start_location, zoom_start=start_zoom, tiles="OpenTopoMap")

        if show_fires and not fires_f.empty:
            folium.GeoJson(
                fires_f,
                name="Fire perimeters",
                style_function=lambda x: {"color": color_fires, "weight": 2, "fill": False},
                tooltip=folium.GeoJsonTooltip(fields=[c for c in ["Region", "Subregion", "Year", "Unique Fire ID (gid)", "Total Adjusted Area (ha)"] if c in fires_f.columns]),
            ).add_to(m)

        if show_patches and not patches_f.empty:
            folium.GeoJson(
                patches_f,
                name="Severity patches",
                style_function=lambda x: {"color": color_patches, "weight": 1.5, "fill": True, "fillOpacity": 0.35},
                tooltip=folium.GeoJsonTooltip(fields=[c for c in ["Region","Subregion", "Year","Patch ID","Majority Cardinal Direction","Patch Area (ha)", "Mean Elevation (m)","Mean Slope Degree" ] if c in patches_f.columns]),
            ).add_to(m)

        if show_region and not region_f.empty:
            folium.GeoJson(
                region_f,
                name="AvCan Region",
                style_function=lambda x: {"color": "#000000", "weight": 2.5, "fill": False},
                tooltip=folium.GeoJsonTooltip(fields=[c for c in ["Region"] if c in region_f.columns]),
            ).add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

        # Fit bounds to data (if available)
        if bnds is not None and (region_changed or st.session_state.map_center is None):
            m.fit_bounds([[bnds[1], bnds[0]], [bnds[3], bnds[2]]])

        out = st_folium(m, key="map", width=None, height=700)


        # Only update stored view if streamlit-folium returns a non-null center/zoom
        # AND we did not just force a fit_bounds on this run.
        if out and not (region_changed or st.session_state.map_center is None):
            c = out.get("center")
            z = out.get("zoom")
            if isinstance(c, dict) and "lat" in c and "lng" in c:
                st.session_state.map_center = [c["lat"], c["lng"]]
            if isinstance(z, (int, float)):
                st.session_state.map_zoom = int(z)

#-- Main --#

def main() -> None:
    configure_page()
    configure_overview()
    mapp_application()

if __name__ == "__main__":
    main()