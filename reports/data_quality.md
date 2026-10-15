# Data quality report

Built 2026-10-15 15:26 UTC from Vadimkin `bf0c323c`, JustJimer `7abc556b`, @air_alert_ua posts #1–#338380 (338,360 posts), @war_monitor 46,492 posts.

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
- Raw raion events (after disaggregation): 862,696; events whose raion is unknown (dropped): 0.
- Merged raion alerts: 475,313, from 2022-02-25 to 2026-10-15 08:20 UTC.
- Merged oblast alerts: 94,444.

Sources of merged raion alerts:

```
sources
official            451444
archive              18535
volunteer             5119
archive+official       215
```

Per year:

```
      alerts  median_min
year                    
2022   78702        37.1
2023   90836        39.0
2024  117218        41.7
2025   96895        56.0
2026   91662        48.5
```

## 2b. Local (hromada/city) alerts, kept apart from raion alerts (D58)

- Merged local alerts: 9,737 in 136 hromadas/cities; they are model inputs and site notes, never the raion's own alert.

## 2c. Guards: very long alerts and units that are almost always under alert (D58)

Raion alerts longer than 3 days: 21
```
            oblast                 raion                     start                       end  days
Запорізька область     Бердянський район 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
Запорізька область    Пологівський район 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
Запорізька область Мелітопольський район 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
Запорізька область     Запорізький район 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
Запорізька область    Василівський район 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
  Донецька область   Краматорський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область     Покровський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область     Горлівський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область    Волноваський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область     Бахмутський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область       Донецький район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область  Маріупольський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область    Кальміуський район 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область    Волноваський район 2026-08-05 11:44:52+00:00 2026-08-08 16:19:12+00:00   3.2
  Донецька область     Бахмутський район 2026-08-05 11:44:52+00:00 2026-08-08 16:19:12+00:00   3.2
```
Oblast alerts longer than 3 days: 3
```
            oblast                     start                       end  days
Запорізька область 2022-03-04 08:02:43+00:00 2022-03-11 18:18:37+00:00   7.4
  Донецька область 2026-02-20 18:47:46+00:00 2026-02-24 10:32:58+00:00   3.7
  Донецька область 2026-08-05 11:44:52+00:00 2026-08-08 16:19:12+00:00   3.2
```
Local alerts longer than 3 days: 6
```
                  oblast               raion                                   hromada                            start                       end  days
      Харківська область   Харківський район            Липецька територіальна громада        2024-05-12 08:37:29+00:00 2026-01-06 09:53:57+00:00 604.1
      Харківська область   Харківський район            Липецька територіальна громада        2026-03-10 14:01:38+00:00 2026-10-15 08:21:00+00:00 218.8
Дніпропетровська область Нікопольський район Червоногригорівська територіальна громада        2026-09-17 10:06:55+00:00 2026-10-15 08:21:00+00:00  27.9
Дніпропетровська область Нікопольський район          Покровська територіальна громада        2026-09-17 10:06:09+00:00 2026-10-15 08:21:00+00:00  27.9
Дніпропетровська область Нікопольський район        Нікопольська територіальна громада 2026-10-02 15:33:26.384000+00:00 2026-10-07 09:02:34+00:00   4.7
Дніпропетровська область Нікопольський район        Нікопольська територіальна громада 2026-09-25 05:03:55.317000+00:00 2026-09-28 05:25:25+00:00   3.0
```

Raion alerts longer than 24 h outside the front-line/border oblasts (review these; a lost end message is fixed in `data/fixes/stuck_alerts.csv`): 4
```
             oblast               raion                            start                       end sources  hours
Житомирська область Коростенський район 2026-09-12 06:22:33.747000+00:00 2026-09-13 06:57:45+00:00 archive   24.6
   Київська область   Броварський район 2026-09-12 04:45:21.537000+00:00 2026-09-13 08:01:42+00:00 archive   27.3
   Київська область Вишгородський район 2026-09-12 03:53:49.220000+00:00 2026-09-13 07:23:51+00:00 archive   27.5
   Київська область Вишгородський район        2026-09-23 17:37:05+00:00 2026-09-24 17:42:59+00:00 archive   24.1
```

