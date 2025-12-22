# streamlit_app/components/folium_map.py

# ===================================================================
# Packages
# ===================================================================
import folium

# ===================================================================
# Functions
# ===================================================================

def build_folium_map(
    *,
    start_location,
    start_zoom,
    region_gdf,
    fires_gdf,
    patches_gdf,
    show_fires: bool,
    show_patches: bool,
    show_region: bool,
    color_fires: str,
    color_patches: str,
    bounds=None,
    fit_bounds: bool = False,
):
    m = folium.Map(location=start_location, zoom_start=start_zoom, tiles="OpenTopoMap")

    if show_fires and fires_gdf is not None and not fires_gdf.empty:
        folium.GeoJson(
            fires_gdf,
            name="Fire perimeters",
            style_function=lambda _: {"color": color_fires, "weight": 2, "fill": False},
            tooltip=folium.GeoJsonTooltip(
                fields=[c for c in ["Region", "Subregion", "Year", "Unique Fire ID (gid)", "Total Adjusted Area (ha)"] if c in fires_gdf.columns],
                labels=True,
            ),
        ).add_to(m)

    if show_patches and patches_gdf is not None and not patches_gdf.empty:
        folium.GeoJson(
            patches_gdf,
            name="Severity patches",
            style_function=lambda _: {"color": color_patches, "weight": 1.5, "fill": True, "fillOpacity": 0.35},
            tooltip=folium.GeoJsonTooltip(
                fields=[c for c in ["Region","Subregion","Year","Patch ID","Majority Cardinal Direction","Patch Area (ha)","Mean Elevation (m)","Mean Slope Degree"] if c in patches_gdf.columns],
                labels=True,
            ),
        ).add_to(m)

    if show_region and region_gdf is not None and not region_gdf.empty:
        folium.GeoJson(
            region_gdf,
            name="AvCan Region",
            style_function=lambda _: {"color": "#000000", "weight": 2.5, "fill": False},
            tooltip=folium.GeoJsonTooltip(fields=[c for c in ["Region"] if c in region_gdf.columns], labels=True),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    if fit_bounds and bounds is not None:
        minx, miny, maxx, maxy = bounds
        m.fit_bounds([[miny, minx], [maxy, maxx]])

    return m
