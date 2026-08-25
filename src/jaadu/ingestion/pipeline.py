from __future__ import annotations

import pandas as pd
from jaadu.ingestion.normalize import normalize_observations
from jaadu.core.registry import load_registry, processed_path, save_registry, write_parquet
from jaadu.ingestion.bigquery_sync import maybe_export
from jaadu.ingestion.earthengine import ingest_earth_engine
from jaadu.ingestion.fetch import (
    ingest_climate,
    ingest_fao_fpi,
    ingest_fred,
    ingest_oni,
    ingest_world_bank,
    static_unavailable_records,
)
from jaadu.ingestion.india_open import ingest_india_open


def _existing(name: str) -> pd.DataFrame:
    path = processed_path(name)
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


def run_ingest(reuse_processed: bool = True) -> pd.DataFrame:
    if reuse_processed and not _existing("observations_climate.parquet").empty:
        climate, r1 = _existing("observations_climate.parquet"), []
    else:
        climate, r1 = ingest_climate()
    if reuse_processed and not _existing("observations_worldbank.parquet").empty:
        wb, r2 = _existing("observations_worldbank.parquet"), []
    else:
        wb, r2 = ingest_world_bank()
    if reuse_processed and not _existing("observations_fao_fpi.parquet").empty:
        fpi, r3 = _existing("observations_fao_fpi.parquet"), []
    else:
        fpi, r3 = ingest_fao_fpi()
    fred, r4 = ingest_fred()
    oni, r5 = ingest_oni()
    if reuse_processed and not _existing("observations_ee.parquet").empty:
        ee_frame, r6 = _existing("observations_ee.parquet"), []
    else:
        ee_frame, r6 = ingest_earth_engine()
    _, r7 = ingest_india_open()
    frames = [f for f in (climate, wb, fpi, fred, oni, ee_frame) if f is not None and (not f.empty)]
    observations = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not observations.empty:
        observations = normalize_observations(observations)
        write_parquet(observations, "observations.parquet")
        maybe_export(observations)
    fresh = r1 + r2 + r3 + r4 + r5 + r6 + r7 + static_unavailable_records()
    by_id = {r.dataset_id: r for r in load_registry()}
    for rec in fresh:
        by_id[rec.dataset_id] = rec
    save_registry(list(by_id.values()))
    return observations
