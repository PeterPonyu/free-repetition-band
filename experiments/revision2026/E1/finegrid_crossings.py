"""Revision integration — verify fine-grid crossings (p1_e1a) and the med/low
12-seed boundary audit (p1_e1b) against the paper's excess-loss conventions.

Referee attacks answered:
  M2 (grid resolution): "the 4-10 band could be grid quantization" -> p1_e1a
     adds n in {6,8} rungs (3 fresh seeds each, seeds 20-22, 20M-token budget)
     to the five cells that previously lacked fine-grid coverage in Sec P4:
     med/high, large/med, med/low, small/low, small/med.
  M1 (seed count): "n=3 threshold verdicts" -> p1_e1b re-runs the med/low
     boundary rung (n=10, U=2M) on 12 fresh seeds (20-31).

Conventions (identical to rfree_two_convention.py):
  excess(n)   = median final_val_loss(n) - H_cell,
  H_cell      = median fresh n=1 final_val_loss of the cell, pooled archive
                (experiments/results/repeated_data{,_ultragoal_seed_audit,
                _ultragoal_large}); 20M budget, markov, adamw only.
  absolute criterion: eps_abs = 0.05 nats.
  relative criterion: eps_rel = phi * H_cell, phi = 0.05 / H_med/med.

Outputs: finegrid_crossings.json + finegrid_crossings.md
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

import numpy as np

ROOT = "/home/zeyufu/Desktop/dl-research/experiments"
ARCHIVE_DIRS = [
    os.path.join(ROOT, "results", "repeated_data"),
    os.path.join(ROOT, "results", "repeated_data_ultragoal_seed_audit"),
    os.path.join(ROOT, "results", "repeated_data_ultragoal_large"),
]
# the paper's existing Sec-P4 fine grid (med/med, large/high, small/high,
# large/low at n in {6,8,12,16}) lives in its own dir — pooled in so the
# 9-cell crossing table is complete
P4_DIR = os.path.join(ROOT, "results", "repeated_data_finegrid")
E1A = os.path.join(ROOT, "revision2026", "pilot-CE1", "results", "p1_e1a")
E1B = os.path.join(ROOT, "revision2026", "pilot-CE1", "results", "p1_e1b")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BUDGET = 20_000_000
ABS_EPS = 0.05
NEW_CELLS = [("med", "high"), ("large", "med"), ("med", "low"),
             ("small", "low"), ("small", "med")]
ALL_CELLS = [(c, e) for c in ("small", "med", "large")
             for e in ("low", "med", "high")]


def read_summary(path):
    last = None
    with open(path) as f:
        for line in f:
            if line.strip():
                last = line
    if last is None:
        return None
    try:
        return json.loads(last)["_summary"]
    except (KeyError, json.JSONDecodeError, TypeError):
        return None


def archive_rows(dirs):
    rows = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            if os.path.basename(path).startswith("probe_"):
                continue
            s = read_summary(path)
            if s is None:
                continue
            if s.get("total_budget") != BUDGET or s.get("generator") != "markov":
                continue
            if s.get("optimizer", "adamw") != "adamw":
                continue
            rows.append(s)
    return rows


def main():
    rows = archive_rows(ARCHIVE_DIRS)
    # per-cell floors + archived coarse excess (as in rfree_two_convention.py)
    by_cell = defaultdict(lambda: defaultdict(list))
    by_cell_can = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = (r["capacity"], r["entropy_level"])
        by_cell[key][r["n_epochs"]].append(r["final_val_loss"])
        if r.get("final_canary_gap") is not None:
            by_cell_can[key][r["n_epochs"]].append(r["final_canary_gap"])
    floors = {k: float(np.median(v[1])) for k, v in by_cell.items() if 1 in v}
    H_ref = floors[("med", "med")]
    phi = ABS_EPS / H_ref
    print(f"H_ref={H_ref:.4f}  phi={phi:.5f}")

    # existing Sec-P4 fine grid runs (own dir, not in the pooled archive)
    p4 = defaultdict(lambda: defaultdict(list))
    for r in archive_rows([P4_DIR]):
        p4[(r["capacity"], r["entropy_level"])][r["n_epochs"]].append(
            r["final_val_loss"])
    n_p4 = sum(len(v) for c in p4.values() for v in c.values())
    print(f"P4 fine-grid dir runs: {n_p4}")

    # --- e1a fine-grid runs ---
    e1a = defaultdict(lambda: defaultdict(list))     # cell -> n -> [val]
    e1a_can = defaultdict(lambda: defaultdict(list))  # cell -> n -> [gap]
    n_e1a = 0
    for path in sorted(glob.glob(os.path.join(E1A, "*.jsonl"))):
        s = read_summary(path)
        assert s is not None, path
        assert s["total_budget"] == BUDGET and s["generator"] == "markov"
        assert s.get("optimizer", "adamw") == "adamw"
        key = (s["capacity"], s["entropy_level"])
        e1a[key][s["n_epochs"]].append(s["final_val_loss"])
        e1a_can[key][s["n_epochs"]].append(s["final_canary_gap"])
        n_e1a += 1
    print(f"e1a runs: {n_e1a}")

    cells_out = {}
    for cap, ent in ALL_CELLS:
        floor = floors[(cap, ent)]
        eps_rel = phi * floor
        # pool every available run per rung: archive (coarse + any archived
        # fine rungs) + Sec-P4 fine-grid dir + new e1a fresh seeds
        pooled = defaultdict(list)
        for n, v in by_cell[(cap, ent)].items():
            pooled[n].extend(v)
        for n, v in p4[(cap, ent)].items():
            pooled[n].extend(v)
        for n, v in e1a[(cap, ent)].items():
            pooled[n].extend(v)
        curve = {n: float(np.median(v)) - floor for n, v in pooled.items()}
        seeds = {n: len(v) for n, v in pooled.items()}
        ns = sorted(curve)

        # new e1a rungs reported separately (fresh-seed-only medians, so the
        # small/low + small/med values double as an independent replication of
        # the archived ten-seed rungs)
        new = {}
        for n, vals in sorted(e1a[(cap, ent)].items()):
            med = float(np.median(vals)) - floor
            per_seed = sorted(round(v - floor, 4) for v in vals)
            can = float(np.median(e1a_can[(cap, ent)][n]))
            new[n] = {"median_excess": round(med, 4),
                      "per_seed_excess": per_seed,
                      "median_canary_gap": round(can, 4),
                      "n_seeds": len(vals)}

        def bracket(eps):
            over = [n for n in ns if n > 1 and curve[n] >= eps]
            if not over:
                return None, None
            first_over = min(over)
            under = [n for n in ns if n < first_over and curve[n] < eps]
            return (max(under) if under else None), first_over

        lo_a, hi_a = bracket(ABS_EPS)
        lo_r, hi_r = bracket(eps_rel)
        cells_out[f"{cap}/{ent}"] = {
            "H_floor": round(floor, 4),
            "eps_abs": ABS_EPS,
            "eps_rel": round(eps_rel, 4),
            "new_rungs": {str(n): d for n, d in new.items()},
            "pooled_curve": {str(n): round(curve[n], 4) for n in ns},
            "pooled_n_seeds": {str(n): seeds[n] for n in ns},
            "crossing_abs": [lo_a, hi_a],
            "crossing_rel": [lo_r, hi_r],
        }

    # --- e1b boundary seed audit: med/low n=10 ---
    floor_ml = floors[("med", "low")]
    e1b_seeds = {}
    for path in sorted(glob.glob(os.path.join(E1B, "*.jsonl"))):
        s = read_summary(path)
        assert s is not None, path
        assert (s["capacity"], s["entropy_level"]) == ("med", "low")
        assert s["n_epochs"] == 10 and s["total_budget"] == BUDGET
        e1b_seeds[s["seed"]] = round(s["final_val_loss"] - floor_ml, 4)
    exc = np.array(sorted(e1b_seeds.values()))
    e1b_out = {
        "cell": "med/low", "n_epochs": 10, "n_seeds": len(exc),
        "floor": round(floor_ml, 4),
        "per_seed_excess": {str(k): v for k, v in sorted(e1b_seeds.items())},
        "n_over_abs_threshold": int((exc >= ABS_EPS).sum()),
        "median_excess": round(float(np.median(exc)), 4),
        "min_excess": round(float(exc.min()), 4),
        "max_excess": round(float(exc.max()), 4),
        "archived_n3_median_excess": round(arch_val := float(
            np.median(by_cell[("med", "low")][10])) - floor_ml, 4),
    }

    result = {"phi": round(phi, 5), "H_ref": round(H_ref, 4),
              "n_e1a_runs": n_e1a, "cells": cells_out, "e1b": e1b_out}
    jp = os.path.join(OUT_DIR, "finegrid_crossings.json")
    with open(jp, "w") as f:
        json.dump(result, f, indent=1)
    print(f"wrote {jp}")

    lines = ["# Fine-grid crossings (all 9 cells) + med/low 12-seed audit (p1_e1b)",
             "",
             f"phi = {phi:.4f}; floors from pooled archive (same convention as"
             " rfree_two_convention.py). New rungs (p1_e1a) = 3 fresh seeds"
             " (20-22); crossings from the pooled per-rung medians"
             " (archive + Sec-P4 fine grid + new runs).",
             "",
             "| cell | eps_rel | excess(6) | excess(8) | crossing (abs)"
             " | crossing (rel) | new data |",
             "|---|---|---|---|---|---|---|"]
    fmt = lambda b: ((f"({b[0]}, {b[1]}]" if b[0] else f"<= {b[1]}")
                     if b[1] else "none")
    for cap, ent in ALL_CELLS:
        c = cells_out[f"{cap}/{ent}"]
        e6 = c["pooled_curve"].get("6")
        e8 = c["pooled_curve"].get("8")
        ca, cr = c["crossing_abs"], c["crossing_rel"]
        newflag = "e1a" if c["new_rungs"] else "-"
        lines.append(
            f"| {cap}/{ent} | {c['eps_rel']:.4f} | "
            f"{e6:.4f} | {e8:.4f} | {fmt(ca)} | {fmt(cr)} | {newflag} |")
    lines += ["",
              f"e1b med/low n=10, {e1b_out['n_seeds']} fresh seeds: "
              f"{e1b_out['n_over_abs_threshold']}/{e1b_out['n_seeds']} over "
              f"0.05 nats; median {e1b_out['median_excess']:+.4f} "
              f"(range {e1b_out['min_excess']:+.4f}..{e1b_out['max_excess']:+.4f}); "
              f"archived n=3 median {e1b_out['archived_n3_median_excess']:+.4f}.",
              ""]
    mp = os.path.join(OUT_DIR, "finegrid_crossings.md")
    with open(mp, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
