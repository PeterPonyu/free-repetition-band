"""S-E1 — real-text repetition band at 30M/57M params (BOX-4, 48 runs).

Full recomputation from raw jsonls (INCREMENTAL.json treated as cross-check
only). Data: experiments/revision2026/stier-E1/*.jsonl — byte-level LMs on
FineWeb-Edu ("fineweb") and github-code-clean ("code"), capacities
xl (30.0M params, B=100M bytes) and xxl (57.2M, B=200M), epoch grids
fineweb {1,2,4,6,8,10,16} / code {1,2,4,10,16}, seeds {50,51}, U = B/n.

Conventions (the paper's):
- excess(n) = final fresh-val loss at n epochs minus the same cell+seed's
  n=1 (fresh-data) control; cell median over seeds.
- R_free(abs) = max grid n with median excess < 0.05 nats;
  decay onset = first grid n with median excess >= 0.05.
- R_free(rel) = same with eps_cell = phi * H_cell, phi = 0.0283
  (rfree_two_convention.py calibration), H_cell = cell-median n=1 val loss.
- canary memorization signal on real bytes = GROWTH of the fresh-minus-canary
  gap above its n=1 level (sec:scale convention); mem onset = first grid n
  with median growth > 0.10 nats; sensitivity thresholds 0.05 / 0.20.

Outputs: stier_realtext_band.json + .md next to this script.
"""
from __future__ import annotations
from pathlib import Path

import glob
import json
import os
import re

import numpy as np

DATA = str(Path(__file__).resolve().parents[3] / 'experiments' / 'revision2026' / 'stier-E1')
OUT = os.path.dirname(os.path.abspath(__file__))
ABS_EPS = 0.05
PHI = 0.0283
MEM_THRESHOLDS = [0.05, 0.10, 0.20]
GRIDS = {"fineweb": [1, 2, 4, 6, 8, 10, 16], "code": [1, 2, 4, 10, 16]}
SEEDS = [50, 51]
CAPS = ["xl", "xxl"]


def load_runs():
    runs = {}
    pat = re.compile(r"^(fineweb|code)_(xl|xxl)_E(\d+)_s(\d+)\.jsonl$")
    for path in sorted(glob.glob(os.path.join(DATA, "*.jsonl"))):
        m = pat.match(os.path.basename(path))
        if not m:
            continue
        corpus, cap, n, seed = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        meta, summary, epochs = None, None, []
        with open(path) as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if "_meta" in rec:
                    meta = rec["_meta"]
                elif "_summary" in rec:
                    summary = rec["_summary"]
                else:
                    epochs.append(rec)
        assert meta is not None and summary is not None, path
        # completeness gate (LESSONS 6c: never integrate a partial run)
        assert len(epochs) == n, f"{path}: {len(epochs)} epoch lines != n={n}"
        assert meta["n_epochs"] == n and meta["seed"] == seed
        assert meta["corpus"] == corpus and meta["capacity"] == cap
        assert abs(summary["final_val_loss"] - epochs[-1]["val_loss"]) < 1e-9
        runs[(corpus, cap, n, seed)] = {
            "val": epochs[-1]["val_loss"],
            "gap": epochs[-1]["canary_gap"],
            "n_params": meta["n_params"],
            "budget": meta["total_budget"],
            "unique": meta["unique_tokens"],
        }
    return runs


def onset(grid, series, eps):
    """First grid n with value >= eps; None if never."""
    for n in grid:
        if series[n] >= eps:
            return n
    return None


def rfree(grid, series, eps):
    """Max grid n with value < eps, scanning up to the first crossing."""
    best = None
    for n in grid:
        if series[n] < eps:
            best = n
        else:
            break
    return best


