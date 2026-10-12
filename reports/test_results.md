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

## Oblast (24 units)

### New alert within 1h

Base rate: 0.197 (16,344 unit-hours).

```
                                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
baseline: same hour, last 14 days  0.1436    0.4992   0.7405  0.3467              0.0000
baseline: persistence              0.1680    0.5433   0.5536  0.2211             -0.1696
logistic regression                0.1206    0.3774   0.8274  0.5278              0.1603
LightGBM (chosen)                  0.1201    0.3767   0.8249  0.5472              0.1640
LightGBM + @war_monitor            0.1194    0.3744   0.8288  0.5541              0.1684
LightGBM + @kpszsu                 0.1200    0.3759   0.8270  0.5445              0.1646
```

Chosen model by time of day:

```
                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
day (06-22 Kyiv)     0.12     0.377    0.832   0.579               0.174
night (22-06 Kyiv)   0.12     0.376    0.811   0.487               0.143
```

Chosen model by test week:

```
        Brier  ROC-AUC  skill vs same-hour
week 1  0.118    0.810               0.130
week 2  0.115    0.853               0.206
week 3  0.118    0.821               0.153
week 4  0.129    0.820               0.171
week 5  0.161    0.778               0.052
```

Calibration (chosen model):

```
                rows  predicted  observed
bin                                      
(-0.001, 0.05]  4396      0.017     0.016
(0.05, 0.1]     2335      0.075     0.078
(0.1, 0.2]      4152      0.146     0.161
(0.2, 0.3]      1900      0.244     0.248
(0.3, 0.4]      1083      0.348     0.343
(0.4, 0.5]       916      0.449     0.486
(0.5, 0.6]       789      0.548     0.579
(0.6, 0.7]       486      0.643     0.673
(0.7, 0.8]       194      0.742     0.742
(0.8, 0.9]        88      0.846     0.898
(0.9, 1.0]         5      0.914     0.800
```

### New alert within 3h

Base rate: 0.429 (16,296 unit-hours).

```
                                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
baseline: same hour, last 14 days  0.2579    0.9476   0.7843  0.6751              0.0000
baseline: persistence              0.2405    0.6745   0.7135  0.5935              0.0677
logistic regression                0.1548    0.4669   0.8524  0.7872              0.4000
LightGBM (chosen)                  0.1543    0.4656   0.8542  0.7977              0.4019
LightGBM + @war_monitor            0.1532    0.4611   0.8560  0.8038              0.4062
LightGBM + @kpszsu                 0.1555    0.4684   0.8516  0.7951              0.3971
```

Chosen model by time of day:

```
                    Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
day (06-22 Kyiv)    0.151     0.458    0.862   0.817               0.417
night (22-06 Kyiv)  0.162     0.481    0.838   0.754               0.371
```

Chosen model by test week:

```
        Brier  ROC-AUC  skill vs same-hour
week 1  0.166    0.828               0.387
week 2  0.138    0.887               0.444
week 3  0.148    0.863               0.356
week 4  0.164    0.843               0.409
week 5  0.158    0.872               0.539
```

Calibration (chosen model):

```
                rows  predicted  observed
bin                                      
(-0.001, 0.05]  2352      0.015     0.017
(0.05, 0.1]      908      0.074     0.068
(0.1, 0.2]      1624      0.149     0.131
(0.2, 0.3]      1568      0.249     0.258
(0.3, 0.4]      1546      0.350     0.339
(0.4, 0.5]      1489      0.451     0.465
(0.5, 0.6]      1498      0.551     0.601
(0.6, 0.7]      1622      0.650     0.686
(0.7, 0.8]      1477      0.749     0.750
(0.8, 0.9]      1517      0.850     0.852
(0.9, 1.0]       695      0.930     0.932
```

### Duration of the next alert (starting within 3h), as a range

7,028 test cases; true durations: median 46 min, middle half 25–97 min. Ideal coverage of a 25–75% range: 50%.

```
                             median abs error of the middle value (min)  pinball loss  true duration inside the 25-75% range  average range width (min)
baseline: last 10 alerts                                         27.796        41.599                                  0.417                     89.042
LightGBM quantiles (chosen)                                      29.699        40.098                                  0.487                    108.626
```

### Next 24 hours

Number of new alerts (true average 5.03):

```
                                          MAE  median abs error   RMSE  skill vs 7-day average
baseline: same as last 24h              2.083             1.000  3.033                  -0.078
baseline: daily average of last 7 days  1.931             1.429  2.722                   0.000
LightGBM (chosen)                       2.086             1.360  2.980                  -0.080
```

Hours under alert (true average 10.25 h):

```
                                          MAE  median abs error   RMSE  skill vs 7-day average
baseline: same as last 24h              2.198             1.085  3.555                   0.015
baseline: daily average of last 7 days  2.231             1.442  3.300                   0.000
LightGBM (chosen)                       2.058             1.018  3.252                   0.077
```

### When: new alert in each 3-hour Kyiv block of the next 7 days

Forecasts issued at 00:00 and 12:00 Kyiv inside the test period; 66,528 (unit, issue, block) cases whose block ended before the end of data (later days of the week have fewer cases).

All blocks:

```
                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs pattern
pattern rule        0.1682    0.5511   0.8296  0.7276           -0.0000
timing model alone  0.2189    0.6256   0.8132  0.7095           -0.3014
blend (chosen)      0.1740    0.5404   0.8278  0.7280           -0.0347
```

ROC-AUC by lead day:

```
                    day 1  day 2  day 3  day 4  day 5  day 6  day 7
pattern rule        0.832  0.828  0.829  0.829  0.831  0.830  0.829
timing model alone  0.822  0.812  0.806  0.811  0.818  0.814  0.811
blend (chosen)      0.830  0.831  0.832  0.829  0.831  0.830  0.829
```

Brier by lead day:

```
                     day 1   day 2   day 3   day 4   day 5   day 6   day 7
pattern rule        0.1662  0.1686  0.1683  0.1687  0.1677  0.1683  0.1695
timing model alone  0.2006  0.2182  0.2269  0.2275  0.2231  0.2183  0.2195
blend (chosen)      0.1899  0.1803  0.1700  0.1687  0.1677  0.1683  0.1695
```

## Red vs yellow (if an alert starts in a raion)

Own split (D32): trained on 9,138 alerts from 6–26 Sep, tested on 6,763 alerts from 27 Sep to the end of data. Red share in the test alerts: 0.29.

```
                                       Brier  log-loss  ROC-AUC  PR-AUC
baseline: overall red share           0.2251    0.6430   0.5000  0.2919
baseline: previous alert's level      0.1763    0.5369   0.7116  0.4691
raion red share last 7 days (chosen)  0.1372    0.4455   0.8454  0.6757
logistic, 5 level features            0.1381    0.4348   0.8372  0.6761
```
