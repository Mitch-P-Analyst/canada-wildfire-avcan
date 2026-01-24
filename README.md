# Avalanche Canada Wildfire Explorer

Interactive geospatial analysis and map explorer that overlays **NBAC wildfire perimeters (1990–2024)** onto **Avalanche Canada (AvCan) forecast regions**, with a derived layer of **Burn Severity Patches (Stage A)** for terrain-focused exploration.

**Live app:** [Avalanche Canada Wildfire Explorer](https://avalanche-canada-fire-explorer.streamlit.app/)

> **Important:** This project is an informational mapping and analysis tool. The derived **Burn Severity Patches (Stage A)** layer is a **screening heuristic** intended to highlight **candidate areas for follow-on verification** (e.g., using current imagery, local knowledge, and appropriate professional guidance).  
> It is **not** a safety product and must **not** be used for route selection, terrain selection, or trip planning decisions.

---

## Overview

### What it does
- Maps **NBAC burned-area polygons** inside **AvCan forecast regions**
- Provides an interactive **topographic map explorer** (Streamlit + Folium)
- Derives **Burn Severity Patches (Stage A)** using calibrated severity + minimum patch-size thresholds
- Computes summary statistics at **national**, **AvCan-filtered**, and **patch** scales

---

### Introduction
This project overlays Canadian wildfire perimeters from the National Burned Area Composite (NBAC) onto Avalanche Canada (AvCan) forecast regions to make wildfire impacts more tangible in mountainous landscapes. In addition to mapping perimeters and regional statistics, the project generates a supplemental layer, **Burn Severity Patches (Stage A)**, which applies configurable spectral-severity and minimum patch-size logic to highlight **candidate post-fire areas for follow-on verification** (e.g., exploring where canopy-loss conditions may exist).

Stage A outputs are best interpreted as a **screening layer** for exploratory research and communication: they can help focus attention on areas that may warrant further review, but they do not confirm on-the-ground conditions, access, hazards, or recreational suitability.


---

### Motivation
As an early-career data scientist, this self-guided project is a practical test of building an end-to-end geospatial pipeline. From data acquisition and spatial processing to analysis, visualization and deployment. It combines my work experience in the adventure sports and tourism industries with personal recreation in mountainous environments. Utilising my skillsets in applied geospatial data science using Google Earth Engine and Landsat imagery (dNBR/NDVI), terrain metrics, GeoPandas/Parquet workflows, and a Streamlit application to communicate results in an applied, user-facing way.

--- 

## Summary Statistics and Insights
The following summary statistics are calculated from NBAC records used in this project (1990–2024) and are reported at both national and AvCan-filtered scales where applicable. 

The data is copied from `streamlit_app/config/summary_stats.yaml`, which is extracted from `notebooks/national_wildfire_analysis.ipynb` after computation of final streamlit application datasets.

---

### Derived map layer - Burn Severity Patches (Stage A)

Stage A identifies post-fire polygons that:
- Meet a calibrated severity criteria for Landsat dNBR ≥ 0.2. 
    - Calibrated against NBAC **fire ID 1990_106** in AvCan region South Coast Inland due to first-hand reports of severity conditions.
- Exceed a minimum patch size threshold ≥ 10 ha
- Enriched with terrain metadata (elevation, slope, aspect variability)

Full technical detail is documented in the Streamlit app’s **Method** page (and in the Stage A scripts).

#### Calibration and limitations
The derived **Burn Severity Patches** from identified thresholds are calibrated to a reference fire and are intended as an initial heuristic. Results are sensitive to Landsat spatial resolution, the seasonal composite window, regional vegetation differences, and the timing of post-fire imagery. 

Future exploration can broaden Stage A calibration across multiple representative fires and the planned Stage B (Regrowth Vegetation + Forest Inventory) will investigate forestry attributes for further analysis, such as canopy openness/crown closure, density/biomass proxies and non-tree vegetation descriptors.

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

## Run Application
There are two common ways to run this project locally:

### Prerequisites
- Python 3.10+ recommended
- Google Earth Engine (for Stage A scripts): `earthengine authenticate`
- (Optional) `gsutil` if pulling exports from GCS


### Option 1: Pre-developed map layers
Run a local streamlit application using the prebuilt parquet app layers shipped in `data/processed/app/`. 

```bash
pip install -r requirements.txt
streamlit run streamlit_app/Home.py
```

### Option 2: Full rebuild map layers
Reproduce all datasets and derived layers (requires Google Earth Engine, personal project id, exports, and longer runtimes), with the option to modifiy thresholds.
> Note: Reprocessing all scripts below may take >48 hours with Google Earth Engine's python API. 

Run all python scripts the the **Pipeline** section below.

--- 

## Pipeline
- Download and process National Burn Area Composite (NBAC) file polygons for years filtered (1990 - 2024).
    - `scripts/01_download_nbacs.py`

- Download Statistics Canada provinces and territories boundaries (2021)
    - `scripts/02_download_statscan_provinces.py`

- Clean and merge annual NBAC polygons into a single master fire-perimeter dataset
    - `scripts/03_clean_merge_nbac.py`

- Create Google Cloud Project (GCP)and resulting Google Cloud Storage (GCS) Bucket
    - [Create Google Cloud Project](https://developers.google.com/workspace/guides/create-project)
    - [Create Google Cloud Storage Bucket](https://console.cloud.google.com/storage/overview)

- Update YAML file with GCP Earth Engine Project ID and Google Cloud Storage (GCP) export bucket 
    - `scripts/config/google_ee.yaml`
        - `earth_engine`:
            - `project_id`: # "YOUR_GCP_PROJECT_ID"
        - `google_cloud_storage`:
            -  `GCS_bucket` # "YOUR_GCS_BUCKET_PATH

- (Optional) Modify **Stage A Burn Severity Patches** thresholds in yaml file 
    - `scripts/config/google_ee.yaml`:
        - `thresholds`:
            - `dnbr_min`    # dNBR threshold for Stage A1 patches
            - `min_patch_area_ha`   # Minimum size logic for Stage A1 patches
            - `r_threshold` # Aspect coherence threshold for Stage A2 aspect labels

- Spatially overlay NBAC fire perimeters with AvCan forecasting regions and retain only fires within AvCan coverage.
    - `scripts/04_AvCan_fires_overlay.py`

- Identify Burn Severity Patches within AvCan fires with Google Earth Engine's python API. Looping through region/year and region/year/fireid arrangements.
    - `scripts/05_stage_a1.py`
        - This script computes aggregated analyses of region-subregion-year groups, before re-try attempts on aggreates that met EE memory threshold, by analysing remaining individual Fire IDs.

- Compute and append applicable geographical metadata to stage A1's Burn Severity Patches with Google Earth Engine's python API.
    - `scripts/06_stage_a2.py`

- Compile and export batches of stage A2's Burn Severity Patches to Google Cloud Storage (GCS) and download to local.
    - `scripts/07_stage_a_ee_export.py`

- Pull Stage A2 GeoJSON exports from GCS (requires gsutil + auth)
        - This python scripts produces a bash script using values from scripts/config/google_ee.yaml
```bash
python scripts/tools/render_readme_snippets.py
``` 
        - This resulting bash file downloads the batches Stage_A2 GeoJSON exports from GCS
```bash
bash scripts/tools/pull_stage_a2_from_gcs.sh
```

- Build streamlit application-ready map explorer layers.
    - `scripts/08_build_app_layers.py`

- Run local streamlit application
```bash
streamlit run streamlit_app/Home.py
```

---

### Next Steps:
- Stage B1 | Forest Inventory.
    - Download Vegetation Resource Inventory (VRI) for each AvCan region. Overlaying patches with VRI inventory polygons, appending selected VRI attributes (e.g Canopy openness, species composition, density/biomass proxies)

- Stage B2 | Regrowth Vegetation.
    - Compute Normalised Difference Vegetation Index (NDVI) from post-fire year to current, assessing and calibrating a regrowth threshold for optimal patch candidates.

---
## Data

### Sourced
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

### Derived layers

- #### Burn Severity Patches (Stage A)
    - **What it is**: Stage A is a **screening heuristic** that identifies post-fire polygons that meet a calibrated Landsat spectral severity threshold (default: dNBR ≥ 0.2) and exceed a minimum patch size threshold (default: ≥ 10 ha). The patches are then enriched with terrain metadata (elevation, slope, and aspect variability)
    - **How to interpret**: These patches are **candidates for follow-on verification**, not a confirmation of “open trees,” “good skiing,” or safety. The layer can be used to support exploratory mapping and analysis of landscape change, and to guide where deeper review may be worthwhile (e.g., reviewing current satellite imagery, consulting local knowledge, land managers, and professional guides). If using Stage A patches as a starting point for further investigation, candidates should be verified with additional context such as:
        - Recent satellite imagery / aerial imagery (post-fire regrowth can change rapidly)
        - Land access status and closures (parks, private tenure, active forestry operations)
        - Local terrain knowledge and conditions (blowdown, snags, creek changes)
        - Current avalanche and weather information (Stage A does not evaluate avalanche conditions)
        - Professional judgment (guides, land managers, local experts)
    Stage A is designed to support exploratory mapping and prioritization of follow-up, not to replace these checks.
    - **Why it's used**: Highlights post-fire patches meeting configured severity and patch-size thresholds as **candidates for follow-on verification** (exploratory screening layer; not a suitability or safety layer).
    - **Shipped to app as**: `data/processed/app/Stage_A2_Burn_Severity_Patches.parquet` (GeoParquet; WGS84 / EPSG:4326)
    - **Calibration and limitations:**: Stage A thresholds are calibrated as a practical, repeatable approach to highlight potential canopy-loss conditions using widely used spectral proxies. Calibration is anchored to a reference fire and region (South_Coast_Inland / Fire ID 1990_106). Results are sensitive to Landsat spatial resolution, seasonal composite window, regional vegetation differences, and timing of post-fire imagery. dNBR is a severity proxy and is not a direct measurement of canopy openness, hazard, access, or suitability.
    - **Thresholds** (from stage_a.yaml):
        - Difference Normalized Burn Ratio (dNBR) ≥ 0.2
        - Minimum patch area ≥ 10 ha / ≈ 49–50 pixels
        - Pixel Connectivity: 8-neighbour
        - Seasonal window used for composites: June 1st to October 31st
    - **Produced with**: Google Earth Engine python API.

Full technical detail is documented in the Streamlit app’s **Method** page (and in the Stage A scripts).

- ##### Interpreting “Candidate Areas” (Verification Checklist)
If using Stage A patches as a starting point for further investigation, candidates should be verified with additional context such as:
- Recent satellite imagery / aerial imagery (post-fire regrowth can change rapidly)
- Land access status and closures (parks, private tenure, active forestry operations)
- Local terrain knowledge and conditions (blowdown, snags, creek changes)
- Current avalanche and weather information (Stage A does not evaluate avalanche conditions)
- Professional judgment (guides, land managers, local experts)

Stage A is designed to support exploratory mapping and prioritization of follow-up, not to replace these checks.

---

### Data Contract (Shipped App Layers)

The Streamlit application reads the following GeoParquet layers from `data/processed/app/`. These are treated as the stable interface between the pipeline and the app UI.

| Layer | Path | Geometry | CRS | Required fields (minimum) | Notes |
|---|---|---:|---:|---|---|
| Fires | `data/processed/app/Fires.parquet` | Polygon / MultiPolygon | EPSG:4326 | `geometry`, `Year`, `Region`, `Subregion`, `National Park`, `Total Adjusted Area (ha)`, `Cause`, `Province/Territory`, `Subregion Area (ha)`, `Unique Fire ID (gid)` | AvCan-filtered NBAC perimeters split by AvCan subregion; may include additional NBAC attributes (cause, admin area, adjusted area). |
| Regions | `data/processed/app/Regions.parquet` | Polygon / MultiPolygon | EPSG:4326 | `geometry`, `Region`, `Subregion`, `Province/Territory` | Avalanche Canada forecast region boundaries used for filtering, aggregation, and map navigation. |
| Burn Severity Patches (Stage A2) | `data/processed/app/Stage_A2_Burn_Severity_Patches.parquet` | Polygon / MultiPolygon | EPSG:4326 | `geometry`,`Year`, `Region`, `Subregion`, `Aspect Label`,`Aspect Coherence (R)`, `Mean Elevation (m)`, `Unique Fire ID (gid)`, `Patch Area (ha)`, `Mean Slope Degree`,`Unique Patch ID` | Derived patches meeting configured severity + minimum area criteria; enriched with terrain metrics (e.g., elevation/slope summaries and aspect variability). |

**Contract expectations**
- All three layers must be valid GeoParquet with a geometry column and correct CRS.
- Region labeling must be consistent across layers (same `Region`/`Subregion` naming convention).
- If Stage A thresholds change, `Stage_A2_Burn_Severity_Patches.parquet` and any displayed summary statistics should be regenerated to keep the app consistent.


## Repository Structure
``` 
canada-wildfire-avcan/
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
│   ├── config/    
│   │   └── google_ee.yaml                      # Google Earth Engine script threholds, callibrations, asset IDs and folder structures 
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
---


Mitchell J. R. Palmer
Geospatial / Environmental Data Science
Portfolio + contact links in profile.