# S-E1 real-text band — recomputed verdicts (48/48 runs)

| cell | params | H floor | eps_rel | R_abs | R_rel | decay@abs | mem@0.05/0.10/0.20 (growth) | ordering@0.10 |
|---|---|---|---|---|---|---|---|---|
| fineweb/xl | 30.0M | 1.181 | 0.033 | 6 (seeds 8/6) | 6 (seeds 6/6) | 8 | 4/4/6 | leads |
| fineweb/xxl | 57.2M | 1.105 | 0.031 | 4 (seeds 4/4) | 2 (seeds 2/4) | 6 | 2/4/6 | leads |
| code/xl | 30.0M | 0.875 | 0.025 | 1 (seeds 1/1) | 1 (seeds 1/1) | 2 | 2/4/4 | lags |
| code/xxl | 57.2M | 0.888 | 0.025 | 2 (seeds 2/2) | 1 (seeds 1/1) | 4 | 2/4/4 | coincides |

Median excess per epoch:
- fineweb/xl: excess={1: 0.0, 2: -0.0181, 4: -0.0002, 6: 0.0202, 8: 0.0581, 10: 0.1169, 16: 0.445} gap_growth={1: 0.0, 2: 0.0472, 4: 0.1671, 6: 0.2835, 8: 0.3283, 10: 0.596, 16: 1.036}
- fineweb/xxl: excess={1: 0.0, 2: 0.0107, 4: 0.0334, 6: 0.0586, 8: 0.0974, 10: 0.1717, 16: 0.5781} gap_growth={1: 0.0, 2: 0.0568, 4: 0.1807, 6: 0.301, 8: 0.4142, 10: 0.7052, 16: 1.2694}
- code/xl: excess={1: 0.0, 2: 0.0907, 4: 0.1523, 10: 0.6046, 16: 1.3001} gap_growth={1: 0.0, 2: 0.0658, 4: 0.2814, 10: 0.688, 16: 0.9395}
- code/xxl: excess={1: 0.0, 2: 0.0401, 4: 0.1139, 10: 0.6709, 16: 1.47} gap_growth={1: 0.0, 2: 0.0605, 4: 0.2457, 10: 0.6015, 16: 0.9457}

INCREMENTAL cross-check: all per-seed excess values agree to <5e-4.
