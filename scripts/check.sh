#!/usr/bin/env bash
set -euo pipefail

python -m ruff check .
python -m pytest
python -m pytest -m integration
pip-audit
npm --prefix frontend audit --audit-level=high
npm --prefix frontend run lint
npm --prefix frontend run typecheck