"""E1-C readout — is the onset ordering an artifact of 4x canary oversampling?

Conventions are the published E1 ones (analyze_repeat.py / analyze_stier_e1.py):

    excess(n)   = final_val_loss(n) - final_val_loss(n=1)   within the same
                  (capacity, entropy, canary_repeats, seed) sweep
    R_free      = max grid n with excess < 0.05 nats
    decay_onset = smallest grid n with excess >= 0.05 nats
    mem_onset   = smallest grid n with canary_gap >= 0.10 nats
    order       = mem_onset vs decay_onset (leads / coincides / lags)

The arm's point is that those two onsets are read on different axes whenever
canaries are planted more than once: a canary at grid point n has had
n * canary_repeats gradient exposures, an ordinary corpus token has had n. The
verdict therefore reports the ordering twice — once in NOMINAL grid units (the
published axis) and once in EXPOSURE units, where the canary onset is placed at
mem_onset * canary_repeats and the decay onset stays at decay_onset. For the
canary_repeats=1 arm the two axes coincide by construction, which is exactly
what makes it the control.

Cell verdicts pool seeds by median (analyze_repeat.py's convention); per-seed
sweeps are reported alongside so seed variability stays visible.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from statistics import median

FREE_EPS = 0.05
CANARY_EPS = 0.10

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RES = os.path.join(_THIS_DIR, "..", "revision2026", "gpu2026", "e1c")


def load_summaries(res_dir: str) -> list[dict]:
    """_summary records of every complete jsonl in res_dir."""
    rows = []
    for path in sorted(glob.glob(os.path.join(res_dir, "*.jsonl"))):
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


def _onsets(ns, excess, gap):
    r_free = max([n for n in ns if excess[n] < FREE_EPS], default=None)
    decay = next((n for n in ns if excess[n] >= FREE_EPS), None)
    mem = next((n for n in ns if gap[n] is not None and gap[n] >= CANARY_EPS),
               None)
    return r_free, decay, mem


def _order(mem, decay):
    if mem is None or decay is None:
        return "no_onset"
    return "leads" if mem < decay else ("coincides" if mem == decay else "lags")


def _sweep_verdict(rows_by_n: dict, n_repeats: int) -> dict | None:
    """One sweep = one (capacity, entropy, canary_repeats, seed) n-ladder."""
    if 1 not in rows_by_n:
        return None
    ns = sorted(rows_by_n)
    fresh = rows_by_n[1]["val"]
    excess = {n: rows_by_n[n]["val"] - fresh for n in ns}
    gap = {n: rows_by_n[n]["gap"] for n in ns}
    r_free, decay, mem = _onsets(ns, excess, gap)
    return {
        "ns": ns,
        "fresh_val": round(fresh, 4),
        "excess": {str(n): round(excess[n], 4) for n in ns},
        "canary_gap": {str(n): (round(gap[n], 4) if gap[n] is not None else None)
                       for n in ns},
        "R_free": r_free,
        "decay_onset": decay,
        "mem_onset": mem,
        "order_nominal": _order(mem, decay),
        "mem_onset_exposures": (mem * n_repeats) if mem is not None else None,
        "decay_onset_exposures": decay,
        "order_exposure": _order(mem * n_repeats if mem is not None else None,
                                 decay),
        "n_seeds_pooled": rows_by_n[ns[0]].get("n_seeds", 1),
    }


def build_verdict(rows: list[dict]) -> dict:
    """Per-seed sweeps + median-pooled cell verdicts + the arm's headline."""
    per_seed = defaultdict(dict)
    pooled = defaultdict(lambda: defaultdict(lambda: {"val": [], "gap": []}))
    for r in rows:
        key = (r["capacity"], r["entropy_level"], r["canary_repeats"])
        n = r["n_epochs"]
        per_seed[key + (r["seed"],)][n] = {
            "val": r["final_val_loss"], "gap": r.get("final_canary_gap")}
        pooled[key][n]["val"].append(r["final_val_loss"])
        if r.get("final_canary_gap") is not None:
            pooled[key][n]["gap"].append(r["final_canary_gap"])

    sweeps = {}
    for key in sorted(per_seed):
        v = _sweep_verdict(per_seed[key], key[2])
        if v:
            sweeps["/".join(map(str, key))] = v

    cells = {}
    for key in sorted(pooled):
        by_n = {n: {"val": median(d["val"]),
                    "gap": median(d["gap"]) if d["gap"] else None,
                    "n_seeds": len(d["val"])}
                for n, d in pooled[key].items()}
        v = _sweep_verdict(by_n, key[2])
        if v:
            v["n_seeds"] = {str(n): by_n[n]["n_seeds"] for n in sorted(by_n)}
            cells["/".join(map(str, key))] = v

    # Headline: per (capacity, entropy) cell, does the published 4x plant rate
    # and the exposure-matched 1x plant rate give the same ordering?
    paired, tally = {}, defaultdict(int)
    for key, v in cells.items():
        cap, ent, nrep = key.split("/")
        if int(nrep) != 1:
            continue
        other = f"{cap}/{ent}/4"
        if other not in cells:
            continue
        v4 = cells[other]
        paired[f"{cap}/{ent}"] = {
            "r4_order_nominal": v4["order_nominal"],
            "r4_order_exposure": v4["order_exposure"],
            "r1_order_nominal": v["order_nominal"],
            "r4_mem_onset": v4["mem_onset"], "r4_decay_onset": v4["decay_onset"],
            "r1_mem_onset": v["mem_onset"], "r1_decay_onset": v["decay_onset"],
            "inverted": (v4["order_nominal"] in ("leads", "coincides")
                         and v["order_nominal"] == "lags"),
        }
        tally[f"r4:{v4['order_nominal']}"] += 1
        tally[f"r1:{v['order_nominal']}"] += 1

    n_inv = sum(1 for p in paired.values() if p["inverted"])
    return {
        "free_eps_nats": FREE_EPS,
        "canary_eps_nats": CANARY_EPS,
        "n_runs_loaded": len(rows),
        "headline": {
            "n_cells_paired": len(paired),
            "n_inverted_r4_to_r1": n_inv,
            "inversion_rate": (f"{n_inv}/{len(paired)}" if paired else None),
            "order_tally": dict(tally),
        },
        "paired_cells": paired,
        "cells": cells,
        "sweeps": sweeps,
    }