Applied corrections from `data/fixes/stuck_alerts.csv`: 2
```
              oblast              raion                 start_utc               new_end_utc
Закарпатська область Мукачівський район 2025-11-19 08:28:49+00:00 2025-11-19 09:08:32+00:00
Закарпатська область Берегівський район 2025-11-19 08:29:40+00:00 2025-11-19 09:08:37+00:00
```

Raion-weeks under alert more than 90% of the time: 304 (expected only for front-line raions of Donetsk/Kharkiv/Sumy/Zaporizhzhia/Kherson oblasts; a raion outside them here means a data problem)
```
oblast                    raion                 
Донецька область          Бахмутський район         30
                          Волноваський район        30
                          Донецький район           30
                          Горлівський район         30
                          Кальміуський район        30
                          Краматорський район       30
                          Покровський район         30
                          Маріупольський район      30
Дніпропетровська область  Синельниківський район    16
Запорізька область        Бердянський район          8
                          Василівський район         8
                          Запорізький район          8
                          Мелітопольський район      8
                          Пологівський район         8
Сумська область           Сумський район             1
Харківська область        Ізюмський район            1
                          Богодухівський район       1
                          Красноградський район      1
                          Куп'янський район          1
                          Лозівський район           1
```

Oblast-weeks under alert more than 90% of the time: 91 (expected only for front-line raions of Donetsk/Kharkiv/Sumy/Zaporizhzhia/Kherson oblasts; a raion outside them here means a data problem)
```
oblast
Донецька область            30
Дніпропетровська область    28
Харківська область          16
Запорізька область           8
Сумська область              7
Чернігівська область         2
```

## 3. Yellow/red (reform period, archive)

- Raion alerts with a level: 18,727; share red: 0.35.

## 4. Holes in the archive and volunteer patches (D26)

Archive silences of at least 2 hours nationwide, checked against volunteer alerts and @war_monitor:

```
                       gap_start                          gap_end  hours  volunteer_unexplained  war_monitor_threat_posts  raions_already_under_alert  judged_hole  volunteer_patches
2026-10-07 00:11:55.359000+00:00 2026-10-07 04:02:40.090000+00:00   3.85                      0                        48                        0.61        False                  0
```

Volunteer alerts used as oblast-level patches: 652 (Івано-Франківська область, Вінницька область, Дніпропетровська область, Донецька область, Житомирська область, Запорізька область, Київська область, Кіровоградська область, Миколаївська область, Одеська область, Полтавська область, Рівненська область, Сумська область, Тернопільська область, Харківська область, Хмельницька область, Черкаська область, Чернівецька область, Чернігівська область, м. Київ).
A silence counts as a hole when @war_monitor shows heavy threat activity at the same time (at least 10 threat posts) **and** fewer than 50% of the raions are already under alert (if most of the country is already under alert, no new alert can start, so silence is normal; e.g. 2026-10-07, confirmed by the user's alerts.in.ua screenshot). Raion truth is then unknown nationwide, so the window is written to `masks.parquet` and excluded from raion targets.

## 4b. Outages of the official feed (D59)

Nationwide silences of the official feed of at least 24 h while the volunteer source logs at least 2 alerts per hour. Raion truth is masked there; official alerts running into the outage are cut at its start (their recorded end is when the feed came back); the oblast table uses the volunteer alerts of the outage (outside the quirk oblasts): 652 alerts.

```
                    start                       end  hours
2026-08-29 04:55:28+00:00 2026-09-02 13:48:04+00:00  104.9
```

## 5. Volunteer quirk in Lviv, Volyn, Kherson (D26)

The volunteer source reports far more alerts in these oblasts than the official system, both before the reform (vs the official dataset) and after it (vs the archive), and @war_monitor never mentions those oblasts around the unexplained alerts. These volunteer alerts are therefore **not** used as patches.
