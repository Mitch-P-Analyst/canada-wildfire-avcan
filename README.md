# Wildfire Counts in Avalanche Canada Regions (2014–2024)

In Progress.

## Overview
The current status of this geospatial analysis project is exploring how Canadian wildfire perimeters intersect Avalanche Canada forecast regions. The current phase focuses on building a clean, multi-year wildfire dataset from NBAC (National Burned Area Composite), overlaying it with Avalanche Canada subregions, and summarizing/visualizing wildfire counts by region.

### Project Status (so far)

- Download and combine NBAC wildfire perimeters into a single multi-year GeoDataFrame
- Clean and standardize schema (using 2024 as the canonical column set)
- Export a reduced, analysis-ready Canada-wide fires shapefile + GeoJSON
- Overlay fire perimeters with Avalanche Canada regions
- Produce wildfire count summaries and a choropleth map by forecast region
- Use Google Earth Engine + Sentinel-2 to compute NBR / dNBR time series
- Quantify vegetation loss/recovery in singular AVCan regions

#### Next Steps:
- Scale NBR / dNBR time terids and vegetation loss across all AvCan regions
- Compare counts vs area burned, severity, and temporal trends
- Identify high burn scars in Avalanche Canada regions

### Data Sources
- NBAC – National Burned Area Composite (Canada wildfires)
    - Annual national wildfire perimeter products.
    - Used here for 2014–2024 fire polygons.
    - Fields include:
        - year, cause, admin area, adjusted hectares, etc.

- Avalanche Canada Forecast Regions
    - Subregion polygons used for avalanche forecasting and public hazard products.
    - Used as the spatial aggregation unit for wildfire counts.

- Statistics Canada – Provincial/Territorial Boundaries
    - Used for validating / assigning fire admin_area via overlays (BC, AB, YT, NL, etc.).
    - Ensures fires in National Parks (PC) are not dropped in provincial filtering.

- (Next Steps) Parks Canada National Parks + Provincial Parks polygons
    - Used to tag fires by park_type and park_name.

## Repository Structure
``` 
wildfire-risk-analysis/
│
├── avcan_map_app/
│   ├── app.py                          # Overview / landing page (Stage status + how to use)
│   ├── pages/
│   │   ├── 01_Explorer.py              # Map + filters + layer toggles + metric cards
│   │   ├── 02_Method.py                # Stage A details + Stage B plan + assumptions
│   │   ├── 03_Data.py                  # Data dictionary + provenance + CRS + update cadence
│   │   └── 04_Roadmap.py               # Changelog + backlog + known issues
│   ├── components/
│   │   ├── sidebar.py                  # region/year/stage controls (single source of truth)
│   │   ├── metrics.py                  # summary stats cards
│   │   ├── legends.py                  # map legend blocks
│   │   └── text.py                     # standardized copy for Stage A/B descriptions
│   └── config/
│       ├── stage_a.yaml                # thresholds + reference fire metadata
│       └── regions.yaml                # optional: map centers/zoom defaults per region
│
├── data/
│   ├── external/
│   │   ├── avalanche_canada/
│   │   │   └── canadian_subregions.geojson     # AVCan forecast regions
│   │   └── stats_canada/
│   │       └── boundaries/                     # Provincial/territory polygons
│   ├── processed/
│   │   ├── analysis/                               
│   │   │   ├── avalanche_canada_fires/
│   │   │   ├── national_canadian_fires/
│   │   │   ├── NBAC/
│   │   │   ├── severe_burns/
│   │   │   ├── stage_A/
│   │   │   ├── subregions_fires/
│   │   │   └── Canada_fires/
│   │   ├── app/
│   │   └── share/
│   └── raw/
│       └── NBAC/                               # Raw NBAC downloads by year
│
├── scripts/
│   ├── 01_download_nbac.py
│   ├── 02_download_statscan_provinces.py
│   ├── 03_clean_merge_nbac.py
│   ├── 04_avcan_fires_overlay.py
│   └── 05_build_app_layers.py                             
│
├── notebooks/
│   ├── 06_wildfire_avcan_analysis.IPYNB                   # Working notebook
│   └── severe_burns.ipynb                                 # Next steps
│
├── outputs/
│   ├── figures/
│   └── tables/
│
├── docs/                                                  # HTML plots + folium charts for sharing
│
├── .gitignore/   
├── requirements.txt
│
└── README.md
```

## Setup

### Environment

- Recommended Python stack:
    - geopandas
    - pandas
    - shapely
    - matplotlib / plotly

### Install
```
pip install -r requirements.txt
```

## Key Outputs
- Processed fires file
- Canada_fires_{min_year}_{max_year}.geojson
- Canada_fires_{min_year}_{max_year}.shp

- Fields retained for analysis:
    - gid 
        - unique fire perimeter id
    - fireid 
        - NBAC fire identifier
    - year
        - fire year
    - admin_area 
        - province/territory
    - natpark
        - NBAC park indicator (when available)
    - adj_ha
        - adjusted burned area (hectares)
    - cause
        - human/natural/unknown categories
    - geometry
        - fire perimeter polygon

- AVCan summary
    - Fire counts per Avalanche Canada region (2014–2024)
    - Choropleth map showing highest totals in interior BC and Alberta


Mitchell J. R. Palmer
Geospatial / Environmental Data Science
Portfolio + contact links in profile.