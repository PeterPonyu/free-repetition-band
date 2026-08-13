# A 4-10 epoch free-repetition band — code, data, and field guide

Warehouse: [`https://github.com/PeterPonyu/free-repetition-band`](https://github.com/PeterPonyu/free-repetition-band).
Concept DOI: [10.5281/zenodo.21020378](https://doi.org/10.5281/zenodo.21020378).

Reproducibility archive for the free-repetition paper: experiment code, per-run result logs, pointer manuscript, and a geologic field-guide portal. Compiled journal PDFs are not included.

## Contents
- `experiments/<study>/` — runner / analysis code per sub-experiment.
- `experiments/results/` — per-run logs (JSON/JSONL) behind every reported number.
- `papers/E1/main.tex` — full canonical pointer manuscript (`\input{../figs/figpreamble.tex}`).
- `papers/figs/` — E1 generators, `figpreamble.tex`, and JSON summaries. Rebuild via `papers/figs/PIPELINE.md`.
- `papers/FIGURE-INDEX.json` — portal figure contract (papers/-relative paths).
- `portal/` — long-scroll field guide (Band / Onset / Capacity / Exposure / Scale / Reproduce).

## Reproducing
The committed per-run logs are the recorded outputs. To re-run a study from
scratch (GPU recommended): `python experiments/<study>/run_*.py`. Runs are seeded
(seed lists appear in result-log filenames). Dependencies: Python 3.11+, PyTorch,
numpy. All inputs are synthetic and fully specified in the code, except large
standard datasets (MNIST / WikiText) which are not bundled.

Figure rebuild: see `papers/figs/PIPELINE.md` and `papers/GENERATORS.md`. Compiled `papers/figs/tex/` and `papers/figs/vec/` are gitignored.

Local portal preview:

```bash
bash portal/build.sh
python3 -m http.server -d _site 8000
```

## Family/optimizer/capacity extensions (v1.5, 2026-07)
- `experiments/repeated_data/run_20260708_pcfg.py` + `experiments/results/repeated_data_pcfg/` (54 runs):
  PCFG corpus family sweep (R_free=20 at all three capacities).
- `experiments/repeated_data/run_20260708_muon_rfree.py` + `experiments/results/repeated_data_muon/` (36 runs):
  Muon optimizer-swap arm.
- `experiments/repeated_data/run_20260708_capacity_xl.py` + `experiments/results/repeated_data_capxl/` (44 runs):
  xl (29.9M) / xxl (57.1M) capacity extension to a ~23x span; `model.py` gains the xl/xxl presets.

## License
Code: MIT (`LICENSE`). Result logs and figures: CC BY 4.0. See `CITATION.cff`.
Zenodo `git archive` packs omit `portal/`, `_site/`, and `.github/`.
