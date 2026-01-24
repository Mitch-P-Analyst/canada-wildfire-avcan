# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
import yaml
import sys

# ===================================================================
# Directories
# ===================================================================
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
data_dir = REPO_ROOT / 'data/'
analysis_dir = data_dir / 'processed' / 'analysis/'
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

    
# ===================================================================
# Configs
# ===================================================================
ee_yaml_path = REPO_ROOT / "scripts/config/google_ee.yaml"
ee_yaml = yaml.safe_load(ee_yaml_path.read_text(encoding="utf-8"))

bucket = ee_yaml["google_cloud_storage"]["GCS_bucket"]
prefix = ee_yaml["google_cloud_storage"]["export_prefix"]

if not bucket or not prefix:
    raise KeyError(f"Missing gcs.bucket or gcs.export_prefix in {ee_yaml_path}")
# ===================================================================
# Constants
# ===================================================================
export_dir = "data/processed/analysis/stage_A/stage_A2"
gcs_uri = f"gs://{bucket}/{prefix}/*.geojson"

out_sh = REPO_ROOT / "scripts" / "tools" / "pull_stage_a2_from_gcs.sh"
# ===================================================================
# Body
# ===================================================================
out_sh.write_text(
f"""#!/usr/bin/env bash
set -euo pipefail

EXPORT_DIR="{export_dir}"
GCS_URI="{gcs_uri}"

mkdir -p "$EXPORT_DIR"
gsutil -m cp "$GCS_URI" "$EXPORT_DIR/"
""",
encoding="utf-8"
)

out_sh.chmod(0o755)
print(f"Wrote: {out_sh}")
print(f"GCS_URI: {gcs_uri}")
