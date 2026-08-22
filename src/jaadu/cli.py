from __future__ import annotations

import argparse
import json
import os


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jaadu")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="Download public datasets and build the observation store")
    p_inv = sub.add_parser("investigate", help="Run the discovery engine for a region and cutoff")
    p_inv.add_argument("--region", required=True)
    p_inv.add_argument("--as-of", required=True)
    p_inv.add_argument("--gemini", action="store_true")
    sub.add_parser("evaluate", help="Run the historical replay benchmark")
    p_pre = sub.add_parser("precompute", help="Run investigations for all benchmark cutoffs")
    p_rob = sub.add_parser("robustness", help="Run missingness/noise/delay stress tests")
    p_leak = sub.add_parser("leakage-audit", help="Audit as-of leakage for a region cutoff")
    p_leak.add_argument("--region", required=True)
    p_leak.add_argument("--as-of", required=True)
    p_serve = sub.add_parser("serve", help="Start the investigation API")
    p_serve.add_argument("--host", default=os.environ.get("JAADU_HOST", "127.0.0.1"))
    p_serve.add_argument("--port", type=int, default=int(os.environ.get("JAADU_PORT", "8000")))
    args = parser.parse_args(argv)
    if args.cmd == "ingest":
        from jaadu.ingestion.pipeline import run_ingest

        obs = run_ingest()
        print(
            json.dumps(
                {
                    "n_observations": int(len(obs)),
                    "variables": sorted(obs["variable"].unique().tolist()) if not obs.empty else [],
                },
                indent=2,
            )
        )
    elif args.cmd == "investigate":
        from jaadu.investigate import investigate

        result = investigate(args.region, args.as_of, use_gemini=args.gemini or None)
        print(json.dumps(result["report"], indent=2, default=str))
    elif args.cmd == "evaluate":
        from jaadu.evaluation.benchmark import run_benchmark

        payload = run_benchmark()
        print(json.dumps(payload["summary"], indent=2))
    elif args.cmd == "precompute":
        from jaadu.core.config import load_benchmark
        from jaadu.investigate import investigate

        out = []
        for event in load_benchmark()["events"]:
            rec = investigate(event["region"], event["prediction_cutoff"], use_gemini=False)
            out.append(
                {
                    "event": event["id"],
                    "region": event["region"],
                    "as_of": event["prediction_cutoff"],
                    "alert": rec.get("detection", {}).get("multi_signal_alert"),
                    "leader": (rec.get("hypotheses") or [{}])[0].get("template_id"),
                }
            )
        print(json.dumps(out, indent=2))
    elif args.cmd == "robustness":
        from jaadu.anomaly.robustness import run_stress
        from jaadu.core.config import load_yaml
        from jaadu.core.config import CONFIG
        from jaadu.investigate import load_observations
        from jaadu.validation.checks import pivot_region

        spec = load_yaml(CONFIG / "experiments" / "robustness.yaml")
        obs = load_observations()
        payload = []
        for ev in spec["events"]:
            panel = pivot_region(obs, ev["region"], ev["as_of"])
            payload.append(
                {"region": ev["region"], "as_of": ev["as_of"], **run_stress(panel, ev["as_of"], spec)}
            )
        from jaadu.core.config import EXPERIMENTS

        outp = EXPERIMENTS / "results" / "robustness.json"
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(payload, indent=2, default=str))
        print(json.dumps(payload, indent=2, default=str))
    elif args.cmd == "leakage-audit":
        from jaadu.evaluation.leakage import run_leakage_audit
        from jaadu.investigate import load_observations

        obs = load_observations()
        print(json.dumps(run_leakage_audit(obs, args.as_of), indent=2, default=str))
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("jaadu.api.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
