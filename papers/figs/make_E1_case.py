"""
Render E1_case.png — case study figure for paper E1.
Cell: med/med (medium capacity, medium entropy) from results/figures-013/repeat_verdicts.json.
Two subplots: (left) excess val loss vs n, (right) canary gap vs n.
Source file: experiments/results/figures-013/repeat_verdicts.json (repo-relative)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- Data (read from repeat_verdicts.json, cell med/med) ---
n_vals = [1, 2, 4, 10, 20, 40]
excess  = [0.0, 0.0033, 0.0141, 0.1358, 1.6454, 3.9072]
canary  = [-0.0262, 0.0306, 0.0463, 0.1619, 0.9736, 2.1923]
free_eps = 0.05      # from repeat_verdicts.json: free_eps_nats
canary_eps = 0.10    # from repeat_verdicts.json: canary_eps
R_free_n = 4         # R_free_epochs for med/med
damage_onset = 10    # decay_onset
mem_onset = 10       # mem_onset

fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8), constrained_layout=True)

# ---- Left panel: excess validation loss ----
ax = axes[0]
ax.plot(n_vals, excess, "o-", color="#1f77b4", linewidth=2, markersize=7,
        label="excess val loss")
ax.axhline(free_eps, color="#2ca02c", linestyle="--", linewidth=1.4,
           label=r"$\varepsilon_{\rm free}=0.05$ nats")
# Shade the "free" region n <= R_free
ax.axvspan(0.5, R_free_n + 0.3, alpha=0.10, color="#2ca02c")
# Mark the boundary
ax.axvline(R_free_n, color="#2ca02c", linestyle=":", linewidth=1.4,
           label=f"$R_{{\\rm free}}={R_free_n}$")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xticks(n_vals)
ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax.set_ylim(3e-3, 10)
ax.set_xlabel("Epoch count $n$", fontsize=11)
ax.set_ylabel("Excess val loss (nats)", fontsize=11)
ax.set_title("(a)", loc="left", fontsize=10)
ax.legend(fontsize=8.5, loc="upper left")
# Annotate exact values for key n points
for ni, ei in zip(n_vals, excess):
    if ni in (4, 10):
        ax.annotate(f"{ei:.4f}", (ni, ei),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=7.5, color="#1f77b4")

# ---- Right panel: canary memorization gap ----
ax2 = axes[1]
ax2.plot(n_vals, canary, "s-", color="#d62728", linewidth=2, markersize=7,
         label="canary gap")
ax2.axhline(canary_eps, color="#ff7f0e", linestyle="--", linewidth=1.4,
            label=r"$\varepsilon_{\rm canary}=0.10$")
ax2.axvline(mem_onset, color="#ff7f0e", linestyle=":", linewidth=1.4,
            label=f"mem onset $n={mem_onset}$")
ax2.axvspan(0.5, R_free_n + 0.3, alpha=0.10, color="#2ca02c",
            label="free zone")
ax2.set_xscale("log")
ax2.set_xticks(n_vals)
ax2.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax2.set_xlabel("Epoch count $n$", fontsize=11)
ax2.set_ylabel("Canary memorization gap", fontsize=11)
ax2.set_title("(b)", loc="left", fontsize=10)
ax2.legend(fontsize=8.5, loc="upper left")

out_path = Path(__file__).resolve().parent / "E1_case.png"
plt.savefig(out_path, dpi=180, bbox_inches="tight")
print(f"Saved {out_path.name}")
