from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from jaadu.core.provenance import evidence_dir, provenance_hash
from jaadu.core.schemas import EvidenceObject, ExtractionKind
from jaadu.ingestion.documents import documents_as_of

VARIABLE_HINTS = {
    "rainfall": "rain|precip|monsoon|chuv",
    "temperature": "heat|temperat|warm",
    "soil_moisture": "soil moisture|soil water",
    "river_discharge": "inflow|discharge|runoff",
    "reservoir_storage": "reservoir|cantareira|storage|armazen",
    "cereal_yield": "yield|pulse|kharif|sugarcane|coffee|crop loss|produção",
    "food_price_index": "price|preço|inflation",
    "enso_oni": "el niñ|el nino|enso",
    "ndvi": "vegetation|ndvi|crop condition",
}


def heuristic_extract(doc: dict) -> list[EvidenceObject]:
    text = doc["text"]
    vars_found = [v for (v, pat) in VARIABLE_HINTS.items() if re.search(pat, text, re.I)]
    direction = None
    if re.search("deficit|below|drought|seca|loss|decline|low", text, re.I):
        direction = "decrease"
    elif re.search("above|excess|flood|surge", text, re.I):
        direction = "increase"
    claim = text.split(".")[0].strip()[:400]
    ev = EvidenceObject(
        evidence_id=f"{doc['doc_id']}:heuristic",
        claim=claim,
        source=doc["source"],
        source_url=doc.get("url"),
        published_at=doc["published_at"],
        ingested_at=datetime.now(timezone.utc).isoformat(),
        geographic_scope=doc["geographic_scope"],
        entities=[doc["geographic_scope"]],
        variables=vars_found,
        direction=direction,
        magnitude=None,
        time_relationship="as_stated_in_source",
        confidence=0.45,
        supporting_passage=text[:800],
        source_reliability=0.7 if "POST-EVENT" not in text else 0.85,
        extraction_kind=ExtractionKind.HEURISTIC_EXTRACTION,
        extractor="jaadu.multimodal.heuristic",
        model_name=None,
        provenance_hash=provenance_hash({"doc": doc["doc_id"], "claim": claim}),
    )
    return [ev]


def gemini_extract(doc: dict) -> list[EvidenceObject]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai
    from google.genai import types

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    schema_instruction = "\nExtract structured evidence objects from the document. Return JSON list with keys:\nclaim, variables (from: rainfall, temperature, soil_moisture, river_discharge,\nreservoir_storage, cereal_yield, food_price_index, enso_oni, ndvi, transport_disruption),\ndirection (increase|decrease|unclear), magnitude (string or null),\ntime_relationship, confidence (0-1), supporting_passage (verbatim quote),\ncontradictory_passage (or null), geographic_scope, entities.\nDo NOT invent numeric measurements that are not in the text.\nIf you interpret rather than quote a measurement, set extraction_kind to interpretation.\nIf the document is post-event analysis, say so in the claim.\n"
    prompt = (
        schema_instruction
        + "\n\nTITLE: "
        + doc["title"]
        + "\nPUBLISHED: "
        + doc["published_at"]
        + "\nSOURCE: "
        + doc["source"]
        + "\nTEXT:\n"
        + doc["text"]
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
    )
    raw = json.loads(response.text)
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("evidence") or [raw]
    out = []
    for i, item in enumerate(raw):
        kind = ExtractionKind.INTERPRETATION
        if item.get("supporting_passage") and item.get("supporting_passage") in doc["text"]:
            kind = ExtractionKind.STRUCTURED_EXTRACT
        ev = EvidenceObject(
            evidence_id=f"{doc['doc_id']}:gemini:{i}",
            claim=str(item.get("claim", ""))[:500],
            source=doc["source"],
            source_url=doc.get("url"),
            published_at=doc["published_at"],
            ingested_at=datetime.now(timezone.utc).isoformat(),
            geographic_scope=str(item.get("geographic_scope") or doc["geographic_scope"]),
            entities=list(item.get("entities") or []),
            variables=list(item.get("variables") or []),
            direction=item.get("direction"),
            magnitude=item.get("magnitude"),
            time_relationship=item.get("time_relationship"),
            confidence=float(item.get("confidence") or 0.5),
            supporting_passage=str(item.get("supporting_passage") or "")[:1000],
            contradictory_passage=item.get("contradictory_passage"),
            source_reliability=0.75,
            extraction_kind=kind,
            extractor="gemini",
            model_name=model,
            provenance_hash=provenance_hash({"doc": doc["doc_id"], "item": item}),
        )
        out.append(ev)
    log_path = evidence_dir() / "gemini_raw.jsonl"
    log_path.open("a").write(json.dumps({"doc_id": doc["doc_id"], "raw": raw}, default=str) + "\n")
    return out


def extract_corpus(cutoff: str, use_gemini: bool | None = None) -> list[dict]:
    docs = documents_as_of(cutoff)
    use = use_gemini if use_gemini is not None else bool(os.environ.get("GEMINI_API_KEY"))
    all_ev = []
    for doc in docs:
        try:
            if use:
                evs = gemini_extract(doc)
            else:
                evs = heuristic_extract(doc)
        except Exception:
            evs = heuristic_extract(doc)
            for e in evs:
                e.notes = "gemini_failed_fallback_heuristic"
        all_ev.extend(evs)
    payload = [e.model_dump() for e in all_ev]
    out = evidence_dir() / f"evidence_{cutoff}.json"
    out.write_text(json.dumps(payload, indent=2, default=str))
    return payload
