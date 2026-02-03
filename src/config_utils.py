# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import ee
import subprocess
from datetime import datetime, timezone
import time
import shutil
import zipfile
import requests

# ===================================================================
# Utility Functions
# ===================================================================

# ===================================================================
# Data Config
# ===================================================================

# URL Downloads 
# =================================================================
def download_file(fname: str, destination: Path, base_url: str, timeout: int = 60) -> Path:
    """
    Download a file to destination.

    Backwards-compatible behavior:
      - If base_url is a normal base (e.g., "https://.../nbac/"), we download base_url + fname
      - If base_url is actually a full URL (e.g., "https://pub.data.../file.zip"),
        we download that directly and ignore concatenation.
    Returns the output Path.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    base_url_str = str(base_url)
    base_no_q = base_url_str.split("?")[0]

    # Detect "base_url is actually a full URL to the file"
    if base_url_str.startswith("http") and (
        base_no_q.endswith(fname) or base_no_q.lower().endswith((".zip", ".xlsx", ".csv", ".parquet", ".gpkg", ".tif"))
    ):
        url = base_url_str
    else:
        url = base_url_str + fname  # preserves your NBAC pattern

    out_path = destination / fname

    if out_path.exists():
        print(f"Already have {fname}, skipping.")
        return out_path

    print(f"Downloading {fname} ...")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(f"Saved to {out_path}")
    return out_path

# Raw Data 
# =================================================================
def unzip_to_folder(zip_path: Path, extract_to: Path) -> Path:
    """
    Unzips a ZIP archive into a specified directory.
    Returns the extract_to path.
    """
    zip_path = Path(zip_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)

    macosx_folder = extract_to / "__MACOSX"
    if macosx_folder.exists():
        shutil.rmtree(macosx_folder)

    return extract_to

# ===================================================================
# Geopackages
# ===================================================================

def fgdb_to_gpkg(
    fgdb_path: Path,
    gpkg_path: Path,
    layer: str,
    *,
    bbox_3005: tuple[float, float, float, float] | None = None,
    overwrite: bool = True,
) -> Path:

    fgdb_path = Path(fgdb_path)
    gpkg_path = Path(gpkg_path)
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)

    # Robust overwrite: remove gpkg + sqlite wal/shm sidecars
    if overwrite:
        for p in (gpkg_path, Path(str(gpkg_path) + "-wal"), Path(str(gpkg_path) + "-shm")):
            if p.exists():
                p.unlink()
    else:
        if gpkg_path.exists():
            return gpkg_path

    ogr2ogr = shutil.which("ogr2ogr")
    if not ogr2ogr:
        raise RuntimeError("ogr2ogr not found. Try: conda install -c conda-forge gdal")

    cmd = [
        ogr2ogr,
        "--config", "OGR_ORGANIZE_POLYGONS", "SKIP",
        "-f", "GPKG",
        str(gpkg_path),
        str(fgdb_path),
        layer,
        "-nln", layer,
        "-nlt", "PROMOTE_TO_MULTI",
        "-makevalid",
        "-overwrite",
        "-lco", "SPATIAL_INDEX=YES",
    ]

    if bbox_3005 is not None:
        minx, miny, maxx, maxy = bbox_3005
        cmd += ["-spat", str(minx), str(miny), str(maxx), str(maxy), "-spat_srs", "EPSG:3005"]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "ogr2ogr failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDOUT:\n{e.stdout}\n"
            f"STDERR:\n{e.stderr}\n"
        ) from e

    return gpkg_path


def find_fgdb_folder(extract_root: Path) -> Path:
    # Prefer the .gdb dir that actually contains *.gdbtable files
    gdbs = [p for p in extract_root.rglob("*.gdb") if p.is_dir()]
    for g in gdbs:
        if any(g.glob("*.gdbtable")):
            return g
    # fallback: return first .gdb found
    if gdbs:
        return gdbs[0]
    raise FileNotFoundError(f"No .gdb folder found under: {extract_root}")


# ===================================================================
# Formatting
# ===================================================================
def pause(sec: float = 1.5) -> None:
    """
    Docstring for pause
    
    :param sec: Pause script operation for readability
    :type sec: float
    """
    time.sleep(sec)

# ===================================================================
# Google EE assets
# ===================================================================

def ee_asset_exists(asset_id: str) -> bool:
    try:
        ee.data.getAsset(asset_id)
        return True
    except Exception:
        return False
    

def ee_upload_table(file_path: Path, asset_id: str, *, wait: bool = False) -> None:
    """
    Upload a local vector file to a Google Earth Engine TABLE asset using the Earth Engine CLI.

    Supported inputs:
      - zipped Shapefile (.zip)
      - GeoJSON (.geojson / .json)

    Requirements:
      - Earth Engine CLI installed: `pip install earthengine-api`
      - Authenticated: `earthengine authenticate`
      - (Recommended) Project set: `earthengine set_project <YOUR_PROJECT_ID>`
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Upload file not found: {file_path}")

    # Optional: wait for ingestion to finish
    cmd = ["earthengine", "upload", "table", f"--asset_id={asset_id}"]

    if wait:
        cmd.append("--wait")

    cmd.append(str(file_path))

    print("\nUploading to Earth Engine...")
    print(" ", " ".join(cmd))

    subprocess.run(cmd, check=True)
    print(f"Upload submitted successfully: {asset_id}")

