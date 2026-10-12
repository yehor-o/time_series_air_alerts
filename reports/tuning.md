# LightGBM tuning (validation only)

Search on 'new alert within 3h', confirmed on 1h. 4 weekly validation folds (Aug 16 – Sep 12 2026); the test period is untouched. Same inputs and training history as before (D40); only the LightGBM settings change. Current settings = candidate 0 (leaves 63, min rows 500, lr 0.05 x 400, cols 0.8, lambda 0.0; subsample 0.7, seed 42).

**Adoption rule (fixed before running):** lower Brier than candidate 0 in at least 3 of 4 weeks, at least 0.5% lower average Brier, and not worse on the 1h target.

Candidates:

- 0: leaves 63, min rows 500, lr 0.05 x 400, cols 0.8, lambda 0.0
- 1: leaves 31, min rows 200, lr 0.05 x 400, cols 0.6, lambda 1.0
- 2: leaves 31, min rows 200, lr 0.05 x 400, cols 0.8, lambda 0.0
- 3: leaves 31, min rows 200, lr 0.03 x 700, cols 0.6, lambda 1.0
- 4: leaves 31, min rows 500, lr 0.03 x 700, cols 0.6, lambda 0.0
- 5: leaves 31, min rows 1000, lr 0.05 x 400, cols 0.6, lambda 1.0
- 6: leaves 31, min rows 1000, lr 0.03 x 700, cols 0.6, lambda 0.0
- 7: leaves 63, min rows 500, lr 0.05 x 400, cols 0.6, lambda 0.0
- 8: leaves 63, min rows 1000, lr 0.05 x 400, cols 0.6, lambda 0.0
- 9: leaves 63, min rows 1000, lr 0.03 x 700, cols 0.8, lambda 1.0
- 10: leaves 127, min rows 200, lr 0.03 x 700, cols 0.6, lambda 0.0
- 11: leaves 127, min rows 500, lr 0.05 x 400, cols 0.6, lambda 1.0

## Raion

New alert within 3h (average of 4 weeks):

```
       Brier  log-loss  ROC-AUC  skill vs same-hour  weeks better than current  Brier change vs current
cand                                                                                                   
0     0.1333    0.4014   0.8516              0.3259                          0                   0.0000
1     0.1329    0.4007   0.8531              0.3277                          3                  -0.0031
2     0.1325    0.3995   0.8533              0.3295                          3                  -0.0062
3     0.1323    0.3995   0.8543              0.3308                          4                  -0.0073
4     0.1320    0.3974   0.8549              0.3329                          4                  -0.0096
5     0.1323    0.3986   0.8542              0.3313                          4                  -0.0072
6     0.1324    0.3996   0.8535              0.3301                          3                  -0.0067
7     0.1324    0.3996   0.8535              0.3300                          4                  -0.0064
8     0.1329    0.4012   0.8524              0.3273                          2                  -0.0026
9     0.1332    0.4015   0.8515              0.3261                          2                  -0.0007
10    0.1337    0.4032   0.8510              0.3233                          1                   0.0027
11    0.1338    0.4039   0.8501              0.3232                          0                   0.0038
```

Brier per week:

```
fold   08-16   08-23   08-30   09-06
cand                                
0     0.1357  0.1453  0.0908  0.1613
1     0.1346  0.1446  0.0915  0.1608
2     0.1349  0.1429  0.0916  0.1605
3     0.1351  0.1432  0.0903  0.1607
4     0.1354  0.1440  0.0887  0.1600
5     0.1353  0.1437  0.0893  0.1611
6     0.1350  0.1430  0.0909  0.1607
7     0.1352  0.1429  0.0907  0.1610
8     0.1349  0.1436  0.0917  0.1615
9     0.1358  0.1445  0.0913  0.1612
10    0.1357  0.1454  0.0925  0.1610
11    0.1358  0.1456  0.0917  0.1622
```

1h check:

```
              Brier  log-loss  ROC-AUC  skill vs same-hour
current (0)  0.0771    0.2556   0.8471              0.1857
candidate 4  0.0769    0.2541   0.8490              0.1881
```

Verdict for raion: **Adopt candidate 4** (leaves 31, min rows 500, lr 0.03 x 700, cols 0.6, lambda 0.0).

## Oblast

New alert within 3h (average of 4 weeks):

```
       Brier  log-loss  ROC-AUC  skill vs same-hour  weeks better than current  Brier change vs current
cand                                                                                                   
0     0.1269    0.3915   0.8701              0.3657                          0                   0.0000
1     0.1266    0.3897   0.8711              0.3662                          2                  -0.0024
2     0.1273    0.3919   0.8689              0.3625                          2                   0.0030
3     0.1259    0.3877   0.8744              0.3713                          2                  -0.0081
4     0.1262    0.3890   0.8724              0.3690                          3                  -0.0054
5     0.1259    0.3871   0.8739              0.3711                          3                  -0.0081
6     0.1258    0.3872   0.8739              0.3714                          3                  -0.0083
7     0.1274    0.3932   0.8676              0.3619                          2                   0.0042
8     0.1266    0.3898   0.8711              0.3672                          3                  -0.0020
9     0.1267    0.3907   0.8709              0.3666                          2                  -0.0016
10    0.1289    0.3977   0.8646              0.3540                          1                   0.0158
11    0.1295    0.3994   0.8620              0.3502                          1                   0.0208
```

Brier per week:

```
fold   08-16   08-23   08-30   09-06
cand                                
0     0.1297  0.1275  0.1011  0.1493
1     0.1293  0.1279  0.1023  0.1468
2     0.1294  0.1277  0.1040  0.1479
3     0.1299  0.1283  0.0979  0.1473
4     0.1295  0.1275  0.1001  0.1477
5     0.1297  0.1271  0.0987  0.1478
6     0.1295  0.1283  0.0981  0.1474
7     0.1294  0.1285  0.1037  0.1481
8     0.1295  0.1285  0.0999  0.1487
9     0.1299  0.1278  0.1005  0.1485
10    0.1302  0.1299  0.1063  0.1491
11    0.1297  0.1313  0.1084  0.1487
```

1h check:

```
              Brier  log-loss  ROC-AUC  skill vs same-hour
current (0)  0.0799    0.2603   0.8659              0.2139
candidate 6  0.0794    0.2588   0.8681              0.2183
```

Verdict for oblast: **Adopt candidate 6** (leaves 31, min rows 1000, lr 0.03 x 700, cols 0.6, lambda 0.0).
