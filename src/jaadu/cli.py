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
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("jaadu.api.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
