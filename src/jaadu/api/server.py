from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jaadu.core.config import DATA, EXPERIMENTS, all_regions, load_benchmark, load_registry
from jaadu.investigate import ablate, investigate, perturb, world_state

app = FastAPI(title="jaadu.exe", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class PerturbBody(BaseModel):
    region: str
    as_of: str
    variable: str
    delta_z: float = -1.0


class AblateBody(BaseModel):
    region: str
    as_of: str
    drop_variables: list[str]


class PhotoBody(BaseModel):
    region: str
    as_of: str
    published_at: str
    caption: str | None = None
    image_b64: str | None = None
    mime_type: str = "image/jpeg"
    source: str | None = None


class TranslateBody(BaseModel):
    text: str
    target: str = "hi"
    source: str = "en"


class BriefBody(BaseModel):
    region: str
    as_of: str
    language_code: str = "en-IN"
    speak: bool = False
    gemini: bool = False


@app.get("/api/health")
def health():
    from jaadu.google.status import google_status

    flags = google_status()
    return {
        "ok": True,
        "product": "jaadu.exe",
        "not_a_dashboard": True,
        "google": {k: flags[k] for k in ("gemini", "earth_engine", "maps", "dialogflow", "vertex") if k in flags},
    }


@app.get("/api/google")
def api_google():
    from jaadu.google.status import google_status

    return google_status()


@app.get("/api/regions")
def regions():
    return all_regions()


@app.get("/api/registry")
def registry():
    return [r.model_dump() for r in load_registry()]


@app.get("/api/events")
def events():
    return load_benchmark()["events"]


@app.get("/api/world-state")
def api_world_state(region: str, as_of: str):
    try:
        return world_state(region, as_of)
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/investigate")
def api_investigate(region: str, as_of: str, gemini: bool = False, refresh: bool = False):
    from jaadu.api.cache import load_cached

    if not gemini and not refresh:
        cached = load_cached(region, as_of)
        if cached:
            return cached
    try:
        return investigate(region, as_of, use_gemini=gemini or None)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/perturb")
def api_perturb(body: PerturbBody):
    return perturb(body.region, body.as_of, body.variable, body.delta_z)


@app.post("/api/ablate")
def api_ablate(body: AblateBody):
    return ablate(body.region, body.as_of, body.drop_variables)


@app.post("/api/dialogflow")
def api_dialogflow(body: dict, x_dialogflow_secret: str | None = Header(default=None)):
    from jaadu.api.dialogflow import handle_webhook, secret_ok

    if not secret_ok(x_dialogflow_secret):
        raise HTTPException(401, "bad webhook secret")
    try:
        return handle_webhook(body)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/evidence/photo")
def api_photo(body: PhotoBody):
    import base64
    import json
    import pandas as pd
    from jaadu.core.provenance import evidence_dir
    from jaadu.multimodal.vision import extract_photo

    if pd.Timestamp(body.published_at) > pd.Timestamp(body.as_of):
        raise HTTPException(400, "photo published_at is after as_of cutoff")
    image_bytes = base64.b64decode(body.image_b64) if body.image_b64 else None
    ev = extract_photo(
        {
            "photo_id": f"{body.region}:{body.published_at}",
            "region": body.region,
            "geographic_scope": body.region,
            "published_at": body.published_at,
            "caption": body.caption,
            "source": body.source or "investigator_upload",
            "mime_type": body.mime_type,
        },
        image_bytes,
    )
    path = evidence_dir() / "photos.jsonl"
    path.open("a").write(json.dumps(ev.model_dump(), default=str) + "\n")
    return ev.model_dump()


@app.post("/api/translate")
def api_translate(body: TranslateBody):
    from jaadu.multimodal.translate import translate_text

    return translate_text(body.text, body.target, body.source)


@app.post("/api/brief")
def api_brief(body: BriefBody):
    import base64
    from jaadu.multimodal.translate import translate_text
    from jaadu.multimodal.voice import synthesize_brief

    inv = investigate(body.region, body.as_of, use_gemini=body.gemini or None)
    if inv.get("error"):
        raise HTTPException(400, str(inv))
    report = inv.get("report") or {}
    leader = report.get("leading_hypothesis") or {}
    next_obs = report.get("next_best_observation") or {}
    text = (
        f"{report.get('risk')} in {report.get('geography')} as of {report.get('detection_time')}. "
        f"Leading hypothesis: {leader.get('statement') or 'none'}. "
        f"Next observation: {next_obs.get('label') or 'n/a'}. "
        "This is not a price or rainfall forecast."
    )
    lang = body.language_code.split("-")[0]
    if lang != "en":
        text = translate_text(text, lang, "en").get("text") or text
    audio = synthesize_brief(text, body.language_code) if body.speak else {"skipped": True, "reason": "speak=false"}
    payload = {"text": text, "tts": {k: audio[k] for k in audio if k != "audio_content"}}
    if audio.get("audio_content"):
        payload["audio_mp3_b64"] = base64.b64encode(audio["audio_content"]).decode("ascii")
    return payload


@app.get("/api/evidence/{evidence_id}")
def api_evidence(evidence_id: str):
    from jaadu.evidence.store import get_evidence

    rec = get_evidence(evidence_id)
    if rec is None:
        raise HTTPException(404, "unknown evidence_id")
    return rec


@app.get("/api/leakage")
def api_leakage(region: str, as_of: str):
    from jaadu.evaluation.leakage import run_leakage_audit
    from jaadu.investigate import load_observations

    try:
        obs = load_observations()
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc
    return run_leakage_audit(obs, as_of)


@app.get("/api/quality")
def api_quality():
    from jaadu.investigate import load_observations
    from jaadu.validation.quality import quality_report

    try:
        return quality_report(load_observations())
    except FileNotFoundError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/benchmark")
def api_benchmark():
    path = EXPERIMENTS / "results" / "benchmark.json"
    if not path.exists():
        return {"error": "run python -m jaadu evaluate first"}
    import json

    return json.loads(path.read_text())


frontend_dir = DATA.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="ui")
