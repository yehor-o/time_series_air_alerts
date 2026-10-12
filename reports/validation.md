# Validation results

Walk-forward validation on 4 weekly folds before the test period (folds start 2026-08-16, 2026-08-23, 2026-08-30, 2026-09-06; the test period from 2026-09-13 is untouched). Numbers are averages over the folds. Data: 119 raions and 24 oblasts, issue time = every hour.

How to read: **Brier** = mean squared error of the probabilities (lower is better); **skill** = how much smaller the Brier is than the 'same hour, last 14 days' rule (0 = no better, 0.3 = 30% smaller); **ROC-AUC** = chance that a random hour with a new alert gets a higher probability than a random hour without one (0.5 = coin flip); **PR-AUC** = how precise the top-ranked hours are (compare with the base rate); **MAE** = average absolute error in the target's units.

## Raion: will a new alert start within 1h?

Base rate (share of hours with a new alert): 0.108

```
                                   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                  
baseline: same hour, last 14 days  0.094     0.380    0.716   0.199               0.000
baseline: persistence              0.096     0.340    0.539   0.120              -0.016
logistic regression                0.081     0.269    0.827   0.362               0.144
LightGBM                           0.078     0.258    0.841   0.416               0.177
```

Training window (LightGBM):

```
                                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                    
LightGBM, train all (since 2024-01)  0.078     0.258    0.841   0.416               0.177
LightGBM, train 12 months            0.077     0.256    0.847   0.426               0.186
LightGBM, train 6 months             0.078     0.259    0.843   0.413               0.177
LightGBM, train 3 months             0.079     0.262    0.838   0.412               0.169
```

Day vs night (LightGBM):

```
                    Brier  log-loss  ROC-AUC  PR-AUC
day (06-22 Kyiv)    0.079     0.262    0.847   0.440
night (22-06 Kyiv)  0.075     0.251    0.833   0.371
```

Calibration (LightGBM): when the model says p, how often did an alert actually start?

```
                 rows  predicted  observed
bin                                       
(-0.001, 0.05]  38392      0.014     0.014
(0.05, 0.1]     13203      0.073     0.081
(0.1, 0.2]      13883      0.142     0.147
(0.2, 0.3]       7143      0.246     0.252
(0.3, 0.4]       3998      0.343     0.355
(0.4, 0.5]       1632      0.441     0.411
(0.5, 0.6]        824      0.547     0.530
(0.6, 0.7]        466      0.644     0.659
(0.7, 0.8]        253      0.750     0.798
(0.8, 0.9]        162      0.834     0.969
(0.9, 1.0]         12      0.911     1.000
```

Most important inputs (share of total gain, last fold):

```
                   gain share
oblast_code             0.086
nat_starts_24h          0.083
parent_starts_24h       0.080
alert_h_168h            0.077
nat_starts_3h           0.075
nat_active_share        0.064
nat_starts_1h           0.059
hour                    0.056
starts_168h             0.054
h_since_end             0.052
```


## Raion: will a new alert start within 3h?

Base rate (share of hours with a new alert): 0.264

```
                                   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                  
baseline: same hour, last 14 days  0.198     0.819    0.732   0.437               0.000
baseline: persistence              0.176     0.532    0.676   0.403               0.105
logistic regression                0.145     0.435    0.819   0.593               0.257
LightGBM                           0.138     0.414    0.837   0.636               0.297
```

Training window (LightGBM):

```
                                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                    
LightGBM, train all (since 2024-01)  0.138     0.414    0.837   0.636               0.297
LightGBM, train 12 months            0.133     0.401    0.852   0.661               0.326
LightGBM, train 6 months             0.134     0.405    0.848   0.656               0.320
LightGBM, train 3 months             0.136     0.411    0.845   0.643               0.310
```

Day vs night (LightGBM):

```
                    Brier  log-loss  ROC-AUC  PR-AUC
day (06-22 Kyiv)    0.136     0.410    0.851   0.669
night (22-06 Kyiv)  0.140     0.424    0.822   0.587
```

Calibration (LightGBM): when the model says p, how often did an alert actually start?

```
                 rows  predicted  observed
bin                                       
(-0.001, 0.05]  22347      0.011     0.013
(0.05, 0.1]      5312      0.075     0.085
(0.1, 0.2]      11003      0.151     0.148
(0.2, 0.3]      11089      0.250     0.264
(0.3, 0.4]       9145      0.349     0.352
(0.4, 0.5]       7249      0.448     0.478
(0.5, 0.6]       5974      0.548     0.569
(0.6, 0.7]       3746      0.645     0.653
(0.7, 0.8]       2058      0.744     0.729
(0.8, 0.9]       1168      0.851     0.828
(0.9, 1.0]        877      0.939     0.968
```

Most important inputs (share of total gain, last fold):

```
                   gain share
oblast_code             0.147
starts_168h             0.114
starts_24h              0.102
nat_starts_24h          0.077
nat_starts_3h           0.063
parent_starts_24h       0.061
hour                    0.060
alert_h_168h            0.045
h_since_start           0.041
nat_active_share        0.036
```


## Raion: how long will the next alert (starting within 1h) last? (minutes)