def render_table(verdict: dict) -> str:
    lines = [f"{'cell (cap/ent/plant)':<26} {'grid':<24} {'R_free':>6} "
             f"{'decay':>6} {'mem':>5} {'order':>10} {'mem_exp':>8}"]
    for key in sorted(verdict["cells"]):
        c = verdict["cells"][key]
        lines.append(f"{key:<26} {str(c['ns']):<24} {str(c['R_free']):>6} "
                     f"{str(c['decay_onset']):>6} {str(c['mem_onset']):>5} "
                     f"{c['order_nominal']:>10} "
                     f"{str(c['mem_onset_exposures']):>8}")
    h = verdict["headline"]
    lines.append("")
    lines.append(f"paired cells: {h['n_cells_paired']}   "
                 f"ordering inverted 4x -> 1x: {h['inversion_rate']}")
    lines.append(f"order tally: {h['order_tally']}")
    for key in sorted(verdict["paired_cells"]):
        p = verdict["paired_cells"][key]
        flag = "  INVERTED" if p["inverted"] else ""
        lines.append(f"  {key:<14} 4x: mem@{p['r4_mem_onset']} vs "
                     f"decay@{p['r4_decay_onset']} = {p['r4_order_nominal']} "
                     f"(exposure-corrected {p['r4_order_exposure']})   "
                     f"1x: mem@{p['r1_mem_onset']} vs "
                     f"decay@{p['r1_decay_onset']} = "
                     f"{p['r1_order_nominal']}{flag}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="E1-C single-plant canary readout")
    ap.add_argument("--res", default=DEFAULT_RES, help="results directory")
    ap.add_argument("--out", default=None,
                    help="verdict json path (default: <res>/e1c_verdict.json)")
    a = ap.parse_args()

    rows = load_summaries(a.res)
    print(f"loaded {len(rows)} runs from {a.res}")
    verdict = build_verdict(rows)
    table = render_table(verdict)
    print(table)

    out = a.out or os.path.join(a.res, "e1c_verdict.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as f:
        json.dump(verdict, f, indent=1, default=str)
    txt = os.path.splitext(out)[0] + ".txt"
    with open(txt, "w") as f:
        f.write(table + "\n")
    print(f"wrote {out}\nwrote {txt}")


if __name__ == "__main__":
    main()
