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
