#!/usr/bin/env bash
# Copy+validate portal build. No TeX engine. Does not enable GitHub Pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="${SITE_DIR:-"$ROOT/_site"}"
INDEX="$ROOT/paper/FIGURE-INDEX.json"
SCHEMA="$ROOT/tests/schemas/figure-index.schema.json"

python3 - "$INDEX" "$SCHEMA" "$ROOT/paper" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import validate

index_path = Path(sys.argv[1])
schema_path = Path(sys.argv[2])
paper = Path(sys.argv[3])
index = json.loads(index_path.read_text(encoding="utf-8"))
schema = json.loads(schema_path.read_text(encoding="utf-8"))
validate(instance=index, schema=schema)
pdfs = sorted(paper.rglob("*.pdf"))
if pdfs:
    raise SystemExit("refusing paper-tree PDFs: " + ", ".join(str(p) for p in pdfs))
print("FIGURE-INDEX.json valid")
PY

rm -rf "$SITE"
mkdir -p "$SITE/data"
cp -a "$ROOT/portal/." "$SITE/"
rm -f "$SITE/build.sh"
cp "$INDEX" "$SITE/data/FIGURE-INDEX.json"
cp "$INDEX" "$SITE/data/figures.json"

if [[ -d "$ROOT/paper/summaries" ]]; then
  mkdir -p "$SITE/data/summaries"
  cp -a "$ROOT/paper/summaries/." "$SITE/data/summaries/"
fi
if [[ -d "$ROOT/paper/previews" ]]; then
  mkdir -p "$SITE/data/previews"
  cp -a "$ROOT/paper/previews/." "$SITE/data/previews/"
fi

rm -rf "$SITE/experiments" "$SITE/.omc" "$SITE/.git"
if [[ -e "$SITE/main.pdf" || -e "$SITE/manuscript.pdf" ]]; then
  echo "refusing journal PDFs in _site/" >&2
  exit 1
fi
echo "built $SITE"
