from __future__ import annotations

"""Dialogflow CX/ES webhook. Maps utterances onto existing engine APIs.

The agent does not generate hypotheses. It calls investigate / perturb / ablate
and returns their structured fields as fulfillment text.
"""

from jaadu.google import settings
from jaadu.investigate import ablate, investigate, perturb


INTENT_INVESTIGATE = "InvestigateRegion"
INTENT_PERTURB = "PerturbVariable"
INTENT_ABLATE = "AblateDataset"
INTENT_VOI = "NextObservation"
INTENT_REVEAL = "RevealOutcome"


def _params(body: dict) -> dict:
    qr = body.get("queryResult") or {}
    session_info = body.get("sessionInfo") or {}
    params = dict(qr.get("parameters") or {})
    params.update(session_info.get("parameters") or {})
    return params


def _intent_name(body: dict) -> str:
    qr = body.get("queryResult") or {}
    intent = qr.get("intent") or {}
    name = intent.get("displayName") or body.get("intentInfo", {}).get("displayName") or ""
    return str(name)


def _fulfillment(text: str, payload: dict | None = None) -> dict:
    out = {"fulfillmentText": text, "fulfillment_text": text}
    if payload is not None:
        out["payload"] = payload
    return out


def handle_webhook(body: dict) -> dict:
    intent = _intent_name(body)
    params = _params(body)
    region = str(params.get("region") or params.get("geo_id") or "").strip()
    as_of = str(params.get("as_of") or params.get("date") or "").strip()

    if intent == INTENT_REVEAL:
        return _fulfillment(
            "Held-out historical outcomes stay on the investigation bench reveal control. "
            "This webhook will not speak conventional visibility dates or documented mechanisms."
        )

    if not region or not as_of:
        return _fulfillment("Need region and as-of date. Example: investigate Marathwada as of 2015-08-01.")

    if intent in {INTENT_INVESTIGATE, INTENT_VOI, ""}:
        inv = investigate(region, as_of, use_gemini=False)
        if inv.get("error"):
            return _fulfillment(f"No panel for {region} at {as_of}. Run ingest first.")
        report = inv.get("report") or {}
        voi = (inv.get("voi") or [{}])[0]
        leader = (inv.get("hypotheses") or [{}])[0]
        if intent == INTENT_VOI:
            text = (
                f"Next observation: {voi.get('label')}. "
                f"EIG {voi.get('expected_information_gain')}. "
                "This is value of information, not a Google suggestion."
            )
        else:
            text = (
                f"{report.get('risk')} in {region} as of {as_of}. "
                f"Leader {leader.get('template_id')}. "
                f"Next: {voi.get('label')}. Gemini did not produce this alert."
            )
        return _fulfillment(text, {"investigation": {"risk": report.get("risk"), "leader": leader.get("template_id")}})

    if intent == INTENT_PERTURB:
        variable = str(params.get("variable") or "rainfall")
        delta = float(params.get("delta_z") or params.get("delta") or -1.5)
        data = perturb(region, as_of, variable, delta)
        leader = (data.get("hypotheses") or [{}])[0]
        return _fulfillment(
            f"Perturbed {variable} by {delta} z. Leader now {leader.get('template_id')}. Synthetic Δz, not a forecast."
        )

    if intent == INTENT_ABLATE:
        raw = params.get("variables") or params.get("drop_variables") or params.get("variable") or ""
        if isinstance(raw, list):
            drop = [str(x) for x in raw]
        else:
            drop = [p.strip() for p in str(raw).split(",") if p.strip()]
        data = ablate(region, as_of, drop)
        return _fulfillment(f"Dropped {drop}. Missingness is explicit; no imputation.")

    return _fulfillment(f"Unknown intent {intent}. Supported: {INTENT_INVESTIGATE}, {INTENT_PERTURB}, {INTENT_ABLATE}, {INTENT_VOI}.")


def secret_ok(header_value: str | None) -> bool:
    expected = settings.dialogflow_webhook_secret()
    if not expected:
        return True
    return header_value == expected
