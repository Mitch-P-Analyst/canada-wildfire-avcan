# ===================================================================
# Packages
# ===================================================================



# ========== Operations =========================================


import numpy as np
import pandas as pd
from pathlib import Path
import sys
import os
import zipfile
import shutil
import geopandas as gpd
from shapely.geometry import Polygon
import textwrap

# ===================================================================
# Directories
# ===================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / 'data/'
processed_dir = data_dir / 'processed' / 'analysis/'
processed_NBAC_dir = processed_dir / 'NBAC/'
raw_dir = data_dir / "raw" / "NBAC"


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))



# ===================================================================
# Helper Functions
# ===================================================================




# Unzip all Shapefiles
def unzip_to_folder(zip_path, extract_to):              # Unzip NBAC files to destination
    """
    Unzips a ZIP archive into a specified directory.
    """
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)                  # Read SHP to destination folder

    macosx_folder = extract_to / '__MACOSX'
    if macosx_folder.exists():
        shutil.rmtree(macosx_folder)


# Function to merge identifed rows split across description
def merge_meta_rows(df, main_idx, extra_idxs):
    parts = [str(df.loc[main_idx, "Attribute"]).strip()]
    for i in extra_idxs:
        field_i = str(df.loc[i, "Field"]).strip()
        attr_i  = str(df.loc[i, "Attribute"]).strip()
        parts.append(f"{field_i} {attr_i}")
    df.loc[main_idx, "Attribute"] = " ".join(parts)
    return df.drop(extra_idxs).reset_index(drop=True)


# Function to split Provonical/Territory abbreviations from descriptions
def split_field_dash(df, field_col="Field", attr_col="Attribute"):
    # 1. rows where the Field contains a dash
    mask = df[field_col].astype(str).str.contains("-", na=False)

    # 2. split on the first '-' into two parts
    split = df.loc[mask, field_col].astype(str).str.split("-", n=1, expand=True)
    split.columns = ["abbr", "name_part"]

    # 3. clean up pieces
    abbr = split["abbr"].str.strip()
    name_part = split["name_part"].fillna("").str.strip()   # text after '-'
    existing_attr = df.loc[mask, attr_col].fillna("").str.strip()

    # 4. combine name_part + existing_attr (add a space only if both non-empty)
    glue = np.where((name_part != "") & (existing_attr != ""), " ", "")
    combined_attr = (name_part + glue + existing_attr).str.strip()

    # 5. write back into the original dataframe
    df.loc[mask, field_col] = abbr
    df.loc[mask, attr_col] = combined_attr

    return df


# ===================================================================
# Constants
# ===================================================================

zippaths = Path(data_dir/'raw/zips')                    # ZIPs folders
zipfolders = list(zippaths.glob('*.zip'))               # Select all .ZIP




# ===================================================================
# Process
# ===================================================================
print('Begin National Burn Area Composite (NBAC) file cleaning.\n')

print('1. Shapefiles.\n')

# ===== Shapefiles =========================================

print('Unzipping NBAC shapefiles...')
for folder in zipfolders:
    unzip_to_folder(folder,processed_dir/'shapefiles'/str(folder.name)[:-4])    # Retain name indentity
    print(f'NBAC Wildfires Year: {(str(folder.name)[5:9])} Shapefiles opened')

print(f'Target folder destination: {processed_dir/'shapefiles'} \n')




# ===== Open All Shapefiles ===== #
print('Opening all shapefiles...')

print(f'Appending into singular dictionary...')
all_gdfs_dct = {}   # Store in dictionary

for folder in (processed_dir / "NBAC/Shapefiles").iterdir(): # shapefiles directory
    if folder.is_dir():
        shp = next(folder.glob("*.shp"), None)          # specific shapefiles
        if shp:
            name = folder.name
            all_gdfs_dct[name] = gpd.read_file(shp)     # Geopandas read

print('All shapefiles opened. \n')




# ===== Assess each shapefile's (key) column structure ===== #

print(f'Beginning Cleaning. \n')
# 1. Get a singular shapefile as the reference file

# Reference shapefile
reference_year = 2024
print(f'Utilise singular shapefile structure as reference guide. \n Referenced shapefile: Year {reference_year}')
    
# Acquire candidate reference file
candidate = [k for k in all_gdfs_dct.keys() if str(reference_year) in str(k)]

if not candidate:
    raise KeyError(f"No shapefile containing reference year {reference_year} found in all_gdfs_dct.")
if len(candidate) > 1:
    print(f"Multiple shapefiles containing reference year {reference_year} candidates found. Using the first: {candidate}")


