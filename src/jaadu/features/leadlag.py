from __future__ import annotations

import pandas as pd
from jaadu.features.seasonal import seasonalize_panel


def change_alignment(z: pd.DataFrame, a: str, b: str, max_lag: int = 6) -> dict:
    if a not in z.columns or b not in z.columns:
        return {"status": "missing_variable"}
    sa = z[a].dropna()
    sb = z[b].dropna()
    joint = pd.concat([sa, sb], axis=1).dropna()
    if len(joint) < 24:
        return {"status": "short_history"}
    best = {"lag": 0, "corr": 0.0}
    for lag in range(0, max_lag + 1):
        c = joint.iloc[:, 0].shift(lag).corr(joint.iloc[:, 1])
        if pd.notna(c) and abs(c) > abs(best["corr"]):
            best = {"lag": lag, "corr": float(c)}
    return {"status": "ok", "source": a, "target": b, **best}


def order_signals(detection: dict) -> list[dict]:
    signals = list(detection.get("current_signals") or [])
    signals.sort(key=lambda s: s.get("timestamp") or "")
    return signals
