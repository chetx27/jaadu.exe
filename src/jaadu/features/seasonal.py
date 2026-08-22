from __future__ import annotations

import numpy as np
import pandas as pd
from jaadu.core.config import engine_config


def month_of_year_baseline(series: pd.Series, min_years: int = 4) -> tuple[pd.Series, pd.Series]:
    s = series.dropna()
    if s.empty:
        z = pd.Series(index=series.index, dtype=float)
        return (z, z)
    month = s.index.month
    loc = s.groupby(month).transform("median")
    mad = s.groupby(month).transform(lambda x: np.median(np.abs(x - np.median(x))) + 1e-06)
    robust_z = 0.6745 * (s - loc) / mad
    return (robust_z.reindex(series.index), loc.reindex(series.index))


def seasonalize_panel(panel: pd.DataFrame) -> pd.DataFrame:
    z = pd.DataFrame(index=panel.index)
    for col in panel.columns:
        (z[col], _) = month_of_year_baseline(panel[col])
    return z


def rolling_trend(series: pd.Series, window: int = 6) -> pd.Series:
    return series.rolling(window, min_periods=max(3, window // 2)).mean().diff()


def feature_bundle(panel: pd.DataFrame, as_of: str) -> dict:
    cfg = engine_config()["anomaly"]
    cut = pd.Timestamp(as_of)
    hist = panel.loc[panel.index <= cut]
    z = seasonalize_panel(hist)
    latest = z.iloc[-1] if not z.empty else pd.Series(dtype=float)
    persist = int(cfg["persistence_months"])
    persistent = {}
    for col in z.columns:
        tail = z[col].dropna().iloc[-persist:] if persist else z[col].dropna().iloc[-1:]
        persistent[col] = bool(
            len(tail) >= persist and (tail.abs() >= cfg["robust_z_threshold"]).all()
        )
    return {
        "panel": hist,
        "seasonal_z": z,
        "latest_z": latest,
        "persistent": persistent,
        "as_of": as_of,
    }
