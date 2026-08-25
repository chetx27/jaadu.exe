from __future__ import annotations

from jaadu.google import settings
from jaadu.google.clients import translate_client


def maybe_translate_doc(doc: dict, target: str | None = None) -> dict:
    """Translate dated document text into the working language.

    Publication date, source, and geographic scope are unchanged. Failure
    returns the original document so extract still runs.
    """
    lang = (doc.get("language") or "en").split("-")[0].lower()
    dest = (target or settings.translate_target()).lower()
    if lang == dest or not doc.get("text"):
        return doc
    client = translate_client()
    if client is None:
        out = dict(doc)
        out["translation"] = "skipped_no_google_project"
        return out
    try:
        result = client.translate(doc["text"], target_language=dest, source_language=lang)
        out = dict(doc)
        out["text_original"] = doc["text"]
        out["text"] = result["translatedText"]
        out["language"] = dest
        out["translation"] = "google_translate"
        return out
    except Exception as exc:
        out = dict(doc)
        out["translation"] = f"failed:{exc}"
        return out


def translate_text(text: str, target: str, source: str = "en") -> dict:
    if not text:
        return {"text": "", "translation": "empty"}
    if source.split("-")[0].lower() == target.split("-")[0].lower():
        return {"text": text, "translation": "identity"}
    client = translate_client()
    if client is None:
        return {"text": text, "translation": "skipped_no_google_project"}
    result = client.translate(text, target_language=target, source_language=source)
    return {"text": result["translatedText"], "translation": "google_translate"}
