#!/usr/bin/env python3
"""Canary-memorization probe on the REAL-byte bridges (2026-07-05).

Ports the synthetic planted-canary design to the byte-level corpora: canaries
are real held-out byte sequences (drawn from beyond the largest training
slice, disjoint from the validation tail), planted into the training pool via
the untouched memprobe.plant_canaries, and the memorization gap is measured
with the untouched memprobe.canary_gap. This measures memorization onset on
real text/code directly, closing E1's "onset inferred from direction" caveat.

Output: results/repeated_data_realtext_canary/<corpus>_med_b<B>M_s<seed>.json
with per-n val_loss/excess/canary_gap.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import torch  # noqa: E402
import run_repeat_realtext as R  # noqa: E402
from train_repeat import Config, build_model, build_optimizer, evaluate  # noqa: E402
from data import epoch_loader  # noqa: E402
from memprobe import CanarySet, plant_canaries, canary_gap  # noqa: E402

OUT = HERE.parent / 'results' / 'repeated_data_realtext_canary'
N_CANARY = 8
N_FRESH = 8
CANARY_REPEATS = 4


def train_one_keep(cfg, base_pool, val_pool, device):
    """train_repeat training loop (as in run_repeat_realtext.train_one) but
    returns the trained model as well."""
    torch.manual_seed(cfg.seed)
    model = build_model(cfg, device)
    opts = build_optimizer(model, cfg)
    tokens_seen = 0
    for epoch in range(cfg.n_epochs):
        model.train()
        for xb in epoch_loader(base_pool, 1, cfg.batch_size, cfg.seq_len,
                               seed=cfg.seed * 1000 + epoch, device=device):
            loss = R._ce_full_sequence(model, xb)
            for opt in opts:
                opt.zero_grad(set_to_none=True)
            loss.backward()
            for opt in opts:
                opt.step()
            tokens_seen += xb.numel()
    val = evaluate(model, val_pool, cfg, device)
    return model, val, tokens_seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', choices=['wiki', 'code'], required=True)
    ap.add_argument('--budget', type=int, default=50_000_000)
    ap.add_argument('--capacity', default='med')
    ap.add_argument('--seq-len', type=int, default=256)
    ap.add_argument('--batch-size', type=int, default=32)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--n-list', type=int, nargs='+', default=[1, 2, 4, 10, 20])
    a = ap.parse_args()

    if a.corpus == 'code':
        R.BYTES_PATH = str(HERE / 'code_bytes.pt')
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f'{a.corpus}_med_b{a.budget // 1_000_000}M_s{a.seed}.json'
    if out.exists():
        print(f'skip {out.name}')
        return

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    toks = R.load_bytes()
    train_region = toks[:-R.VAL_BYTES]
    val_pool = toks[-R.VAL_BYTES:].to(device)

    # Canary + fresh banks: real byte sequences from just beyond the largest
    # training slice (bytes budget .. budget+4k), never trained on unplanted,
    # disjoint from the validation tail by construction.
    c0 = a.budget
    need = (N_CANARY + N_FRESH) * a.seq_len
    if c0 + need > train_region.numel():
        raise SystemExit('corpus too small for held-out canary region')
    can = train_region[c0:c0 + N_CANARY * a.seq_len].view(N_CANARY, a.seq_len)
    fresh = train_region[c0 + N_CANARY * a.seq_len:c0 + need].view(N_FRESH, a.seq_len)
    cset = CanarySet(canaries=can.clone(), fresh=fresh.clone(), seq_len=a.seq_len)

    rows = {}
    for n in a.n_list:
        U = a.budget // n
        base = train_region[:U]
        planted = plant_canaries(base, cset, n_repeats=CANARY_REPEATS,
                                 seed=a.seed).to(device)
        cfg = Config(unique_tokens=U, n_epochs=n, total_budget=a.budget,
                     seq_len=a.seq_len, batch_size=a.batch_size, vocab=256,
                     capacity=a.capacity, optimizer='adamw', lr=3e-4,
                     weight_decay=0.01, seed=a.seed, device=device)
        t = time.time()
        model, val, seen = train_one_keep(cfg, planted, val_pool, device)
        cg = canary_gap(model, cset, device=device)
        del model
        torch.cuda.empty_cache()
        rows[n] = {'n': n, 'U': U, 'val_loss': val, 'tokens_seen': seen, **cg}
        print(f'  {a.corpus} n={n:2d} val={val:.4f} gap={cg["canary_gap"]:+.4f} '
              f'({time.time()-t:.0f}s)', flush=True)
    freshv = rows.get(1, {}).get('val_loss')
    for n, r in rows.items():
        r['excess'] = (r['val_loss'] - freshv) if freshv is not None else None
    v = {'rows': rows, 'fresh_val': freshv, 'corpus': a.corpus,
         'budget': a.budget, 'capacity': a.capacity, 'seed': a.seed,
         'n_canary': N_CANARY, 'canary_repeats': CANARY_REPEATS}
    out.write_text(json.dumps(v, indent=2, default=str) + '\n')
    print(f'done {out.name}')


if __name__ == '__main__':
    main()
