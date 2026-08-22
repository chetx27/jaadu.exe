from __future__ import annotations

import pandas as pd
from jaadu.features.leadlag import change_alignment


def test_leadlag_prefers_true_lag():
    idx = pd.date_range("2010-01-01", periods=60, freq="MS")
    a = pd.Series(range(60), index=idx, dtype=float)
    z = pd.DataFrame({"rainfall": a, "soil_moisture": a.shift(3)})
    out = change_alignment(z, "rainfall", "soil_moisture", max_lag=6)
    assert out["status"] == "ok"
    assert out["lag"] == 3
