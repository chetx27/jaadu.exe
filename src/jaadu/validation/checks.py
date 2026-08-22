from __future__ import annotations

import pandas as pd
from jaadu.core.time import filter_as_of, to_month

REQUIRED_COLS = [
    "observation_id",
    "variable",
    "node_type",
    "timestamp",
    "available_at",
    "geo_id",
    "value",
    "unit",
    "source",
    "quality_score",
]


def validate_observations(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in frame.columns]
    if missing:
        raise ValueError(f"observations missing columns: {missing}")
    out = frame.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out["available_at"] = pd.to_datetime(out["available_at"])
    if (out["available_at"] < out["timestamp"]).any():
        bad = out.loc[out["available_at"] < out["timestamp"]]
        raise ValueError(f"{len(bad)} rows have available_at before timestamp")
    out = out.dropna(subset=["variable", "geo_id"])
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out


def as_of_panel(observations: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    obs = validate_observations(observations)
    return filter_as_of(obs, cutoff, "available_at")


def pivot_region(observations: pd.DataFrame, geo_id: str, cutoff: str) -> pd.DataFrame:
    obs = as_of_panel(observations, cutoff)
    local = obs[obs["geo_id"] == geo_id]
    extra_geos = ["global_market", "global_climate", "india_national", "brazil_national"]
    extra = obs[obs["geo_id"].isin(extra_geos)]
    parts = []
    for g, chunk in [("local", local), ("context", extra)]:
        if chunk.empty:
            continue
        tmp = (
            chunk.assign(month=chunk["timestamp"].map(to_month))
            .groupby(["month", "variable"], as_index=False)["value"]
            .mean()
        )
        wide = tmp.pivot(index="month", columns="variable", values="value").sort_index()
        wide.columns = [str(c) for c in wide.columns]
        parts.append(wide)
    if not parts:
        return pd.DataFrame()
    panel = parts[0]
    for other in parts[1:]:
        overlap = [c for c in other.columns if c in panel.columns]
        other = other.drop(columns=overlap)
        panel = panel.join(other, how="outer")
    panel.index.name = "timestamp"
    return panel
