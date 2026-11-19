"""E1 scale-up — the repetition value-decay law on REAL text (byte-level).

Tests whether the synthetic-Markov finding (excess val-loss < 0.05 nats through
~4 epochs, then a sharp cliff; R_free ~= 4) survives on a real corpus at larger
scale. We use WikiText-103 as a byte stream (vocab = 256, so the model is
IDENTICAL to the synthetic E1 setup — a clean comparison), a ~5M-param decoder LM
(capacity 'med', vs the synthetic 'small'), and a larger token budget.

Design: fixed budget B. For each epoch count n in {1,2,4,10,20,40}, the unique
pool is the first U = B/n bytes of the train region; we train from scratch for n
passes (=> ~B tokens seen) and evaluate on a HELD-OUT byte region. The repetition
law is excess(n) = val_loss(n) - val_loss(n=1) (n=1 = all-fresh reference).

Reuses train_repeat primitives (build_model/optimizer, evaluate, epoch_loader,
_ce_full_sequence). Canary probe omitted for the real-text arm (the headline is
the cliff; canary onset is a synthetic-arm corroborator).

Usage:
  python run_repeat_realtext.py --smoke
  python run_repeat_realtext.py --budget 50000000 --capacity med --seeds 0
"""
from __future__ import annotations
import argparse, json, os, sys, time

_THIS = os.path.dirname(os.path.abspath(__file__))
if _THIS not in sys.path:
    sys.path.insert(0, _THIS)
import torch  # noqa: E402
from train_repeat import (Config, build_model, build_optimizer, evaluate,  # noqa: E402
                          _ce_full_sequence)
from data import epoch_loader  # noqa: E402

OUT = os.path.abspath(os.path.join(_THIS, "..", "results", "repeated_data_realtext"))
BYTES_PATH = os.path.join(_THIS, "wikitext_bytes.pt")
N_LIST = [1, 2, 4, 10, 20, 40]
VAL_BYTES = 2_000_000


def load_bytes():
    if not os.path.isfile(BYTES_PATH):
        raise RuntimeError(f"missing {BYTES_PATH}; build it via _fetch_wikitext.py")
    return torch.load(BYTES_PATH).long()


def train_one(cfg: Config, base_pool, val_pool, device):
    """Train from scratch on base_pool for cfg.n_epochs passes; return val_loss."""
    torch.manual_seed(cfg.seed)
    model = build_model(cfg, device)
    opts = build_optimizer(model, cfg)
    tokens_seen = 0
    for epoch in range(cfg.n_epochs):
        model.train()
        for xb in epoch_loader(base_pool, 1, cfg.batch_size, cfg.seq_len,
                               seed=cfg.seed * 1000 + epoch, device=device):
            loss = _ce_full_sequence(model, xb)
            for opt in opts:
                opt.zero_grad(set_to_none=True)
            loss.backward()
            for opt in opts:
                opt.step()
            tokens_seen += xb.numel()
    val = evaluate(model, val_pool, cfg, device)
    return val, tokens_seen, sum(p.numel() for p in model.parameters())


def run_sweep(budget, capacity, seq_len, batch_size, seed, device):
    toks = load_bytes()
    train_region = toks[:-VAL_BYTES]
    val_pool = toks[-VAL_BYTES:].to(device)
    rows = {}
    nparams = None
    for n in N_LIST:
        U = budget // n
        if U > train_region.numel():
            print(f"  n={n}: U={U} exceeds corpus; skipping", flush=True)
            continue
        base = train_region[:U].to(device)
        cfg = Config(unique_tokens=U, n_epochs=n, total_budget=budget,
                     seq_len=seq_len, batch_size=batch_size, vocab=256,
                     capacity=capacity, optimizer="adamw", lr=3e-4,
                     weight_decay=0.01, seed=seed, device=device)
        t = time.time()
        val, seen, nparams = train_one(cfg, base, val_pool, device)
        rows[n] = {"n": n, "U": U, "val_loss": val, "tokens_seen": seen}
        print(f"  n={n:2d} U={U:>9d} val_loss={val:.4f} ({time.time()-t:.0f}s, ~{seen/1e6:.0f}M toks)",
              flush=True)
    fresh = rows.get(1, {}).get("val_loss")
    for n, r in rows.items():
        r["excess"] = (r["val_loss"] - fresh) if fresh is not None else None
    # R_free = largest n with excess < 0.05
    rfree = max([n for n, r in rows.items()
                 if r["excess"] is not None and r["excess"] < 0.05], default=None)
    return {"rows": rows, "fresh_val": fresh, "R_free": rfree, "n_params": nparams,
            "budget": budget, "capacity": capacity, "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--budget", type=int, default=50_000_000)
    ap.add_argument("--capacity", default="med")
    ap.add_argument("--seq_len", type=int, default=256)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if a.smoke:
        global N_LIST
        N_LIST = [1, 4]
        v = run_sweep(200_000, "small", 128, 16, 0, device)
        print("SMOKE realtext OK:", json.dumps({k: v[k] for k in ("fresh_val", "R_free", "n_params")}))
        return

    os.makedirs(OUT, exist_ok=True)
    for seed in a.seeds:
        print(f"=== realtext repetition sweep: budget={a.budget} capacity={a.capacity} seed={seed} ===", flush=True)
        v = run_sweep(a.budget, a.capacity, a.seq_len, a.batch_size, seed, device)
        out = os.path.join(OUT, f"{a.capacity}_b{a.budget//1_000_000}M_s{seed}.json")
        with open(out, "w") as f:
            json.dump(v, f, indent=1, default=str)
        print(f"-> R_free={v['R_free']} fresh_val={v['fresh_val']:.4f} "
              f"excess@10={v['rows'].get(10,{}).get('excess')} wrote {out}", flush=True)


if __name__ == "__main__":
    main()