ref_key = candidate[0]
# Use reference shapefile columns
ref_cols = set(all_gdfs_dct[ref_key].columns)

# 2. Create a dictionary for any irregular shapefiles 
irregular = {}

# 3. Mark columns that exist in each GeoDataFrame
print(f'Comparing shapefile structure to reference file...')
for name, gdf in all_gdfs_dct.items():
    cols = set(gdf.columns)

# 4. Assess column structure
    missing_from_this = sorted(ref_cols - cols)
    extra_in_this     = sorted(cols - ref_cols)
# 5. Identify irregular shapefiles
    if missing_from_this or extra_in_this:
        irregular[name] = {
            f"missing_vs_{reference_year}": missing_from_this,
            f"extra_vs_{reference_year}": extra_in_this
        }

if not irregular:
    print(f" All shapefiles match the {reference_year} reference structure: {ref_key}")
else:
    print(f"{len(irregular)} shapefile(s) differ from {reference_year} reference: {ref_key}\n")
    for name, diffs in irregular.items():
        print(f"- {name}")
        if diffs[f"missing_vs_{reference_year}"]:
            print(f"   missing: {diffs[f'missing_vs_{reference_year}']}")
        if diffs[f"extra_vs_{reference_year}"]:
            print(f"   missing: {diffs[f'missing_vs_{reference_year}']}")
        if diffs[f"extra_vs_{reference_year}"]:
            print(f"   extra:   {diffs[f'extra_vs_{reference_year}']}")
        print()

    raise ValueError(f"Irregular column structures detected vs {reference_year}. See details above.")


# ===== Singular GDF Location ===== #

print(f'\nProducing singular GDF..')


# 1. Pick a reference CRS from the first GeoDataFrame
first_gdf = next(iter(all_gdfs_dct.values()))
target_crs = first_gdf.crs

gdfs_to_concat = []

for name, gdf in all_gdfs_dct.items():
    # reproject if needed
    if gdf.crs != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    # either keep only columns shared by all:
    # gdf = gdf[common_cols]

    # or, if you’re okay with missing columns being NaN, skip that line
    gdfs_to_concat.append(gdf)

# 2. Stack them vertically
fires_all_years = gpd.GeoDataFrame(
    pd.concat(gdfs_to_concat, ignore_index=True),
    crs=target_crs
)

# 3. Combine

combined = {"NBAC_all_years": fires_all_years}
all_gdf_df = combined["NBAC_all_years"]
print(f' Singular GDF produced.')

print(f' All fire geometries dataframe shape: {all_gdf_df.shape} \n')

# print(f'Null Values: \n{all_gdf_df.isnull().sum()}\n')


#--- Geodataframe Cleaning ---#

# 1. Create copy
all_gdf_df = all_gdf_df.copy()

# 2. rename and format columns 
col_names = {
    'Shape_Leng' : "shape_length",
    "FIRECAUS": "CAUSE",
    "NFIREID": "FIREID",
    'ADMIN_AREA':'prov_terr'
}

all_gdf_df = all_gdf_df.rename(columns=col_names)
print(f'Columns formatted')


# 3. lower-case all column names in one line
all_gdf_df.columns = all_gdf_df.columns.str.lower()

# 4. reassign datatypes
all_gdf_df['year'] = all_gdf_df['year'].astype(int)
all_gdf_df['fireid'] = all_gdf_df['fireid'].astype(int)
all_gdf_df['hs_sdate'] = all_gdf_df['hs_sdate'].astype('datetime64[ns]')
all_gdf_df['hs_edate'] = all_gdf_df['hs_edate'].astype('datetime64[ns]')
all_gdf_df['ag_sdate'] = all_gdf_df['ag_sdate'].astype('datetime64[ns]')
all_gdf_df['ag_edate'] = all_gdf_df['ag_edate'].astype('datetime64[ns]')
all_gdf_df['capdate'] = all_gdf_df['capdate'].astype('datetime64[ns]')

print(f'Column datatypes assigned.')
cols = ['gid', 'fireid', 'year', 'prov_terr', 'natpark', 'adj_ha','cause', 'geometry']
print(f'Columns selected for further analysis: \n {cols}')
Canfires_simple = all_gdf_df[cols].copy()

# Identify year range (cast to int to avoid "2014.0")
Canfires_year_min = int(Canfires_simple['year'].min())
Canfires_year_max = int(Canfires_simple['year'].max())

# Reproject to WGS84 for GeoJSON / broad compatibility
print('Reprojecting CRS...')
Canfire_4326 = Canfires_simple.to_crs(epsg=4326)
print(f' Reprojected CRS for GeoJSON export: {Canfire_4326.crs}')

