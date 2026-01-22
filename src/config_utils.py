from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

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
