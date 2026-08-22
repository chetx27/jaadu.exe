from __future__ import annotations

import math
from jaadu.core.config import engine_config, load_domain
from jaadu.core.schemas import CausalStatus, Hypothesis, HypothesisScore
from jaadu.graph.temporal import node_type_for


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _z_map(detection: dict) -> dict[str, float]:
    return {s["variable"]: s["seasonal_z"] for s in detection.get("current_signals", [])}


def _types_present(variables: list[str]) -> set[str]:
    return {node_type_for(v).value for v in variables}


def instantiate_hypotheses(
    geo_id: str, as_of: str, detection: dict, graph: dict, evidence: list[dict]
) -> list[Hypothesis]:
    domain = load_domain()
    cfg = engine_config()["hypothesis"]
    zmap = _z_map(detection)
    hot = [s["variable"] for s in detection.get("current_signals", [])]
    hot_types = _types_present(hot)
    edges = graph.get("edges", [])

    def edge_support(order: list[str]) -> float:
        if len(order) < 2:
            return 0.0
        score = 0.0
        n = 0
        for a, b in zip(order, order[1:]):
            n += 1
            matches = [
                e
                for e in edges
                if node_type_for(e["source"]).value == a and node_type_for(e["target"]).value == b
            ]
            if matches:
                score += max((abs(e["strength"]) * (1 - e["uncertainty"]) for e in matches))
        return score / max(n, 1)

    def temporal_ok(order: list[str]) -> float:
        times = {s["variable"]: s["timestamp"] for s in detection.get("current_signals", [])}
        seq = []
        for t in order:
            vs = [v for v in hot if node_type_for(v).value == t and v in times]
            if vs:
                seq.append(min((times[v] for v in vs)))
        if len(seq) < 2:
            return 0.4
        pairs = sum((1 for (a, b) in zip(seq, seq[1:]) if a <= b))
        return pairs / (len(seq) - 1)

    hyps: list[Hypothesis] = []
    combo = detection.get("combination", {})
    persist = set(detection.get("persistent_variables", []))
    for tmpl in domain["mechanism_templates"]:
        required = set(tmpl.get("required_node_types", []))
        expected_order = tmpl.get("expected_order", [])
        missing_required = [t for t in required if t not in hot_types]
        supporting_vars = [
            v for v in hot if node_type_for(v).value in (required or expected_order or hot_types)
        ]
        contradictory = []
        unknown = list(missing_required)
        if tmpl["id"] == "reporting_artifact":
            supporting = 0.35 if detection["n_abnormal"] <= 2 else 0.1
            contradictory_score = 0.5 if len(persist) >= 3 else 0.15
            temporal = 0.5
            spatial = 0.5
            mechanism = 0.2
            histp = 0.4
        elif tmpl["id"] == "seasonal_baseline":
            supporting = 0.55 if detection["n_abnormal"] == 0 else 0.08
            contradictory_score = 0.7 if detection.get("multi_signal_alert") else 0.2
            temporal = 0.5
            spatial = 0.5
            mechanism = 0.1
            histp = 0.6
        elif tmpl["id"] == "market_disturbance":
            market_hot = [v for v in hot if node_type_for(v).value == "MARKET"]
            climate_hot = [
                v for v in hot if node_type_for(v).value in {"CLIMATE", "WATER", "AGRICULTURE"}
            ]
            supporting = 0.2 + 0.15 * len(market_hot)
            contradictory_score = (
                0.45 if climate_hot and (not market_hot) else 0.15 if climate_hot else 0.05
            )
            temporal = 0.35 if climate_hot else 0.6
            spatial = 0.3
            mechanism = 0.4 if market_hot else 0.15
            histp = 0.4
            unknown.append("local_food_price")
        elif tmpl["id"] == "logistics_disruption":
            supporting = 0.12
            contradictory_score = 0.2
            temporal = 0.3
            spatial = 0.2
            mechanism = 0.25
            histp = 0.25
            unknown.extend(["transport_disruption", "market_arrivals"])
        elif tmpl["id"] == "energy_constraint":
            energy_hot = [v for v in hot if node_type_for(v).value == "ENERGY"]
            supporting = 0.15 + 0.2 * len(energy_hot)
            contradictory_score = 0.1
            temporal = temporal_ok(["ENERGY", "WATER", "AGRICULTURE"])
            spatial = 0.4
            mechanism = 0.35 if energy_hot else 0.15
            histp = 0.3
            if not energy_hot:
                unknown.append("electricity_generation")
        else:
            supporting = (
                0.2
                + 0.12 * len(supporting_vars)
                + 0.08 * len(persist.intersection(supporting_vars))
            )
            supporting += 0.15 * edge_support(expected_order)
            supporting += 0.05 * min(combo.get("surprise", 0), 3)
            contradictory_score = 0.1
            if tmpl["id"] == "environmental_production_shock" and "CLIMATE" not in hot_types:
                contradictory_score += 0.4
            if tmpl["id"] == "hydrological_constraint" and "WATER" not in hot_types:
                contradictory_score += 0.35
            temporal = temporal_ok(expected_order)
            spatial = 0.7 if geo_id not in {"global_market"} else 0.3
            mechanism = 0.55 + 0.2 * edge_support(expected_order)
            histp = min(0.8, 0.3 + 0.1 * combo.get("historical_count", 0))
        for ev in evidence:
            overlap = set(ev.get("variables") or []) & set(hot)
            if not overlap:
                continue
            boost = 0.05 * float(ev.get("confidence", 0.5))
            if tmpl["id"] in {"environmental_production_shock", "hydrological_constraint"}:
                if any(
                    (
                        k in (ev.get("claim") or "").lower()
                        for k in ("drought", "rain", "seca", "reservoir", "monsoon")
                    )
                ):
                    supporting += boost
            if tmpl["id"] == "market_disturbance" and "price" in (ev.get("claim") or "").lower():
                supporting += boost
        data_q = 0.75
        energy = (
            1.4 * supporting
            - 1.2 * contradictory_score
            + 0.8 * temporal
            + 0.5 * spatial
            + 0.7 * mechanism
            + 0.4 * histp
            + 0.3 * data_q
        )
        if tmpl["id"] in {"reporting_artifact"}:
            energy += math.log(cfg["artifact_prior"])
        if tmpl["id"] == "seasonal_baseline":
            energy += math.log(cfg["seasonal_prior"])
        if tmpl["id"] in {"environmental_production_shock", "hydrological_constraint"}:
            energy += math.log(cfg["mechanism_prior_boost"])
        statement = {
            "environmental_production_shock": f"Climate anomalies in {geo_id} may be initiating a production shock via water stress.",
            "hydrological_constraint": f"Hydrological state in {geo_id} may be constraining agricultural activity independently of a new rainfall shock.",
            "logistics_disruption": f"A logistics or transport disruption could produce similar market/activity movements in {geo_id}.",
            "market_disturbance": "International or speculative market movements may explain the observed market signals without a local production shock.",
            "energy_constraint": f"Energy availability may be constraining irrigation or processing in {geo_id}.",
            "reporting_artifact": "The pattern may be a measurement or reanalysis artifact rather than a physical shock.",
            "seasonal_baseline": "The pattern may be ordinary seasonality that the detector has not fully removed.",
        }[tmpl["id"]]
        hyps.append(
            Hypothesis(
                hypothesis_id=f"{geo_id}:{as_of}:{tmpl['id']}",
                template_id=tmpl["id"],
                label=tmpl["label"],
                statement=statement,
                causal_status=CausalStatus.CAUSAL_HYPOTHESIS,
                geo_id=geo_id,
                as_of=as_of,
                assumptions=[
                    "Seasonal z-scores are an adequate baseline.",
                    "ERA5/GloFAS reanalysis is not systematically biased in this window.",
                    "Missing local prices and reservoirs are not secretly driving the conclusion.",
                ],
                expected_moved=supporting_vars,
                expected_not_moved=[],
                supporting_observation_ids=[],
                contradictory_observation_ids=[],
                supporting_evidence_ids=[
                    e["evidence_id"] for e in evidence if e.get("supports_template") == tmpl["id"]
                ],
                unknown_variables=sorted(set(unknown)),
                score=HypothesisScore(
                    supporting=float(supporting),
                    contradictory=float(contradictory_score),
                    temporal_consistency=float(temporal),
                    spatial_consistency=float(spatial),
                    mechanism_support=float(mechanism),
                    historical_precedent=float(histp),
                    data_quality=float(data_q),
                    posterior=float(energy),
                    rank=0,
                ),
                invalidation_tests=[
                    "If the hypothesized driver is held near its seasonal baseline in matched historical windows, downstream anomalies should shrink.",
                    "An independent dataset of a different type should not show the same pattern if this is an artifact.",
                ],
            )
        )
    energies = [h.score.posterior for h in hyps]
    m = max(energies)
    exps = [math.exp((e - m) / cfg["posterior_temperature"]) for e in energies]
    zsum = sum(exps)
    for h, p in zip(hyps, exps):
        h.score.posterior = float(p / zsum)
    hyps.sort(key=lambda h: -h.score.posterior)
    for i, h in enumerate(hyps, start=1):
        h.score.rank = i
    return hyps


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
        attacks.append(
            f"Cannot distinguish from {runner.template_id} (Δ posterior={abs(leading.score.posterior - runner.score.posterior):.3f})."
        )
    if not detection.get("multi_signal_alert"):
        attacks.append(
            "Joint anomaly does not meet the multi-signal rule; leader may be overfit to noise."
        )
    return {
        "leading_id": leading.hypothesis_id,
        "attacks": attacks,
        "indistinguishable": bool(indistinct),
        "verdict": "insufficient_to_distinguish"
        if indistinct
        else "leader_survives_with_uncertainty",
    }
