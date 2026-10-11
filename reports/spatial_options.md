# Spatial options: exploration results

Raions: 119, oblasts: 24. Train 2025-06-01..2026-08-09, evaluation 2026-08-10..2026-09-06 (official data, pre-reform).
All options are scored against **raion-level truth** (new alert starts in the raion).

## Horizon 1h

| | Brier | Brier skill vs baseline | log-loss | ROC-AUC | base rate |
|---|---|---|---|---|---|
| baseline (raion, same hour last 14 days) | 0.0912 | 0.0000 | 0.3608 | 0.7296 | 0.1050 |
| O1 oblast model -> raion | 0.0913 | -0.0009 | 0.3014 | 0.7696 | 0.1050 |
| O3 raion model (disaggregated) | 0.0784 | 0.1406 | 0.2598 | 0.8388 | 0.1050 |
| O4 hierarchical oblast x share | 0.0882 | 0.0322 | 0.3157 | 0.7377 | 0.1050 |

### Horizon 1h, judged on oblast-level truth

| | Brier | Brier skill vs baseline | log-loss | ROC-AUC | base rate |
|---|---|---|---|---|---|
| baseline (oblast) | 0.0997 | 0.0000 | 0.3797 | 0.7459 | 0.1195 |
| O1 oblast model | 0.0826 | 0.1707 | 0.2714 | 0.8549 | 0.1195 |
| O3 raion model aggregated 1-prod(1-p) | 0.1691 | -0.6965 | 0.5087 | 0.7974 | 0.1195 |

## Horizon 3h

| | Brier | Brier skill vs baseline | log-loss | ROC-AUC | base rate |
|---|---|---|---|---|---|
| baseline (raion, same hour last 14 days) | 0.1858 | 0.0000 | 0.7478 | 0.7439 | 0.2541 |
| O1 oblast model -> raion | 0.1547 | 0.1675 | 0.4543 | 0.8077 | 0.2541 |
| O3 raion model (disaggregated) | 0.1334 | 0.2824 | 0.4036 | 0.8491 | 0.2541 |
| O4 hierarchical oblast x share | 0.1524 | 0.1797 | 0.4493 | 0.8060 | 0.2541 |

### Horizon 3h, judged on oblast-level truth

| | Brier | Brier skill vs baseline | log-loss | ROC-AUC | base rate |
|---|---|---|---|---|---|
| baseline (oblast) | 0.1930 | 0.0000 | 0.7687 | 0.7558 | 0.2770 |
| O1 oblast model | 0.1309 | 0.3221 | 0.4026 | 0.8641 | 0.2770 |
| O3 raion model aggregated 1-prod(1-p) | 0.2498 | -0.2937 | 0.9474 | 0.8135 | 0.2770 |
