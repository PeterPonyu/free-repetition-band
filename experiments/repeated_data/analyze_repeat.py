"""Direction 013 analysis — repetition-value decay constant R*_D on controlled data.

At fixed token budget B=20M, unique-token U is swept so n_epochs = B/U ∈
{1,2,4,10,20,40}; val_loss(n) rises as repetition increases. Muennighoff's
"R*_D ≈ 4 epochs free" says repetition up to ~4 epochs is nearly as valuable as
fresh data. We test (P1) whether that threshold reproduces at ~1000× smaller
scale, (P2 headline) whether it shifts with the capacity/entropy ratio across
3 capacities × 3 entropy levels, and (P3) whether the decay onset couples to a
measurable memorization onset (the copied-canary gap).

Robust operationalization (avoids misquoting Muennighoff's exact closed form):
  excess(n)   = val_loss(n) − val_loss(n=1, fresh)            [nats]
  R_free      = largest n with median excess < FREE_EPS (the "free epochs")
  decay_onset = smallest n with median excess ≥ FREE_EPS
  mem_onset   = smallest n with median canary_gap ≥ CANARY_EPS
P3 = decay_onset vs mem_onset coincidence; P2 = R_free across the 9 cells.
Writes results/figures-013/: repeat_verdicts.json, fig_repeat.png.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, "/home/zeyufu/Desktop/dl-research/experiments")
import figstyle
figstyle.apply()

# colourblind-safe colours for the 6 corpus cells (Okabe-Ito), each with a
# distinct marker + linestyle so the cells separate even in greyscale.
_CB = figstyle.CB
CELL_STYLE = {
    "small/low":  dict(color=_CB["blue"],       marker="o", ls="-"),
    "small/med":  dict(color=_CB["orange"],     marker="s", ls="--"),
    "small/high": dict(color=_CB["green"],      marker="^", ls="-."),
    "med/low":    dict(color=_CB["vermillion"], marker="D", ls=":"),
    "med/med":    dict(color=_CB["purple"],     marker="v", ls="-"),
    "med/high":   dict(color=_CB["black"],      marker="P", ls="--"),
}

_THIS = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(_THIS, "..", "..", "experiments", "results", "repeated_data")
RES_EXTRA = os.path.join(_THIS, "..", "..", "experiments", "results",
                         "repeated_data_ultragoal_seed_audit")
# Large-capacity sweep that completes the high-capacity row to full epoch-grid
# coverage (large/{low,med,high} at n in {1,2,4,10,20,40}).
RES_LARGE = os.path.join(_THIS, "..", "..", "experiments", "results",
                         "repeated_data_ultragoal_large")
FIG = os.path.join(_THIS, "..", "..", "experiments", "results", "figures-013")

BUDGET = 20_000_000
FREE_EPS = 0.05      # nats; "nearly free" excess threshold
CANARY_EPS = 0.10    # canary-gap memorization threshold
CAPS = ["small", "med", "large"]
ENTS = ["low", "med", "high"]


def load():
    out = []
    paths = sorted(glob.glob(os.path.join(RES, "*.jsonl")))
    paths += sorted(glob.glob(os.path.join(RES_EXTRA, "*.jsonl")))
    paths += sorted(glob.glob(os.path.join(RES_LARGE, "*.jsonl")))
    # probe_* files are auxiliary single-cell diagnostics, not grid runs.
    paths = [p for p in paths if not os.path.basename(p).startswith("probe_")]
    for path in paths:
        with open(path) as f:
            last = None
            for l in f:
                if l.strip():
                    last = l
        if last is None:
            continue
        try:
            out.append(json.loads(last)["_summary"])
        except (KeyError, json.JSONDecodeError, TypeError):
            continue
    return out


def median(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


def cell_curve(rows, cap, ent):
    by_n = defaultdict(lambda: {"val": [], "canary": []})
    for r in rows:
        if (r["total_budget"] == BUDGET and r["capacity"] == cap
                and r["entropy_level"] == ent):
            by_n[r["n_epochs"]]["val"].append(r["final_val_loss"])
            by_n[r["n_epochs"]]["canary"].append(r.get("final_canary_gap"))
    ns = sorted(by_n)
    return ns, {n: {"val": median(by_n[n]["val"]),
                    "canary": median(by_n[n]["canary"]),
                    "n_seeds": len(by_n[n]["val"])} for n in ns}


def analyze_cell(ns, cur):
    if 1 not in cur:
        return None
    fresh = cur[1]["val"]
    excess = {n: cur[n]["val"] - fresh for n in ns}
    free_ns = [n for n in ns if excess[n] < FREE_EPS]
    R_free = max(free_ns) if free_ns else 1
    decay_onset = next((n for n in ns if n > 1 and excess[n] >= FREE_EPS), None)
    mem_onset = next((n for n in ns if cur[n]["canary"] is not None
                      and cur[n]["canary"] >= CANARY_EPS), None)
    return {
        "n_points": ns, "fresh_val": fresh,
        "excess": {str(n): round(excess[n], 4) for n in ns},
        "canary": {str(n): (round(cur[n]["canary"], 4)
                            if cur[n]["canary"] is not None else None) for n in ns},
        "R_free_epochs": R_free,
        "decay_onset": decay_onset, "mem_onset": mem_onset,
        "onset_coincide": (decay_onset == mem_onset) if
                          (decay_onset and mem_onset) else None,
        "coverage_full": ns == [1, 2, 4, 10, 20, 40],
    }


def main():
    os.makedirs(FIG, exist_ok=True)
    rows = load()
    print(f"loaded {len(rows)} cells")

    cells = {}
    for cap in CAPS:
        for ent in ENTS:
            ns, cur = cell_curve(rows, cap, ent)
            res = analyze_cell(ns, cur) if ns else None
            if res:
                cells[f"{cap}/{ent}"] = res

    # P2: R_free stability across entropy (within capacity) and across capacity
    R_by_ent = defaultdict(list)
    R_by_cap = defaultdict(list)
    for key, c in cells.items():
        cap, ent = key.split("/")
        R_by_ent[ent].append(c["R_free_epochs"])
        R_by_cap[cap].append(c["R_free_epochs"])
    all_Rfree = [c["R_free_epochs"] for c in cells.values()]

    # P3: onset coincidence tally (only full-coverage cells)
    coinc = [(k, c["decay_onset"], c["mem_onset"]) for k, c in cells.items()
             if c["decay_onset"] is not None and c["mem_onset"] is not None]
    n_coincide = sum(1 for _, d, m in coinc if d == m)

    verdicts = {
        "budget": BUDGET, "free_eps_nats": FREE_EPS, "canary_eps": CANARY_EPS,
        "p1_R_free_all_cells": all_Rfree,
        "p1_R_free_range": [min(all_Rfree), max(all_Rfree)] if all_Rfree else None,
        "p2_R_free_by_entropy": {e: sorted(set(v)) for e, v in R_by_ent.items()},
        "p2_R_free_by_capacity": {c: sorted(set(v)) for c, v in R_by_cap.items()},
        "p3_onset_pairs": [{"cell": k, "decay_onset": d, "mem_onset": m}
                           for k, d, m in coinc],
        "p3_n_coincide": f"{n_coincide}/{len(coinc)}",
        "cells": cells,
    }
    out = os.path.join(FIG, "repeat_verdicts.json")
    with open(out, "w") as f:
        json.dump(verdicts, f, indent=1, default=str)
    print(f"wrote {out}")

    # figure: excess-loss decay curves (left) + canary onset overlay (right).
    # Rendered at full 2-column (figure*) width so LaTeX scale factor ~= 1.
    fig, axes = plt.subplots(1, 2, figsize=(figstyle.WIDTH_IN["col2_full"], 3.2))
    for key, c in cells.items():
        if not c["coverage_full"]:
            continue
        st = CELL_STYLE.get(key, dict(marker="o", ls="-"))
        ns = c["n_points"]; ex = [c["excess"][str(n)] for n in ns]
        axes[0].plot(ns, ex, label=key, alpha=0.9, **st)
        cn = [c["canary"][str(n)] for n in ns]
        axes[1].plot(ns, cn, label=key, alpha=0.9, **st)
    for ax, tag, yl in ((axes[0], "(a)", "Excess val loss (nats)"),
                        (axes[1], "(b)", "Canary memorization gap")):
        ax.set_xscale("log")
        ax.axvline(4, color=_CB["grey"], ls=":", lw=1.0,
                   label=r"$R_{\mathrm{free}}\approx4$ (Muennighoff)")
        ax.set_xlabel("Epoch count $n = B/U$"); ax.set_ylabel(yl)
        ax.set_title(tag, loc="left")
        ax.legend(ncol=2, fontsize=7.5)
    axes[0].axhline(FREE_EPS, color=_CB["grey"], ls="--", lw=0.7)
    fig.tight_layout()
    fp = os.path.join(FIG, "fig_repeat.png"); fig.savefig(fp)
    print(f"wrote {fp}")

    print("\n=== P1/P2 R_free (free epochs) per cell ===")
    for key in sorted(cells):
        c = cells[key]
        flag = "" if c["coverage_full"] else " [partial coverage]"
        print(f"  {key:12s} R_free={c['R_free_epochs']:>2}  decay_onset={c['decay_onset']}"
              f"  mem_onset={c['mem_onset']}{flag}")
    print(f"\nR_free range across all cells: {verdicts['p1_R_free_range']}")
    print(f"R_free by entropy: {dict(verdicts['p2_R_free_by_entropy'])}")
    print(f"P3 onset coincidence: {verdicts['p3_n_coincide']}")


if __name__ == "__main__":
    main()
