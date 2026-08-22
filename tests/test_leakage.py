from __future__ import annotations

import pandas as pd
from jaadu.evaluation.leakage import audit_documents, audit_observations
from jaadu.evaluation.metrics import binary_scores, lead_days


def test_lead_days_positive_when_early():
    assert lead_days("2015-08-01", "2015-11-01") == 92


def test_binary_scores_perfect():
    s = binary_scores([True, False], [True, False])
    assert s["precision"] == 1.0
    assert s["recall"] == 1.0


def test_observation_audit_flags_future_availability():
    df = pd.DataFrame(
        {
            "observation_id": ["a", "b"],
            "variable": ["rainfall", "rainfall"],
            "node_type": ["CLIMATE", "CLIMATE"],
            "timestamp": ["2015-07-01", "2015-09-01"],
            "available_at": ["2015-07-01", "2015-09-01"],
            "geo_id": ["x", "x"],
            "value": [1.0, 2.0],
            "unit": ["mm", "mm"],
            "source": ["t", "t"],
            "quality_score": [0.8, 0.8],
        }
    )
    out = audit_observations(df, "2015-08-01")
    assert out["n_used"] == 1
    assert out["leaked_available_at_after_cutoff"] == 0
    assert out["pass"] is True


def test_documents_respect_cutoff():
    early = audit_documents("2014-01-01")
    late = audit_documents("2017-01-01")
    assert early["pass"] is True
    assert late["n_admitted"] >= early["n_admitted"]
