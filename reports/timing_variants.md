# Timing model: how to combine model and pattern (D45 variants, validation)

Last 2 validation weeks (Aug 30 – Sep 12 2026); the test period is untouched. Lower Brier is better; skill = Brier improvement over the pattern rule (negative = worse than the pattern).

## Raion

All 56 blocks:

```
                                       Brier  log-loss  ROC-AUC  skill vs pattern
variant                                                                          
pattern                               0.1787    0.5972   0.7713           -0.0000
full model                            0.1801    0.5327   0.7844           -0.0078
calendar-only model                   0.2085    0.6186   0.7693           -0.1604
hybrid A (full <48h, pattern after)   0.1763    0.5704   0.7808            0.0143
hybrid B (full <48h, calendar after)  0.1911    0.5657   0.7760           -0.0665
blend full/calendar (w=1-lead/72h)    0.1934    0.5696   0.7767           -0.0787
blend full/pattern (w=1-lead/72h)     0.1760    0.5616   0.7810            0.0155
```

Brier by lead day (day 1 = next 24 h):

```
day                                    day 1   day 2   day 3   day 4   day 5   day 6   day 7
variant                                                                                     
pattern                               0.1672  0.1740  0.1786  0.1823  0.1817  0.1883  0.2050
full model                            0.1542  0.1701  0.1820  0.1899  0.1878  0.1950  0.2050
calendar-only model                   0.1937  0.2047  0.2086  0.2121  0.2087  0.2096  0.2157
hybrid A (full <48h, pattern after)   0.1542  0.1701  0.1786  0.1823  0.1817  0.1883  0.2050
hybrid B (full <48h, calendar after)  0.1542  0.1701  0.2086  0.2121  0.2087  0.2096  0.2157
blend full/calendar (w=1-lead/72h)    0.1577  0.1824  0.2012  0.2121  0.2087  0.2096  0.2157
blend full/pattern (w=1-lead/72h)     0.1547  0.1696  0.1779  0.1823  0.1817  0.1883  0.2050
```

ROC-AUC by lead day:

```
day                                   day 1  day 2  day 3  day 4  day 5  day 6  day 7
variant                                                                              
pattern                               0.759  0.765  0.773  0.779  0.774  0.755  0.705
full model                            0.803  0.782  0.776  0.783  0.783  0.759  0.726
calendar-only model                   0.762  0.764  0.771  0.777  0.772  0.749  0.721
hybrid A (full <48h, pattern after)   0.803  0.782  0.773  0.779  0.774  0.755  0.705
hybrid B (full <48h, calendar after)  0.803  0.782  0.771  0.777  0.772  0.749  0.721
blend full/calendar (w=1-lead/72h)    0.799  0.776  0.773  0.777  0.772  0.749  0.721
blend full/pattern (w=1-lead/72h)     0.800  0.780  0.781  0.779  0.774  0.755  0.705
```

## Oblast

All 56 blocks:

```
                                       Brier  log-loss  ROC-AUC  skill vs pattern
variant                                                                          
pattern                               0.1811    0.6044   0.7907            0.0000
full model                            0.1820    0.5428   0.7966           -0.0052
calendar-only model                   0.1892    0.5508   0.7808           -0.0454
hybrid A (full <48h, pattern after)   0.1769    0.5745   0.7982            0.0231
hybrid B (full <48h, calendar after)  0.1839    0.5411   0.7913           -0.0164
blend full/calendar (w=1-lead/72h)    0.1846    0.5413   0.7897           -0.0203
blend full/pattern (w=1-lead/72h)     0.1768    0.5668   0.7989            0.0238
```

Brier by lead day (day 1 = next 24 h):

```
day                                    day 1   day 2   day 3   day 4   day 5   day 6   day 7
variant                                                                                     
pattern                               0.1729  0.1785  0.1822  0.1856  0.1841  0.1874  0.2010
full model                            0.1557  0.1720  0.1857  0.1945  0.1926  0.1996  0.2139
calendar-only model                   0.1734  0.1816  0.1883  0.1959  0.1950  0.2012  0.2132
hybrid A (full <48h, pattern after)   0.1557  0.1720  0.1822  0.1856  0.1841  0.1874  0.2010
hybrid B (full <48h, calendar after)  0.1557  0.1720  0.1883  0.1959  0.1950  0.2012  0.2132
blend full/calendar (w=1-lead/72h)    0.1573  0.1752  0.1871  0.1959  0.1950  0.2012  0.2132
blend full/pattern (w=1-lead/72h)     0.1563  0.1720  0.1813  0.1856  0.1841  0.1874  0.2010
```

ROC-AUC by lead day:

```
day                                   day 1  day 2  day 3  day 4  day 5  day 6  day 7
variant                                                                              
pattern                               0.769  0.778  0.791  0.801  0.799  0.782  0.729
full model                            0.804  0.792  0.793  0.794  0.794  0.771  0.718
calendar-only model                   0.762  0.772  0.783  0.789  0.788  0.767  0.718
hybrid A (full <48h, pattern after)   0.804  0.792  0.791  0.801  0.799  0.782  0.729
hybrid B (full <48h, calendar after)  0.804  0.792  0.783  0.789  0.788  0.767  0.718
blend full/calendar (w=1-lead/72h)    0.799  0.784  0.786  0.789  0.788  0.767  0.718
blend full/pattern (w=1-lead/72h)     0.802  0.791  0.797  0.801  0.799  0.782  0.729
```
