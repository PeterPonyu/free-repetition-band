# Fine-grid crossings (all 9 cells) + med/low 12-seed audit (p1_e1b)

phi = 0.0283; floors from pooled archive (same convention as rfree_two_convention.py). New rungs (p1_e1a) = 3 fresh seeds (20-22); crossings from the pooled per-rung medians (archive + Sec-P4 fine grid + new runs).

| cell | eps_rel | excess(6) | excess(8) | crossing (abs) | crossing (rel) | new data |
|---|---|---|---|---|---|---|
| small/low | 0.0115 | 0.0200 | 0.0398 | (10, 12] | (2, 4] | e1a |
| small/med | 0.0500 | 0.0143 | 0.0259 | (10, 12] | (10, 12] | e1a |
| small/high | 0.1164 | 0.0166 | 0.0462 | (8, 10] | (10, 12] | - |
| med/low | 0.0108 | 0.0287 | 0.0484 | (8, 10] | (4, 6] | e1a |
| med/med | 0.0500 | 0.0272 | 0.0585 | (6, 8] | (6, 8] | - |
| med/high | 0.1162 | 0.0512 | 0.1338 | (4, 6] | (6, 8] | e1a |
| large/low | 0.0105 | 0.0209 | 0.0386 | (8, 10] | (4, 6] | - |
| large/med | 0.0500 | 0.0395 | 0.0974 | (6, 8] | (6, 8] | e1a |
| large/high | 0.1162 | 0.0735 | 0.2308 | (4, 6] | (6, 8] | - |

e1b med/low n=10, 12 fresh seeds: 12/12 over 0.05 nats; median +0.0731 (range +0.0678..+0.1014); archived n=3 median +0.0776.
