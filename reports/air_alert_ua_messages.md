# @air_alert_ua: message types (full history)

338,360 posts, #1 (2022-03-14) → #338380 (2026-09-07 06:09 UTC). Classified by `src/alerts/telegram.py` (start and all-clear posts of the same type count together).

## Posts per quarter and type

```
kind    air_raid  artillery  ballistic_threat  drone_threat  kab_threat  missile_threat  other  radiation  urban_fights
q                                                                                                                      
2022Q1      3336          0                 0             0           0               0      1          0             0
2022Q2     13060        130                 0             0           0               0      5          0             0
2022Q3     10397        343                 0             0           0               0      0          0             0
2022Q4      7468        310                 0             0           0               0      2          0             0
2023Q1      6943        366                 0             0           0               0      0          0             0
2023Q2      7015        422                 0             0           0               0      1          0             0
2023Q3      9633        446                 0             0           0               0      0          6             0
2023Q4      9030        861                 0             0           0               0      0          0             0
2024Q1     10792       2333                 0             0           0               0      0          0             2
2024Q2     12014       2948                 0             0           0               0     26          0             3
2024Q3     11229       1989                 0             0           0               0     22          0             0
2024Q4      9309       1703                 0             0           0               0    338          0             0
2025Q1     10469       1529                 0           228           0               0    479          0             0
2025Q2     11641       2244                 0          1737           0               0    655          2             0
2025Q3     21793       2164                 0          1243           0               0    834          9             0
2025Q4     34198       2427                 0          1955           0               0   1073         16             0
2026Q1     32422       1961                 0          2384           0               0   1390          2             4
2026Q2     37330       1282                16          2535          24               7   1994          4             0
2026Q3     33632        469               161          2526         293              90   2651          2             2
```

## First appearance of each type

```
kind
air_raid            2022-03-15
artillery           2022-05-02
ballistic_threat    2026-06-23
drone_threat        2025-01-24
kab_threat          2026-06-22
missile_threat      2026-06-25
other               2022-03-14
radiation           2023-08-17
urban_fights        2024-03-31
```

## Drone-threat posts (D14, D28)

12,608 posts. Two formats:

- 🔴 'Загроза ударних БпЛА в <place>' (local warning, counted as an alert by the Vadimkin parser): 934

- 🟠 'Загроза ударних БпЛА / Загроза БпЛА невизначеного типу' and 🟢 all-clears (not in the dataset): 11,674

Most frequent locations (hashtag of the post):

```
text
м_Нікополь_та_Нікопольська_територіальна_громада    8495
м_Харків_та_Харківська_територіальна_громада        3172
м_Запоріжжя_та_Запорізька_територіальна_громада      933
Донецька_область                                       4
🇺🇦                                                     2
http://bit.ly/4kVwSqM                                  1
Запорізький_район                                      1
```

## Other typed threats (local, mostly Zaporizhzhia city)

```
                  text                                               
ballistic_threat  м_Запоріжжя_та_Запорізька_територіальна_громада        177
missile_threat    м_Запоріжжя_та_Запорізька_територіальна_громада         97
kab_threat        м_Запоріжжя_та_Запорізька_територіальна_громада        315
                  м_Краматорськ_та_Краматорська_територіальна_громада      2
```

## What this means

- Typed threat warnings are local (a few cities/hromadas) and appear mostly from 2025, so they can't serve as a nationwide threat-type label for the past. For yellow/red we rely on the archive (since 2026-09-06) and on @war_monitor.

- They are kept as possible features for the affected units (D28).
