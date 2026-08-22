from __future__ import annotations

import pandas as pd
from jaadu.core.registry import save_registry, write_parquet
from jaadu.ingestion.fetch import (
    ingest_climate,
    ingest_fao_fpi,
    ingest_fred,
    ingest_oni,
    ingest_world_bank,
    static_unavailable_records,
)


def run_ingest() -> pd.DataFrame:
    (climate, r1) = ingest_climate()
    (wb, r2) = ingest_world_bank()
    (fpi, r3) = ingest_fao_fpi()
    (fred, r4) = ingest_fred()
    (oni, r5) = ingest_oni()
    frames = [f for f in (climate, wb, fpi, fred, oni) if f is not None and (not f.empty)]
    observations = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not observations.empty:
        observations = observations.sort_values(["timestamp", "geo_id", "variable"])
        write_parquet(observations, "observations.parquet")
    records = r1 + r2 + r3 + r4 + r5 + static_unavailable_records()
    save_registry(records)
    return observations
