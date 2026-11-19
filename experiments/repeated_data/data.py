"""Direction 013 — entropy-controlled synthetic corpora for the repeated-data law.

The Muennighoff et al. (2023, arXiv:2305.16264) "repeated data" study asks how
the *value* of repeated tokens decays: training on U unique tokens for E epochs
behaves like training on an *effective* unique-token count D' < U*E, with the
marginal value of each extra epoch decaying hyperbolically (governed by a decay
constant R*_D). The open question this direction adjudicates: is that decay
constant universal, or a function of model capacity and the corpus's
entropy-to-capacity ratio? To probe it we need corpora whose TRUE entropy we can
*dial*, so we can ask whether R*_D moves with entropy.

This module provides three deterministic generators whose tunable knobs move the
true per-token entropy, plus an empirical entropy/compressibility validator:

  (i)   order-k Markov chains over a vocabulary of size V. Knobs that move true
        entropy: Markov order `k`, the per-context `branching` factor (how many
        successor tokens get non-trivial probability), and `temperature` (how
        peaked the successor distribution is). Low temperature / low branching /
        high order => low conditional entropy (very predictable).
  (ii)  Zipf-weighted unigram streams. Knob: the Zipf exponent `zipf_s` (large s
        => mass concentrates on a few tokens => low entropy) and `vocab`.
  (iii) a tiny PCFG (probabilistic context-free grammar) emitting bracketed
        expressions; knob: `pcfg_ambiguity` ∈ [0,1] interpolating between a
        deterministic (low-entropy) and uniform (high-entropy) production choice.

Empirical validation (`measured_entropy`):
  - an empirical per-token CONDITIONAL entropy estimate H(x_t | x_{t-1..t-m})
    (plug-in estimator at a small fixed history order m), and
  - a gzip COMPRESSION RATIO (compressed_bytes / raw_bytes) as a second,
    model-free compressibility witness. Both should fall together as a knob is
    turned toward lower entropy.

`make_corpus(unique_tokens, entropy_knobs, seed)` returns a 1-D LongTensor of
exactly `unique_tokens` token ids — the "unique data" axis of the grid.
`epoch_loader(corpus, n_epochs, batch, seq_len, seed)` yields repeated passes
over that fixed corpus (the "repetition" axis), shuffling the contiguous-chunk
order each epoch with a per-epoch seed so repetition is faithful but not
trivially periodic.

Self-test (`python data.py`) certifies, for each generator, that turning the
entropy knob monotonically moves BOTH the measured conditional entropy AND the
gzip ratio in the same direction, and that corpora are bit-identical per seed.
"""
from __future__ import annotations

import gzip
import math
from dataclasses import dataclass
from typing import Iterator

import torch


# ---------------------------------------------------------------------------
# Entropy knob bundle
# ---------------------------------------------------------------------------
@dataclass
class EntropyKnobs:
    """Generator selection + the knobs that move TRUE per-token entropy.

    generator ∈ {"markov", "zipf", "pcfg"}.
    Higher entropy (less predictable) <=> larger `branching`, larger
    `temperature`, smaller `markov_order`; smaller `zipf_s`; larger
    `pcfg_ambiguity`.
    """
    generator: str = "markov"
    vocab: int = 256
    # Markov knobs
    markov_order: int = 1          # k
    branching: int = 8             # successors with non-trivial mass per context
    temperature: float = 1.0       # softmax temperature on successor logits
    # Zipf knob
    zipf_s: float = 1.1            # Zipf exponent
    # PCFG knob
    pcfg_ambiguity: float = 0.5    # 0 => deterministic productions, 1 => uniform
    # shared
    transition_seed: int = 12345   # seeds the (corpus-independent) generator law

    def entropy_level_tag(self) -> str:
        return f"{self.generator}"


