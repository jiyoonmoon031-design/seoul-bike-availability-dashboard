#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root"

pandoc \
  reports/final/presentation.md \
  --resource-path=. \
  --slide-level=1 \
  --output reports/final/seoul-bike-final-presentation.pptx

echo "Created reports/final/seoul-bike-final-presentation.pptx"