```
                                      MAE  median abs error   RMSE
model                                                             
baseline: median of last 10 alerts  112.4              35.9  356.1
LightGBM (log minutes)              108.1              37.9  348.9
```

## Raion: how long will the next alert (starting within 3h) last? (minutes)

```
                                      MAE  median abs error   RMSE
model                                                             
baseline: median of last 10 alerts  109.6              35.5  349.3
LightGBM (log minutes)              103.9              36.5  340.8
```

## Raion: next 24 hours

Number of new alerts:

```
                             MAE  median abs error  RMSE
model                                                   
baseline: same as last 24h  1.53              0.75  2.41
LightGBM (Poisson)          1.49              0.99  2.17
```

Hours under alert:

```
                             MAE  median abs error  RMSE
model                                                   
baseline: same as last 24h  1.97              0.76  3.46
LightGBM                    2.01              0.96  3.33
```

Timing: will an alert start in each 6-hour block of the next 24h?

```
                                    Brier  log-loss  ROC-AUC  PR-AUC
model                                                               
block +0..6h baseline: yesterday    0.191     0.569    0.716   0.570
block +0..6h LightGBM               0.157     0.466    0.837   0.735
block +6..12h baseline: yesterday   0.191     0.570    0.717   0.573
block +6..12h LightGBM              0.161     0.477    0.832   0.706
block +12..18h baseline: yesterday  0.192     0.571    0.718   0.572
block +12..18h LightGBM             0.174     0.509    0.805   0.662
block +18..24h baseline: yesterday  0.192     0.572    0.719   0.573
block +18..24h LightGBM             0.170     0.500    0.817   0.686
```

## Oblast: will a new alert start within 1h?

Base rate (share of hours with a new alert): 0.120

```
                                   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                  
baseline: same hour, last 14 days  0.101     0.393    0.732   0.232               0.000
baseline: persistence              0.105     0.366    0.560   0.144              -0.036
logistic regression                0.084     0.276    0.845   0.408               0.169
LightGBM                           0.081     0.264    0.859   0.477               0.205
```

Training window (LightGBM):

```
                                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                    
LightGBM, train all (since 2024-01)  0.081     0.264    0.859   0.477               0.205
LightGBM, train 12 months            0.080     0.264    0.860   0.479               0.207
LightGBM, train 6 months             0.081     0.265    0.859   0.472               0.203
LightGBM, train 3 months             0.082     0.269    0.856   0.462               0.191
```

Day vs night (LightGBM):

```
                    Brier  log-loss  ROC-AUC  PR-AUC
day (06-22 Kyiv)    0.084     0.273    0.860   0.494
night (22-06 Kyiv)  0.074     0.247    0.863   0.455
```

Calibration (LightGBM): when the model says p, how often did an alert actually start?

```
                rows  predicted  observed
bin                                      
(-0.001, 0.05]  7786      0.015     0.014
(0.05, 0.1]     2523      0.073     0.073
(0.1, 0.2]      2619      0.143     0.147
(0.2, 0.3]      1308      0.246     0.279
(0.3, 0.4]       878      0.347     0.368
(0.4, 0.5]       516      0.446     0.469
(0.5, 0.6]       247      0.540     0.559
(0.6, 0.7]       108      0.642     0.639
(0.7, 0.8]        81      0.746     0.802
(0.8, 0.9]        59      0.839     0.915
(0.9, 1.0]         3      0.916     1.000
```

Most important inputs (share of total gain, last fold):

```
                gain share
oblast_code          0.147
starts_24h           0.102
h_since_end          0.086
h_since_start        0.069
alert_h_168h         0.066
nat_starts_24h       0.059
alert_h_24h          0.059
hour                 0.058
nat_starts_3h        0.046
starts_168h          0.043
```


## Oblast: will a new alert start within 3h?

Base rate (share of hours with a new alert): 0.282

```
                                   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                  
baseline: same hour, last 14 days  0.202     0.814    0.754   0.492               0.000
baseline: persistence              0.177     0.532    0.715   0.468               0.121
logistic regression                0.139     0.423    0.843   0.649               0.296
LightGBM                           0.129     0.398    0.864   0.707               0.350
```

Training window (LightGBM):

```
                                     Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                    
LightGBM, train all (since 2024-01)  0.129     0.398    0.864   0.707               0.350
LightGBM, train 12 months            0.131     0.404    0.858   0.710               0.344
LightGBM, train 6 months             0.129     0.399    0.866   0.720               0.357
LightGBM, train 3 months             0.137     0.418    0.852   0.684               0.309
```

Day vs night (LightGBM):

```
                    Brier  log-loss  ROC-AUC  PR-AUC
day (06-22 Kyiv)    0.128     0.393    0.877   0.740
night (22-06 Kyiv)  0.132     0.408    0.849   0.663
```

Calibration (LightGBM): when the model says p, how often did an alert actually start?

