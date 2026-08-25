from __future__ import annotations

from jaadu.google import settings


def google_status() -> dict:
    """Public, non-secret capability flags for the investigation bench."""
    project = settings.project_id()
    creds = settings.credentials_path()
    return {
        "product": "jaadu.exe",
        "rule": (
            "Google services structure evidence, maps, language, deploy, and an "
            "optional Vertex comparator. They do not produce the multi-signal alert "
            "and cannot write numeric observations."
        ),
        "gemini": bool(settings.gemini_api_key()),
        "gemini_model": settings.gemini_model() if settings.gemini_api_key() else None,
        "vertex": bool(project),
        "vertex_baseline_endpoint": bool(settings.vertex_baseline_endpoint()),
        "vertex_vision_endpoint": bool(settings.vertex_vision_endpoint()),
        "earth_engine": bool(project or creds),
        "bigquery": bool(project),
        "translate": bool(project),
        "speech": bool(project),
        "text_to_speech": bool(project),
        "dialogflow": bool(settings.dialogflow_agent_id()),
        "firebase": bool(settings.env("FIREBASE_PROJECT_ID")),
        "maps": bool(settings.maps_browser_key()),
        "maps_browser_key": settings.maps_browser_key(),
        "data_gov_in": bool(settings.data_gov_in_key()),
        "project_configured": bool(project),
        "location": settings.location(),
    }
