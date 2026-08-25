from __future__ import annotations

import json
from datetime import datetime, timezone
from jaadu.core.provenance import provenance_hash
from jaadu.core.schemas import EvidenceObject, ExtractionKind
from jaadu.google import settings
from jaadu.google.clients import gemini_client


PHOTO_PROMPT = """You are structuring a dated field photograph as evidence for a research
investigation engine. Return JSON with keys:
claim, variables (from: rainfall, temperature, soil_moisture, river_discharge,
reservoir_storage, cereal_yield, food_price_index, enso_oni, ndvi, crop_disease,
air_quality, transport_disruption), direction (increase|decrease|unclear),
magnitude (string or null), confidence (0-1), supporting_passage (describe only
what is visible), geographic_scope.
Do NOT invent rainfall millimetres, prices, or reservoir percentages.
If you interpret crop stress or haze, say so. extraction is always interpretation.
"""


def caption_only_evidence(meta: dict) -> EvidenceObject:
    caption = (meta.get("caption") or "Photograph admitted without automated interpretation.")[:500]
    return EvidenceObject(
        evidence_id=f"{meta.get('photo_id', 'photo')}:caption",
        claim=caption,
        source=meta.get("source") or "investigator_upload",
        source_url=meta.get("source_url"),
        published_at=meta["published_at"],
        ingested_at=datetime.now(timezone.utc).isoformat(),
        geographic_scope=str(meta.get("geographic_scope") or meta.get("region") or "unknown"),
        entities=[str(meta.get("region") or "")],
        variables=[],
        direction=None,
        magnitude=None,
        time_relationship="as_stated_in_source",
        confidence=0.25,
        supporting_passage=caption,
        source_reliability=0.4,
        extraction_kind=ExtractionKind.INTERPRETATION,
        extractor="jaadu.multimodal.vision.caption",
        model_name=None,
        provenance_hash=provenance_hash({"photo": meta.get("photo_id"), "caption": caption}),
    )


def gemini_photo_extract(meta: dict, image_bytes: bytes) -> EvidenceObject:
    from google.genai import types

    model = settings.gemini_model()
    client = gemini_client()
    prompt = (
        PHOTO_PROMPT
        + f"\nPUBLISHED_AT: {meta['published_at']}\nREGION: {meta.get('region')}\nCAPTION: {meta.get('caption') or ''}"
    )
    response = client.models.generate_content(
        model=model,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=meta.get("mime_type") or "image/jpeg"),
        ],
        config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
    )
    raw = json.loads(response.text)
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    claim = str(raw.get("claim") or meta.get("caption") or "photo")[:500]
    return EvidenceObject(
        evidence_id=f"{meta.get('photo_id', 'photo')}:gemini-vision",
        claim=claim,
        source=meta.get("source") or "investigator_upload",
        source_url=meta.get("source_url"),
        published_at=meta["published_at"],
        ingested_at=datetime.now(timezone.utc).isoformat(),
        geographic_scope=str(raw.get("geographic_scope") or meta.get("region") or "unknown"),
        entities=list(raw.get("entities") or [meta.get("region")]),
        variables=list(raw.get("variables") or []),
        direction=raw.get("direction"),
        magnitude=raw.get("magnitude"),
        time_relationship="as_stated_in_source",
        confidence=float(raw.get("confidence") or 0.4),
        supporting_passage=str(raw.get("supporting_passage") or claim)[:1000],
        source_reliability=0.45,
        extraction_kind=ExtractionKind.INTERPRETATION,
        extractor="gemini_multimodal",
        model_name=model,
        provenance_hash=provenance_hash({"photo": meta.get("photo_id"), "raw": raw}),
    )


def extract_photo(meta: dict, image_bytes: bytes | None = None) -> EvidenceObject:
    if image_bytes and settings.gemini_api_key():
        try:
            return gemini_photo_extract(meta, image_bytes)
        except Exception:
            return caption_only_evidence(meta)
    return caption_only_evidence(meta)