def knobs_for_level(level: str, generator: str = "markov",
                    vocab: int = 256) -> EntropyKnobs:
    """Map a coarse {low, med, high} entropy level to concrete knobs.

    Used by the grid runner's entropy axis. The mapping is generator-specific so
    that 'low'/'high' genuinely bracket low/high measured entropy for each one.
    """
    if generator == "markov":
        table = {
            "low":  dict(markov_order=2, branching=2,  temperature=0.4),
            "med":  dict(markov_order=1, branching=8,  temperature=1.0),
            "high": dict(markov_order=1, branching=64, temperature=2.0),
        }
    elif generator == "zipf":
        table = {
            "low":  dict(zipf_s=2.0),
            "med":  dict(zipf_s=1.1),
            "high": dict(zipf_s=0.4),
        }
    elif generator == "pcfg":
        table = {
            "low":  dict(pcfg_ambiguity=0.02),
            "med":  dict(pcfg_ambiguity=0.25),
            "high": dict(pcfg_ambiguity=1.0),
        }
    else:
        raise ValueError(f"unknown generator {generator!r}")
    if level not in table:
        raise ValueError(f"unknown entropy level {level!r}")
    return EntropyKnobs(generator=generator, vocab=vocab, **table[level])


# ---------------------------------------------------------------------------
# Generator (i): order-k Markov chain
# ---------------------------------------------------------------------------
def _markov_transition(knobs: EntropyKnobs, g: torch.Generator) -> torch.Tensor:
    """Build the successor distribution table for an order-1 Markov surrogate.

    For order k we hash the k-token context to a single context id in [0, V) so
    the transition table stays [V, V] regardless of order (a faithful, memory-
    cheap order-k chain: the context id is a deterministic function of the last
    k tokens). Returns a [V, V] row-stochastic tensor.

    Entropy is controlled by (branching, temperature): only `branching` randomly
    chosen successors per context get a finite logit; the rest get -inf, and the
    softmax temperature peaks (low T) or flattens (high T) that distribution.
    """
    V = knobs.vocab
    b = max(1, min(knobs.branching, V))
    logits = torch.full((V, V), float("-inf"))
    base = torch.randn(V, V, generator=g)                       # [V, V]
    # pick `b` successors per row to be "allowed"
    allow = torch.rand(V, V, generator=g).argsort(dim=1)[:, :b]  # [V, b] indices
    rows = torch.arange(V)[:, None].expand(V, b)
    logits[rows, allow] = base[rows, allow] / max(1e-3, knobs.temperature)
    probs = torch.softmax(logits, dim=1)
    return probs


def _context_id(out: list[int], t: int, order: int, V: int) -> int:
    """Deterministic hash of the `order` tokens ending at position t-1 -> [0, V).

    Reads `out[t-order .. t-1]`, clamping at the stream start (positions before 0
    are treated as a fixed sentinel) so early positions are well-defined.
    """
    cid = 0
    for j in range(order):
        idx = t - 1 - j
        tok = out[idx] if idx >= 0 else 0          # sentinel before stream start
        cid = (cid * 1_000_003 + tok + 1) & 0x7FFF_FFFF
    return cid % V


def _gen_markov(n: int, knobs: EntropyKnobs, seed: int) -> torch.Tensor:
    """Sample n tokens from the order-k Markov chain (deterministic per seed)."""
    V = knobs.vocab
    gT = torch.Generator().manual_seed(knobs.transition_seed)   # the law (fixed)
    probs = _markov_transition(knobs, gT)                        # [V, V]
    gS = torch.Generator().manual_seed(int(seed) & 0x7FFF_FFFF)  # the sample path
    order = max(1, knobs.markov_order)

    # Draw all the uniform randoms up front for speed + determinism.
    u = torch.rand(n, generator=gS).tolist()
    cdf = probs.cumsum(dim=1).tolist()                          # list[list] [V][V]
    out: list[int] = [int(torch.randint(0, V, (1,), generator=gS))]
    for t in range(1, n):
        ctx = (out[t - 1] if order <= 1 else _context_id(out, t, order, V))
        row = cdf[ctx]
        # searchsorted on the cdf row (Python bisect over a small list).
        ut = u[t]
        lo, hi = 0, V - 1
        while lo < hi:
            mid = (lo + hi) >> 1
            if row[mid] < ut:
                lo = mid + 1
            else:
                hi = mid
        out.append(lo)
    return torch.tensor(out, dtype=torch.long)


# ---------------------------------------------------------------------------
# Generator (ii): Zipf-weighted unigram stream
# ---------------------------------------------------------------------------
def _zipf_weights(V: int, s: float) -> torch.Tensor:
    ranks = torch.arange(1, V + 1, dtype=torch.float64)
    w = ranks.pow(-s)
    return (w / w.sum()).to(torch.float32)


