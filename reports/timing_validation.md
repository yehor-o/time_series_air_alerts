# Timing model: when in the next 7 days? (validation)

One LightGBM predicts, for each 3-hour Kyiv-time block of the next 7 days, the chance that a new alert starts in it. Forecasts issued at 00:00 and 12:00 Kyiv. Last 2 validation weeks (Aug 30 – Sep 12 2026); the test period is untouched. **Pattern rule** = share of the last 14 days with a new alert in the same clock block. Skill = Brier improvement over the pattern rule.

## Raion

All 56 blocks:

```
                                          Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                         
pattern rule (same block, last 14 days)  0.1787    0.5972   0.7713  0.5392             -0.0000
LightGBM timing model                    0.1801    0.5327   0.7844  0.5797             -0.0078
```

By how far ahead (day 1 = next 24 hours):

```
       pattern AUC  model ROC-AUC  model skill vs pattern  model Brier
model                                                                 
day 1        0.759          0.803                   0.084        0.154
day 2        0.765          0.782                   0.025        0.170
day 3        0.773          0.776                  -0.019        0.182
day 4        0.779          0.783                  -0.042        0.190
day 5        0.774          0.783                  -0.034        0.188
day 6        0.755          0.759                  -0.037        0.195
day 7        0.705          0.726                  -0.005        0.205
```

## Oblast

All 56 blocks:

```
                                          Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                         
pattern rule (same block, last 14 days)  0.1811    0.6044   0.7907  0.5849              0.0000
LightGBM timing model                    0.1820    0.5428   0.7966  0.6014             -0.0052
```

By how far ahead (day 1 = next 24 hours):

```
       pattern AUC  model ROC-AUC  model skill vs pattern  model Brier
model                                                                 
day 1        0.769          0.804                   0.102        0.156
day 2        0.778          0.792                   0.038        0.172
day 3        0.791          0.793                  -0.019        0.186
day 4        0.801          0.794                  -0.049        0.195
day 5        0.799          0.794                  -0.048        0.193
day 6        0.782          0.771                  -0.065        0.200
day 7        0.729          0.718                  -0.063        0.214
```
