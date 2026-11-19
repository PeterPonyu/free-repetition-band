#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments" / "repeated_data"
sys.path.insert(0, str(EXP))
sys.path.append(str(ROOT / "experiments"))
import run_repeat_realtext as R  # noqa:E402

OUT = ROOT / "experiments/results/ultragoal_20260619_fullattack/e1_realtext_extension"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=10_000_000)
    ap.add_argument("--capacity", default="med")
    ap.add_argument("--seq-len", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1])
    ap.add_argument("--n-list", type=int, nargs="+", default=[1, 2, 4, 10, 20])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    R.N_LIST = list(a.n_list)
    dev = "cuda" if __import__("torch").cuda.is_available() else "cpu"
    allv = []
    for seed in a.seeds:
        out = OUT / f"{a.capacity}_b{a.budget // 1_000_000}M_s{seed}.json"
        if out.exists():
            print(f"skip {out.name}", flush=True)
            allv.append(json.loads(out.read_text()))
            continue
        print(
            f"run realtext budget={a.budget} cap={a.capacity} seed={seed} n_list={R.N_LIST}",
            flush=True,
        )
        v = R.run_sweep(a.budget, a.capacity, a.seq_len, a.batch_size, seed, dev)
        out.write_text(json.dumps(v, indent=2, default=str) + "\n")
        allv.append(v)
    (OUT / "summaries.json").write_text(json.dumps(allv, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