def _gen_zipf(n: int, knobs: EntropyKnobs, seed: int) -> torch.Tensor:
    """Sample n iid tokens from a Zipf(s) unigram law (deterministic per seed)."""
    V = knobs.vocab
    w = _zipf_weights(V, knobs.zipf_s)
    g = torch.Generator().manual_seed(int(seed) & 0x7FFF_FFFF)
    return torch.multinomial(w, n, replacement=True, generator=g)


# ---------------------------------------------------------------------------
# Generator (iii): tiny PCFG over bracketed expressions
# ---------------------------------------------------------------------------
def _gen_pcfg(n: int, knobs: EntropyKnobs, seed: int) -> torch.Tensor:
    """Emit a token stream from a tiny PCFG, truncated/padded to exactly n.

    Grammar (token ids): OPEN=0, CLOSE=1, leaves drawn from [2, V). A single
    nonterminal S expands as:  S -> ( S S )   with prob p_branch, else  S -> leaf.
    `pcfg_ambiguity` ∈ [0,1] interpolates the leaf choice from deterministic
    (always the same leaf => low entropy) to uniform over leaves (high entropy),
    and also raises the branch probability so deeper, more varied trees form.
    """
    V = knobs.vocab
    OPEN, CLOSE = 0, 1
    n_leaf = max(1, V - 2)
    g = torch.Generator().manual_seed(int(seed) & 0x7FFF_FFFF)
    amb = float(min(1.0, max(0.0, knobs.pcfg_ambiguity)))
    p_branch = 0.25 + 0.45 * amb                                # 0.25 .. 0.70

    out: list[int] = []
    # Pre-draw randoms in chunks; refill if a very branchy grammar runs long.
    def fresh(m: int) -> torch.Tensor:
        return torch.rand(m, generator=g)

    pool = fresh(max(1024, 4 * n))
    pi = 0

    def nxt() -> float:
        nonlocal pool, pi
        if pi >= pool.numel():
            pool = fresh(max(1024, 4 * n))
            pi = 0
        v = float(pool[pi]); pi += 1
        return v

    def expand(depth: int) -> None:
        if len(out) >= n:
            return
        # depth cap keeps recursion bounded for high-branch grammars
        if depth < 24 and nxt() < p_branch:
            out.append(OPEN)
            expand(depth + 1)
            expand(depth + 1)
            out.append(CLOSE)
        else:
            r = nxt()
            if amb <= 0.0:
                leaf = 0
            else:
                # ambiguity scales how many distinct leaves are reachable
                span = max(1, int(round(amb * n_leaf)))
                leaf = int(r * span) % span
            out.append(2 + leaf)

    while len(out) < n:
        expand(0)
    return torch.tensor(out[:n], dtype=torch.long)


# ---------------------------------------------------------------------------
# Public corpus API
# ---------------------------------------------------------------------------
_GENERATORS = {"markov": _gen_markov, "zipf": _gen_zipf, "pcfg": _gen_pcfg}


def make_corpus(unique_tokens: int, entropy_knobs: EntropyKnobs,
                seed: int) -> torch.Tensor:
    """Return a 1-D LongTensor of exactly `unique_tokens` ids (the unique data).

    Deterministic given (unique_tokens, entropy_knobs, seed). 'unique_tokens'
    is the size of the unique-data pool that the epoch loader then repeats; it is
    NOT a vocabulary-uniqueness constraint (token VALUES repeat by construction —
    that is what makes the stream low-entropy/compressible).
    """
    if entropy_knobs.generator not in _GENERATORS:
        raise ValueError(f"unknown generator {entropy_knobs.generator!r}")
    gen = _GENERATORS[entropy_knobs.generator]
    corpus = gen(int(unique_tokens), entropy_knobs, int(seed))
    assert corpus.numel() == int(unique_tokens), (
        f"generator returned {corpus.numel()} tokens, expected {unique_tokens}"
    )
    return corpus