def ee_ensure_folder(folder_id: str) -> None:
    """
    Ensure an Earth Engine FOLDER asset exists.
    folder_id example:
      "projects/<PROJECT_ID>/assets/AvCan_Wildfire_Explorer/Stage_A2"
    """
    if ee_asset_exists(folder_id):
        return
    ee.data.createAsset({"type": "FOLDER"}, folder_id)
    print(f"Created folder: {folder_id}")

def ee_ensure_tree(project_id: str, folder_path: str) -> None:
    """
    Create intermediate folders under projects/<project_id>/assets.

    folder_path example: "AvCan_Wildfire_Explorer/Stage_A2"
    """
    base = f"projects/{project_id}/assets"
    parts = [p for p in folder_path.strip("/").split("/") if p]

    cur = base
    for p in parts:
        cur = f"{cur}/{p}"
        ee_ensure_folder(cur)


# ===================================================================
# YAML Write / Update Helpers
# ===================================================================
def read_yaml(path: Path, *, default: Optional[Dict[str, Any]] = None, strict: bool = False) -> Dict[str, Any]:
    if not path.exists():
        if strict:
            raise FileNotFoundError(f"Missing config file: {path}")
        return default or {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        if strict:
            raise TypeError(f"Expected a YAML mapping (dict) in {path}, got {type(data).__name__}")
        return default or {}

    return data


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """
    Write YAML to disk (overwrites file contents). This is the safe way to persist structured updates.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )


def update_yaml(path: Path, updates: Dict[str, Any], *, strict: bool = False) -> Dict[str, Any]:
    """
    Update top-level keys in a YAML file and write back to disk.
    Returns the updated dict.
    """
    cfg = read_yaml(path, strict=strict)

    if not isinstance(cfg, dict):
        cfg = {}

    cfg.update(updates)
    write_yaml(path, cfg)
    return cfg


def deep_update(d: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively update dict `d` with `patch` (like a deep merge).
    """
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d


def update_yaml_deep(path: Path, patch: Dict[str, Any], *, strict: bool = False) -> Dict[str, Any]:
    """
    Deep-merge `patch` into YAML file contents and write back.
    Returns the updated dict.
    """
    cfg = read_yaml(path, strict=strict)
    if not isinstance(cfg, dict):
        cfg = {}

    deep_update(cfg, patch)
    write_yaml(path, cfg)
    return cfg

def set_avcan_overrides(
    yaml_path: Path,
    *,
    avcan_fires_asset_id: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Update the `overrides` block in google_ee.yaml for AvCan fires.
    Writes file back to disk and returns updated config dict.
    """
    patch: Dict[str, Any] = {"overrides": {}}

    if enabled is not None:
        patch["overrides"]["enabled"] = bool(enabled)
    if avcan_fires_asset_id is not None:
        patch["overrides"]["avcan_fires_asset_id"] = str(avcan_fires_asset_id)
    if min_year is not None:
        patch["overrides"]["min_year"] = int(min_year)
    if max_year is not None:
        patch["overrides"]["max_year"] = int(max_year)

    patch["overrides"]["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return update_yaml_deep(yaml_path, patch)
