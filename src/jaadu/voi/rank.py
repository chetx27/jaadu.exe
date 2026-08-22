from __future__ import annotations

import math
from jaadu.core.config import engine_config
from jaadu.core.schemas import Hypothesis, VoICandidate

CANDIDATES = [
    {
        "observation_id": "reservoir_storage_survey",
        "label": "Targeted reservoir / irrigation storage reading",
        "variable": "reservoir_storage",
        "method": "agency request or field gauge photograph with timestamp",
        "cost_usd": 250,
        "days_required": 3,
        "availability": "often obtainable from CWC/SABESP even when not in this repo",
        "geographic_coverage": "basin",
        "informative_for": ["hydrological_constraint", "environmental_production_shock"],
        "not_informative_for": ["market_disturbance", "reporting_artifact"],
    },
    {
        "observation_id": "ndvi_scene",
        "label": "Recent NDVI/EVI scene for the agricultural mask",
        "variable": "ndvi",
        "method": "MODIS/VIIRS or Sentinel-2 composite",
        "cost_usd": 0,
        "days_required": 5,
        "availability": "public, ~1–2 week latency",
        "geographic_coverage": "region",
        "informative_for": ["environmental_production_shock", "hydrological_constraint"],
        "not_informative_for": ["market_disturbance"],
    },
    {
        "observation_id": "local_market_price",
        "label": "Local staple wholesale price (mandi / CEPEA)",
        "variable": "local_food_price",
        "method": "existing market information system pull",
        "cost_usd": 40,
        "days_required": 2,
        "availability": "public delayed feeds exist but were not ingested",
        "geographic_coverage": "market region",
        "informative_for": ["market_disturbance", "environmental_production_shock"],
        "not_informative_for": ["reporting_artifact"],
    },
    {
        "observation_id": "transport_check",
        "label": "Road/rail disruption and market-arrival check",
        "variable": "transport_disruption",
        "method": "logistics bulletin + arrival volumes",
        "cost_usd": 600,
        "days_required": 7,
        "availability": "partial",
        "geographic_coverage": "corridor",
        "informative_for": ["logistics_disruption"],
        "not_informative_for": ["seasonal_baseline"],
    },
    {
        "observation_id": "field_transect",
        "label": "Rapid agricultural field transect / farmer interview sample",
        "variable": "planting_status",
        "method": "enumerator sample",
        "cost_usd": 2400,
        "days_required": 14,
        "availability": "requires field access",
        "geographic_coverage": "district sample",
        "informative_for": ["environmental_production_shock", "hydrological_constraint"],
        "not_informative_for": ["market_disturbance"],
    },
    {
        "observation_id": "wait_next_month",
        "label": "Wait one more month of the existing public series",
        "variable": "existing_panel",
        "method": "no new instrument",
        "cost_usd": 0,
        "days_required": 30,
        "availability": "certain",
        "geographic_coverage": "same as now",
        "informative_for": ["seasonal_baseline", "reporting_artifact"],
        "not_informative_for": [],
    },
    {
        "observation_id": "independent_reanalysis",
        "label": "Cross-check rainfall with a second dataset (IMD/INMET vs ERA5)",
        "variable": "rainfall_crosscheck",
        "method": "gauge or alternative reanalysis extract",
        "cost_usd": 80,
        "days_required": 4,
        "availability": "public with effort",
        "geographic_coverage": "region",
        "informative_for": ["reporting_artifact"],
        "not_informative_for": ["logistics_disruption"],
    },
]


def entropy(probs: list[float]) -> float:
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log(p + 1e-15)
    return h


def likelihoods(hypotheses: list[Hypothesis], cand: dict) -> dict[str, dict[str, float]]:
    out = {}
    inf = set(cand["informative_for"])
    notinf = set(cand["not_informative_for"])
    for h in hypotheses:
        if h.template_id in inf:
            out[h.template_id] = {"support": 0.62, "ambiguous": 0.23, "contradict": 0.15}
        elif h.template_id in notinf:
            out[h.template_id] = {"support": 0.22, "ambiguous": 0.4, "contradict": 0.38}
        else:
            out[h.template_id] = {"support": 0.28, "ambiguous": 0.44, "contradict": 0.28}
    return out


def expected_information_gain(hypotheses: list[Hypothesis], cand: dict) -> tuple[float, float]:
    prior = {h.template_id: h.score.posterior for h in hypotheses}
    h_prior = entropy(list(prior.values()))
    lik = likelihoods(hypotheses, cand)
    xs = ["support", "ambiguous", "contradict"]
    eig = 0.0
    leader = max(prior, key=prior.get)
    expected_leader = 0.0
    for x in xs:
        px = sum((prior[h] * lik[h][x] for h in prior))
        if px <= 0:
            continue
        post = {h: prior[h] * lik[h][x] / px for h in prior}
        eig += px * (h_prior - entropy(list(post.values())))
        expected_leader += px * post[leader]
    return (eig, expected_leader - prior[leader])


def rank_observations(
    hypotheses: list[Hypothesis], already_have: set[str] | None = None
) -> list[VoICandidate]:
    cfg = engine_config()["voi"]
    already_have = already_have or set()
    ranked = []
    for cand in CANDIDATES:
        if cand["variable"] in already_have:
            continue
        (eig, dlead) = expected_information_gain(hypotheses, cand)
        denom = max(cand["cost_usd"], 1.0) * (
            1.0 + cfg["time_penalty_lambda"] * cand["days_required"]
        )
        if cand["cost_usd"] <= 0:
            denom = 1.0 + cfg["time_penalty_lambda"] * cand["days_required"]
        cnv = eig / denom
        unc_red = eig / max(entropy([h.score.posterior for h in hypotheses]), 1e-06)
        ranked.append(
            VoICandidate(
                observation_id=cand["observation_id"],
                label=cand["label"],
                variable=cand["variable"],
                method=cand["method"],
                cost_usd=float(cand["cost_usd"]),
                days_required=float(cand["days_required"]),
                availability=cand["availability"],
                geographic_coverage=cand["geographic_coverage"],
                expected_information_gain=float(eig),
                expected_uncertainty_reduction=float(unc_red),
                decision_impact=float(dlead),
                cost_normalized_voi=float(cnv),
                rank=0,
                rationale=f"EIG={eig:.3f} nats over the hypothesis simplex; expected change in leader posterior={dlead:.3f}; cost-normalized VoI={cnv:.4f}.",
            )
        )
    ranked.sort(key=lambda c: -c.cost_normalized_voi)
    for i, c in enumerate(ranked, start=1):
        c.rank = i
    return ranked
