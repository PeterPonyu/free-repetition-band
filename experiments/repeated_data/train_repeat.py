"""Direction 013 — repeated-data LM trainer (next-token CE, full sequence).

One run = one (unique_tokens, n_epochs, capacity, entropy, seed) cell at a fixed
total token budget. The model trains on a FIXED unique-data corpus repeated for
`n_epochs` passes (the repetition axis); validation uses a held-out FRESH stream
from the same generator (so val loss measures generalization, not memorization);
a planted-canary probe reports the memorization gap each eval.

Optimizer: AdamW is the FIXED default (the study's main axis is data, not the
optimizer). A subordinated Muon arm is available via --optimizer muon for an
optional robustness check, reusing the grokking name-based split; it is NOT the
default and is never required by the smoke or the main grid.

Per-eval jsonl record (real runs only): train loss, val loss (fresh stream),
canary gap (+ its two components), tokens-seen, epoch.

--smoke contract (EXACT lines, exit 0, <60s, NO files):
  SMOKE DATASET SHAPE: ...
  SMOKE PARAM COUNT: <n>
  SMOKE FORWARD LOSS: <float>
  SMOKE OPTIMIZER STEP: OK
  SMOKE REPEAT PROBE: entropy=<f> gzip_ratio=<f> fit_selftest=<PASS|FAIL> canary_gap=<f>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict

# --- local-first import discipline (no grokking-dir shadowing of local mods) ---
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR in sys.path:
    sys.path.remove(_THIS_DIR)
sys.path.insert(0, _THIS_DIR)
_GROKKING_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "grokking"))
if _GROKKING_DIR not in sys.path:
    sys.path.append(_GROKKING_DIR)

import torch
import torch.nn.functional as F

from data import (  # noqa: E402
    EntropyKnobs, knobs_for_level, make_corpus, epoch_loader, one_batch,
    measured_entropy,
)
from model import build_lm, count_params, CAPACITY_PRESETS  # noqa: E402
from memprobe import make_canaries, plant_canaries, canary_gap  # noqa: E402


@dataclass
class Config:
    # data / budget
    unique_tokens: int = 50000     # U — size of the unique-data pool
    n_epochs: int = 4              # E — repetition passes over the pool
    total_budget: int = 0          # B — if >0, asserts U*E ~ B (else informational)
    seq_len: int = 128             # L
    batch_size: int = 32
    # entropy
    generator: str = "markov"      # markov | zipf | pcfg
    entropy_level: str = "med"     # low | med | high (-> concrete knobs)
    vocab: int = 256               # V (also the model vocab_size)
    # model capacity
    capacity: str = "small"        # small | med | large (~2M / 5M / 10M params)
    mlp_ratio: int = 4
    init_scale: float = 1.0
    # canary memorization probe
    n_canary: int = 8
    canary_repeats: int = 4
    # optimization (AdamW fixed default; muon arm subordinated)
    optimizer: str = "adamw"       # adamw | muon
    lr: float = 3e-4
    muon_lr: float = 0.02
    weight_decay: float = 0.01
    beta1: float = 0.9
    beta2: float = 0.98
    eval_every: int = 1            # eval cadence in EPOCHS
    val_batches: int = 4
    seed: int = 0
    device: str = "cuda"


def make_knobs(cfg: Config) -> EntropyKnobs:
    return knobs_for_level(cfg.entropy_level, generator=cfg.generator,
                           vocab=cfg.vocab)


def build_model(cfg: Config, device: str):
    return build_lm(vocab_size=cfg.vocab, seq_len=cfg.seq_len,
                    capacity=cfg.capacity, mlp_ratio=cfg.mlp_ratio,
                    init_scale=cfg.init_scale, device=device)


def build_optimizer(model, cfg: Config):
    """AdamW (default) or a subordinated Muon hybrid arm (optional)."""
    if cfg.optimizer == "adamw":
        return [torch.optim.AdamW(model.parameters(), lr=cfg.lr,
                                  betas=(cfg.beta1, cfg.beta2),
                                  weight_decay=cfg.weight_decay)]
    elif cfg.optimizer == "muon":
        # Reuse grokking's name-based split (2-D block matrices -> Muon, the
        # rest -> AdamW). Imported lazily so the AdamW default never needs it.
        from muon import Muon, split_params_for_muon  # noqa: E402
        muon_p, adamw_p = split_params_for_muon(model)
        return [
            Muon(muon_p, lr=cfg.muon_lr, momentum=0.95, nesterov=True,
                 ns_steps=5, weight_decay=cfg.weight_decay),
            torch.optim.AdamW(adamw_p, lr=cfg.lr, betas=(cfg.beta1, cfg.beta2),
                              weight_decay=cfg.weight_decay),
        ]
    raise ValueError(f"unknown optimizer {cfg.optimizer!r}")


def _ce_full_sequence(model, batch: torch.Tensor) -> torch.Tensor:
    """Mean next-token CE over a full sequence batch [B, T]."""
    logits = model(batch)                                  # [B, T, V]
    V = logits.shape[-1]
    pred = logits[:, :-1, :].reshape(-1, V)
    tgt = batch[:, 1:].reshape(-1)
    return F.cross_entropy(pred, tgt)


@torch.no_grad()
def evaluate(model, val_corpus, cfg: Config, device: str) -> float:
    """Mean val CE over a few fresh batches (held-out stream, same generator)."""
    model.eval()
    losses = []
    for i, xb in enumerate(epoch_loader(val_corpus, 1, cfg.batch_size,
                                        cfg.seq_len, seed=777 + cfg.seed,
                                        device=device)):
        losses.append(_ce_full_sequence(model, xb).item())
        if i + 1 >= cfg.val_batches:
            break
    model.train()
    return float(sum(losses) / max(1, len(losses)))


def run(cfg: Config, out_path: str | None = None):
    torch.manual_seed(cfg.seed)
    device = cfg.device if torch.cuda.is_available() else "cpu"
    knobs = make_knobs(cfg)

    # Unique-data pool, then plant repeated canaries into it.
    base_corpus = make_corpus(cfg.unique_tokens, knobs, seed=cfg.seed)
    cset = make_canaries(knobs, cfg.seq_len, n_canary=cfg.n_canary,
                         n_fresh=cfg.n_canary, seed=cfg.seed)
    train_corpus = plant_canaries(base_corpus, cset,
                                  n_repeats=cfg.canary_repeats, seed=cfg.seed)
    # Held-out fresh val stream from the same generator (disjoint seed).
    val_corpus = make_corpus(max(cfg.unique_tokens, cfg.batch_size * cfg.seq_len),
                             knobs, seed=500_000_000 + cfg.seed)

    model = build_model(cfg, device)
    optimizers = build_optimizer(model, cfg)

    history: list = []
    t0 = time.time()
    f = open(out_path, "w") if out_path else None
    if f:
        f.write(json.dumps({"_meta": asdict(cfg)}) + "\n")

    tokens_seen = 0
    for epoch in range(cfg.n_epochs):
        model.train()
        ep_losses = []
        for xb in epoch_loader(train_corpus, 1, cfg.batch_size, cfg.seq_len,
                               seed=cfg.seed * 1000 + epoch, device=device):
            loss = _ce_full_sequence(model, xb)
            for opt in optimizers:
                opt.zero_grad(set_to_none=True)
            loss.backward()
            for opt in optimizers:
                opt.step()
            ep_losses.append(loss.item())
            tokens_seen += xb.numel()

        if (epoch % cfg.eval_every == 0) or (epoch == cfg.n_epochs - 1):
            val = evaluate(model, val_corpus, cfg, device)
            cg = canary_gap(model, cset, device=device)
            rec = {
                "epoch": epoch,
                "tokens_seen": tokens_seen,
                "train_loss": float(sum(ep_losses) / max(1, len(ep_losses))),
                "val_loss": val,
                "canary_loss": cg["canary_loss"],
                "fresh_loss": cg["fresh_loss"],
                "canary_gap": cg["canary_gap"],
            }
            history.append(rec)
            if f:
                f.write(json.dumps(rec) + "\n")
                f.flush()

    elapsed = time.time() - t0
    summary = {
        **asdict(cfg),
        "final_train_loss": history[-1]["train_loss"],
        "final_val_loss": history[-1]["val_loss"],
        "final_canary_gap": history[-1]["canary_gap"],
        "tokens_seen": tokens_seen,
        "n_params": count_params(model),
        "elapsed_sec": elapsed,
    }
    if f:
        f.write(json.dumps({"_summary": summary}) + "\n")
        f.close()
    return summary, history


# ---------------------------------------------------------------------------
# Smoke: EXACT labeled lines, <=1 step, NO files, exit 0.
# ---------------------------------------------------------------------------
def run_smoke():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    # Tiny corpus / model so smoke is well under 60s and writes nothing.
    cfg = Config(unique_tokens=4096, n_epochs=1, seq_len=32, batch_size=8,
                 generator="markov", entropy_level="med", vocab=64,
                 capacity="small", n_canary=4, canary_repeats=2, seed=0,
                 device=device)
    knobs = make_knobs(cfg)

    # 1. one batch shape from a tiny corpus
    corpus = make_corpus(cfg.unique_tokens, knobs, seed=0)
    xb = one_batch(corpus, cfg.batch_size, cfg.seq_len, seed=0, device=device)
    print(f"SMOKE DATASET SHAPE: corpus={tuple(corpus.shape)}, "
          f"batch={tuple(xb.shape)}")

    # 2. param count
    model = build_model(cfg, device)
    print(f"SMOKE PARAM COUNT: {count_params(model)}")

    # 3. forward + full-sequence CE loss
    loss = _ce_full_sequence(model, xb)
    print(f"SMOKE FORWARD LOSS: {loss.item():.6f}")

    # 4. one optimizer step
    optimizers = build_optimizer(model, cfg)
    for opt in optimizers:
        opt.zero_grad(set_to_none=True)
    loss.backward()
    for opt in optimizers:
        opt.step()
    print("SMOKE OPTIMIZER STEP: OK")

    # 5. bonus: generators + fitter + memprobe end-to-end
    m = measured_entropy(corpus, cond_order=1)
    from fitting import _self_test as _fit_self_test
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fit_rc = _fit_self_test()
    fit_tag = "PASS" if fit_rc == 0 else "FAIL"
    cset = make_canaries(knobs, cfg.seq_len, n_canary=cfg.n_canary,
                         n_fresh=cfg.n_canary, seed=0)
    cg = canary_gap(model, cset, device=device)
    print(f"SMOKE REPEAT PROBE: entropy={m['cond_entropy_bits']:.4f} "
          f"gzip_ratio={m['gzip_ratio']:.4f} fit_selftest={fit_tag} "
          f"canary_gap={cg['canary_gap']:.4f}")


def parse_args() -> tuple[Config, bool]:
    ap = argparse.ArgumentParser(description="repeated-data LM trainer (dir 013)")
    ap.add_argument("--smoke", action="store_true",
                    help="Run smoke checks and exit (no files written)")
    defaults = asdict(Config())
    for k, v in defaults.items():
        ap.add_argument(f"--{k}", type=type(v) if v is not None else str, default=v)
    a = vars(ap.parse_args())
    smoke = a.pop("smoke")
    cfg = Config(**a)
    return cfg, smoke


if __name__ == "__main__":
    cfg, smoke = parse_args()
    if smoke:
        run_smoke()
        sys.exit(0)
    summary, _ = run(cfg, out_path=None)
    print(json.dumps(summary, indent=2))