print(f'\nCleaning complete. \n')


#--- Canada Fires Export ---#
print(f'Beginning Export procedure.')
# Output folder
out_dir = processed_dir / "national_canadian_fires"
out_dir.mkdir(parents=True, exist_ok=True)

# ---- GeoJSON export ----
Canfires_path_geojson = out_dir / f"Canada_fires_{Canfires_year_min}_{Canfires_year_max}.geojson"
print('Exporting Canadian fires GeoJSON...')

try:
    Canfire_4326.to_file(Canfires_path_geojson, driver="GeoJSON")
    print(f'GeoJSON export successful: {Canfires_path_geojson}')
except Exception as e:
    raise RuntimeError(f'Canadian fires GeoJSON failed to export: {e}')

# ---- Shapefile export ----
Canfires_path_shp = out_dir / f"Canada_fires_{Canfires_year_min}_{Canfires_year_max}.shp"
print('Exporting Canadian fires Shapefile...')

try:
    Canfire_4326.to_file(Canfires_path_shp, driver="ESRI Shapefile")
    print(f'Shapefile export successful: {Canfires_path_shp}')
except Exception as e:
    raise RuntimeError(f'Canadian fires Shapefile failed to export: {e}\n')



# ========== Summary Statistics =========================================
# =================================================================


print('2. Summary Statistics.\n')


print('Load (NBAC) summary statistics Excel file')
# Find all matching NBAC formatted summarystats_*.xlsx files
summary_files = sorted(raw_dir.glob("NBAC_summarystats_*.xlsx"))

if not summary_files:
    raise FileNotFoundError(" No NBAC_summarystats_*.xlsx found in data/raw")

# If there's more than one, take the last (alphabetically = usually latest)
data_path = summary_files[-1]

print(f" Using summary statistics file: {data_path.name}")

NBAC = pd.read_excel(data_path, sheet_name=None)
print(f'NBCA Summary Statistics read. \n Latest statistics update: {data_path.name[-13:-5]}\n')


#-- Assign variables for excel sheets --#
NBAC_admin = NBAC['sumstats_admin']
NBAC_meta = NBAC['metadata']
NBAC_admin2 = NBAC['sumstats_admin2']
NBAC_parks = NBAC['sumstats_natpark']
NBAC_years = NBAC['NBAC_1972_2024_20250506']


#-- Clean Data --#
print("Begin Cleaning...")
#--- Metadata ---#

NBAC_meta = NBAC_meta['National Burned Area Composite - Metadata']

#---- Summary ----#
meta_summary_list = []
for row in NBAC_meta[4:11]:
    meta_summary_list.append(row)
meta_summary = "".join(meta_summary_list)
print(" Meta Summary")
#---- Description -----#
print(" Meta Description")
meta_description = " ".join(NBAC_meta.iloc[np.r_[13:67]].dropna().astype(str))

#---- Fields & Attributes ----#

# 1. Take just the “fields” section of the metadata
meta_lines = (
    NBAC_meta.iloc[67:]      # start at row 67
    .dropna()                # drop blank lines
    .astype(str).str.strip() # make sure they're strings, strip spaces
)

# (optional) drop the header line if it exists
meta_lines = meta_lines[meta_lines != "Fields / Attributes"]

# 2. Split each line into first word + rest
split = meta_lines.str.split(n=1, expand=True)

# 3. Name the two resulting columns
print("Splitting fields & attributes.")
split.columns = ["Field", "Attribute"]

meta_fields = split.reset_index(drop=True)

# 4. Merge meta field rows that are split over multiple lines
print("Merging split rows")
#--- Example: NFIREID + its two continuation lines --#
meta_fields = merge_meta_rows(meta_fields, main_idx=1, extra_idxs=[2, 3])
meta_fields = merge_meta_rows(meta_fields, main_idx=6, extra_idxs=[7])
meta_fields = merge_meta_rows(meta_fields, main_idx=8, extra_idxs=[9])
meta_fields = merge_meta_rows(meta_fields, main_idx=10, extra_idxs=[11,12,13])
meta_fields = merge_meta_rows(meta_fields, main_idx=11, extra_idxs=[12,13])
meta_fields = merge_meta_rows(meta_fields, main_idx=12, extra_idxs=[13])
meta_fields = merge_meta_rows(meta_fields, main_idx=15, extra_idxs=[16])
meta_fields = merge_meta_rows(meta_fields, main_idx=79, extra_idxs=[80])
meta_fields = merge_meta_rows(meta_fields, main_idx=13, extra_idxs=[14])

# 5. Split province / territory column
print("Splitting province / territory abr columns")
NBAC_meta_fields_clean = split_field_dash(meta_fields)

