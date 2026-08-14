#!/usr/bin/env bash
# Validate FIGURE-INDEX, then Next.js static export to out/. No LaTeX.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import json
import shutil
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

# Door copy: ids + summary filenames only. No captions, venue PDFs, or findings.
door = {
    "github": index["github"],
    "zenodo_concept_doi": index["zenodo_concept_doi"],
    "figures": [
        {"id": fig["id"], "summary": fig.get("summary")}
        for fig in index["figures"]
    ],
}
public = root / "portal/public/data"
if public.exists():
    shutil.rmtree(public)
public.mkdir(parents=True, exist_ok=True)
payload = json.dumps(door, indent=2) + "\n"
(public / "figures.json").write_text(payload, encoding="utf-8")
print("INDEX valid; public data is pointer-only; no papers/**/*.pdf")
PY

(
  cd portal
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
  npm run build
)

rm -rf out _site
cp -a portal/out/. out/
cp -a portal/out/. _site/

if [[ -e out/experiments || -e out/.omc ]]; then
  echo "I4: experiments or .omc leaked into out/" >&2
  exit 1
fi
if find out -iname '*.pdf' | grep -q .; then
  echo "U5: PDFs leaked into out/" >&2
  exit 1
fi
test -f out/index.html
test -d out/onset
test -f out/data/figures.json
if [[ -d out/data/figs ]]; then
  echo "U-leak: warehouse summaries/previews copied into out/data/figs" >&2
  exit 1
fi
echo "exported out/ from Next.js (basePath /free-repetition-band)"
