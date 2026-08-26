from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def project_id() -> str | None:
    return env("GOOGLE_CLOUD_PROJECT") or env("GCLOUD_PROJECT") or env("FIREBASE_PROJECT_ID")


def location() -> str:
    return env("GOOGLE_CLOUD_LOCATION", "asia-south1") or "asia-south1"


def gemini_api_key() -> str | None:
    return env("GEMINI_API_KEY")


def gemini_model() -> str:
    return env("GEMINI_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash"


def credentials_path() -> str | None:
    return env("GOOGLE_APPLICATION_CREDENTIALS") or env("EARTHENGINE_SERVICE_ACCOUNT")


def maps_browser_key() -> str | None:
    return env("MAPS_BROWSER_KEY") or env("MAPS_API_KEY")


def bigquery_dataset() -> str:
    return env("BIGQUERY_DATASET", "jaadu_public") or "jaadu_public"


def vertex_baseline_endpoint() -> str | None:
    return env("VERTEX_BASELINE_ENDPOINT")


def vertex_baseline_opt_in() -> bool:
    flag = (env("JAADU_VERTEX_BASELINE") or "").lower()
    return flag in {"1", "true", "yes", "on"}


def vertex_vision_endpoint() -> str | None:
    return env("VERTEX_VISION_ENDPOINT")


def dialogflow_agent_id() -> str | None:
    return env("DIALOGFLOW_AGENT_ID")


def dialogflow_webhook_secret() -> str | None:
    return env("DIALOGFLOW_WEBHOOK_SECRET")


def data_gov_in_key() -> str | None:
    return env("DATA_GOV_IN_API_KEY")


def translate_target() -> str:
    return env("TRANSLATE_TARGET", "en") or "en"
