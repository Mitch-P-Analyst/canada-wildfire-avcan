#!/usr/bin/env bash
set -euo pipefail

EXPORT_DIR="data/processed/analysis/stage_A/stage_A2"
GCS_URI="gs://avcan_wildfire_explorer_stage_a/exports/stage_A2/*.geojson"

mkdir -p "$EXPORT_DIR"
gsutil -m cp "$GCS_URI" "$EXPORT_DIR/"
