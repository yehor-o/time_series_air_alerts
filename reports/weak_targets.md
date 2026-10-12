# Weak targets: diagnosis and attempts to strengthen them

Oblast level, 4 weekly validation folds (Aug 16 – Sep 12 2026), training rows since 2024-01-31; the test period is untouched. `+ @war_monitor` adds threat features from posts published before the forecast time (26 features: drone/missile/KAB post counts, drone counts written in posts, strategic aviation status, posts naming the oblast).

## 1. Why duration is hard

Durations in the validation weeks: median 51 min, middle half 26–121 min, 10% longer than 280 min, 1% longer than 26 h. A single number cannot describe this, so we predict a **range** (25th–75th percentile) and **bands**.

### Duration as a range (next alert starting within 3h)

Pinball loss scores a percentile forecast (lower is better). A good 25–75% range should contain the true duration about 50% of the time; narrower is better at equal coverage.

```
                                        median abs error (min)  pinball loss (avg of 3 quantiles)  true duration inside predicted 25-75% range  average range width (min)
model                                                                                                                                                                    
baseline: last 10 alerts of the oblast                  35.818                             56.189                                        0.410                    131.386
LightGBM quantiles                                      37.259                             54.380                                        0.454                    143.321
LightGBM quantiles + @war_monitor                       37.963                             54.372                                        0.441                    140.116
```

### Duration bands (<30 min, 30-60 min, 1-2 h, 2-4 h, >4 h)

```
                                         accuracy (most likely band)  log-loss
model                                                                         
baseline: band shares of last 30 alerts                        0.330     1.604
LightGBM bands                                                 0.315     1.515
LightGBM bands + @war_monitor                                  0.326     1.504
```

## 2. Next 24 hours: number of alerts and hours under alert

Skill = how much smaller the average error is than the 'daily average of the last 7 days' rule.

Number of new alerts:

```
                                          MAE  skill vs 7-day average
model                                                                
baseline: same as last 24h              1.694                   0.066
baseline: daily average of last 7 days  1.814                   0.000
LightGBM                                1.665                   0.082
LightGBM + @war_monitor                 1.683                   0.072
```

Hours under alert:

```
                                          MAE  skill vs 7-day average
model                                                                
baseline: same as last 24h              2.114                   0.065
baseline: daily average of last 7 days  2.262                   0.000
LightGBM                                2.035                   0.100
LightGBM + @war_monitor                 2.081                   0.080
```

## 3. Telegram check on a strong target: new alert within 3h

```
                          Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                         
LightGBM                 0.1297    0.3978   0.8634  0.7057              0.3488
LightGBM + @war_monitor  0.1299    0.3984   0.8624  0.7071              0.3481
```
