# Avalanche Canada Wildfire Explorer

Interactive geospatial analysis and map explorer that overlays **NBAC wildfire perimeters (1990–2024)** onto **Avalanche Canada (AvCan) forecast regions**, with a derived layer of **Burn Severity Patches (Stage A)** for terrain-focused exploration.

**Live app:** [Avalanche Canada Wildfire Explorer](https://avalanche-canada-fire-explorer.streamlit.app/)

> Disclaimer: This project is for informational and exploratory analysis only. It is not a safety product and should not be used to make operational or field safety decisions.

---

## Overview

### What it does
- Maps **NBAC burned-area polygons** inside **AvCan forecast regions**
- Provides an interactive **topographic map explorer** (Streamlit + Folium)
- Derives **Burn Severity Patches (Stage A)** using calibrated severity + minimum patch-size thresholds
- Computes summary statistics at **national**, **AvCan-filtered**, and **patch** scales

---

### Introduction
This geospatial analysis project maps Canadian wildfire perimeters from the National Burned Area Composite (NBAC) by Natural Resources Canada / CWFIS, within Avalanche Canada (AvCan) forecast regions. The goal is to make wildfire impacts more interpretable in backcountry-relevant terrain by combining fire perimeters with regional forecasting geographies, and producing an interactive topographic explorer. A derived map layer, "Burn Severity Patches (Stage A)", highlights post-fire areas that meet calibrated severity and minimum patch-size thresholds as potential “burnt tree zone” candidate areas for further evaluation of open-canopy post-fire terrain relevant to winter travel.

---

### Motivation
As an early-career data scientist, this self-guided project is a practical test of building an end-to-end geospatial pipeline. From data acquisition and spatial processing to analysis, visualization and deployment. It combines my work experience in the adventure sports and tourism industries with personal recreation in mountainous environments. Utilising my skillsets in applied geospatial data science using Google Earth Engine and Landsat imagery (dNBR/NDVI), terrain metrics, GeoPandas/Parquet workflows, and a Streamlit application to communicate results in a field-relevant way.

--- 

## Summary Statistics and Insights
The following summary statistics are calculated from NBAC records used in this project (1990–2024) and are reported at both national and AvCan-filtered scales where applicable. 

The data is copied from `streamlit_app/config/summary_stats.yaml`, which is extracted from `notebooks/national_wildfire_analysis.ipynb` after computation of final streamlit application datasets.

---

### How Stage A patches are created (high level)

Stage A identifies post-fire polygons that:
1. Meet calibrated spectral severity criteria (Landsat dNBR/NDVI-derived logic)
2. Exceed a minimum patch size threshold
3. Are enriched with terrain metadata (elevation, slope, aspect variability)

Full technical detail is documented in the Streamlit app’s **Method** page (and in the Stage A scripts).

---

### Highlights (1990–2024)

**National (NBAC)**
- Total fires: 39,616  
- Total burned area: 90,465,666 ha  

**AvCan-filtered (NBAC ∩ AvCan)**
- Total fires: 3,838  
- Total burned area: 2,271,966 ha  

**Stage A2 patches**
- Total patches: 6,625  
- Total patch area: 377,178.88 ha  
- Typical patch elevation (median of patch-mean elevations): 1,408 m  
- Typical patch slope (median of patch-mean slopes): 21.6°  

> Note: Summary statistics are sourced from `streamlit_app/config/summary_stats.yaml`, exported from `notebooks/national_wildfire_analysis.ipynb`.

---

## Quick start

### Prerequisites
- Python 3.10+ recommended
- Google Earth Engine (for Stage A scripts): `earthengine authenticate`
- (Optional) `gsutil` if pulling exports from GCS

### Install & run app
```bash
pip install -r requirements.txt
streamlit run streamlit_app/Home.py
```

### Optional: 
Reprocess EE exports layers with modified thresholds, and rebuild Streamlit-ready layers.
```bash
python scripts/05_stage_a1.py
python scripts/06_stage_a2.py
python scripts/07_stage_a_ee_export.py
python scripts/08_build_app_layers.py
```
- 



--- 

## Pipeline
- Download and process National Burn Area Composite (NBAC) file polygons.
    - `scripts/01_download_nbacs.py`

- Download Statistics Canada provinces and territories boundaries (2021)
    - `scripts/02_download_statscan_provinces.py`

- Clean and merge annual NBAC polygons into a single master fire-perimeter dataset
    - `scripts/03_clean_merge_nbac.py`

- Spatially overlay NBAC fire perimeters with AvCan forecasting regions and retain only fires within AvCan coverage.
    - `scripts/04_AvCan_fires_overlay.py`

- Identify Burn Severity Patches within AvCan fires with Google Earth Engine's python API. Looping through region/year and region/year/fireid arrangements.
    - `scripts/05_stage_a1.py`
        - (Optional) Modify **Stage A Burn Severity Patches** thresholds in file `streamlit_app/config/stage_a.yaml`
            - `dnbr_min`
            - `min_patch_area_ha`

        - If you change thresholds, you must rerun Stage A and rebuild app layers, otherwise the app may display thresholds that do not match the shipped dataset.

- Compute and append applicable geographical metadata to stage A1's Burn Severity Patches with Google Earth Engine's python API.
    - `scripts/06_stage_a2.py`

- Compile and export batches of stage A2's Burn Severity Patches to Google Cloud Storage (GCS) and download to local.
    - `scripts/07_stage_a_ee_export.py`
        - Pull Stage A2 GeoJSON exports from GCS (requires gsutil + auth)
            ```bash
            EXPORT_DIR="data/raw/stage_a2_geojson"
            GCS_URI="gs://<your-bucket>/exports/stage_a2_geojson/*.geojson"
            
            mkdir -p "$EXPORT_DIR"
            gsutil -m cp "$GCS_URI" "$EXPORT_DIR/"
            ```

- Build streamlit application-ready map explorer layers.
    - `scripts/08_build_app_layers.py`

---

### Next Steps:
- Stage B1 | Forest Inventory.
    - Download Vegetation Resource Inventory (VRI) for each AvCan region. Overlaying patches with VRI inventory polygons, appending selected VRI attributes (e.g Canopy openness, species composition, density/biomass proxies)
- Stage B2 | Regrowth Vegetation.
    - Compute Normalised Difference Vegetation Index (NDVI) from post-fire year to current, assessing and calibrating a regrowth threshold for optimal patch candidates.

---
## Data

### Sources
- #### National Burned Area Composite (NBAC)
    - **What it is**: National Burned Area Composite (NBAC): an annually updated national dataset of burned area polygons.
    - **Publisher**: Natural Resources Canada – Canadian Forest Service (CWFIS)
    - **Why it’s used**: Provides the fire perimeter geometry that is filtered to Avalanche Canada regions.
    - **Temporal coverage**: Annual records (project currently uses the years processed into the app layers).
    - **Fields include**:
        - year, cause, admin area, adjusted hectares, etc.
    - **Downloaded as**: One ZIP file per year (NBAC burned area polygons) for years 1990 – 2024.
    - **Transformed**: NBAC fire perimeters were intersected with Avalanche Canada forecast regions and split by subregions to create an AvCan-filtered fire-perimeter layer (NBAC fires within AvCan regions only).
    - **Shipped to app as**: `data/processed/app/Fires.parquet` (GeoParquet; WGS84 / EPSG:4326)
    - **Source**: [Canadian Forest Service - Natural Resources Canada](https://cwfis.cfs.nrcan.gc.ca)
    
- #### Avalanche Canada (AvCan) Forecast Regions
    - **What it is**: Avalanche forecasting region geometry boundaries.
    - **Publisher**: Avalanche Canada
    - **Why it’s used**: Defines the spatial extent for filtering fires and presenting results in backcountry-relevant regions.
    - **Downloaded as**: `canadian_subregions.geojson`
    - **Shipped to app as**: `data/processed/app/Regions.parquet` (GeoParquet; WGS84 / EPSG:4326)
    - **Source**: [Avalanche Canada Github Forecast Polygons](https://github.com/avalanche-canada/forecast-polygons)

- #### Provincial / Territorial boundaries (2021)
    - **What it is**: Cartographic boundary file for provinces/territories (2021 Census).
    - **Publisher**: Statistics Canada
    - **Why it’s used**: Provides national context and support sanity-check filtering / labeling during AvCan/NBAC overlay.
    - **File**: `lpr_000b21a_e.zip`
    - **Source**: [Statistics Canada Boundary Limits](https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?Year=21)

---

## Repository Structure
``` 
wildfire-risk-analysis/
│
├── streamlit_app/                      # Published application
│   ├── Home.py                         # Introduction / Overview / Roadmap
│   ├── pages/
│   │   ├── 01_Explorer.py              # Map + filters + layer toggles + metric cards
│   │   ├── 02_Method.py                # Stage A details + Stage B plan + assumptions
│   │   ├── 03_Data.py                  # Data dictionary + provenance + CRS + update cadence
│   ├── components/
│   │   ├── folium_map.py               # Wildfire Explorer map
│   │   ├── loaders.py                  # parquet map layers loader
│   │   ├── map_layers.py               # parquet map layers
│   │   ├── metrics.py                  # Explorer page summary statistics
│   │   ├── roadmap.py                  # Project status current + plans
│   │   └── sidebar.py                  # map manipulation bar
│   └── config/
│       ├── summary_stats.yaml          # Summary statistics for streamlit application map layers
│       ├── stage_a.yaml                # thresholds + reference fire metadata for computed stage a patches
│       └── regions.yaml                # Custom map centers/zoom defaults per region
│
├── data/
│   ├── external/
│   │   ├── avalanche_canada/
│   │   │   └── canadian_subregions.geojson     # AvCan forecast regions
│   │   ├── bc_vri/                             # Vegetation Resource Inventory data (Stage B)
│   │   └── stats_canada/
│   │       └── boundaries/                     # Provincial/territory polygons
│   ├── processed/
│   │   ├── analysis/                               
│   │   │   ├── avalanche_canada_fires/         # AvCan fires analysis outputs
│   │   │   ├── national_canadian_fires/        # Canadian fires analysis outputs
│   │   │   ├── NBAC/                           # Cleaned + Prepped NBAC fire perimeters
│   │   │   └── stage_A/
│   │   │       ├── stage_A1/                   # Jsons of Google EE Stage A patch job statuses 
│   │   │       └── stage_A2/                   # stage A2 batched files from Google EE / GCS export
│   │   │  
│   │   ├── app/                                # Map layers for streamlit application
│   │   │   ├── Fires.parquet                   # AvCan fires geometries
│   │   │   ├── Regions.parquet                 # AvCan region geometries
│   │   │   └── Stage_A2_Burn_Severity_Patches.parquet                   # Stage A Burn Severity Patches
│   │   ├── cached/
│   │   │   └── Canada_fires_1990_2024.parquet  # Cached parquet NBAC fires
│   │   └── share/
│   │       └── AvCan_layers.gpkg               # All streamlit app layers in singular gpkg
│   └── raw/
│       ├── Ecozones_of_Canada...json           # Province/Territory boundaries
│       └── NBAC/                               # Raw NBAC downloads by year
│
├── scripts/
│   ├── 01_download_nbacs.py                    # Download NBAC fire perimeters 
│   ├── 02_download_statscan_provinces.py       # Download province/territory data
│   ├── 03_clean_merge_nbac.py                  # Prepare NBAC fire perimeters 
│   ├── 04_AvCan_fires_overlay.py               # Overlay NBAC fire perimeters within AvCan forecast regions
│   ├── 05_stage_a1.py                          # Identify *Burn Severity Patches* within AvCan fires
│   ├── 06_stage_a2.py                          # Compute metadata of stage A's *Burn Severity Patches*
│   ├── 07_stage_a_ee_export.py                 # Export stage_A data to GCS and download to local
│   ├── 08_build_app_layers.py                  # Build parquet map layers for streamlit app    
│   └── 09_AOI_VRI_regions.py                   # Vegetation Resource Inventory analysis of stage a polygons (Stage B - In prgress)
│ 
├── notebooks/
│   ├── aoi_analysis.ipnb                       # Stage B VRI analysis - Next stage
│   ├── AvCan_wildfire_visualisations.ipnb      # DOCs visualisations
│   └── national_wildfire_analysis.ipynb        # Summary stats analysis of wildfires
│
├── outputs/
│   ├── figures/
│   └── tables/
│
├── docs/                                       # HTML plots + folium charts for sharing
│
├── .gitignore/   
├── requirements.txt
│
└── README.md
```



Mitchell J. R. Palmer
Geospatial / Environmental Data Science
Portfolio + contact links in profile.