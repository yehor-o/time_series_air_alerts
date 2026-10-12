# Final test results (scored once)

Test period: **2026-09-13 00:00 UTC → 2026-10-11 10:00 UTC** (28.4 days). Models trained once on data before the test start; nothing in the test period was used for any choice. Pinned data: Vadimkin `bf0c323c`, JustJimer `7abc556b`.

## Raion (119 units)

### New alert within 1h

Base rate: 0.155 (81,039 unit-hours).

```
                                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
baseline: same hour, last 14 days  0.1222    0.4507   0.7326  0.2896              0.0000
baseline: persistence              0.1340    0.4459   0.5465  0.1738             -0.0965
logistic regression                0.1058    0.3418   0.8134  0.4569              0.1340
LightGBM (chosen)                  0.1041    0.3350   0.8218  0.4805              0.1478
LightGBM + @war_monitor            0.1046    0.3370   0.8187  0.4767              0.1438
LightGBM + @kpszsu                 0.1048    0.3369   0.8192  0.4733              0.1424
```

Chosen model by time of day:

```
                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
day (06-22 Kyiv)    0.105     0.338    0.830   0.510               0.150
night (22-06 Kyiv)  0.102     0.329    0.804   0.416               0.143
```

Chosen model by test week:

```
        Brier  ROC-AUC  skill vs same-hour
week 1  0.103    0.799               0.115
week 2  0.104    0.848               0.176
week 3  0.098    0.820               0.145
week 4  0.111    0.818               0.155
week 5  0.125    0.803               0.106
```

Calibration (chosen model):

```
                 rows  predicted  observed
bin                                       
(-0.001, 0.05]  28758      0.016     0.020
(0.05, 0.1]     12339      0.074     0.084
(0.1, 0.2]      17156      0.144     0.146
(0.2, 0.3]       8747      0.247     0.240
(0.3, 0.4]       6562      0.347     0.346
(0.4, 0.5]       3956      0.445     0.468
(0.5, 0.6]       2102      0.545     0.581
(0.6, 0.7]        798      0.638     0.643
(0.7, 0.8]        237      0.744     0.764
(0.8, 0.9]        344      0.846     0.927
(0.9, 1.0]         40      0.919     1.000
```

### New alert within 3h

Base rate: 0.360 (80,801 unit-hours).

```
                                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
baseline: same hour, last 14 days  0.2380    0.9206   0.7593  0.5878              0.0000
baseline: persistence              0.2142    0.6181   0.6785  0.4942              0.0998
logistic regression                0.1616    0.4829   0.8263  0.7097              0.3209
LightGBM (chosen)                  0.1572    0.4742   0.8355  0.7289              0.3393
LightGBM + @war_monitor            0.1578    0.4756   0.8344  0.7283              0.3369
LightGBM + @kpszsu                 0.1605    0.4819   0.8287  0.7136              0.3256
```

Chosen model by time of day:

```
                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
day (06-22 Kyiv)    0.154     0.466    0.847   0.757               0.357
night (22-06 Kyiv)  0.164     0.491    0.811   0.663               0.303
```

Chosen model by test week:

```
        Brier  ROC-AUC  skill vs same-hour
week 1  0.167    0.809               0.327
week 2  0.145    0.862               0.391
week 3  0.151    0.844               0.283
week 4  0.166    0.825               0.341
week 5  0.155    0.854               0.499
```

Calibration (chosen model):

```
                 rows  predicted  observed
bin                                       
(-0.001, 0.05]  16462      0.014     0.029
(0.05, 0.1]      4585      0.074     0.100
(0.1, 0.2]       8584      0.151     0.151
(0.2, 0.3]       8495      0.250     0.243
(0.3, 0.4]       8230      0.350     0.353
(0.4, 0.5]       7787      0.450     0.459
(0.5, 0.6]       8517      0.551     0.557
(0.6, 0.7]       8275      0.648     0.665
(0.7, 0.8]       5583      0.745     0.752
(0.8, 0.9]       3127      0.845     0.866
(0.9, 1.0]       1156      0.937     0.967
```

### Duration of the next alert (starting within 3h), as a range

29,194 test cases; true durations: median 45 min, middle half 24–96 min. Ideal coverage of a 25–75% range: 50%.

```
                             median abs error of the middle value (min)  pinball loss  true duration inside the 25-75% range  average range width (min)
baseline: last 10 alerts                                         28.042        38.828                                  0.425                     98.378
LightGBM quantiles (chosen)                                      29.096        36.352                                  0.481                    102.842
```

### Next 24 hours

Number of new alerts (true average 3.90):

```
                                          MAE  median abs error   RMSE  skill vs 7-day average
baseline: same as last 24h              1.876             1.000  2.735                  -0.130
baseline: daily average of last 7 days  1.661             1.143  2.381                   0.000
LightGBM (chosen)                       1.720             1.137  2.526                  -0.036
```

Hours under alert (true average 7.33 h):

```
                                          MAE  median abs error   RMSE  skill vs 7-day average
baseline: same as last 24h              2.170             1.014  3.591                  -0.070
baseline: daily average of last 7 days  2.028             1.092  3.160                   0.000
LightGBM (chosen)                       1.870             0.897  3.058                   0.078
```

### When: new alert in each 3-hour Kyiv block of the next 7 days

Forecasts issued at 00:00 and 12:00 Kyiv inside the test period; 329,868 (unit, issue, block) cases whose block ended before the end of data (later days of the week have fewer cases).

All blocks:

```
                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs pattern
pattern rule        0.1715    0.5499   0.8091  0.6480           -0.0000
timing model alone  0.1795    0.5296   0.8038  0.6556           -0.0464
blend (chosen)      0.1711    0.5281   0.8108  0.6553            0.0025
```

ROC-AUC by lead day:

```
                    day 1  day 2  day 3  day 4  day 5  day 6  day 7
pattern rule        0.813  0.808  0.808  0.807  0.810  0.810  0.807
timing model alone  0.812  0.803  0.801  0.802  0.803  0.805  0.803
blend (chosen)      0.817  0.814  0.813  0.807  0.810  0.810  0.807
```

Brier by lead day:

```
                     day 1   day 2   day 3   day 4   day 5   day 6   day 7
pattern rule        0.1692  0.1723  0.1723  0.1726  0.1707  0.1710  0.1726
timing model alone  0.1714  0.1798  0.1831  0.1836  0.1815  0.1788  0.1788
blend (chosen)      0.1689  0.1712  0.1709  0.1726  0.1707  0.1710  0.1726
```
