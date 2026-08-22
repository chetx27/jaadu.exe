from __future__ import annotations

from jaadu.core.schemas import Hypothesis
from jaadu.graph.temporal import node_type_for


def challenge(leading: Hypothesis, others: list[Hypothesis], detection: dict) -> dict:
    attacks = []
    if leading.score.temporal_consistency < 0.5:
        attacks.append("Temporal order does not match the claimed mechanism.")
    if leading.score.contradictory > 0.3:
        attacks.append("Contradictory numeric pattern is already material.")
    if leading.unknown_variables:
        attacks.append(
            "Leader depends on unobserved variables: " + ", ".join(leading.unknown_variables[:6])
        )
    runner = others[0] if others else None
    indistinct = runner is not None and abs(leading.score.posterior - runner.score.posterior) < 0.12
    if indistinct and runner:
        delta = abs(leading.score.posterior - runner.score.posterior)
        attacks.append(f"Cannot distinguish from {runner.template_id} (Δ posterior={delta:.3f}).")
    if not detection.get("multi_signal_alert"):
        attacks.append(
            "Joint anomaly does not meet the multi-signal rule; leader may be overfit to noise."
        )
    expected = set(leading.expected_moved or [])
    hot = {s["variable"] for s in detection.get("current_signals", [])}
    missing_expected = sorted(expected - hot)
    if missing_expected:
        attacks.append("Expected movers not currently hot: " + ", ".join(missing_expected[:6]))
    if leading.template_id == "logistics_disruption" and "TRANSPORT" not in {
        node_type_for(v).value for v in hot
    }:
        attacks.append("Logistics hypothesis has no transport observation in the panel.")
    if leading.template_id == "market_disturbance":
        climate_hot = [v for v in hot if node_type_for(v).value in {"CLIMATE", "WATER"}]
        if climate_hot and not [v for v in hot if node_type_for(v).value == "MARKET"]:
            attacks.append("Climate/water moved without a market signal; market-only story is weak.")
    return {
        "leading_id": leading.hypothesis_id,
        "attacks": attacks,
        "indistinguishable": bool(indistinct),
        "verdict": "insufficient_to_distinguish"
        if indistinct
        else "leader_survives_with_uncertainty",
        "missing_expected_movers": missing_expected,
    }
