from __future__ import annotations

from functools import lru_cache
from jaadu.google import settings


def gemini_client():
    api_key = settings.gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai

    return genai.Client(api_key=api_key)


def earth_engine_ready() -> bool:
    return bool(settings.project_id() or settings.credentials_path())


def init_earth_engine() -> bool:
    """Initialize the Earth Engine client. Returns False if unused/unconfigured."""
    if not earth_engine_ready():
        return False
    import ee

    project = settings.project_id()
    creds_path = settings.credentials_path()
    if creds_path:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/earthengine"],
        )
        ee.Initialize(credentials=creds, project=project)
        return True
    ee.Initialize(project=project)
    return True


@lru_cache(maxsize=1)
def translate_client():
    if not settings.project_id():
        return None
    from google.cloud import translate_v2 as translate

    return translate.Client()


@lru_cache(maxsize=1)
def speech_client():
    if not settings.project_id():
        return None
    from google.cloud import speech

    return speech.SpeechClient()


@lru_cache(maxsize=1)
def tts_client():
    if not settings.project_id():
        return None
    from google.cloud import texttospeech

    return texttospeech.TextToSpeechClient()


def bigquery_client():
    if not settings.project_id():
        return None
    from google.cloud import bigquery

    return bigquery.Client(project=settings.project_id(), location=settings.location())


def vertex_init() -> bool:
    if not settings.project_id():
        return False
    import vertexai

    vertexai.init(project=settings.project_id(), location=settings.location())
    return True
