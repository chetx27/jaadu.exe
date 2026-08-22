from __future__ import annotations

from fastapi import FastAPI, HTTPException
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


@app.get("/api/health")
def health():
    return {"ok": True, "product": "jaadu.exe", "not_a_dashboard": True}


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
def api_investigate(region: str, as_of: str, gemini: bool = False):
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