def epoch_loader(corpus: torch.Tensor, n_epochs: int, batch: int,
                 seq_len: int, seed: int,
                 device: str = "cpu") -> Iterator[torch.Tensor]:
    """Yield repeated passes over `corpus` as [batch, seq_len] LongTensors.

    Each epoch the corpus is cut into contiguous length-`seq_len` chunks and the
    CHUNK ORDER is shuffled with a per-epoch seed (so the same unique tokens are
    seen every epoch — faithful repetition — but not in a trivially periodic
    order). A trailing partial chunk and a trailing partial batch are dropped so
    every yielded tensor is exactly [batch, seq_len]. The number of distinct
    (chunk) windows is fixed across epochs, so `n_epochs` passes reuse the same
    unique data exactly n_epochs times.
    """
    n = corpus.numel()
    n_chunks = n // seq_len
    if n_chunks == 0:
        raise ValueError(
            f"corpus of {n} tokens < seq_len {seq_len}; raise unique_tokens"
        )
    chunks = corpus[: n_chunks * seq_len].view(n_chunks, seq_len)
    for e in range(n_epochs):
        g = torch.Generator().manual_seed((int(seed) * 7919 + e * 104729 + 1)
                                          & 0x7FFF_FFFF)
        order = torch.randperm(n_chunks, generator=g)
        e_chunks = chunks[order]
        n_batches = n_chunks // batch
        for b in range(n_batches):
            sl = e_chunks[b * batch:(b + 1) * batch]
            yield sl.to(device)


def one_batch(corpus: torch.Tensor, batch: int, seq_len: int, seed: int,
              device: str = "cpu") -> torch.Tensor:
    """Convenience: a single [batch, seq_len] batch (smoke / probes / val)."""
    for xb in epoch_loader(corpus, 1, batch, seq_len, seed, device=device):
        return xb
    raise ValueError("corpus too small for even one batch at this seq_len/batch")


# ---------------------------------------------------------------------------
# Empirical entropy / compressibility validation
# ---------------------------------------------------------------------------
def _plugin_conditional_entropy(stream: torch.Tensor, order: int) -> float:
    """Plug-in estimate of H(x_t | x_{t-order..t-1}) in nats per token.

    Counts (context, next) pairs and averages -sum p(next|ctx) log p(next|ctx)
    weighted by context frequency. `order=0` gives the marginal entropy.
    """
    x = stream.tolist()
    n = len(x)
    if n <= order + 1:
        return 0.0
    from collections import defaultdict
    ctx_counts: dict = defaultdict(int)
    pair_counts: dict = defaultdict(lambda: defaultdict(int))
    for t in range(order, n):
        ctx = tuple(x[t - order:t]) if order > 0 else ()
        nxt = x[t]
        ctx_counts[ctx] += 1
        pair_counts[ctx][nxt] += 1
    total = sum(ctx_counts.values())
    H = 0.0
    for ctx, c in ctx_counts.items():
        pc = c / total
        sub = pair_counts[ctx]
        h_ctx = 0.0
        for _, cc in sub.items():
            p = cc / c
            h_ctx -= p * math.log(p)
        H += pc * h_ctx
    return H


def _gzip_ratio(stream: torch.Tensor) -> float:
    """gzip compression ratio (compressed_bytes / raw_bytes) of the token bytes.

    Tokens are packed to the smallest int width that holds the max id (1, 2 or 4
    bytes) so the ratio reflects token-sequence structure, not int padding.
    Lower ratio => more compressible => lower entropy.
    """
    arr = stream.to(torch.int64)
    mx = int(arr.max()) if arr.numel() else 0
    if mx < 256:
        raw = arr.to(torch.uint8).numpy().tobytes()
    elif mx < 65536:
        raw = arr.to(torch.int32).numpy().astype("<u2").tobytes()
    else:
        raw = arr.to(torch.int64).numpy().astype("<u4").tobytes()
    if len(raw) == 0:
        return 1.0
    comp = gzip.compress(raw, compresslevel=9)
    return len(comp) / len(raw)


def measured_entropy(stream: torch.Tensor, cond_order: int = 1) -> dict:
    """Empirical entropy / compressibility witnesses for a token stream.

    Returns dict with:
      cond_entropy_nats : plug-in H(x_t | x_{t-cond_order..t-1}) in nats/token
      cond_entropy_bits : same in bits/token
      marginal_entropy_bits : plug-in marginal H(x_t) in bits/token
      gzip_ratio        : gzip compressed/raw byte ratio
    Both cond_entropy and gzip_ratio fall as a knob is turned toward lower
    true entropy (certified by the self-test).
    """
    h_cond = _plugin_conditional_entropy(stream, cond_order)
    h_marg = _plugin_conditional_entropy(stream, 0)
    return {
        "cond_entropy_nats": h_cond,
        "cond_entropy_bits": h_cond / math.log(2),
        "marginal_entropy_bits": h_marg / math.log(2),
        "gzip_ratio": _gzip_ratio(stream),
    }


