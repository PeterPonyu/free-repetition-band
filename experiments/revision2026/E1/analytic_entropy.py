"""E1-T0-2 — exact analytic entropy rates of the three Markov presets.

Computes, from the ACTUAL generator law in experiments/repeated_data/data.py
(NOT the paper's Methods description, which is inaccurate — see evidence note):

  low  : order-2 chain (hashed 2-token context -> one of V=256 rows),
         branching=2, temperature=0.4
  med  : order-1 chain, branching=8, temperature=1.0
  high : order-1 chain, branching=64, temperature=2.0

For order-1 presets the entropy rate is H = sum_i pi_i H(P_i) with pi the
stationary distribution of P (power iteration). For the order-2 preset the
token process is a Markov chain on pairs (x_{t-1}, x_t): next token
c ~ P[cid(a,b)] where cid hashes (b,a); entropy rate =
sum_{(a,b)} pi(a,b) H(P[cid(a,b)]).

Each exact value is cross-checked by a Monte Carlo estimate (mean H(row) over
the contexts visited by a freshly sampled 2M-token stream — an unbiased
estimator using the true law). Also reports the per-window achievable floor
correction for the order-2 preset (the first prediction of each 128-token
window has a 1-token context) and compares against the model-based validation
floors from rfree_two_convention.json.

Output: analytic_entropy.json (+ printed table).
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import torch

sys.path.insert(0, "/home/zeyufu/Desktop/dl-research/experiments/repeated_data")
from data import knobs_for_level, make_corpus, _markov_transition  # noqa: E402

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
V = 256
SEQ_LEN = 128


def row_entropies(P: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -P * np.log(P)
    return np.nan_to_num(t).sum(axis=1)


def transition_matrix(level: str) -> tuple[np.ndarray, int]:
    knobs = knobs_for_level(level, generator="markov", vocab=V)
    g = torch.Generator().manual_seed(knobs.transition_seed)
    P = _markov_transition(knobs, g).double().numpy()
    return P, max(1, knobs.markov_order)


def cid_matrix() -> np.ndarray:
    """cid(a,b) for order-2: hash reads (b, a) = (x_{t-1}, x_{t-2})."""
    a = np.arange(V)[:, None]  # x_{t-2}
    b = np.arange(V)[None, :]  # x_{t-1}
    cid = ((b + 1).astype(np.int64) * 1_000_003 + (a + 1)) & 0x7FFF_FFFF
    return (cid % V).astype(np.int64)  # [a, b]


def stationary_order1(P: np.ndarray, iters=20000, tol=1e-14) -> np.ndarray:
    pi = np.full(V, 1.0 / V)
    for _ in range(iters):
        nxt = pi @ P
        if np.abs(nxt - pi).sum() < tol:
            pi = nxt
            break
        pi = nxt
    return pi / pi.sum()

def stationary_pairs(P: np.ndarray, R: np.ndarray, iters=5000,
                     tol=1e-12) -> np.ndarray:
    """Stationary dist over pairs (a,b); transition (a,b)->(b,c) w.p. P[R[a,b],c]."""
    pi = np.full((V, V), 1.0 / (V * V))
    for it in range(iters):
        nxt = np.zeros_like(pi)
        for b in range(V):
            # pi'[b, :] = sum_a pi[a, b] * P[R[a, b], :]
            nxt[b, :] = pi[:, b] @ P[R[:, b], :]
        delta = np.abs(nxt - pi).sum()
        pi = nxt
        if delta < tol:
            break
    return pi / pi.sum(), it, delta


def mc_entropy(level: str, P: np.ndarray, order: int, n=2_000_000,
               seed=424242) -> float:
    """Unbiased MC: mean row-entropy over contexts visited by a fresh stream."""
    knobs = knobs_for_level(level, generator="markov", vocab=V)
    stream = make_corpus(n, knobs, seed=seed).numpy()
    hrow = row_entropies(P)
    if order == 1:
        ctx = stream[:-1]
        return float(hrow[ctx].mean())
    # order 2: cid from (x_{t-1}, x_{t-2})
    b = stream[1:-1].astype(np.int64)   # x_{t-1}
    a = stream[:-2].astype(np.int64)    # x_{t-2}
    cid = (((b + 1) * 1_000_003 + (a + 1)) & 0x7FFF_FFFF) % V
    return float(hrow[cid].mean())


def main():
    tc = os.path.join(OUT_DIR, "rfree_two_convention.json")
    floors = {}
    if os.path.exists(tc):
        d = json.load(open(tc))
        for cell, c in d["cells"].items():
            floors[cell] = c["H_floor_nats"]

    out = {}
    for level in ["low", "med", "high"]:
        P, order = transition_matrix(level)
        hrow = row_entropies(P)
        rec = {"markov_order": order}
        if order == 1:
            pi = stationary_order1(P)
            H = float(pi @ hrow)
            rec["H_rate_nats"] = H
            rec["window_floor_nats"] = H  # order-1: every position has full ctx
        else:
            R = cid_matrix()
            pi2, iters, delta = stationary_pairs(P, R)
            H = float((pi2 * hrow[R]).sum())
            rec["H_rate_nats"] = H
            rec["pair_iters"] = iters
            rec["pair_delta"] = delta
            # 1-token-context entropy for the first prediction of each window:
            # P(c|b) = sum_a pi(a|b) P[R[a,b], c]
            pib = pi2.sum(axis=0)  # marginal over x_{t-1}=b
            H1 = 0.0
            for b in range(V):
                if pib[b] <= 0:
                    continue
                w = pi2[:, b] / pib[b]
                mix = w @ P[R[:, b], :]
                H1 += pib[b] * float(-(mix[mix > 0] * np.log(mix[mix > 0])).sum())
            rec["H_1ctx_nats"] = H1
            rec["window_floor_nats"] = (H1 + (SEQ_LEN - 2) * H) / (SEQ_LEN - 1)
        rec["H_mc_nats"] = mc_entropy(level, P, order)
        rec["H_rate_bits"] = rec["H_rate_nats"] / math.log(2)
        rec["model_floors_nats"] = {
            cap: floors.get(f"{cap}/{level}") for cap in ["small", "med", "large"]}
        rec["floor_minus_H"] = {
            cap: (round(floors[f"{cap}/{level}"] - rec["window_floor_nats"], 4)
                  if f"{cap}/{level}" in floors else None)
            for cap in ["small", "med", "large"]}
        out[level] = rec
        print(f"[{level}] order={order}  H_rate={rec['H_rate_nats']:.4f} nats "
              f"({rec['H_rate_bits']:.3f} bits)  MC={rec['H_mc_nats']:.4f}  "
              f"window_floor={rec['window_floor_nats']:.4f}")
        print(f"        model floors: {rec['model_floors_nats']}  "
              f"floor-H: {rec['floor_minus_H']}")

    jp = os.path.join(OUT_DIR, "analytic_entropy.json")
    with open(jp, "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"wrote {jp}")


if __name__ == "__main__":
    main()
