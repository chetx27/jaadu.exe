from __future__ import annotations

import pandas as pd
from jaadu.features.seasonal import seasonalize_panel
from jaadu.validation.checks import pivot_region


NEIGHBORS = {
    "marathwada": ["vidarbha"],
    "vidarbha": ["marathwada"],
    "sao_paulo_cantareira": [],
}


def spatial_coherence(
    observations: pd.DataFrame, geo_id: str, as_of: str, variables: list[str]
) -> dict:
    neighbors = NEIGHBORS.get(geo_id, [])
    if not neighbors or not variables:
        return {
            "status": "not_evaluated",
            "reason": "No configured neighbor region or no hot variables.",
            "agreements": [],
        }
    local = pivot_region(observations, geo_id, as_of)
    if local.empty:
        return {"status": "not_evaluated", "reason": "empty local panel", "agreements": []}
    z_local = seasonalize_panel(local.loc[local.index <= pd.Timestamp(as_of)])
    latest_local = z_local.iloc[-1] if not z_local.empty else pd.Series(dtype=float)
    agreements = []
    for nb in neighbors:
        other = pivot_region(observations, nb, as_of)
        if other.empty:
            agreements.append({"neighbor": nb, "status": "unavailable"})
            continue
        z_other = seasonalize_panel(other.loc[other.index <= pd.Timestamp(as_of)])
        latest_other = z_other.iloc[-1] if not z_other.empty else pd.Series(dtype=float)
        shared = []
        for v in variables:
            if v in latest_local.index and v in latest_other.index:
                a = latest_local[v]
                b = latest_other[v]
                if pd.notna(a) and pd.notna(b):
                    shared.append(
                        {
                            "variable": v,
                            "local_z": float(a),
                            "neighbor_z": float(b),
                            "same_sign": bool(a * b > 0),
                            "both_weak_or_strong": bool(abs(a) >= 1.5 and abs(b) >= 1.5),
                        }
                    )
        n = len(shared) or 1
        score = sum(1 for s in shared if s["same_sign"]) / n
        agreements.append(
            {
                "neighbor": nb,
                "status": "compared",
                "same_sign_fraction": score,
                "details": shared,
            }
        )
    return {
        "status": "evaluated",
        "interpretation": "Same-sign anomalies in a neighboring agro-climatic region raise spatial credibility. Opposite signs weaken a local-only artifact hypothesis only weakly.",
        "agreements": agreements,
    }
