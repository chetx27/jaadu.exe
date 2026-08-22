from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from jaadu.baselines.retrieval import retrieval_baseline
from jaadu.core.config import engine_config
from jaadu.features.seasonal import month_of_year_baseline


def _series(panel: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for c in candidates:
        if c in panel.columns and panel[c].notna().sum() >= 24:
            return panel[c].dropna()
    return None


def baseline_single_variable(panel: pd.DataFrame, as_of: str) -> dict:
    s = _series(panel.loc[:as_of], ["rainfall", "climatic_water_balance"])
    if s is None or len(s) < 36:
        return {"name": "single_variable_forecast", "alert": False, "reason": "insufficient series"}
    (z, loc) = month_of_year_baseline(s)
    last = float(z.iloc[-1])
    alert = abs(last) >= engine_config()["anomaly"]["strong_z_threshold"]
    return {
        "name": "single_variable_forecast",
        "alert": bool(alert),
        "score": abs(last),
        "variable": s.name,
        "method": "seasonal robust z on primary climate series (Holt-Winters unused if shorter)",
    }


def baseline_multivariate_iforest(panel: pd.DataFrame, as_of: str) -> dict:
    hist = panel.loc[:as_of].select_dtypes("number").dropna()
    if len(hist) < 36 or hist.shape[1] < 3:
        return {"name": "multivariate_iforest", "alert": False, "reason": "insufficient"}
    model = IsolationForest(contamination=0.08, random_state=42)
    model.fit(hist.iloc[:-1])
    pred = model.predict(hist.iloc[[-1]])[0]
    score = float(-model.decision_function(hist.iloc[[-1]])[0])
    return {"name": "multivariate_iforest", "alert": bool(pred == -1), "score": score}


def baseline_rule(panel: pd.DataFrame, as_of: str) -> dict:
    s = _series(panel.loc[:as_of], ["rainfall"])
    if s is None:
        return {"name": "rule_based_spi", "alert": False, "reason": "no rainfall"}
    (z, _) = month_of_year_baseline(s)
    tail = z.iloc[-2:]
    alert = len(tail) == 2 and (tail < -1.5).all()
    return {"name": "rule_based_spi", "alert": bool(alert), "score": float(-tail.mean())}


def baseline_llm_retrieval(as_of: str, geo_id: str) -> dict:
    return retrieval_baseline(as_of, geo_id)


def run_baselines(panel: pd.DataFrame, as_of: str, geo_id: str) -> list[dict]:
    return [
        baseline_single_variable(panel, as_of),
        baseline_multivariate_iforest(panel, as_of),
        baseline_rule(panel, as_of),
        retrieval_baseline(as_of, geo_id),
    ]
