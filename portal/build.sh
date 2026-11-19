#!/usr/bin/env bash
# Validate FIGURE-INDEX, then Next.js static export to out/. No LaTeX.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import json
import re
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

# Door copy: epoch-stratum beds only. No ids, paths, captions, or venue names.
LEAK = re.compile(
    r"R_free|WikiText|FIGURE-INDEX|PIPELINE|venue|Figure\d|E1_|papers/",
    re.I,
)
CHAPTERS = [
    {
        "chapter": "band",
        "title": "Band",
        "object": "Opening bed of the epoch field.",
        "artifact": "E1_scale_band",
    },
    {
        "chapter": "onset",
        "title": "Onset",
        "object": "Onset coincidence of the free unit.",
        "artifact": "E1_repeat",
    },
    {
        "chapter": "capacity",
        "title": "Capacity",
        "object": "Capacity–entropy test of the free-repetition band.",
        "artifact": "E1_capxl",
    },
    {
        "chapter": "exposure",
        "title": "Exposure",
        "object": "Exposure control of the free-repetition band.",
        "artifact": "E1_exposure_control",
    },
    {
        "chapter": "scale",
        "title": "Scale",
        "object": "Scale invariance of the free-repetition band.",
        "artifact": "E1_scale",
    },
]
by_id = {fig["id"]: fig for fig in index["figures"]}
beds = []
for spec in CHAPTERS:
    fig = by_id[spec["artifact"]]
    summary_rel = fig.get("summary")
    asks = []
    if summary_rel:
        summary_path = root / "papers" / summary_rel
        if not summary_path.is_file():
            raise SystemExit(f"missing summary for {spec['chapter']}: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        asks = [panel["question"] for panel in summary.get("panels") or [] if panel.get("question")]
    layers = [layer for layer in (fig.get("caption_panels") or []) if layer]
    blob = " ".join(asks + layers + [spec["object"]])
    if LEAK.search(blob):
        raise SystemExit(f"refuse: leak in {spec['chapter']} door copy")
    beds.append(
        {
            "chapter": spec["chapter"],
            "title": spec["title"],
            "object": spec["object"],
            "layers": layers,
            "asks": asks,
        }
    )
door = {
    "github": index["github"],
    "zenodo_concept_doi": index["zenodo_concept_doi"],
    "beds": beds,
}
public = root / "portal/public/data"
if public.exists():
    shutil.rmtree(public)
public.mkdir(parents=True, exist_ok=True)
payload = json.dumps(door, indent=2) + "\n"
(public / "figures.json").write_text(payload, encoding="utf-8")
print("INDEX valid; public data is stratum beds; no papers/**/*.pdf")
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
