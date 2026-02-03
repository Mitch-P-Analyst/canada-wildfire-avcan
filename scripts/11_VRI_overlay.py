# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from pathlib import Path
import sys
import re

import geopandas as gpd
import pandas as pd
from pyogrio import read_dataframe

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

data_dir = REPO_ROOT / "data"
analysis_dir = data_dir / "processed" / "analysis"
app_dir = data_dir / "processed" / "app"
raw_dir = data_dir / "raw"

stage_B_dir = analysis_dir / "stage_B"
stage_B_dir.mkdir(parents=True, exist_ok=True)

# ===================================================================
# Config Utils
# ===================================================================
from src.config_utils import pause, fgdb_to_gpkg, find_fgdb_folder  
# ===================================================================
# Helpers
# ===================================================================
def slugify(s: str) -> str:
    """Filesystem-safe slug."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"

def lowercase_columns(df: pd.DataFrame, *, keep: set[str] = {"geometry"}) -> pd.DataFrame:
    # guard against collisions after lowercasing
    lowered = [c.lower() if c not in keep else c for c in df.columns]
    if len(lowered) != len(set(lowered)):
        dupes = pd.Series(lowered)[pd.Series(lowered).duplicated()].tolist()
        raise ValueError(f"Column collision after lowercasing: {dupes}")
    return df.rename(columns={old: new for old, new in zip(df.columns, lowered)})


# ===================================================================
# Inputs
# ===================================================================
print("Loading Avalanche Canada (AvCan) regions file...")
avcan_path = analysis_dir / "avalanche_canada" / "regions" / "AvCan_cleaned_subregions.geojson"
if not avcan_path.exists():
    raise FileNotFoundError(f"Missing AvCan file: {avcan_path}")

avcan_shapes = gpd.read_file(avcan_path)
if "region" not in avcan_shapes.columns:
    raise KeyError(f"Expected column 'region' in AvCan shapes. Found: {avcan_shapes.columns.tolist()}")

print(f" AvCan regions loaded. CRS: {avcan_shapes.crs}\n")
pause(2)
print("Loading Stage A Severity Patches...")
pause(1)
PATCHES_FP = app_dir / "Stage_A2_Burn_Severity_Patches.parquet"
if not PATCHES_FP.exists():
    raise FileNotFoundError(f"Missing patches parquet: {PATCHES_FP}")

patches = gpd.read_parquet(PATCHES_FP)

# Work in EPSG:3005 for area/overlay
patches = patches.to_crs(3005)
print(f" Stage A patches loaded. CRS: {patches.crs} | n={len(patches)}\n")
pause(1)
print("")


# ===================================================================
# Locate FGDB (source for per-region GPKG creation)
# ===================================================================
VRI_LAYER = "VEG_COMP_LYR_R1_POLY"

# Prefer your known extracted path, otherwise auto-find under data/raw/VRI/gdb
VRI_GDB_ROOT = raw_dir / "VRI" / "gdb"
if not VRI_GDB_ROOT.exists():
    raise FileNotFoundError(f"Missing VRI gdb folder: {VRI_GDB_ROOT}")

# If you know the exact folder, you can set it directly:
candidate = VRI_GDB_ROOT / "VEG_COMP_LYR_R1_POLY_2024.gdb" / "VEG_COMP_LYR_R1_POLY_2024.gdb"
if candidate.exists():
    VRI_FGDB = candidate
else:
    # Fall back to scanning for the actual FGDB folder that contains *.gdbtable
    VRI_FGDB = find_fgdb_folder(VRI_GDB_ROOT)

print(f"Using VRI FGDB: {VRI_FGDB}")

# Where region gpkg files live
VRI_GPKG_DIR = raw_dir / "VRI" / "gpkg_regions"
VRI_GPKG_DIR.mkdir(parents=True, exist_ok=True)

# ===================================================================
# Cleaning
# ===================================================================
print("CRS matching")

# Ensure AvCan regions match CRS
if avcan_shapes.crs != patches.crs:
    avcan_shapes = avcan_shapes.to_crs(patches.crs)

# Create / ensure stable patch id
PATCH_ID = "Unique Patch ID"
if PATCH_ID not in patches.columns:
    patches = patches.reset_index().rename(columns={"index": PATCH_ID})

print("VRI Column Formatting")

# ===================================================================
# 1) Acquire Avcan regions by patches
# ===================================================================
patch_with_region = (
    patches[[PATCH_ID, "Region"]]
    .copy()
)

# ===================================================================
# 2) Loop regions: build region GPKG (bbox subset) + overlay
# ===================================================================
out_parts: list[gpd.GeoDataFrame] = []

for region_name, grp in patch_with_region.groupby("Region", dropna=True):
    if grp.empty:
        continue

    region_slug = slugify(str(region_name))
    print(f"--- Region: {region_name} ({len(grp)} patches) ---")

    # region patches
    region_patch_ids = grp[PATCH_ID].unique().tolist()
    region_patches = patches[patches[PATCH_ID].isin(region_patch_ids)].copy()
    if region_patches.empty:
        print("  No patches found after filter, skipping.\n")
        continue

    # bbox in EPSG:3005
    minx, miny, maxx, maxy = region_patches.total_bounds
    buf = 5000
    bbox = (minx - buf, miny - buf, maxx + buf, maxy + buf)

    # region gpkg path
    region_gpkg = VRI_GPKG_DIR / f"vri_{VRI_LAYER.lower()}_2024_{region_slug}.gpkg"

    # Build region gpkg once
    if not region_gpkg.exists():
        print(f"  Building region GPKG: {region_gpkg.name}")
        fgdb_to_gpkg(
            VRI_FGDB,
            region_gpkg,
            VRI_LAYER,
            bbox_3005=bbox,
            overwrite=True,
        )
        print("  Region GPKG built.")
    else:
        print("  Region GPKG exists, reusing.")

    # VRI column variables    
    VRI_ATTRS = [
        "reference_year",
        "alpine_designation",
        "species_cd_1", 
        "species_pct_1", 
        "bark_biomass_per_ha",
        ]


    READ_COLS = [c.upper() for c in VRI_ATTRS] + ["geometry"]        # matches REFERENCE_YEAR etc.

    

    vri_region_df = read_dataframe(
        str(region_gpkg), 
        layer=VRI_LAYER, 
        bbox=bbox, 
        columns=READ_COLS)
    
    # Normalize names to metadata style
    vri_region_df = lowercase_columns(vri_region_df)

    vri_region = gpd.GeoDataFrame(
        vri_region_df, 
        geometry="geometry", 
        crs=3005)

    if vri_region.empty:
        print("  VRI subset returned 0 features. Keeping patches with NA VRI fields.\n")
        enriched_region = region_patches.copy()
        for c in VRI_ATTRS:
            enriched_region[c] = pd.NA
        enriched_region["AvCan_Region"] = region_name
        out_parts.append(enriched_region)
        continue

    # Overlay intersection
    print("  Overlaying…")
    inter = gpd.overlay(
        region_patches[[PATCH_ID, "geometry"]],
        vri_region,
        how="intersection",
    )
    

    if inter.empty:
        print("  Intersection empty. Keeping patches with NA VRI fields.\n")
        enriched_region = region_patches.copy()
        for c in VRI_ATTRS:
            enriched_region[c] = pd.NA
        enriched_region["AvCan_Region"] = region_name
        out_parts.append(enriched_region)
        continue

    inter["overlap_area"] = inter.geometry.area

    

    # choose best VRI attributes per patch (max overlap)
    idx = inter.groupby(PATCH_ID)["overlap_area"].idxmax()
    best = inter.loc[idx].drop(columns=["geometry", "overlap_area"])

    enriched_region = region_patches.merge(best, on=PATCH_ID, how="left")
    enriched_region["AvCan_Region"] = region_name
    out_parts.append(enriched_region)

    print("  Done.\n")

# ===================================================================
# 3) Save output
# ===================================================================
if not out_parts:
    raise RuntimeError("No region outputs were produced (out_parts is empty). Check joins/CRS/inputs.")

enriched = gpd.GeoDataFrame(pd.concat(out_parts, ignore_index=True), crs=3005)

OUT_FP = stage_B_dir / "stage_B_patches_with_vri.parquet"
enriched.to_parquet(OUT_FP)

print("Saved:", OUT_FP)
