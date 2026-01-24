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

# ===================================================================
# Utility Functions
# ===================================================================

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
