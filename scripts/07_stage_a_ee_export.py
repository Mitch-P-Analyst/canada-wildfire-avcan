# ===================================================================
# Overview
# ===================================================================
"""
Stage_A2 batch export to Google Cloud Storage (GeoJSON).

- Lists TABLE assets under STAGE_A2_FOLDER
- Batches into chunks
- Merges each batch into one FeatureCollection (server-side iterate)
- Exports each merged batch to Cloud Storage as GeoJSON
- Throttles + polls tasks
"""

# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

import time
from typing import List, Dict, Any
import ee
from pathlib import Path
import sys

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent
data_dir = REPO_ROOT / 'data/'
analysis_dir = data_dir / 'processed' / 'analysis/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ===================================================================
# Components
# ===================================================================
from src.config_utils import read_yaml, pause
    

# ===================================================================
# Helper Functions
# ===================================================================
def list_table_assets(parent_folder: str) -> List[str]:
    """Return asset IDs of TABLE assets under a parent folder."""
    try:
        resp = ee.data.listAssets({"parent": parent_folder})
        assets = resp.get("assets", [])
        return [a["id"] for a in assets if a.get("type") == "TABLE"]
    except Exception:
        assets = ee.data.getList({"id": parent_folder})
        return [a["id"] for a in assets if a.get("type") == "Table"]


def chunk_list(xs: List[str], size: int) -> List[List[str]]:
    """
    Chunk EE assets
    """
    return [xs[i:i + size] for i in range(0, len(xs), size)]


def poll_active(active: Dict[str, Dict[str, Any]]) -> None:
    """Poll submitted tasks; remove completed/failed from active dict."""
    done = []

    for tid, rec in list(active.items()):
        task = rec["task"]
        desc = rec["description"]
        uri = rec["gcs_uri"]

        try:
            st = task.status()
        except Exception as e:
            msg = str(e).lower()
            if "operation" in msg and "not found" in msg:
                print(f"[WARN] {tid} :: {desc} status unavailable (operation not found). Dropping.")
                done.append(tid)
            continue

        state = st.get("state")
        if state in ("READY", "RUNNING"):
            continue

        if state == "COMPLETED":
            print(f"[OK]   {tid} :: {desc} -> {uri}")
        else:
            print(f"[FAIL] {tid} :: {desc} -> {uri} :: {state} :: {st.get('error_message','')}")
        done.append(tid)

    for tid in done:
        active.pop(tid, None)

    if active:
        time.sleep(POLL_SECONDS)

def merge_assets_client_side(asset_ids: List[str]) -> ee.FeatureCollection:
    """
    Merge TABLE assets into one FeatureCollection using client-side constants.
    (EE cannot load assets from server-side/computed strings.)
    """
    if not asset_ids:
        return ee.FeatureCollection([])

    merged = ee.FeatureCollection(asset_ids[0])  # asset_ids[0] is a Python str
    for aid in asset_ids[1:]:
        merged = merged.merge(ee.FeatureCollection(aid))
    return merged

# ===================================================================
# CONFIG
# ===================================================================

# Google Earth Engine 
# =================================================================
ee_yaml_path = REPO_ROOT / "scripts/config/google_ee.yaml"
ee_yaml = read_yaml(ee_yaml_path, strict=True)

# ========== YAML Values =====================================
ee_project = ee_yaml.get("earth_engine", {}) or {}
params = ee_yaml.get("parameters", {}) or {}
gcs = ee_yaml.get("google_cloud_storage", {}) or {}

# ======= EE Setup =======#
ee_project_id = ee_project.get("project_id")
if not ee_project_id:
    raise ValueError("Missing earth_engine.project_id in google_ee.yaml")

gcs_bucket = gcs.get("GCS_bucket")
if not gcs_bucket:
    raise ValueError("Missing earth_engine.gcs_bucket in google_ee.yaml")


# Google Cloud Storage (GCS)
# =================================================================

# Directories 
# =================================================================
# GCS Project
PROJECT_ID = ee_project_id
# Project folder
STAGE_A2_FOLDER = f"projects/{ee_project_id}/assets/AvCan_Wildfire_Explorer/Stage_A2"
# GCS bucket
GCS_BUCKET = gcs_bucket

# ======= Constants =======#
# Bucket folder
GCS_PREFIX = gcs.get("export_prefix")

#======= Parameters =======#

# ==== Task Throttling ====#
BATCH_SIZE = int(gcs.get("batch_size",25))
MAX_ACTIVE_TASKS = int(params.get("maximum_tasks_active", 6))   # READY + RUNNING combined
SLEEP_BETWEEN_SUBMISSIONS = int(params.get("submission_sleep", 2))  # Seconds
POLL_SECONDS = 30

# ===================================================================
# EE Intialized
# ===================================================================
print("\nInitializing Google Earth Engine...")
print(f" EE Project: {PROJECT_ID}")
ee.Initialize(project=PROJECT_ID)
print(" Complete.\n")
pause(1)
print(f"Export asset folder (Stage A2):{STAGE_A2_FOLDER}")
pause(2)
print(f"Google Cloud Storage (GCS) output bucket: {GCS_BUCKET}")
pause(2)

# ===================================================================
# Inputs
# ===================================================================
print(f"""
Export Parameters
    Max Active Tasks: {MAX_ACTIVE_TASKS}
    Sleep seconds: {SLEEP_BETWEEN_SUBMISSIONS}
    Batch size: {BATCH_SIZE}
    Poll seconds: {POLL_SECONDS}
    """)
pause(2.5)


# ===================================================================
# Main Function
# ===================================================================
def main() -> None:
    asset_ids = sorted(list_table_assets(STAGE_A2_FOLDER))
    if not asset_ids:
        raise RuntimeError(f"No TABLE assets found under: {STAGE_A2_FOLDER}")

    batches = chunk_list(asset_ids, BATCH_SIZE)

    print(f"Found {len(asset_ids)} Stage_A2 TABLE assets.")
    print(f"Batch size: {BATCH_SIZE} -> {len(batches)} export task(s)\n")
    print(f"GCS bucket export path: gs://{GCS_BUCKET}/{GCS_PREFIX}\n")
    pause(2)
    print("\nBegin.\n")

    active: Dict[str, Dict[str, Any]] = {}

    for bi, batch_ids in enumerate(batches, start=1):
        desc = f"AvCan_Stage_A2_batch_{bi:03d}"
        file_prefix = f"{GCS_PREFIX}/{desc}"
        gcs_uri = f"gs://{GCS_BUCKET}/{file_prefix}.geojson"

        print(f"[BATCH {bi:03d}/{len(batches)}] merge {len(batch_ids)} assets -> {gcs_uri}")

        merged_fc = merge_assets_client_side(batch_ids)

        task = ee.batch.Export.table.toCloudStorage(
            collection=merged_fc,
            description=desc,
            bucket=GCS_BUCKET,
            fileNamePrefix=file_prefix,
            fileFormat="GeoJSON",
        )

        # throttle
        while len(active) >= MAX_ACTIVE_TASKS:
            poll_active(active)

        task.start()
        st0 = task.status()
        tid = st0.get("id") or st0.get("name") or f"unknown_{time.time()}"

        active[tid] = {"task": task, "description": desc, "gcs_uri": gcs_uri}

        print(f"[SUBMIT] {tid} :: {desc}")
        time.sleep(SLEEP_BETWEEN_SUBMISSIONS)

    # drain
    while active:
        poll_active(active)

    print("\nAll batch exports submitted and completed (or reported failed).")


if __name__ == "__main__":
    main()
