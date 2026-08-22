from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from jaadu.core.config import DATA


def cache_path(region: str, as_of: str) -> Path:
    safe = as_of.replace(":", "-")
    return DATA / "processed" / f"investigation_{region}_{safe}.json"


def load_cached(region: str, as_of: str) -> dict | None:
    path = cache_path(region, as_of)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_cached(region: str, as_of: str, payload: dict) -> Path:
    path = cache_path(region, as_of)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path