def main():
    runs = load_runs()
    assert len(runs) == 48, f"expected 48 runs, got {len(runs)}"

    cells = {}
    for corpus in GRIDS:
        for cap in CAPS:
            grid = GRIDS[corpus]
            # per-seed floors and series
            floors = {s: runs[(corpus, cap, 1, s)]["val"] for s in SEEDS}
            gap1 = {s: runs[(corpus, cap, 1, s)]["gap"] for s in SEEDS}
            excess = {}   # n -> median over seeds
            growth = {}   # n -> median gap growth over n=1 level
            rawgap = {}
            per_seed = {s: {} for s in SEEDS}
            for n in grid:
                exc = [runs[(corpus, cap, n, s)]["val"] - floors[s] for s in SEEDS]
                gro = [runs[(corpus, cap, n, s)]["gap"] - gap1[s] for s in SEEDS]
                raw = [runs[(corpus, cap, n, s)]["gap"] for s in SEEDS]
                excess[n] = float(np.median(exc))
                growth[n] = float(np.median(gro))
                rawgap[n] = float(np.median(raw))
                for i, s in enumerate(SEEDS):
                    per_seed[s][n] = {"excess": round(exc[i], 4), "growth": round(gro[i], 4)}
            H = float(np.median(list(floors.values())))
            eps_rel = PHI * H
            decay_abs = onset(grid, excess, ABS_EPS)
            decay_rel = onset(grid, excess, eps_rel)
            mem = {f"{t:.2f}": onset(grid, growth, t) for t in MEM_THRESHOLDS}
            # per-seed R_free under both conventions
            rf_seed_abs = {s: rfree(grid, {n: per_seed[s][n]["excess"] for n in grid}, ABS_EPS)
                           for s in SEEDS}
            rf_seed_rel = {s: rfree(grid, {n: per_seed[s][n]["excess"] for n in grid}, eps_rel)
                           for s in SEEDS}
            m10 = mem["0.10"]
            order = ("n/a" if m10 is None or decay_abs is None else
                     "leads" if m10 < decay_abs else
                     "coincides" if m10 == decay_abs else "lags")
            cells[f"{corpus}/{cap}"] = {
                "n_params": runs[(corpus, cap, 1, SEEDS[0])]["n_params"],
                "budget_bytes": runs[(corpus, cap, 1, SEEDS[0])]["budget"],
                "H_floor": round(H, 4),
                "eps_rel": round(eps_rel, 4),
                "excess_median": {n: round(v, 4) for n, v in excess.items()},
                "gap_growth_median": {n: round(v, 4) for n, v in growth.items()},
                "gap_raw_median": {n: round(v, 4) for n, v in rawgap.items()},
                "per_seed": per_seed,
                "R_free_abs": rfree(grid, excess, ABS_EPS),
                "R_free_rel": rfree(grid, excess, eps_rel),
                "R_free_abs_per_seed": rf_seed_abs,
                "R_free_rel_per_seed": rf_seed_rel,
                "decay_onset_abs": decay_abs,
                "decay_onset_rel": decay_rel,
                "mem_onset_growth": mem,
                "ordering_at_0.10": order,
            }

    # cross-check against the box's INCREMENTAL.json (per-seed, raw-gap conv.)
    with open(os.path.join(DATA, "INCREMENTAL.json")) as f:
        incr = json.load(f)
    mismatches = []
    sweeps = incr.get("sweeps", incr)
    if isinstance(sweeps, dict):
        for key, rec in sweeps.items():
            if not isinstance(rec, dict) or "excess" not in rec:
                continue
            m = re.match(r"(fineweb|code)/(xl|xxl)/(\d+)", key)
            if not m:
                continue
            corpus, cap, seed = m.group(1), m.group(2), int(m.group(3))
            for n_str, v in rec["excess"].items():
                n = int(n_str)
                mine = runs[(corpus, cap, n, seed)]["val"] - runs[(corpus, cap, 1, seed)]["val"]
                if abs(mine - v) > 5e-4:
                    mismatches.append((key, n, v, round(mine, 4)))

    out = {
        "n_runs": 48,
        "phi": PHI,
        "abs_eps": ABS_EPS,
        "cells": cells,
        "incremental_crosscheck_mismatches": mismatches,
    }
    with open(os.path.join(OUT, "stier_realtext_band.json"), "w") as f:
        json.dump(out, f, indent=1)

    lines = ["# S-E1 real-text band — recomputed verdicts (48/48 runs)\n"]
    lines.append("| cell | params | H floor | eps_rel | R_abs | R_rel | decay@abs | "
                 "mem@0.05/0.10/0.20 (growth) | ordering@0.10 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for key, c in cells.items():
        mem = c["mem_onset_growth"]
        lines.append(
            f"| {key} | {c['n_params']/1e6:.1f}M | {c['H_floor']:.3f} | {c['eps_rel']:.3f} "
            f"| {c['R_free_abs']} (seeds {c['R_free_abs_per_seed'][50]}/{c['R_free_abs_per_seed'][51]}) "
            f"| {c['R_free_rel']} (seeds {c['R_free_rel_per_seed'][50]}/{c['R_free_rel_per_seed'][51]}) "
            f"| {c['decay_onset_abs']} | {mem['0.05']}/{mem['0.10']}/{mem['0.20']} "
            f"| {c['ordering_at_0.10']} |")
    lines.append("\nMedian excess per epoch:")
    for key, c in cells.items():
        lines.append(f"- {key}: excess={c['excess_median']} gap_growth={c['gap_growth_median']}")
    if mismatches:
        lines.append(f"\nINCREMENTAL cross-check MISMATCHES: {mismatches}")
    else:
        lines.append("\nINCREMENTAL cross-check: all per-seed excess values agree to <5e-4.")
    with open(os.path.join(OUT, "stier_realtext_band.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
