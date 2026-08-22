#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -e .
python -m jaadu ingest
python -m jaadu evaluate
python -m pytest -q
echo "Then: python -m jaadu serve"