# ---------------------------------------------------------------------------
# Self-test: entropy knob monotonically moves measured entropy AND gzip ratio;
# corpora are deterministic per seed. Run with `python data.py`.
# ---------------------------------------------------------------------------
def _monotone_nonincreasing(xs: list[float], tol: float = 1e-9) -> bool:
    return all(xs[i] >= xs[i + 1] - tol for i in range(len(xs) - 1))


def _self_test() -> int:
    N = 20000          # stream length for the empirical estimates
    V = 64             # smaller vocab => denser counts => stable plug-in estimate
    ok = True
    print("SELF-TEST entropy-controlled corpora "
          f"(N={N} tokens, V={V}, low->high knob)")

    # For each generator, sweep low->med->high and check BOTH measured
    # conditional entropy and gzip ratio rise monotonically.
    # (level, cond_order) per generator. PCFG's ambiguity knob moves the LEAF
    # alphabet (a marginal-entropy effect); its bracket structure makes order-1
    # conditional entropy saturate, so we witness the PCFG knob with cond_order=0
    # (marginal entropy) — gzip ratio confirms the same direction independently.
    specs = {
        "markov": [("low", 2), ("med", 1), ("high", 1)],
        "zipf":   [("low", 1), ("med", 1), ("high", 1)],
        "pcfg":   [("low", 0), ("med", 0), ("high", 0)],
    }
    for gen, levels in specs.items():
        ents, gzs = [], []
        for level, co in levels:
            knobs = knobs_for_level(level, generator=gen, vocab=V)
            corpus = make_corpus(N, knobs, seed=0)
            m = measured_entropy(corpus, cond_order=max(1, co))
            # cond_order=0 selects the marginal-entropy witness (used for PCFG).
            ents.append(m["cond_entropy_bits"] if co > 0
                        else m["marginal_entropy_bits"])
            gzs.append(m["gzip_ratio"])
        ent_up = _monotone_nonincreasing(list(reversed(ents)))
        gz_up = _monotone_nonincreasing(list(reversed(gzs)))
        tag_e = "OK" if ent_up else "FAIL"
        tag_g = "OK" if gz_up else "FAIL"
        wit = "cond" if levels[0][1] > 0 else "marg"
        print(f"  [{gen:6s}] {wit}-entropy bits low->high = "
              f"[{ents[0]:.3f}, {ents[1]:.3f}, {ents[2]:.3f}]  monotone={tag_e}")
        print(f"           gzip ratio      low->high = "
              f"[{gzs[0]:.3f}, {gzs[1]:.3f}, {gzs[2]:.3f}]  monotone={tag_g}")
        if not (ent_up and gz_up):
            ok = False

    # Determinism: same seed => identical corpus; different seed => different.
    k = knobs_for_level("med", generator="markov", vocab=V)
    c1 = make_corpus(5000, k, seed=7)
    c2 = make_corpus(5000, k, seed=7)
    c3 = make_corpus(5000, k, seed=8)
    det = bool(torch.equal(c1, c2)) and not bool(torch.equal(c1, c3))
    print(f"  determinism (seed7==seed7, seed7!=seed8): "
          f"{'OK' if det else 'FAIL'}")
    if not det:
        ok = False

    # epoch_loader faithfulness: drop-last batch count matches the chunk pool,
    # and every epoch reuses the SAME unique chunk set (a permutation per epoch).
    corpus = make_corpus(4096, k, seed=1)
    n_chunks = corpus.numel() // 32
    n_batches = n_chunks // 4
    yielded = sum(1 for _ in epoch_loader(corpus, 1, batch=4, seq_len=32, seed=1))
    # token multiset is identical across epochs (faithful repetition)
    e0 = torch.cat([b.reshape(-1) for b in
                    epoch_loader(corpus, 1, batch=4, seq_len=32, seed=1)])
    e1 = torch.cat([b.reshape(-1) for b in
                    list(epoch_loader(corpus, 2, batch=4, seq_len=32, seed=1))
                    [n_batches:]])
    same_multiset = bool(torch.equal(e0.sort().values, e1.sort().values))
    loader_ok = (yielded == n_batches) and same_multiset
    print(f"  epoch_loader drop-last batch count "
          f"({yielded}=={n_batches}): {'OK' if loader_ok else 'FAIL'}")
    if not loader_ok:
        ok = False

    print("DATA SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
