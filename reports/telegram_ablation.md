# With vs without Telegram (@war_monitor)

Same model, same data, same 4 validation weeks (Aug 16 – Sep 12 2026; the test period is untouched). The only difference: the second model also sees 26 features computed from @war_monitor posts published **before** the forecast time (drone / missile / guided-bomb posts in the last 3, 6, 24 h, drone counts written in posts, strategic-aviation status, posts naming the oblast, channel silence).

Rule agreed with the user: the map uses the Telegram version only if it wins on these weeks.

## Raion

New alert within 1h:

```
                   Brier  log-loss  ROC-AUC  PR-AUC  skill vs same-hour
model                                                                  
without Telegram  0.0771    0.2556   0.8471  0.4260              0.1857
with Telegram     0.0778    0.2582   0.8420  0.4195              0.1789
```
