# Canary-threshold sensitivity of the memorization-onset ordering

Decay onset fixed at the declared 0.05-nat excess criterion; memorization onset recomputed at eps_can in {0.05, 0.10, 0.20} nats. Fine = pooled rung set (half-octave where covered); coarse = n in {1,2,4,10,20,40} (the paper's Table 4 convention).

| eps_can | fine leads-or-coincides | fine lags | coarse coincide | mem onset at n=1 |
|---|---|---|---|---|
| 0.05 | 9/9 | 0/9 | 5/9 | 0 |
| 0.10 | 9/9 | 0/9 | 8/9 | 0 |
| 0.20 | 3/9 | 6/9 | 6/9 | 0 |

Per-cell onsets (fine): decay | mem@0.05 / mem@0.10 / mem@0.20

- small/low: decay 12 | 4 (leads) / 8 (leads) / 16 (lags); gap(n=1)=0.0325
- small/med: decay 12 | 10 (leads) / 12 (coincides) / 16 (lags); gap(n=1)=-0.0251
- small/high: decay 10 | 6 (leads) / 8 (leads) / 10 (coincides); gap(n=1)=-0.013
- med/low: decay 10 | 6 (leads) / 8 (leads) / 20 (lags); gap(n=1)=0.0211
- med/med: decay 8 | 8 (coincides) / 8 (coincides) / 12 (lags); gap(n=1)=-0.0262
- med/high: decay 6 | 6 (coincides) / 6 (coincides) / 8 (lags); gap(n=1)=-0.0148
- large/low: decay 10 | 6 (leads) / 8 (leads) / 12 (lags); gap(n=1)=0.0222
- large/med: decay 8 | 4 (leads) / 6 (leads) / 8 (coincides); gap(n=1)=-0.0248
- large/high: decay 6 | 4 (leads) / 6 (coincides) / 6 (coincides); gap(n=1)=-0.0139
