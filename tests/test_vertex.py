from __future__ import annotations

import inspect
import math
import pandas as pd
from jaadu.baselines.vertex import (
    baseline_vertex,
    instance_from_row,
    parse_vertex_prediction,
    slice_as_of,
)
from jaadu.google.status import google_status
from jaadu.investigate import investigate


def test_vertex_skips_without_opt_in():
    panel = pd.DataFrame(
        {"rainfall": [1.0, 2.0]}, index=pd.to_datetime(["2015-07-01", "2015-08-01"])
    )
    out = baseline_vertex(panel, "2015-08-01", "marathwada")
    assert out["name"] == "vertex_automl"
    assert out["skipped"] is True
    assert out["alert"] is False
    assert out["used_as_jaadu_alert"] is False
    assert "JAADU_VERTEX_BASELINE" in out["reason"]


def test_slice_as_of_drops_future_months():
    panel = pd.DataFrame(
        {"rainfall": [1.0, 2.0, 99.0]},
        index=pd.to_datetime(["2015-07-01", "2015-08-01", "2015-09-01"]),
    )
    sliced = slice_as_of(panel, "2015-08-01")
    assert list(sliced["rainfall"]) == [1.0, 2.0]


def test_instance_drops_nan_and_inf():
    row = pd.Series({"rainfall": 3.2, "ndvi": math.nan, "bad": math.inf, "label": "x"})
    inst = instance_from_row(row)
    assert inst == {"rainfall": 3.2}


def test_unlabeled_score_is_not_an_alert():
    parsed = parse_vertex_prediction(0.9)
    assert parsed["alert"] is False
    assert parsed["score"] == 0.9
    assert parsed["vertex_model_alert"] is None
    assert parsed["used_as_jaadu_alert"] is False


def test_explicit_model_alert_is_recorded_not_promoted():
    parsed = parse_vertex_prediction({"alert": True, "score": 0.2})
    assert parsed["alert"] is True
    assert parsed["used_as_jaadu_alert"] is False
    assert parsed["vertex_model_alert"] is True


def test_google_status_vertex_off_by_default():
    flags = google_status()
    assert flags["vertex_opt_in"] is False
    assert flags["vertex"] is False


def test_investigate_module_does_not_reference_vertex():
    source = inspect.getsource(inspect.getmodule(investigate))
    assert "vertex" not in source.lower()
