# Training window: how much history should the models learn from?

Same LightGBM and features; 4 weekly validation folds (Aug 16, Aug 23, Aug 30, Sep 06); the test period from 2026-09-13 is untouched. Averages over the folds. Skill = Brier improvement over the 'same hour, last 14 days' rule.

## Oblast: new alert within 1h (4 folds)

```
                                              training rows   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                                             
full history (2022-04 on)                            926000  0.0801    0.2618   0.8638  0.4828              0.2109
since 2024-01                                        541000  0.0806    0.2644   0.8585  0.4766              0.2050
last 12 months                                       210000  0.0805    0.2638   0.8600  0.4789              0.2066
last 6 months                                        105000  0.0808    0.2652   0.8591  0.4721              0.2030
last 3 months                                         52000  0.0820    0.2692   0.8559  0.4624              0.1905
full, recency-weighted (half-life 12 months)         926000  0.0799    0.2603   0.8659  0.4870              0.2139
```

## Oblast: new alert within 3h (4 folds)

```
                                              training rows   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                                             
full history (2022-04 on)                            926000  0.1285    0.3946   0.8657  0.7141              0.3557
since 2024-01                                        541000  0.1294    0.3983   0.8637  0.7070              0.3505
last 12 months                                       210000  0.1306    0.4038   0.8582  0.7098              0.3436
last 6 months                                        105000  0.1289    0.3989   0.8657  0.7200              0.3571
last 3 months                                         52000  0.1371    0.4181   0.8522  0.6843              0.3092
full, recency-weighted (half-life 12 months)         926000  0.1269    0.3915   0.8701  0.7240              0.3657
```

## Raion: new alert within 3h (2 folds)

```
                                              training rows   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                                                             
full history (2022-04 on)                           4614000  0.1350    0.4107   0.8341  0.6292              0.3078
since 2024-01                                       2700000  0.1349    0.4118   0.8327  0.6264              0.3075
last 12 months                                      1042000  0.1261    0.3843   0.8623  0.6779              0.3675
full, recency-weighted (half-life 12 months)        4614000  0.1294    0.3966   0.8521  0.6626              0.3435
```
