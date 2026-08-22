from __future__ import annotations

"Scenario analysis, not causal identification.\n\nWe do not claim synthetic-control or do-calculus identification on these series.\nThe module answers: in historical months where a hypothesized driver was near\nits seasonal baseline, how often did the downstream anomaly still occur?\nThat is a matched-period scenario, not an ATE.\n"
import numpy as np
import pandas as pd
from jaadu.features.seasonal import seasonalize_panel
from jaadu.graph.temporal import node_type_for

DRIVER_VARS = {
    "environmental_production_shock": ["rainfall", "climatic_water_balance", "enso_oni"],
    "hydrological_constraint": ["soil_moisture", "river_discharge", "climatic_water_balance"],
    "market_disturbance": ["food_price_index", "wheat_price", "rice_price"],
    "energy_constraint": ["electricity_generation"],
}


def matched_driver_hold(
    panel: pd.DataFrame, as_of: str, template_id: str, downstream: list[str]
) -> dict:
    z = seasonalize_panel(panel.loc[panel.index <= pd.Timestamp(as_of)])
    drivers = [v for v in DRIVER_VARS.get(template_id, []) if v in z.columns]
    downs = [v for v in downstream if v in z.columns]
    if not drivers or not downs or len(z) < 36:
        return {
            "status": "not_identifiable",
            "reason": "Insufficient overlapping history for matched-period scenario.",
            "assumptions": [
                "Would require a well-defined intervention on the driver and no unmeasured confounding."
            ],
        }
    latest = z.iloc[-1]
    mask = (z[drivers].abs() < 0.5).all(axis=1)
    hist = z.loc[mask]
    if len(hist) < 8:
        return {
            "status": "not_identifiable",
            "reason": "Too few matched months with driver near baseline.",
            "assumptions": ["Matched months are not a randomized intervention."],
        }
    observed_down = float(np.nanmean([abs(latest[v]) for v in downs if pd.notna(latest.get(v))]))
    matched_down = float(hist[downs].abs().mean().mean())
    return {
        "status": "scenario_analysis",
        "not_causal_estimate": True,
        "template_id": template_id,
        "drivers": drivers,
        "downstream": downs,
        "observed_downstream_abs_z": observed_down,
        "matched_baseline_downstream_abs_z": matched_down,
        "ratio": observed_down / (matched_down + 1e-06),
        "n_matched_months": int(len(hist)),
        "interpretation": f"If the driver is near its seasonal baseline, downstream |z| has historically been {matched_down:.2f} versus {observed_down:.2f} now. A large ratio is consistent with the driver mattering, but confounding remains.",
        "assumptions": [
            "Month-of-year matching is not full confounder control.",
            "Reanalysis errors that co-move across variables can induce spurious ratios.",
            "No claim of identification; labeled scenario analysis.",
        ],
    }


def expected_pattern(template_id: str, detection: dict) -> dict:
    zmap = {s["variable"]: s["seasonal_z"] for s in detection.get("current_signals", [])}
    should_move = DRIVER_VARS.get(template_id, [])
    moved = [v for v in should_move if abs(zmap.get(v, 0)) >= 1.0]
    missing = [v for v in should_move if v not in zmap]
    return {
        "template_id": template_id,
        "should_have_moved": should_move,
        "did_move": moved,
        "not_observed": missing,
        "should_not_need_transport": template_id != "logistics_disruption",
    }
