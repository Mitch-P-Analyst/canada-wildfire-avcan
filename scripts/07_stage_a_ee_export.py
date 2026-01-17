#!/usr/bin/env python3
"""
Stage_A2 batch export to Google Cloud Storage (GeoJSON).

- Lists TABLE assets under STAGE_A2_FOLDER
- Batches into chunks
- Merges each batch into one FeatureCollection (server-side iterate)
- Exports each merged batch to Cloud Storage as GeoJSON
- Throttles + polls tasks
"""

from __future__ import annotations

import time
from typing import List, Dict, Any
import ee


# ==============================
# CONFIG
# ==============================
PROJECT_ID = "wildfire-canada-475322"

STAGE_A2_FOLDER = "projects/wildfire-canada-475322/assets/AvCan_Wildfire_Explorer/Stage_A2"

# REQUIRED: your bucket name (no gs:// prefix)
GCS_BUCKET = "avcan_wildfire_explorer_stage_a"

# Optional "folder" path inside the bucket
GCS_PREFIX = "exports/stage_a2_geojson"

# Batch sizing: start conservative; lower if exports shard or fail
BATCH_SIZE = 25

# Task throttling
MAX_ACTIVE_TASKS = 4
SLEEP_BETWEEN_SUBMISSIONS = 2
POLL_SECONDS = 30


# ==============================
# EE INIT
# ==============================
print("\nInitializing Google Earth Engine...")
ee.Initialize(project=PROJECT_ID)
print("Complete.\n")


# ==============================
# HELPERS
# ==============================
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

# ==============================
# MAIN
# ==============================
def main() -> None:
    asset_ids = sorted(list_table_assets(STAGE_A2_FOLDER))
    if not asset_ids:
        raise RuntimeError(f"No TABLE assets found under: {STAGE_A2_FOLDER}")

    batches = chunk_list(asset_ids, BATCH_SIZE)

    print(f"Found {len(asset_ids)} Stage_A2 TABLE assets.")
    print(f"Batch size: {BATCH_SIZE} -> {len(batches)} export task(s)\n")
    print(f"GCS bucket: gs://{GCS_BUCKET}/{GCS_PREFIX}\n")

    active: Dict[str, Dict[str, Any]] = {}

    for bi, batch_ids in enumerate(batches, start=1):
        desc = f"AvCan_Stage_A2_batch_{bi:03d}_GeoJSON"
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
