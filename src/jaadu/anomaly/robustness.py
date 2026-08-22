from __future__ import annotations

import numpy as np
import pandas as pd
from jaadu.anomaly.detect import detect


def add_gaussian_noise(panel: pd.DataFrame, scale: float, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = panel.copy()
    for col in out.columns:
        s = out[col]
        sd = float(s.std()) if s.notna().any() else 0.0
        noise = rng.normal(0.0, scale * (sd if sd > 0 else 1.0), size=len(out))
        out[col] = s + noise
    return out


def delay_series(panel: pd.DataFrame, variable: str, months: int) -> pd.DataFrame:
    out = panel.copy()
    if variable in out.columns:
        out[variable] = out[variable].shift(months)
    return out


def drop_variables(panel: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    return panel.drop(columns=[c for c in variables if c in panel.columns], errors="ignore")


def mask_random(panel: pd.DataFrame, fraction: float, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = panel.copy()
    mask = rng.random(out.shape) < fraction
    out = out.mask(mask)
    return out


def compare_detection(base: dict, perturbed: dict) -> dict:
    return {
        "base_alert": bool(base.get("multi_signal_alert")),
        "perturbed_alert": bool(perturbed.get("multi_signal_alert")),
        "base_n_abnormal": base.get("n_abnormal"),
        "perturbed_n_abnormal": perturbed.get("n_abnormal"),
        "alert_flipped": bool(base.get("multi_signal_alert")) != bool(perturbed.get("multi_signal_alert")),
        "base_variables": [s["variable"] for s in base.get("current_signals", [])],
        "perturbed_variables": [s["variable"] for s in perturbed.get("current_signals", [])],
    }


def run_stress(panel: pd.DataFrame, as_of: str, spec: dict) -> dict:
    results = {"as_of": as_of, "cases": []}
    base = detect(panel, as_of, include_isolation=False)
    results["base"] = {
        "multi_signal_alert": base["multi_signal_alert"],
        "n_abnormal": base["n_abnormal"],
    }
    for case in spec.get("cases", []):
        kind = case.get("kind")
        p = panel
        if kind == "noise":
            p = add_gaussian_noise(panel, float(case.get("scale", 0.2)), int(case.get("seed", 42)))
        elif kind == "delay":
            p = delay_series(panel, case.get("variable", "rainfall"), int(case.get("months", 1)))
        elif kind == "drop":
            p = drop_variables(panel, list(case.get("variables", [])))
        elif kind == "missing":
            p = mask_random(panel, float(case.get("fraction", 0.1)), int(case.get("seed", 42)))
        else:
            continue
        if p.empty or p.shape[1] == 0:
            rec = {"name": case.get("name", kind), "error": "empty_panel"}
        else:
            d = detect(p, as_of, include_isolation=False)
            rec = {"name": case.get("name", kind), "kind": kind, **compare_detection(base, d)}
        results["cases"].append(rec)
    return results
