"""Revision analysis — canary-threshold sensitivity of the memorization-onset
ordering (referee item, both rounds).

Question: the paper declares eps_can = 0.10 nats for memorization onset
(smallest n at which the median canary gap exceeds eps_can). Does the
leads-or-coincides-never-lags ordering (fine grid, 9/9 cells) and the
coarse-grid coincidence tally (8/9 at eps_can = 0.10) survive halving or
doubling the threshold, eps_can in {0.05, 0.10, 0.20}?

Data + conventions identical to finegrid_crossings.py:
  pooled archive (results/repeated_data{,_ultragoal_seed_audit,_ultragoal_large})
  + Sec-P4 fine-grid dir (results/repeated_data_finegrid)
  + revision fine grid (revision2026/pilot-CE1/results/p1_e1a);
  20M budget, markov, adamw only.
  excess(n)  = median final_val_loss(n) - H_cell (H_cell = pooled fresh n=1
               median); decay onset = smallest n > 1 with excess >= 0.05.
  gap(n)     = median final_canary_gap(n); mem onset = smallest n with
               gap >= eps_can (paper Methods convention).
  Fine ordering: mem onset <= decay onset -> leads-or-coincides (never lags),
  computed on the pooled rung set (half-octave where covered).
  Coarse tally: same onsets restricted to n in {1,2,4,10,20,40} rungs,
  "coincide" = equal onset rung (the paper's Table `Coincide' column).

Outputs: canary_threshold_sensitivity.json + .md
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
P4_DIR = os.path.join(ROOT, "results", "repeated_data_finegrid")
E1A = os.path.join(ROOT, "revision2026", "pilot-CE1", "results", "p1_e1a")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BUDGET = 20_000_000
DECAY_EPS = 0.05
CAN_EPS = [0.05, 0.10, 0.20]
COARSE = {1, 2, 4, 10, 20, 40}
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


def rows_from(dirs):
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


def onset(curve, ns, eps, min_n=None):
    over = [n for n in ns if (min_n is None or n >= min_n)
            and curve[n] >= eps]
    return min(over) if over else None


def main():
    val = defaultdict(lambda: defaultdict(list))
    gap = defaultdict(lambda: defaultdict(list))
    n_rows = 0
    for r in rows_from(ARCHIVE_DIRS + [P4_DIR, E1A]):
        key = (r["capacity"], r["entropy_level"])
        val[key][r["n_epochs"]].append(r["final_val_loss"])
        if r.get("final_canary_gap") is not None:
            gap[key][r["n_epochs"]].append(r["final_canary_gap"])
        n_rows += 1
    print(f"pooled rows: {n_rows}")

    floors = {k: float(np.median(v[1])) for k, v in val.items() if 1 in v}

    cells = {}
    tallies = {}  # eps -> {"fine_never_lags": int, "coarse_coincide": int, ...}
    for eps in CAN_EPS:
        tallies[f"{eps:.2f}"] = {"fine_leads_or_coincides": 0, "fine_lags": 0,
                                 "coarse_coincide": 0,
                                 "mem_onset_at_n1": 0}
    for cap, ent in ALL_CELLS:
        floor = floors[(cap, ent)]
        exc = {n: float(np.median(v)) - floor
               for n, v in val[(cap, ent)].items()}
        g = {n: float(np.median(v)) for n, v in gap[(cap, ent)].items()}
        ns_all = sorted(set(exc) & set(g))
        ns_coarse = sorted(set(ns_all) & COARSE)

        d_fine = onset(exc, ns_all, DECAY_EPS, min_n=2)
        d_coarse = onset(exc, ns_coarse, DECAY_EPS, min_n=2)
        out = {"H_floor": round(floor, 4),
               "rungs": ns_all,
               "gap_curve": {str(n): round(g[n], 4) for n in ns_all},
               "excess_curve": {str(n): round(exc[n], 4) for n in ns_all},
               "decay_onset_fine": d_fine, "decay_onset_coarse": d_coarse,
               "mem_onset": {}}
        for eps in CAN_EPS:
            m_fine = onset(g, ns_all, eps)
            m_coarse = onset(g, ns_coarse, eps)
            key = f"{eps:.2f}"
            rel = ("lags" if (m_fine is None or m_fine > d_fine)
                   else ("coincides" if m_fine == d_fine else "leads"))
            out["mem_onset"][key] = {
                "fine": m_fine, "coarse": m_coarse,
                "ordering_fine": rel,
                "coincide_coarse": bool(m_coarse == d_coarse
                                        and m_coarse is not None),
                "gap_at_n1": round(g.get(1, float("nan")), 4)}
            t = tallies[key]
            if rel in ("leads", "coincides"):
                t["fine_leads_or_coincides"] += 1
            else:
                t["fine_lags"] += 1
            if m_coarse == d_coarse and m_coarse is not None:
                t["coarse_coincide"] += 1
            if m_fine == 1:
                t["mem_onset_at_n1"] += 1
        cells[f"{cap}/{ent}"] = out

    result = {"decay_eps": DECAY_EPS, "canary_eps": CAN_EPS,
              "n_pooled_rows": n_rows, "tallies": tallies, "cells": cells}
    jp = os.path.join(OUT_DIR, "canary_threshold_sensitivity.json")
    with open(jp, "w") as f:
        json.dump(result, f, indent=1)
    print(f"wrote {jp}")

    lines = ["# Canary-threshold sensitivity of the memorization-onset ordering",
             "",
             "Decay onset fixed at the declared 0.05-nat excess criterion;"
             " memorization onset recomputed at eps_can in {0.05, 0.10, 0.20}"
             " nats. Fine = pooled rung set (half-octave where covered);"
             " coarse = n in {1,2,4,10,20,40} (the paper's Table 4 convention).",
             "",
             "| eps_can | fine leads-or-coincides | fine lags |"
             " coarse coincide | mem onset at n=1 |",
             "|---|---|---|---|---|"]
    for eps in CAN_EPS:
        t = tallies[f"{eps:.2f}"]
        lines.append(f"| {eps:.2f} | {t['fine_leads_or_coincides']}/9 |"
                     f" {t['fine_lags']}/9 | {t['coarse_coincide']}/9 |"
                     f" {t['mem_onset_at_n1']} |")
    lines += ["", "Per-cell onsets (fine): decay | mem@0.05 / mem@0.10 / mem@0.20",
              ""]
    for cap, ent in ALL_CELLS:
        c = cells[f"{cap}/{ent}"]
        m = c["mem_onset"]
        lines.append(
            f"- {cap}/{ent}: decay {c['decay_onset_fine']} | "
            f"{m['0.05']['fine']} ({m['0.05']['ordering_fine']}) / "
            f"{m['0.10']['fine']} ({m['0.10']['ordering_fine']}) / "
            f"{m['0.20']['fine']} ({m['0.20']['ordering_fine']}); "
            f"gap(n=1)={m['0.10']['gap_at_n1']}")
    mp = os.path.join(OUT_DIR, "canary_threshold_sensitivity.md")
    with open(mp, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
