# Data quality report

Built 2026-10-11 22:55 UTC from Vadimkin `bf0c323c`, JustJimer `7abc556b`, @air_alert_ua posts #21214–#338380 (256,786 posts), @war_monitor 46,492 posts.

## 1. Official rows by message type (D25)

Each row of the official dataset was traced back to the @air_alert_ua message that created it (same timestamp; location from the message hashtags). Only `air_raid` rows are used, plus `unknown` rows at oblast/raion level (artillery and other threats only ever appear at hromada level).

```
loc_level         hromada  oblast   raion     All
kind                                             
air_raid             8712   95457  105169  209338
artillery           16503       0       0   16503
ballistic_threat       50       0       0      50
drone_threat          232       0       0     232
kab_threat             64       0       0      64
missile_threat         30       0       0      30
radiation              12       0      15      27
unknown             11181   34778   27067   73026
urban_fights            5       0       0       5
All                 36789  130235  132251  299275
```

How the rows were matched:

```
label_how
time+location             196252
no message found           51882
time only                  29997
outside scraped period     21144
```

## 2. Raion alert table

- Raions: 119 in 24 oblasts (incl. Kyiv City; Luhansk and Crimea excluded).
- Raw raion events (after disaggregation): 871,343; events whose raion is unknown (dropped): 0.
- Merged raion alerts: 471,007, from 2022-02-25 to 2026-10-11 09:53 UTC.
- Merged oblast alerts: 91,643.

Sources of merged raion alerts:

```
sources
official            449963
archive              15719
volunteer             5119
archive+official       206
```

Per year:

```
      alerts  median_min
year                    
2022   78700        37.1
2023   90840        39.0
2024  117215        41.7
2025   96926        56.0
2026   87326        48.4
```

## 3. Yellow/red (reform period, archive)

- Raion alerts with a level: 15,901; share red: 0.37.

## 4. Holes in the archive and volunteer patches (D26)

Archive silences of at least 2 hours nationwide, checked against volunteer alerts and @war_monitor:

```
                       gap_start                          gap_end  hours  volunteer_unexplained  war_monitor_threat_posts  judged_hole  volunteer_patches
2026-10-07 00:11:55.359000+00:00 2026-10-07 04:02:40.090000+00:00   3.85                      0                        48         True                  0
```

Volunteer alerts used as oblast-level patches: 0.
A silence counts as a hole when @war_monitor shows heavy threat activity at the same time (at least 10 threat posts): a massive attack without a single new alert is implausible. Raion truth is then unknown nationwide, so the window is written to `masks.parquet` and excluded from raion targets.

## 5. Volunteer quirk in Lviv, Volyn, Kherson (D26)

The volunteer source reports far more alerts in these oblasts than the official system, both before the reform (vs the official dataset) and after it (vs the archive), and @war_monitor never mentions those oblasts around the unexplained alerts. These volunteer alerts are therefore **not** used as patches.
