#!/usr/bin/env bash
# Validate FIGURE-INDEX then copy portal/ → _site/. No LaTeX.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

import jsonschema

root = Path(".")
schema = json.loads((root / "papers/FIGURE-INDEX.schema.json").read_text(encoding="utf-8"))
index = json.loads((root / "papers/FIGURE-INDEX.json").read_text(encoding="utf-8"))
jsonschema.validate(instance=index, schema=schema)

tracked = subprocess.run(
    ["git", "ls-files", "papers/**/*.pdf"],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()
if tracked:
    raise SystemExit(f"refuse: committed PDFs under papers/: {tracked}")
print("INDEX valid; no papers/**/*.pdf")
PY

rm -rf _site
mkdir -p _site/data/figs
cp -a portal/. _site/
cp papers/FIGURE-INDEX.json _site/data/figures.json
cp papers/FIGURE-INDEX.json _site/data/FIGURE-INDEX.json
if [[ -d papers/figs/summaries ]]; then
  mkdir -p _site/data/figs/summaries
  cp -a papers/figs/summaries/. _site/data/figs/summaries/
fi
if [[ -d papers/figs/previews ]]; then
  mkdir -p _site/data/figs/previews
  cp -a papers/figs/previews/. _site/data/figs/previews/
fi
if [[ -e _site/experiments || -e _site/.omc ]]; then
  echo "I4: experiments or .omc leaked into _site" >&2
  exit 1
fi
if find _site -iname '*.pdf' | grep -q .; then
  echo "U5: PDFs leaked into _site" >&2
  exit 1
fi
echo "built _site/ from portal/ + FIGURE-INDEX"
