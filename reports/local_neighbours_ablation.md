# New inputs: local (hromada/city) alerts and neighbouring districts

Same model (tuned LightGBM, D47), same training history (D40), same 4 validation weeks (Aug 16 – Sep 12 2026; the test period from Sep 13 is untouched). All arms use the corrected data (D58: a hromada/city alert is not an alert of the whole district; D59: official-feed outage of Aug 29 – Sep 2 masked, stuck alerts fixed). The arms differ only in their inputs.

**skill** = how much smaller the Brier score is than the 'same hour, last 14 days' rule (higher is better); **ROC-AUC**: 0.5 = coin flip, 1 = perfect ranking; **MAE** = average error (lower is better).

## Raion

New alert within 1h:

```
               Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                              
base          0.0950    0.3079   0.8254  0.4292              0.1331
+ local       0.0946    0.3069   0.8264  0.4333              0.1359
+ neighbours  0.0942    0.3048   0.8302  0.4377              0.1395
+ both        0.0941    0.3043   0.8304  0.4380              0.1405
```

Brier score for the most affected units, 1h (lower is better):

```
arm                                              base  + local  + neighbours  + both
unit                                                                                
Дніпропетровська область|Нікопольський район   0.2123   0.2118        0.2115  0.2107
Кіровоградська область|Олександрійський район  0.1555   0.1552        0.1540  0.1545
Харківська область|Харківський район           0.1990   0.1965        0.1977  0.1955
```

New alert within 3h:

```
               Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                              
base          0.1569    0.4641   0.8350  0.6907              0.3342
+ local       0.1572    0.4645   0.8341  0.6890              0.3329
+ neighbours  0.1557    0.4607   0.8362  0.6914              0.3388
+ both        0.1561    0.4615   0.8359  0.6906              0.3371
```

Brier score for the most affected units, 3h (lower is better):

```
arm                                              base  + local  + neighbours  + both
unit                                                                                
Дніпропетровська область|Нікопольський район   0.2108   0.2098        0.2100  0.2101
Кіровоградська область|Олександрійський район  0.2556   0.2543        0.2527  0.2525
Харківська область|Харківський район           0.1935   0.1929        0.1923  0.1925
```

Next 24h, number of alerts and hours under alert (average error):

```
              count MAE  hours MAE
model                             
base              1.475      2.199
+ local           1.474      2.183
+ neighbours      1.463      2.191
+ both            1.464      2.185
```

## Oblast

New alert within 1h:

```
               Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                              
base          0.1066    0.3381   0.8339  0.5038              0.1757
+ local       0.1067    0.3385   0.8333  0.5021              0.1748
+ neighbours  0.1053    0.3325   0.8412  0.5112              0.1849
+ both        0.1054    0.3328   0.8409  0.5121              0.1845
```

Brier score for the most affected units, 1h (lower is better):

```
arm                         base  + local  + neighbours  + both
unit                                                           
Дніпропетровська область  0.1039   0.1043        0.1068  0.1076
Харківська область        0.1401   0.1398        0.1400  0.1407
```
