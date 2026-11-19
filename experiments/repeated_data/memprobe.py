"""Direction 013 — memorization probe via planted canary sequences.

To separate *learning* (generalization to fresh stream) from *memorization* (the
model fitting the specific repeated tokens), we plant a small set of CANARY
sequences inside the training corpus and track, every epoch, the gap between

  - the model's loss on those exact canary sequences (which it has SEEN, possibly
    many times if the corpus is repeated), and
  - its loss on MATCHED FRESH sequences from the same generator that it has NOT
    seen (same length, same entropy law, disjoint seeds).

canary_gap = mean_loss(fresh_matched) - mean_loss(canary)

A large positive gap means the model assigns much lower loss to the exact seen
canaries than to statistically identical unseen sequences — i.e. it memorized
the specific tokens rather than only learning the distribution. Under the
repeated-data law this gap should GROW with repetition epochs (more exposure to
the same tokens), which is the memorization signature the study probes alongside
the loss-vs-budget surface.

All evaluation is @torch.no_grad and model.eval(); the probe never updates the
model and writes no files.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from data import EntropyKnobs, make_corpus


@dataclass
class CanarySet:
    """A fixed bank of canary sequences + a matched fresh (unseen) bank."""
    canaries: torch.Tensor      # [n_canary, seq_len] planted-in-corpus seqs
    fresh: torch.Tensor         # [n_fresh,  seq_len] matched, unseen seqs
    seq_len: int


def make_canaries(entropy_knobs: EntropyKnobs, seq_len: int, n_canary: int = 8,
                  n_fresh: int = 8, seed: int = 0) -> CanarySet:
    """Build a canary bank and a matched fresh bank from the SAME generator.

    The canaries are sampled with a dedicated `canary_seed` (so they can be
    planted into the training corpus by `plant_canaries`); the fresh bank uses a
    disjoint seed range, so it is statistically identical but never trained on.
    """
    can_tokens = (n_canary * seq_len)
    fresh_tokens = (n_fresh * seq_len)
    canary_stream = make_corpus(can_tokens, entropy_knobs,
                                seed=900_000_000 + seed)
    fresh_stream = make_corpus(fresh_tokens, entropy_knobs,
                               seed=910_000_000 + seed)
    canaries = canary_stream.view(n_canary, seq_len)
    fresh = fresh_stream.view(n_fresh, seq_len)
    return CanarySet(canaries=canaries, fresh=fresh, seq_len=seq_len)


def plant_canaries(corpus: torch.Tensor, cset: CanarySet,
                   n_repeats: int = 4, seed: int = 0) -> torch.Tensor:
    """Splice the canary sequences into `corpus` `n_repeats` times each.

    Returns a new corpus (1-D LongTensor) with the canaries inserted at evenly
    spaced, deterministic offsets so they are guaranteed to be SEEN during
    training. The original tokens are preserved (canaries are inserted, the
    corpus grows by n_canary*n_repeats*seq_len tokens).
    """
    flat_canaries = cset.canaries.reshape(-1)
    block = flat_canaries.repeat(n_repeats)               # all planted copies
    n = corpus.numel()
    g = torch.Generator().manual_seed((int(seed) * 2_654_435_761) & 0x7FFF_FFFF)
    # one insertion point per canary copy, spread across the corpus
    n_inserts = cset.canaries.shape[0] * n_repeats
    cuts = torch.sort(torch.randint(0, n + 1, (n_inserts,), generator=g)).values
    pieces = []
    prev = 0
    seg = block.view(n_inserts, cset.seq_len)
    for i in range(n_inserts):
        pieces.append(corpus[prev:int(cuts[i])])
        pieces.append(seg[i])
        prev = int(cuts[i])
    pieces.append(corpus[prev:])
    return torch.cat(pieces)


@torch.no_grad()
def _seq_loss(model, seqs: torch.Tensor, device: str) -> float:
    """Mean next-token CE over a batch of full sequences (no grad, eval)."""
    was_training = model.training
    model.eval()
    x = seqs.to(device)
    logits = model(x)                                     # [B, T, V]
    V = logits.shape[-1]
    # next-token shift: predict x[:,1:] from x[:,:-1]
    pred = logits[:, :-1, :].reshape(-1, V)
    tgt = x[:, 1:].reshape(-1)
    loss = F.cross_entropy(pred, tgt).item()
    if was_training:
        model.train()
    return loss


@torch.no_grad()
def canary_gap(model, cset: CanarySet, device: str = "cpu") -> dict:
    """Memorization signal = fresh-loss minus canary-loss (>0 => memorization)."""
    can_loss = _seq_loss(model, cset.canaries, device)
    fresh_loss = _seq_loss(model, cset.fresh, device)
    return {
        "canary_loss": can_loss,
        "fresh_loss": fresh_loss,
        "canary_gap": fresh_loss - can_loss,
    }


# ---------------------------------------------------------------------------
# Lightweight self-import check (no heavy self-test; exercised by smoke).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal sanity: build a canary set + planted corpus, check shapes.
    knobs = EntropyKnobs(generator="markov", vocab=64, branching=8)
    cset = make_canaries(knobs, seq_len=16, n_canary=4, n_fresh=4, seed=0)
    base = make_corpus(2000, knobs, seed=0)
    planted = plant_canaries(base, cset, n_repeats=3, seed=0)
    grew = planted.numel() - base.numel()
    expect = 4 * 3 * 16
    ok = (cset.canaries.shape == (4, 16) and cset.fresh.shape == (4, 16)
          and grew == expect)
    print(f"MEMPROBE SELF-CHECK: canaries={tuple(cset.canaries.shape)} "
          f"fresh={tuple(cset.fresh.shape)} planted_growth={grew} "
          f"(expect {expect}) {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)
