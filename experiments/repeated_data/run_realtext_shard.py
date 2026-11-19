#!/usr/bin/env python3
"""Corpus-shard replication sweeps for the byte-level bridges (red-team M1).

Identical protocol to run_repeat_realtext.run_sweep, but the byte corpus is an
explicit --bytes-file (one of the disjoint wiki_shard{k}.pt / code_v2_shard{k}.pt
files), so different "seeds" now correspond to genuinely different corpus
draws, not just optimization noise on one fixed draw.

Output: results/repeated_data_realtext_shards/<tag>_s<seed>.json
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_repeat_realtext as R  # noqa: E402

OUT = HERE.parent / 'results' / 'repeated_data_realtext_shards'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bytes-file', required=True)
    ap.add_argument('--tag', required=True,
                    help='output prefix, e.g. wiki_shard1 / code_v2_shard0')
    ap.add_argument('--budget', type=int, default=50_000_000)
    ap.add_argument('--capacity', default='med')
    ap.add_argument('--seq-len', type=int, default=256)
    ap.add_argument('--batch-size', type=int, default=32)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--n-list', type=int, nargs='+', default=[1, 2, 4, 10, 20])
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f'{a.tag}_s{a.seed}.json'
    if out.exists():
        print(f'skip {out.name}')
        return
    R.BYTES_PATH = str(Path(a.bytes_file).resolve())
    R.N_LIST = list(a.n_list)
    import torch
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    v = R.run_sweep(a.budget, a.capacity, a.seq_len, a.batch_size, a.seed, dev)
    v['bytes_file'] = a.bytes_file
    v['tag'] = a.tag
    out.write_text(json.dumps(v, indent=2, default=str) + '\n')
    print(f"done {out.name} R_free={v.get('R_free')}")


if __name__ == '__main__':
    main()
