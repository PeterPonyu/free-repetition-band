# A 4-10 epoch free-repetition band — code & data

Reproducibility archive: **experiment code and per-run result logs only**.
Manuscript and write-up/derivation documents are intentionally **not** included.

## Contents
- `experiments/<study>/` — runner / analysis code per sub-experiment.
- `experiments/results/` — per-run logs (JSON/JSONL) behind every reported number.

## Reproducing
The committed per-run logs are the recorded outputs. To re-run a study from
scratch (GPU recommended): `python experiments/<study>/run_*.py`. Runs are seeded
(seed lists appear in result-log filenames). Dependencies: Python 3.11+, PyTorch,
numpy. All inputs are synthetic and fully specified in the code, except large
standard datasets (MNIST / WikiText) which are not bundled.

## Family/optimizer/capacity extensions (v1.5, 2026-07)
- `experiments/repeated_data/run_20260708_pcfg.py` + `experiments/results/repeated_data_pcfg/` (54 runs):
  PCFG corpus family sweep (R_free=20 at all three capacities).
- `experiments/repeated_data/run_20260708_muon_rfree.py` + `experiments/results/repeated_data_muon/` (36 runs):
  Muon optimizer-swap arm.
- `experiments/repeated_data/run_20260708_capacity_xl.py` + `experiments/results/repeated_data_capxl/` (44 runs):
  xl (29.9M) / xxl (57.1M) capacity extension to a ~23x span; `model.py` gains the xl/xxl presets.

## License
Code: MIT (`LICENSE`). Result logs: CC BY 4.0. See `CITATION.cff`.