```
                rows  predicted  observed
bin                                      
(-0.001, 0.05]  4909      0.013     0.021
(0.05, 0.1]     1224      0.073     0.087
(0.1, 0.2]      2072      0.148     0.126
(0.2, 0.3]      1884      0.248     0.286
(0.3, 0.4]      1478      0.348     0.375
(0.4, 0.5]      1197      0.450     0.470
(0.5, 0.6]       992      0.548     0.592
(0.6, 0.7]       850      0.648     0.680
(0.7, 0.8]       776      0.749     0.765
(0.8, 0.9]       541      0.841     0.852
(0.9, 1.0]       205      0.943     0.971
```

Most important inputs (share of total gain, last fold):

```
                gain share
oblast_code          0.267
starts_24h           0.110
h_since_start        0.062
hour                 0.060
starts_168h          0.053
nat_starts_24h       0.052
alert_h_168h         0.049
nat_starts_3h        0.045
med_dur10            0.043
alert_h_24h          0.042
```


## Oblast: how long will the next alert (starting within 1h) last? (minutes)

```
                                      MAE  median abs error   RMSE
model                                                             
baseline: median of last 10 alerts  121.8              36.2  408.6
LightGBM (log minutes)              116.4              37.0  408.2
```

## Oblast: how long will the next alert (starting within 3h) last? (minutes)

```
                                      MAE  median abs error   RMSE
model                                                             
baseline: median of last 10 alerts  122.9              35.8  419.9
LightGBM (log minutes)              117.6              37.4  419.7
```

## Oblast: next 24 hours

Number of new alerts:

```
                             MAE  median abs error  RMSE
model                                                   
baseline: same as last 24h  1.69              0.75  2.65
LightGBM (Poisson)          1.64              1.07  2.40
```

Hours under alert:

```
                             MAE  median abs error  RMSE
model                                                   
baseline: same as last 24h  2.11              0.75  3.70
LightGBM                    2.09              0.94  3.47
```

Timing: will an alert start in each 6-hour block of the next 24h?

```
                                    Brier  log-loss  ROC-AUC  PR-AUC
model                                                               
block +0..6h baseline: yesterday    0.187     0.561    0.730   0.593
block +0..6h LightGBM               0.147     0.449    0.858   0.785
block +6..12h baseline: yesterday   0.188     0.562    0.731   0.596
block +6..12h LightGBM              0.156     0.475    0.844   0.747
block +12..18h baseline: yesterday  0.189     0.565    0.731   0.594
block +12..18h LightGBM             0.167     0.503    0.822   0.698
block +18..24h baseline: yesterday  0.190     0.567    0.731   0.595
block +18..24h LightGBM             0.162     0.492    0.838   0.738
```

## Yellow/red: if an alert starts in a raion, is it red? (reform period only)

Folds: train from 2026-09-06, validate on the weeks of Sep 13–19 and Sep 20–26 (6468 alerts). Red share overall: 0.43. Thin data: about 3 weeks of training at most.

```
                                       Brier  log-loss  ROC-AUC  PR-AUC
model                                                                  
baseline: overall red share            0.252     0.697    0.500   0.384
baseline: previous alert's level       0.208     0.607    0.689   0.527
baseline: raion red share last 7 days  0.157     0.520    0.823   0.768
logistic regression                    0.230     0.706    0.745   0.661
LightGBM                               0.238     0.711    0.745   0.710
```

## Follow-up experiments (same folds)

```
RED: if an alert starts, is it red?          Brier  log-loss  ROC-AUC  PR-AUC
baseline: raion red share last 7 days        0.157     0.520    0.823   0.768
logistic, 5 level features                   0.162     0.503    0.819   0.753
LightGBM small, 5 level features             0.184     0.551    0.802   0.741

DURATION, oblast, next alert within 3h (min)   MAE  median abs error   RMSE
baseline: median of last 10                  122.9              35.8  419.9
LightGBM median (quantile 0.5)               118.1              37.6  416.9
```
Alert durations in the validation weeks are extremely skewed: median 51 min, 75% under 121 min, but 1% over 26 hours (long frontline alerts).

## Summary and recommendation (Proposed, D35)

| Target | Best on validation | Verdict |
|---|---|---|
| New alert within 1h (raion / oblast) | LightGBM: skill 0.18 / 0.21, AUC 0.85 / 0.86 | **Good**, well calibrated |
| New alert within 3h (raion / oblast) | LightGBM: skill 0.33 / 0.36, AUC 0.85 / 0.87 | **Good**, well calibrated |
| Training window | 12 months (raion), 6 months (oblast 3h); differences are small | Use the last 12 months |
| 24h timing (4 six-hour blocks) | LightGBM: AUC 0.80–0.86 vs 0.72 for "same as yesterday" | **Good** |
| 24h number of alerts / hours under alert | LightGBM ≈ "same as last 24h" (MAE 1.5 alerts, 2.0 h) | **Weak**: little beyond persistence |
| Duration of the next alert | LightGBM ≈ "median of last 10 alerts" (median error ~37 min) | **Weak**: show as a typical range, not a precise number |
| Red given alert (reform period) | Simple rule "raion red share last 7 days" (AUC 0.82) ≈ small logistic; full models overfit | Use the simple rule or the 5-feature logistic |

The final test run (from 2026-09-13) has **not** been done. It waits for the user's go.
