# S-E1 incremental summary — 2026-07-18T03:40:11

Completed runs: 48/48 (xl 24/24, xxl 24/24, xxxl CANCELLED by user 2026-07-17)

Conventions: excess vs own-sweep n=1; R_free = max grid n with excess<0.05 nats ('*' = grid incomplete, value may still move); decay@/mem@ = first grid n crossing 0.05 excess / 0.10 gap.

## Per-sweep verdicts

- `code/xl/50` [5/5 rungs]: R_free=1 decay@2 mem@4 
    excess={1: 0.0, 2: 0.0889, 4: 0.1501, 10: 0.6139, 16: 1.2707}
    gap={1: -0.136, 2: -0.063, 4: 0.1589, 10: 0.5308, 16: 0.7788}
- `code/xl/51` [5/5 rungs]: R_free=1 decay@2 mem@4 
    excess={1: 0.0, 2: 0.0925, 4: 0.1544, 10: 0.5953, 16: 1.3295}
    gap={1: -0.1355, 2: -0.077, 4: 0.1324, 10: 0.5737, 16: 0.8286}
- `code/xxl/50` [5/5 rungs]: R_free=2 decay@4 mem@4 COINCIDE
    excess={1: 0.0, 2: 0.0356, 4: 0.108, 10: 0.6667, 16: 1.4578}
    gap={1: -0.0885, 2: 0.0021, 4: 0.1664, 10: 0.5049, 16: 0.8608}
- `code/xxl/51` [5/5 rungs]: R_free=2 decay@4 mem@4 COINCIDE
    excess={1: 0.0, 2: 0.0445, 4: 0.1198, 10: 0.6752, 16: 1.4822}
    gap={1: -0.0998, 2: -0.0695, 4: 0.1367, 10: 0.5097, 16: 0.8424}
- `fineweb/xl/50` [7/7 rungs]: R_free=8 decay@10 mem@4 
    excess={1: 0.0, 2: -0.0173, 4: -0.0179, 6: 0.0121, 8: 0.0473, 10: 0.1086, 16: 0.3654}
    gap={1: 0.0071, 2: 0.059, 4: 0.202, 6: 0.271, 8: 0.2822, 10: 0.6248, 16: 0.9154}
- `fineweb/xl/51` [7/7 rungs]: R_free=6 decay@8 mem@4 
    excess={1: 0.0, 2: -0.0188, 4: 0.0175, 6: 0.0283, 8: 0.0688, 10: 0.1251, 16: 0.5246}
    gap={1: 0.0172, 2: 0.0596, 4: 0.1566, 6: 0.3202, 8: 0.3987, 10: 0.5913, 16: 1.1808}
- `fineweb/xxl/50` [7/7 rungs]: R_free=4 decay@6 mem@4 
    excess={1: 0.0, 2: 0.0168, 4: 0.0383, 6: 0.059, 8: 0.0982, 10: 0.1668, 16: 0.5389}
    gap={1: -0.0104, 2: 0.0475, 4: 0.18, 6: 0.2754, 8: 0.3593, 10: 0.7183, 16: 1.2341}
- `fineweb/xxl/51` [7/7 rungs]: R_free=4 decay@6 mem@4 
    excess={1: 0.0, 2: 0.0047, 4: 0.0286, 6: 0.0582, 8: 0.0966, 10: 0.1766, 16: 0.6172}
    gap={1: -0.0038, 2: 0.052, 4: 0.1673, 6: 0.3126, 8: 0.4548, 10: 0.6779, 16: 1.2905}

## TRIM-DECISION: RESOLVED BY USER (2026-07-17) — stop at 57M; the xxxl (158M / 400M-byte) block was cancelled before any xxxl cell started. The evidence below is the complete xl+xxl record this decision rests on.


- fineweb/xl/50: R_free=8 decay@10 mem@4  excess={1: 0.0, 2: -0.0173, 4: -0.0179, 6: 0.0121, 8: 0.0473, 10: 0.1086, 16: 0.3654} gap={1: 0.0071, 2: 0.059, 4: 0.202, 6: 0.271, 8: 0.2822, 10: 0.6248, 16: 0.9154}
- fineweb/xl/51: R_free=6 decay@8 mem@4  excess={1: 0.0, 2: -0.0188, 4: 0.0175, 6: 0.0283, 8: 0.0688, 10: 0.1251, 16: 0.5246} gap={1: 0.0172, 2: 0.0596, 4: 0.1566, 6: 0.3202, 8: 0.3987, 10: 0.5913, 16: 1.1808}
- fineweb/xxl/50: R_free=4 decay@6 mem@4  excess={1: 0.0, 2: 0.0168, 4: 0.0383, 6: 0.059, 8: 0.0982, 10: 0.1668, 16: 0.5389} gap={1: -0.0104, 2: 0.0475, 4: 0.18, 6: 0.2754, 8: 0.3593, 10: 0.7183, 16: 1.2341}
- fineweb/xxl/51: R_free=4 decay@6 mem@4  excess={1: 0.0, 2: 0.0047, 4: 0.0286, 6: 0.0582, 8: 0.0966, 10: 0.1766, 16: 0.6172} gap={1: -0.0038, 2: 0.052, 4: 0.1673, 6: 0.3126, 8: 0.4548, 10: 0.6779, 16: 1.2905}
- code/xl/50: R_free=1 decay@2 mem@4  excess={1: 0.0, 2: 0.0889, 4: 0.1501, 10: 0.6139, 16: 1.2707} gap={1: -0.136, 2: -0.063, 4: 0.1589, 10: 0.5308, 16: 0.7788}
- code/xl/51: R_free=1 decay@2 mem@4  excess={1: 0.0, 2: 0.0925, 4: 0.1544, 10: 0.5953, 16: 1.3295} gap={1: -0.1355, 2: -0.077, 4: 0.1324, 10: 0.5737, 16: 0.8286}
- code/xxl/50: R_free=2 decay@4 mem@4 COINCIDE excess={1: 0.0, 2: 0.0356, 4: 0.108, 10: 0.6667, 16: 1.4578} gap={1: -0.0885, 2: 0.0021, 4: 0.1664, 10: 0.5049, 16: 0.8608}
- code/xxl/51: R_free=2 decay@4 mem@4 COINCIDE excess={1: 0.0, 2: 0.0445, 4: 0.1198, 10: 0.6752, 16: 1.4822} gap={1: -0.0998, 2: -0.0695, 4: 0.1367, 10: 0.5097, 16: 0.8424}

Band at 30M+57M real text: R_free values [8, 6, 4, 4, 1, 1, 2, 2] (range 1-8); 4/8 inside the paper's 4-10 band; onset coincidence 2/8.

What the 160M rung adds: extends the capacity span 30M->158M (5.3x, cumulative 2.5M->158M = 63x vs the paper's 23x capxl leg) on REAL text at the 400M-byte budget. If the xl/xxl values above already sit in-band and coincide, xxxl is the capacity-invariance confirmation rung (the strongest anti-'Markov-family constant' leg); if xl vs xxl shows a trend, xxxl resolves its direction. Cost of the remaining xxxl block: ~98 GPU-h (~49 h wall on 2 GPUs). Trimming to {2,4,10} x fineweb only would cut that to ~24 GPU-h; full trim saves the whole 98.
