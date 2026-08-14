# Free-repetition band — epoch stratum field

**Live door:** https://peterponyu.github.io/free-repetition-band/

The free-repetition band is an epoch stratum: a free unit between the unique-data floor and the overburden of diminishing returns. The door walks Band, Onset, Capacity, Exposure, and Scale, then rebuild from committed runners and per-run logs.

Clone: https://github.com/PeterPonyu/free-repetition-band  
Concept DOI: [10.5281/zenodo.21020378](https://doi.org/10.5281/zenodo.21020378)

## Contents
- `experiments/<study>/` — runner / analysis code per sub-experiment.
- `experiments/results/` — per-run logs (JSON/JSONL) behind every recorded number.
- `portal/` — long-scroll field guide (Band / Onset / Capacity / Exposure / Scale / Reproduce-as-rebuild).

## Reproducing
The committed per-run logs are the recorded outputs. To re-run a study from
scratch (GPU recommended): `python experiments/<study>/run_*.py`. Runs are seeded
(seed lists appear in result-log filenames). Dependencies: Python 3.11+, PyTorch,
numpy. Inputs are specified in the runners; large standard corpora are not bundled.

Local door preview (Next.js static export, basePath `/free-repetition-band`):

```bash
bash portal/build.sh
mkdir -p /tmp/frb-pages/free-repetition-band
cp -a out/. /tmp/frb-pages/free-repetition-band/
python3 -m http.server -d /tmp/frb-pages 8000
# http://127.0.0.1:8000/free-repetition-band/
```

## Family, optimizer, and capacity extensions
- PCFG corpus-family sweep (`experiments/repeated_data/run_20260708_pcfg.py`).
- Optimizer-swap arm (`experiments/repeated_data/run_20260708_muon_rfree.py`).
- Width extension across a wide capacity span (`experiments/repeated_data/run_20260708_capacity_xl.py`).

## License
Code: MIT (`LICENSE`). Result logs and figures: CC BY 4.0. See `CITATION.cff`.
Zenodo `git archive` packs omit `portal/`, `_site/`, and `.github/`.
