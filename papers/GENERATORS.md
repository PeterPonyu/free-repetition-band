# Figure generators (Paper E1)

Rebuild vector figures from this warehouse with the R → TikZ/PDF pipeline documented in `papers/figs/PIPELINE.md`.

Primary scripts:

- `figs/make_E1_figs_r.R` — repeat, grid, scale, case
- `figs/make_E1_new_figs_r.R` — large-completion, capxl, scale-band, within-run
- `figs/make_E1_exposure_control_r.R` — exposure-matched control
- `figs/make_evidence_figures_r.R` — capacity-bridge
- `figs/make_E1_landscape.py` — landscape schematic
- `figs/figpreamble.tex` — byte-stable `\figtikz` / heatmap graphicspath

Compiled `figs/tex/` and `figs/vec/` are gitignored build products. Portals consume `FIGURE-INDEX.json` and `figs/summaries/*.json`, never PeerJ `FigureN.pdf`.