#-- Provincial/Territory Summary Statistics --#

# 1. Save the description from the first column name
admin_description = NBAC_admin.columns[0]

# 2. Drop the first row (all NaN / banner)
NBAC_summary_stats = NBAC_admin.iloc[1:].copy()

# 3. Use the next row as header
NBAC_summary_stats.columns = NBAC_summary_stats.iloc[0]

# 4. Drop that header row from the data and reset index
NBAC_summary_stats_clean = NBAC_summary_stats.iloc[1:].reset_index(drop=True)

NBAC_summary_stats_clean.attrs['description'] = admin_description

#-- Compile metadata --#
dataset_meta = {
    "name": "NBAC burned area by administrative area",
    "description": admin_description,
    "source": "https://cwfis.cfs.nrcan.gc.ca",  # example
    "units": "adjusted hectares",
}


#--- National Parks ---#

# 1. Save the description (first non-NaN banner row)
parks_description = NBAC_parks.iloc[1, 0]   # "Sum of SUM_ADJ_HA"

# 2. Drop top two rows; row 2 becomes header
NBAC_parks_clean = NBAC_parks.iloc[2:].copy()

# set header from the first remaining row
NBAC_parks_clean.columns = NBAC_parks_clean.iloc[0]

# 3. Drop that header row from the data and reset index
NBAC_parks_clean = NBAC_parks_clean.iloc[1:-1].reset_index(drop=True)

# 4. Rename the first column from "Row Labels" to YEAR (they’re years)
NBAC_parks_clean = NBAC_parks_clean.rename(columns={"Row Labels": "YEAR"})

# (optional) convert YEAR to integer
NBAC_parks_clean["YEAR"] = NBAC_parks_clean["YEAR"].astype(int)

# 5. Attach the description as metadata (like alt text)
NBAC_parks_clean.attrs["description"] = parks_description

#--- Individual Fires ---#

# 1. Capture the description from the first few rows of the first column
NBAC_years_description = (
    NBAC_years.iloc[0:3, 0]      # rows 0–2, first column
    .dropna()
    .astype(str)
    .str.strip()
    .str.join(" ")               # join into one sentence; use "\n".join(...) for line breaks
)

# 2. Drop the first 3 rows; row index 3 becomes the header row
NBAC_years_clean = NBAC_years.iloc[3:].copy()

# set header from the first remaining row
NBAC_years_clean.columns = NBAC_years_clean.iloc[0]

# 3. Drop that header row from the data and reset index
NBAC_years_clean = NBAC_years_clean.iloc[1:].reset_index(drop=True)

# optional: attach description as metadata (like "alt text")
NBAC_years_clean.attrs["description"] = NBAC_years_description

# optional: make YEAR numeric
NBAC_years_clean["YEAR"] = NBAC_years_clean["YEAR"].astype(int)

NBAC_summary_stats_two_clean = NBAC_admin2.copy()

#-- Export Files --#
print('Exporting Cleaned Summary Statistics Excel file...')
output_path = processed_NBAC_dir / 'NBAC_Summary_Stats_Cleaned.xlsx'

try: 
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        NBAC_summary_stats_clean.to_excel(writer, sheet_name='Admin_ProvTerr',index=False)
        NBAC_summary_stats_two_clean.to_excel(writer, sheet_name='Admin_ProvTerr_Summary',index=False)
        NBAC_parks_clean.to_excel(writer,sheet_name='Parks',index=False)
        NBAC_years_clean.to_excel(writer,sheet_name='Fires_Yearly',index=False)
        NBAC_meta_fields_clean.to_excel(writer,sheet_name='Metafields',index=False)
    print(f'Excel file export successful: {output_path}\n')
except Exception as e:
    raise RuntimeError(f'Summary Statistics Excel file failed to export: {e}\n')


print('Exporting NBAC README Markdown file... ')

output_path_txt = processed_NBAC_dir / 'NBAC_README.md'
width = 80  # characters per line

wrapped_summary = textwrap.fill(meta_summary, width=width,initial_indent="  ",subsequent_indent="  ")
wrapped_description = textwrap.fill(meta_description, width=width,initial_indent="  ",subsequent_indent="  ")

try:
    with open(output_path_txt, 'w') as file:
        file.write("README\n\n")
        file.write("Meta Summary\n")
        file.write(wrapped_summary + "\n\n")
        file.write("Meta Description\n")
        file.write(wrapped_description + "\n")
    print(f'Markdown file export successful: {output_path_txt}')
except Exception as e:
    raise RuntimeError(f'NBAC README Markdown file failed to export: {e}\n')





print('\nPy file complete.')
