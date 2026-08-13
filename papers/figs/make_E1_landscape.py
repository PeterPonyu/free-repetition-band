"""Paper E1 opener: the free-repetition (R_free) landscape across scale.
Single rendered PNG. Verified sources:
  Muennighoff et al. 2023 (2305.16264): R_free ~4 "nearly free"; repeated-token half-life R*_D~15
    (~16 epochs); up to 8.7B params, 900B tokens.
  Yan et al. 2025 (2511.13421): tolerable repetitions grow ~Theta(log N) with dataset size.
  Charton & Kempe 2024 (2410.07041): 22-35M-param algorithmic transformers; repetition is net-helpful.
  This work: synthetic Markov grid R_free 4-10 (0.5-10M params); WikiText byte bridge R_free=4 (~5M).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7.4, 3.9))

# half-life ceiling and free-floor reference
ax.axhline(15.4, color="#7f7f7f", ls="--", lw=1.0)
ax.text(1.3e9, 15.9, "Muennighoff half-life $R^{*}_{D}\\approx15$ ($\\approx16$ ep.)",
        fontsize=8, color="#7f7f7f", va="bottom", ha="right")
ax.axhspan(0, 4, color="#2ca02c", alpha=0.06)
ax.text(1.6e5, 4.25, "$\\approx4$-epoch free floor", fontsize=8, color="#2ca02c", va="bottom")

# our synthetic grid: small-cap corner =10, larger cells =4
ax.scatter([2.5e6], [10], s=120, marker="s", color="#d62728", edgecolor="white",
           linewidth=1.0, zorder=4, label="This work: synthetic (small-cap corner)")
ax.scatter([5.6e6, 9.9e6], [4, 4], s=90, marker="s", color="#d62728", alpha=0.75,
           edgecolor="white", linewidth=1.0, zorder=4, label="This work: synthetic (larger cells)")
ax.scatter([5e6], [4], s=120, marker="^", color="#ff7f0e", edgecolor="white",
           linewidth=1.0, zorder=4, label="This work: WikiText-103 byte bridge")
# Muennighoff anchor
ax.scatter([8.7e9], [4], s=150, marker="o", color="#1f77b4", edgecolor="white",
           linewidth=1.0, zorder=4, label="Muennighoff et al. 2023 (LLM)")

# Charton band annotation (different axis: repetition helps, accuracy)
ax.annotate("Charton \\& Kempe 2024 (22--35M):\nrepetition net-helpful at fixed steps",
            (3e7, 12.4), fontsize=7.6, color="#555555", ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="#f5f5f5", ec="#cccccc", lw=0.6))
# Yan trend arrow
ax.annotate("", xy=(7e9, 12.5), xytext=(3e8, 6.5),
            arrowprops=dict(arrowstyle="->", color="#9467bd", lw=1.4))
ax.text(7e9, 12.8, "Yan et al. 2025:\n$R_{\\mathrm{free}}\\!\\sim\\!\\Theta(\\log N)$",
        fontsize=7.8, color="#9467bd", ha="right", va="bottom")

ax.set_xscale("log")
ax.set_xlim(1.3e5, 3e10)
ax.set_ylim(0, 18)
ax.set_xlabel("model scale (parameters, log)")
ax.set_ylabel("$R_{\\mathrm{free}}$ (free-repetition epochs)")
ax.set_title("The free-repetition landscape: a $\\approx4$-epoch floor across six orders of magnitude",
             fontsize=10)
ax.legend(fontsize=7.6, loc="lower center", bbox_to_anchor=(0.5, 0.0), framealpha=0.92)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.tight_layout()
fig.savefig("E1_landscape.png", dpi=200)
print("wrote E1_landscape.png")
