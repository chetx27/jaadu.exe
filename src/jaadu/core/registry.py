from __future__ import annotations

from pathlib import Path
import pandas as pd
import yaml
from jaadu.core.config import DATA
from jaadu.core.schemas import Availability, DatasetRecord

REGISTRY_PATH = DATA / "registry" / "datasets.yaml"


def load_registry() -> list[DatasetRecord]:
    if not REGISTRY_PATH.exists():
        return []
    raw = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
    return [DatasetRecord(**row) for row in raw.get("datasets", [])]


def save_registry(records: list[DatasetRecord]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"datasets": [r.model_dump(mode="json") for r in records]}
    REGISTRY_PATH.write_text(yaml.safe_dump(payload, sort_keys=False))


def mark(records: list[DatasetRecord], dataset_id: str, **updates) -> None:
    for r in records:
        if r.dataset_id == dataset_id:
            for k, v in updates.items():
                setattr(r, k, v)


def unavailable(
    dataset_id: str,
    name: str,
    source: str,
    url: str,
    country: str,
    variables: list[str],
    why: str,
    reason: str,
) -> DatasetRecord:
    return DatasetRecord(
        dataset_id=dataset_id,
        name=name,
        source=source,
        url=url,
        country=country,
        geographic_resolution="unknown",
        temporal_resolution="unknown",
        units="unknown",
        license="not ingested",
        update_frequency="unknown",
        known_limitations=reason,
        missingness="100%",
        quality_score=0.0,
        transformation="none",
        variables=variables,
        why_it_matters=why,
        status=Availability.UNAVAILABLE,
        citation=source,
    )


def processed_path(name: str) -> Path:
    p = DATA / "processed" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_parquet(frame: pd.DataFrame, name: str) -> Path:
    path = processed_path(name)
    frame.to_parquet(path, index=False)
    return path
