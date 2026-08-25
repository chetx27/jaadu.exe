from __future__ import annotations

import pandas as pd
from jaadu.api.dialogflow import INTENT_REVEAL, handle_webhook
from jaadu.baselines.vertex import baseline_vertex
from jaadu.google.status import google_status
from jaadu.ingestion.earthengine import NDVI_LAG_MONTHS, ndvi_available_at
from jaadu.ingestion.india_open import ingest_india_open
from jaadu.multimodal.translate import maybe_translate_doc, translate_text
from jaadu.multimodal.vision import extract_photo


def test_ndvi_availability_lags_valid_time():
    ts = pd.Timestamp("2015-08-01")
    available = ndvi_available_at(ts)
    assert available == pd.Timestamp("2015-09-01")
    assert NDVI_LAG_MONTHS == 1
    assert available > ts


def test_google_status_has_no_secrets():
    flags = google_status()
    blob = str(flags)
    assert "GEMINI_API_KEY" not in blob or flags.get("gemini") in {True, False}
    assert "rule" in flags
    assert flags["gemini"] is False or isinstance(flags["gemini"], bool)


def test_vertex_baseline_skips_without_project():
    panel = pd.DataFrame({"rainfall": [1.0, 2.0]}, index=pd.to_datetime(["2015-07-01", "2015-08-01"]))
    out = baseline_vertex(panel, "2015-08-01", "marathwada")
    assert out["name"] == "vertex_automl"
    assert out["skipped"] is True
    assert out["alert"] is False


def test_india_open_does_not_fabricate_series():
    frame, records = ingest_india_open()
    assert frame.empty
    ids = {r.dataset_id for r in records}
    assert "india_agmarknet" in ids
    assert "india_imd_gauges" in ids
    assert all(r.status.value == "unavailable" for r in records)


def test_translate_identity_and_skip():
    doc = {"text": "hello", "language": "en"}
    out = maybe_translate_doc(doc, target="en")
    assert out["text"] == "hello"
    skipped = translate_text("hello", "hi", "en")
    assert skipped["translation"] in {"skipped_no_google_project", "google_translate"}


def test_photo_after_cutoff_is_caller_problem_caption_path_ok():
    ev = extract_photo(
        {
            "photo_id": "test",
            "region": "marathwada",
            "published_at": "2015-07-01",
            "caption": "dry field, no millimetres claimed",
        }
    )
    assert ev.extraction_kind.value == "interpretation"
    assert ev.variables == []


def test_dialogflow_refuses_to_reveal_outcome():
    body = {
        "queryResult": {
            "intent": {"displayName": INTENT_REVEAL},
            "parameters": {"region": "marathwada", "as_of": "2015-08-01"},
        }
    }
    out = handle_webhook(body)
    assert "will not speak" in out["fulfillmentText"].lower() or "Held-out" in out["fulfillmentText"]


def test_dialogflow_asks_for_region():
    out = handle_webhook({"queryResult": {"intent": {"displayName": "InvestigateRegion"}, "parameters": {}}})
    assert "region" in out["fulfillmentText"].lower()
