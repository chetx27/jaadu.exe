from __future__ import annotations

import pandas as pd
from jaadu.graph.temporal import lagged_crosscorr, node_type_for


def test_node_type_climate():
    assert node_type_for("rainfall").value == "CLIMATE"
    assert node_type_for("soil_moisture").value == "WATER"


def test_lagged_crosscorr_finds_shift():
    idx = pd.date_range("2010-01-01", periods=80, freq="MS")
    a = pd.Series(range(80), index=idx, dtype=float)
    b = a.shift(2)
    lag, c = lagged_crosscorr(a, b, 6)
    assert lag == 2
    assert abs(c) > 0.8
