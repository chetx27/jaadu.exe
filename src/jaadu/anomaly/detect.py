from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from jaadu.core.config import engine_config
from jaadu.features.seasonal import seasonalize_panel


def _cusum(z: pd.Series, threshold: float = 4.0) -> list[pd.Timestamp]:
    x = z.dropna()
    if len(x) < 12:
        return []
    s_pos = 0.0
    s_neg = 0.0
    changes = []
    for t, v in x.items():
        s_pos = max(0.0, s_pos + v - 0.5)
        s_neg = min(0.0, s_neg + v + 0.5)
        if s_pos > threshold or s_neg < -threshold:
            changes.append(pd.Timestamp(t))
            s_pos = 0.0
            s_neg = 0.0
    return changes


def univariate_flags(z: pd.DataFrame, threshold: float) -> pd.DataFrame:
    flags = z.abs() >= threshold
    return flags


def mahalanobis_p(z_row: pd.Series, hist: pd.DataFrame) -> tuple[float, float]:
    cols = [c for c in hist.columns if hist[c].notna().sum() > 24 and pd.notna(z_row.get(c))]
    if len(cols) < 3:
        return (float("nan"), float("nan"))
    X = hist[cols].dropna()
    if len(X) < 24:
        return (float("nan"), float("nan"))
    mu = X.mean()
    cov = X.cov().values
    try:
        inv = np.linalg.pinv(cov)
    except np.linalg.LinAlgError:
        return (float("nan"), float("nan"))
    delta = (z_row[cols] - mu).values.astype(float)
    d2 = float(delta @ inv @ delta)
    from scipy.stats import chi2

    p = float(chi2.sf(d2, df=len(cols)))
    return (d2, p)


def isolation_score(hist: pd.DataFrame, contamination: float) -> pd.Series:
    X = hist.dropna()
    if len(X) < 36 or X.shape[1] < 3:
        return pd.Series(index=hist.index, dtype=float)
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    model.fit(X.values)
    raw = -model.decision_function(X.values)
    return pd.Series(raw, index=X.index)


def relationship_shift(panel: pd.DataFrame, a: str, b: str, window: int = 24) -> pd.Series:
    if a not in panel or b not in panel:
        return pd.Series(dtype=float)
    roll = panel[a].rolling(window, min_periods=window // 2).corr(panel[b])
    (z, _) = _z_of_series(roll)
    return z


def _z_of_series(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    mu = s.rolling(36, min_periods=12).median()
    mad = (s - mu).abs().rolling(36, min_periods=12).median() + 1e-06
    return (0.6745 * (s - mu) / mad, mu)


def joint_combination_surprise(z: pd.DataFrame, as_of: str, threshold: float) -> dict:
    cut = pd.Timestamp(as_of)
    hist = z.loc[z.index <= cut]
    if hist.empty:
        return {"surprise": 0.0, "variables": [], "historical_count": 0, "expected_indep": None}
    latest = hist.iloc[-1]
    active = [c for c in hist.columns if pd.notna(latest.get(c)) and abs(latest[c]) >= threshold]
    if len(active) < 2:
        return {"surprise": 0.0, "variables": active, "historical_count": 0, "expected_indep": None}
    mask = (hist[active].abs() >= threshold).all(axis=1)
    historical_count = int(mask.sum())
    rates = [(hist[c].abs() >= threshold).mean() for c in active]
    expected = float(np.prod(rates) * len(hist))
    ratio = (historical_count + 0.5) / (expected + 0.5)
    surprise = float(max(0.0, -np.log(max(ratio, 1e-06))))
    return {
        "surprise": surprise,
        "variables": active,
        "historical_count": historical_count,
        "expected_indep": expected,
        "n_hist": int(len(hist)),
    }


def detect(panel: pd.DataFrame, as_of: str) -> dict:
    cfg = engine_config()["anomaly"]
    cut = pd.Timestamp(as_of)
    hist = panel.loc[panel.index <= cut].copy()
    z = seasonalize_panel(hist)
    latest_z = z.iloc[-1] if not z.empty else pd.Series(dtype=float)
    flags_mod = univariate_flags(z, cfg["robust_z_threshold"])
    flags_strong = univariate_flags(z, cfg["strong_z_threshold"])
    persist = int(cfg["persistence_months"])
    persistent = []
    earliest = None
    current = []
    for col in z.columns:
        series = z[col].dropna()
        if series.empty:
            continue
        tail = series.iloc[-persist:]
        is_persist = len(tail) >= persist and (tail.abs() >= cfg["robust_z_threshold"]).all()
        last_z = float(series.iloc[-1])
        if abs(last_z) >= cfg["robust_z_threshold"]:
            current.append(
                {
                    "variable": col,
                    "seasonal_z": last_z,
                    "strong": abs(last_z) >= cfg["strong_z_threshold"],
                    "persistent": is_persist,
                    "timestamp": series.index[-1].isoformat(),
                }
            )
        if is_persist:
            persistent.append(col)
            abs_s = series.abs()
            run = (abs_s >= cfg["robust_z_threshold"]).astype(int)
            if run.iloc[-1] == 1:
                start = run.index[-1]
                for t, v in list(run.items())[::-1]:
                    if v == 0:
                        break
                    start = t
                if earliest is None or start < pd.Timestamp(earliest):
                    earliest = start.isoformat()
        changes = _cusum(series)
    (d2, p_mah) = mahalanobis_p(latest_z, z.iloc[:-1] if len(z) > 1 else z)
    iso = isolation_score(z.fillna(0.0), cfg["isolation_forest_contamination"])
    iso_latest = (
        float(iso.iloc[-1]) if not iso.empty and iso.index[-1] == z.index[-1] else float("nan")
    )
    combo = joint_combination_surprise(z, as_of, cfg["robust_z_threshold"])
    n_abn = len(
        [c for c in current if c["persistent"] or abs(c["seasonal_z"]) >= cfg["robust_z_threshold"]]
    )
    multi = n_abn >= int(cfg["min_abnormal_variables"]) and (
        combo["surprise"] > 0.4 or (pd.notna(p_mah) and p_mah < cfg["mahalanobis_p_threshold"])
    )
    conventional_hit = any((c["strong"] for c in current))
    return {
        "as_of": as_of,
        "seasonal_z": z,
        "current_signals": sorted(current, key=lambda x: -abs(x["seasonal_z"])),
        "persistent_variables": persistent,
        "earliest_signal": earliest,
        "mahalanobis_d2": d2,
        "mahalanobis_p": p_mah,
        "isolation_score": iso_latest,
        "combination": combo,
        "multi_signal_alert": bool(multi),
        "conventional_univariate_hit": bool(conventional_hit),
        "n_abnormal": n_abn,
        "changepoints": {
            col: [t.isoformat() for t in _cusum(z[col].dropna())][-3:]
            for col in z.columns
            if z[col].notna().any()
        },
    }
