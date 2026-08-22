from __future__ import annotations

import json
from jaadu.core.config import DATA
from jaadu.core.schemas import AlertReport


def write_markdown_report(payload: dict, path=None):
    report = payload.get("report") or {}
    if not isinstance(report, dict):
        report = AlertReport.model_validate(report).model_dump()
    lines = [
        f"# {report.get('risk', 'investigation')}",
        "",
        f"- Geography: {report.get('geography')}",
        f"- Detection time: {report.get('detection_time')}",
        f"- Earliest signal: {report.get('earliest_signal')}",
        f"- Action class: {report.get('intervention_vs_investigation')}",
        "",
        "## Pathway",
        "",
    ]
    for step in report.get("discovered_pathway") or []:
        lines.append(f"- {step}")
    lead = report.get("leading_hypothesis") or {}
    lines += [
        "",
        "## Leading hypothesis",
        "",
        f"{lead.get('statement') if isinstance(lead, dict) else lead}",
        "",
        "## Next observation",
        "",
        str((report.get("next_best_observation") or {}).get("label") if isinstance(report.get("next_best_observation"), dict) else report.get("next_best_observation")),
        "",
        "## Low-regret action",
        "",
        str(report.get("low_regret_action", "")),
        "",
        "## What would invalidate",
        "",
    ]
    for item in report.get("what_would_invalidate") or []:
        lines.append(f"- {item}")
    text = "\n".join(lines) + "\n"
    out = path or (DATA / "processed" / f"report_{report.get('geography')}_{report.get('detection_time')}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return out
