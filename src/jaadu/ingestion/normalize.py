from __future__ import annotations

import pandas as pd
from jaadu.core.time import to_month


def to_month_index(frame: pd.DataFrame, time_col: str = "timestamp") -> pd.DataFrame:
    out = frame.copy()
    out[time_col] = pd.to_datetime(out[time_col]).map(to_month)
    return out


def collapse_stations(frame: pd.DataFrame) -> pd.DataFrame:
    if "station" not in frame.columns:
        return frame
    keys = [c for c in ("geo_id", "variable", "timestamp") if c in frame.columns]
    if len(keys) < 3:
        return frame
    num = frame.groupby(keys, as_index=False)["value"].mean()
    meta = (
        frame.sort_values(keys)
        .drop_duplicates(keys, keep="first")
        .drop(columns=["value"], errors="ignore")
    )
    return num.merge(meta, on=keys, how="left")


def attach_geo_resolution(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "geo_resolution" not in out.columns:
        out["geo_resolution"] = "unknown"
    out.loc[out["geo_id"].isin(["global_market", "global_climate"]), "geo_resolution"] = "global"
    out.loc[out["geo_id"].str.endswith("_national", na=False), "geo_resolution"] = "country"
    return out


def normalize_observations(frame: pd.DataFrame) -> pd.DataFrame:
    out = to_month_index(frame)
    out = collapse_stations(out)
    out = attach_geo_resolution(out)
    out = out.sort_values(["timestamp", "geo_id", "variable"])
    return out.reset_index(drop=True)
