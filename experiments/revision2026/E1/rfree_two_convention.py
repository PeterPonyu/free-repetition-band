"""E1-T0-1 — two-convention R_free reanalysis (absolute vs relative threshold).

Referee attack (M4): the 0.05-nat absolute excess criterion is a larger RELATIVE
tolerance for low-entropy cells (0.05/0.37 = 13.5%) than for high-entropy cells
(0.05/4.10 = 1.2%), so the "4-10 band" could be a convention artifact.

Reanalysis: recompute R_free across the 9-cell (capacity x entropy) core grid
under a relative excess criterion
    eps_cell = phi * H_cell,    phi = 0.05 / H_ref  (reference cell med/med),
where H_cell is the paper's per-cell entropy floor operationalization (median
fresh n=1 validation loss of that cell). phi is calibrated so the reference
cell's verdict matches the absolute 0.05-nat verdict by construction.

Data: pooled experiments/results/repeated_data{,_ultragoal_seed_audit,
_ultragoal_large}/ jsonl summaries (same loader convention as
repeated_data/analyze_repeat.py — median over all available seeds per point).

Output: rfree_two_convention.json + rfree_two_convention.md (comparison table).
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

import numpy as np

ROOT = "/home/zeyufu/Desktop/dl-research/experiments/results"
DIRS = [
    os.path.join(ROOT, "repeated_data"),
    os.path.join(ROOT, "repeated_data_ultragoal_seed_audit"),
    os.path.join(ROOT, "repeated_data_ultragoal_large"),
]
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BUDGET = 20_000_000
ABS_EPS = 0.05          # nats; the paper's declared absolute threshold
REF_CELL = ("med", "med")
CAPS = ["small", "med", "large"]
ENTS = ["low", "med", "high"]
GRID = [1, 2, 4, 10, 20, 40]


def load_rows():
    rows = []
    for d in DIRS:
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            if os.path.basename(path).startswith("probe_"):
                continue
            last = None
            with open(path) as f:
                for line in f:
                    if line.strip():
                        last = line
            if last is None:
                continue
            try:
                rows.append(json.loads(last)["_summary"])
            except (KeyError, json.JSONDecodeError, TypeError):
                continue
    return rows


def cell_curves(rows):
    """cell -> n -> dict(median excess-ready val, canary, n_seeds)."""
    by_cell = defaultdict(lambda: defaultdict(lambda: {"val": [], "can": []}))
    for r in rows:
        if r.get("total_budget") != BUDGET or r.get("generator") != "markov":
            continue
        if r.get("optimizer", "adamw") != "adamw":
            continue
        key = (r["capacity"], r["entropy_level"])
        by_cell[key][r["n_epochs"]]["val"].append(r["final_val_loss"])
        by_cell[key][r["n_epochs"]]["can"].append(r.get("final_canary_gap"))
    out = {}
    for key, by_n in by_cell.items():
        out[key] = {
            n: {
                "val": float(np.median(v["val"])),
                "canary": (float(np.median([c for c in v["can"] if c is not None]))
                           if any(c is not None for c in v["can"]) else None),
                "n_seeds": len(v["val"]),
            }
            for n, v in sorted(by_n.items())
        }
    return out


def rfree(excess: dict, eps: float):
    ns = sorted(excess)
    free = [n for n in ns if excess[n] < eps]
    r = max(free) if free else 1
    onset = next((n for n in ns if n > 1 and excess[n] >= eps), None)
    return r, onset


def main():
    rows = load_rows()
    curves = cell_curves(rows)
    print(f"loaded {len(rows)} run summaries; {len(curves)} cells")

    # per-cell floor H = median fresh (n=1) val loss (paper's operationalization)
    floors = {}
    for cap in CAPS:
        for ent in ENTS:
            cur = curves[(cap, ent)]
            floors[(cap, ent)] = cur[1]["val"]

    H_ref = floors[REF_CELL]
    phi = ABS_EPS / H_ref
    print(f"reference cell {REF_CELL}: H_ref={H_ref:.4f} nats -> phi={phi:.4f}")

    cells = {}
    for cap in CAPS:
        for ent in ENTS:
            cur = curves[(cap, ent)]
            fresh = cur[1]["val"]
            excess_all = {n: cur[n]["val"] - fresh for n in cur}
            # PRIMARY comparison on the paper's coarse epoch grid only
            # (fine-grid rungs n in {6,8,12,16} exist for a subset of cells;
            # mixing them in would make the per-cell grids non-uniform).
            excess = {n: e for n, e in excess_all.items() if n in GRID}
            eps_rel = phi * floors[(cap, ent)]
            r_abs, on_abs = rfree(excess, ABS_EPS)
            r_rel, on_rel = rfree(excess, eps_rel)
            r_abs_f, on_abs_f = rfree(excess_all, ABS_EPS)
            r_rel_f, on_rel_f = rfree(excess_all, eps_rel)
            cells[f"{cap}/{ent}"] = {
                "H_floor_nats": round(fresh, 4),
                "eps_abs": ABS_EPS,
                "eps_rel": round(eps_rel, 4),
                "excess": {str(n): round(excess_all[n], 4)
                           for n in sorted(excess_all)},
                "n_seeds": {str(n): cur[n]["n_seeds"] for n in sorted(cur)},
                "R_free_abs": r_abs, "decay_onset_abs": on_abs,
                "R_free_rel": r_rel, "decay_onset_rel": on_rel,
                "all_rungs": {"R_free_abs": r_abs_f, "decay_onset_abs": on_abs_f,
                              "R_free_rel": r_rel_f, "decay_onset_rel": on_rel_f},
                "verdict_changed": r_abs != r_rel,
            }

    band_abs = sorted({c["R_free_abs"] for c in cells.values()})
    band_rel = sorted({c["R_free_rel"] for c in cells.values()})
    changed = [k for k, c in cells.items() if c["verdict_changed"]]

    result = {
        "phi": round(phi, 5),
        "H_ref": round(H_ref, 4),
        "reference_cell": "med/med",
        "band_absolute": band_abs,
        "band_relative": band_rel,
        "cells_changed": changed,
        "cells": cells,
    }
    jp = os.path.join(OUT_DIR, "rfree_two_convention.json")
    with open(jp, "w") as f:
        json.dump(result, f, indent=1)
    print(f"wrote {jp}")

    # markdown comparison table
    lines = [
        "# E1-T0-1 two-convention R_free comparison",
        "",
        f"phi = {phi:.4f} (= 0.05 / H_ref, H_ref = med/med floor {H_ref:.3f} nats)",
        "",
        "| cell | H floor (nats) | eps_abs | eps_rel | R_free (abs) | R_free (rel) "
        "| onset (abs) | onset (rel) | changed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cap in CAPS:
        for ent in ENTS:
            c = cells[f"{cap}/{ent}"]
            lines.append(
                f"| {cap}/{ent} | {c['H_floor_nats']:.3f} | 0.05 | "
                f"{c['eps_rel']:.4f} | {c['R_free_abs']} | {c['R_free_rel']} | "
                f"{c['decay_onset_abs']} | {c['decay_onset_rel']} | "
                f"{'YES' if c['verdict_changed'] else ''} |")
    lines += ["", f"Band absolute: {band_abs}   Band relative: {band_rel}",
              f"Cells changed: {changed or 'none'}", ""]
    mp = os.path.join(OUT_DIR, "rfree_two_convention.md")
    with open(mp, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {mp}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
