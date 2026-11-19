"""Direction 013 — tiny decoder LM for the repeated-data value-decay study.

MODEL CHOICE (documented per task rule)
---------------------------------------
We REUSE the grokking `GrokTransformer` architecture UNMODIFIED (imported via
importlib from `experiments/grokking/model.py`; that file is never touched) and
add a thin local `SeqTransformer` subclass whose `forward` returns next-token
logits at EVERY position (`[B, T, vocab]`), exactly as direction 007's
`induction_emergence/model.py` does. The grokking forward returns only the last
position (`logits[:, -1]`) because the modular task predicts one answer token;
a repeated-data LM needs full-sequence cross-entropy, so we override forward.

We deliberately re-implement the tiny full-sequence subclass here rather than
importing `induction_emergence.model.SeqTransformer`, because that module does a
local-first `from muon import ...` that assumes the grokking dir is appended to
sys.path with no competing local `muon.py` — a fragile two-hop import. A direct
one-hop reuse of `GrokTransformer` is cleaner and keeps this directory's import
surface self-contained (we do NOT need Muon's name-based split here: the default
optimizer is plain AdamW; see train_repeat.py for the subordinated Muon arm).

CAPACITY AXIS
-------------
`GrokTransformer.__init__` already exposes `vocab_size, seq_len, d_model,
n_heads, n_layers, mlp_ratio` — every knob the capacity sweep needs. The
{small, med, large} presets in train_repeat.py vary `d_model` / `n_layers`
(and the data's vocab feeds `vocab_size`) to land at ~2M / ~5M / ~10M params.
Param count is dominated by tok_emb + unembed (both vocab*d_model) and the
per-block 4*d_model^2 (qkv+proj) + 8*d_model^2 (mlp, ratio 4) matrices.
"""
from __future__ import annotations

import importlib.util as _ilu
import os

import torch

# Import the grokking GrokTransformer WITHOUT modifying it and WITHOUT putting
# the grokking dir on sys.path (avoids shadowing this dir's local modules).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROK_MODEL_PATH = os.path.abspath(
    os.path.join(_THIS_DIR, "..", "grokking", "model.py")
)
_spec = _ilu.spec_from_file_location("grokking_model_for_repeat", _GROK_MODEL_PATH)
_grok_model = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_grok_model)  # type: ignore[union-attr]
GrokTransformer = _grok_model.GrokTransformer


class SeqTransformer(GrokTransformer):
    """GrokTransformer returning next-token logits at ALL positions.

    Identical parameters / init to GrokTransformer (so the capacity sweep and
    param count are governed entirely by the GrokTransformer kwargs); only the
    forward output slice differs (full `[B, T, vocab]` vs grokking's `[:, -1]`).
    """

    def forward(self, idx):  # type: ignore[override]
        T = idx.shape[1]
        pos = torch.arange(T, device=idx.device)
        x = self.tok_emb(idx) + self.pos_emb(pos)[None]
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_f(x)
        logits = self.unembed(x)  # [B, T, vocab]
        return logits             # full sequence (vs grokking's [:, -1])


# Capacity presets: (d_model, n_heads, n_layers). vocab_size/seq_len are set by
# the data config at build time. Tuned so param counts land near the nominal
# 2M / 5M / 10M targets at the study's default vocab (V=256) and seq_len (128):
#   small d=256 h=4 L=3 -> 2.53M ; med d=384 h=6 L=3 -> 5.56M ;
#   large d=448 h=8 L=4 -> 9.93M  (exact counts verified in model self-test).
CAPACITY_PRESETS = {
    "small": dict(d_model=256, n_heads=4, n_layers=3),
    "med":   dict(d_model=384, n_heads=6, n_layers=3),
    "large": dict(d_model=448, n_heads=8, n_layers=4),
    # capacity-span extension (direction 013 follow-up, 2026-07-08): ~25M / ~50M
    # params at the study's default vocab (V=256) and seq_len (128) — exact
    # counts verified via count_params() in run_20260708_capacity_xl.py.
    "xl":    dict(d_model=640, n_heads=8, n_layers=6),
    "xxl":   dict(d_model=768, n_heads=8, n_layers=8),
}


def build_lm(vocab_size: int, seq_len: int, capacity: str = "small",
             mlp_ratio: int = 4, init_scale: float = 1.0,
             device: str = "cpu") -> SeqTransformer:
    """Build a full-sequence tiny decoder LM at the named capacity preset."""
    if capacity not in CAPACITY_PRESETS:
        raise ValueError(
            f"unknown capacity {capacity!r}; choose from {sorted(CAPACITY_PRESETS)}"
        )
    preset = CAPACITY_PRESETS[capacity]
    return SeqTransformer(
        vocab_size=vocab_size,
        seq_len=seq_len,
        mlp_ratio=mlp_ratio,
        init_scale=init_scale,
        **preset,
    ).to(device)


def count_params(model) -> int:
    return sum(p.numel() for p in model.parameters())
