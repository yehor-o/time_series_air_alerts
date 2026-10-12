# With vs without @kpszsu

Same model, data and 4 validation weeks as the @war_monitor test (Aug 16 – Sep 12 2026; the test period is untouched). The second model also sees 25 features from @kpszsu posts published **before** the forecast time (drone / missile / guided-bomb posts in the last 3, 6, 24 h, drone counts, posts naming the oblast, channel silence). @kpszsu covers 2025-08-31 onward; earlier hours are 'unknown', not 'quiet'. 44,019 posts, 2.5% flagged as edited (kept, as for @war_monitor).

Rule (D44): the map uses the Telegram version only if it wins on these weeks.

## Raion

New alert within 1h:

```
                  Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                 
without @kpszsu  0.0771    0.2556   0.8471  0.4260              0.1857
with @kpszsu     0.0770    0.2559   0.8449  0.4286              0.1871
```

New alert within 3h:

```
                  Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                 
without @kpszsu  0.1333    0.4014   0.8516  0.6608              0.3259
with @kpszsu     0.1384    0.4180   0.8356  0.6347              0.2960
```

Next 24h, number of alerts and hours under alert (average error):

```
                 count MAE  hours MAE
model                                
without @kpszsu      1.475      1.914
with @kpszsu         1.487      1.932
```

## Oblast

New alert within 1h:

```
                  Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                 
without @kpszsu  0.0799    0.2603   0.8659  0.4870              0.2139
with @kpszsu     0.0822    0.2688   0.8551  0.4556              0.1904
```

New alert within 3h:

```
                  Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                 
without @kpszsu  0.1269    0.3915   0.8701  0.7240              0.3657
with @kpszsu     0.1331    0.4119   0.8556  0.6911              0.3320
```

Next 24h, number of alerts and hours under alert (average error):

```
                 count MAE  hours MAE
model                                
without @kpszsu      1.639      2.015
with @kpszsu         1.619      2.026
```
