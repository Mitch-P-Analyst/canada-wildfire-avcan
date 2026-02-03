# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from pathlib import Path
import requests
import sys
import fiona
import geopandas as gpd
import os
from typing import Any


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
VRI_RAW_DIR = raw_dir / "VRI"
VRI_ZIPS_DIR = VRI_RAW_DIR / "zips"
VRI_EXTRACT_DIR = VRI_RAW_DIR / "gdb"
VRI_GPKG_DIR = VRI_RAW_DIR / "gpkg"



for d in (VRI_ZIPS_DIR, VRI_EXTRACT_DIR, VRI_GPKG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Avoid slow polygon ring “organization” on very complex polygons (VRI has many)
os.environ.setdefault("OGR_ORGANIZE_POLYGONS", "SKIP")


CKAN_API_BASE = "https://open.canada.ca/data/api/action/"
VRI_DATASET_ID = "2ebb35d8-c82f-4a17-9c96-612ac3532d55"

EXTRACT_VRI_ZIPS = True
CONVERT_TO_GPKG = True
OVERWRITE_GPKG = True

# Optional: subset using your Stage A patches if present
PATCHES_FP = REPO_ROOT / "data/processed/app/Stage_A2_Burn_Severity_Patches.parquet"
# ===================================================================
# Config Imports
# ===================================================================
from src.config_utils import unzip_to_folder, download_file, fgdb_to_gpkg, find_fgdb_folder


# ===================================================================
# Custom Functions
# ===================================================================
def ckan_get(action: str, params: dict) -> dict:
    url = CKAN_API_BASE + action
    r = requests.get(
        url,
        params=params,
        timeout=90,
        headers={"User-Agent": "vri-downloader/1.0"},
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success", False):
        raise RuntimeError(f"CKAN API call failed: {action} params={params}")
    return data["result"]


def list_dataset_resources(dataset_id: str) -> list[dict]:
    pkg = ckan_get("package_show", {"id": dataset_id})
    return pkg.get("resources", [])



def is_vri_fgdb_zip(res: dict) -> bool:
    url = (res.get("url") or "").lower()
    fmt = (res.get("format") or "").lower()
    name = (res.get("name") or "").lower()

    return (
        ".gdb.zip" in url
        or (url.endswith(".zip") and "gdb" in url and "doc" not in url and "metadata" not in url)
        or ("zip" in fmt and "gdb" in name)
    )


def pick_best_fgdb_zip(resources: list[dict]) -> dict:
    candidates = [r for r in resources if is_vri_fgdb_zip(r)]
    if not candidates:
        raise RuntimeError("No FGDB zip resource found in CKAN dataset resources.")

    # Prefer the one whose URL contains "current" or "2024"
    def score(r):
        url = (r.get("url") or "").lower()
        s = 0
        if "pub.data.gov.bc.ca" in url: s += 30
        if "current" in url: s += 10
        if "2024" in url: s += 5
        if ".gdb.zip" in url: s += 20
        return s

    return sorted(candidates, key=score, reverse=True)[0]

def pick_filename(res: dict) -> str:
    url = res.get("url") or ""
    base = url.split("?")[0].rstrip("/").split("/")[-1]
    if base:
        return base
    name = (res.get("name") or "").strip().replace(" ", "_")
    return (name + ".zip") if name and not name.lower().endswith(".zip") else (name or f"{res.get('id','resource')}.zip")

def download_vri_dataset(dataset_id: str) -> None:
    resources = list_dataset_resources(dataset_id)
    res = pick_best_fgdb_zip(resources)

    url = res.get("url")
    if not url:
        raise RuntimeError("Best FGDB resource has no URL.")

    fname = pick_filename(res)
    print(f"Resources found: {len(resources)}")
    print(f"Selected FGDB ZIP: {fname}")
    print(f"URL: {url}")

    expected_zip = VRI_ZIPS_DIR / fname
    if expected_zip.exists() and expected_zip.stat().st_size > 0:
        print(f"ZIP already exists, skipping download: {expected_zip.name}")
        zip_path = expected_zip
    else:
        zip_path = download_file(fname=fname, destination=VRI_ZIPS_DIR, base_url=url)

    if not EXTRACT_VRI_ZIPS:
        print("Download complete (extraction disabled).")
        return

    # zip_path.stem for ".gdb.zip" becomes "... .gdb" which is okay; this is just explicit/stable
    extract_target = VRI_EXTRACT_DIR / zip_path.name.replace(".zip", "")


    if extract_target.exists() and any(extract_target.rglob("*.gdb")):
        print("Already extracted, skipping unzip.")
    else:
        print("\nUnzipping VRI Zip.")
        unzip_to_folder(zip_path, extract_target)
        print("Unzip complete.")

    if not CONVERT_TO_GPKG:
        print("Extraction complete (conversion disabled).")
        return

    fgdb_path = find_fgdb_folder(extract_target)
    layers = fiona.listlayers(str(fgdb_path))
    if not layers:
        raise RuntimeError(f"No layers found in FGDB: {fgdb_path}")

    layer = "VEG_COMP_LYR_R1_POLY" if "VEG_COMP_LYR_R1_POLY" in layers else layers[0]

    bbox_3005 = None
    suffix = "full"

    if PATCHES_FP.exists():
        patches_3005 = gpd.read_parquet(PATCHES_FP)
        if len(patches_3005) == 0:
            print("PATCHES_FP exists but has 0 rows; skipping bbox subset.")
        else:
            patches_3005 = patches_3005.to_crs(3005)
            minx, miny, maxx, maxy = patches_3005.total_bounds
            buf = 5000
            bbox_3005 = (minx - buf, miny - buf, maxx + buf, maxy + buf)
            suffix = "subset"


    gpkg_path = VRI_GPKG_DIR / f"vri_{layer.lower()}_2024_{suffix}.gpkg"

    print(f"Converting FGDB -> GPKG: {gpkg_path.name}")
    fgdb_to_gpkg(
        fgdb_path,
        gpkg_path,
        layer,
        bbox_3005=bbox_3005,
        overwrite=OVERWRITE_GPKG,
    )
    print("GPKG conversion complete.")
    print("VRI pipeline complete.")

# ===================================================================
# Main
# ===================================================================
print("Begin BC VRI Download.")

print("Access Comprehensive Knowledge Archive Network (CKAN) API")

if __name__ == "__main__":
    download_vri_dataset(VRI_DATASET_ID)




# ===================================================================
# Py Complete
# ===================================================================
print("\nPy File Complete.")

