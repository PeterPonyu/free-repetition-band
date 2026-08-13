# Figure generators (E1 warehouse)

Canonical R/Python generators live in the lab `papers/figs/` pipeline
(`PIPELINE.md`). This GitHub tree stores the **pointer contract**
(`FIGURE-INDEX.json` + summaries), not compiled `tex/` or `vec/` PDFs.

| id | generator | notes |
|---|---|---|
| E1_landscape | `figs/make_E1_landscape.py` | documented schematic (`*_landscape`) |
| E1_scheme | this file, `#scheme` | documented schematic (`*_scheme`); PeerJ Fig. 2 |
| E1_repeat | `figs/make_E1_figs_r.R` | |
| E1_large_completion | `figs/make_E1_new_figs_r.R` | |
| E1_capxl | `figs/make_E1_new_figs_r.R` | |
| E1_grid | `figs/make_E1_figs_r.R` | |
| E1_scale | `figs/make_E1_figs_r.R` | |
| E1_scale_band | `figs/make_E1_new_figs_r.R` | optional SVG preview seeded |
| E1_capacity_bridge | `figs/make_evidence_figures_r.R` | |
| E1_case | `figs/make_E1_figs_r.R` | |
| E1_within_run | `figs/make_E1_new_figs_r.R` | |
| E1_exposure_control | `figs/make_E1_exposure_control_r.R` | canon-only; no PeerJ `FigureN.pdf` |

## scheme

`E1_scheme` is a documented schematic (study-design plate). Rebuild from the
lab figure pipeline; do not commit `Figure2.pdf` next to `main.tex`.
