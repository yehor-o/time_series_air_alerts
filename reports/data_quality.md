# Data quality report

Built 2026-10-12 10:22 UTC from Vadimkin `bf0c323c`, JustJimer `7abc556b`, @air_alert_ua posts #1–#338380 (338,360 posts), @war_monitor 46,492 posts.

## 1. Official rows by message type (D25)

Each row of the official dataset was traced back to the @air_alert_ua message that created it (same timestamp; location from the message hashtags). Only `air_raid` rows are used, plus `unknown` rows at oblast/raion level (artillery and other threats only ever appear at hromada level).

```
loc_level         hromada  oblast   raion     All
kind                                             
air_raid            14118  130235  132212  276565
artillery           22273       0       0   22273
ballistic_threat       50       0       0      50
drone_threat          232       0       0     232
kab_threat             64       0       0      64
missile_threat         30       0       0      30
radiation              12       0      23      35
unknown                 1       0      16      17
urban_fights            9       0       0       9
All                 36789  130235  132251  299275
```

How the rows were matched:

```
label_how
time+location       264546
time only            34712
no message found        17
```

## 2. Raion alert table

- Raions: 119 in 24 oblasts (incl. Kyiv City; Luhansk and Crimea excluded).
- Raw raion events (after disaggregation): 876,741; events whose raion is unknown (dropped): 0.
- Merged raion alerts: 468,092, from 2022-02-25 to 2026-10-11 09:53 UTC.
- Merged oblast alerts: 88,538.

Sources of merged raion alerts:

```
sources
official            447048
archive              15719
volunteer             5119
archive+official       206
```

Per year:

```
      alerts  median_min
year                    
2022   79086        37.2
2023   90840        39.0
2024  116032        41.5
2025   94836        56.2
2026   87298        48.4
```

## 3. Yellow/red (reform period, archive)

- Raion alerts with a level: 15,901; share red: 0.37.

## 4. Holes in the archive and volunteer patches (D26)

Archive silences of at least 2 hours nationwide, checked against volunteer alerts and @war_monitor:

```
                       gap_start                          gap_end  hours  volunteer_unexplained  war_monitor_threat_posts  raions_already_under_alert  judged_hole  volunteer_patches
2026-10-07 00:11:55.359000+00:00 2026-10-07 04:02:40.090000+00:00   3.85                      0                        48                        0.61        False                  0
```

Volunteer alerts used as oblast-level patches: 0.
A silence counts as a hole when @war_monitor shows heavy threat activity at the same time (at least 10 threat posts) **and** fewer than 50% of the raions are already under alert (if most of the country is already under alert, no new alert can start, so silence is normal; e.g. 2026-10-07, confirmed by the user's alerts.in.ua screenshot). Raion truth is then unknown nationwide, so the window is written to `masks.parquet` and excluded from raion targets.

## 5. Volunteer quirk in Lviv, Volyn, Kherson (D26)

The volunteer source reports far more alerts in these oblasts than the official system, both before the reform (vs the official dataset) and after it (vs the archive), and @war_monitor never mentions those oblasts around the unexplained alerts. These volunteer alerts are therefore **not** used as patches.
