from jaadu.core.time import apply_availability_lag, filter_as_of
from jaadu.voi.rank import entropy, rank_observations
from jaadu.core.schemas import CausalStatus, Hypothesis, HypothesisScore
import pandas as pd


def test_availability_cannot_precede_valid_time_math():
    ts = pd.Timestamp("2015-08-01")
    assert apply_availability_lag(ts, 0) == ts
    assert apply_availability_lag(ts, 8) == pd.Timestamp("2016-04-01")


def test_as_of_filter_excludes_future():
    df = pd.DataFrame({"available_at": ["2015-07-01", "2015-09-01"], "v": [1, 2]})
    out = filter_as_of(df, "2015-08-01")
    assert list(out["v"]) == [1]


def _h(tid, p):
    return Hypothesis(
        hypothesis_id=tid,
        template_id=tid,
        label=tid,
        statement=tid,
        causal_status=CausalStatus.CAUSAL_HYPOTHESIS,
        geo_id="x",
        as_of="2015-08-01",
        score=HypothesisScore(
            supporting=0.5,
            contradictory=0.1,
            temporal_consistency=0.5,
            spatial_consistency=0.5,
            mechanism_support=0.5,
            historical_precedent=0.5,
            data_quality=0.5,
            posterior=p,
            rank=1,
        ),
    )


def test_voi_ranks_and_sums_to_positive_eig():
    hyps = [
        _h("environmental_production_shock", 0.45),
        _h("hydrological_constraint", 0.25),
        _h("market_disturbance", 0.15),
        _h("reporting_artifact", 0.15),
    ]
    ranked = rank_observations(hyps, already_have=set())
    assert ranked
    assert ranked[0].expected_information_gain >= 0
    assert entropy([h.score.posterior for h in hyps]) > 0
    ids = [c.observation_id for c in ranked]
    assert "wait_next_month" in ids
