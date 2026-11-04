| step   | what changed                                                                               |   Sharpe |   accuracy |
|:-------|:-------------------------------------------------------------------------------------------|---------:|-----------:|
| 0      | original script (same-day target, 'ret' as a feature, random split, trade at same close)   |    13.7  |      1     |
| 1      | + remove 'ret' from the features (target is still today's return)                          |     2.85 |      0.612 |
| 2      | + target is tomorrow's direction, position earns tomorrow's return (random split still on) |     0.55 |      0.525 |
| 3      | + chronological train/test split (no shuffling, 2 days purged)                             |     1.01 |      0.538 |
| 4      | + volume z-score uses only past 60 days, zero volume treated as missing                    |     0.56 |      0.535 |
| 5a     | + execution at next open (still no costs)                                                  |     0.72 |      0.53  |
| 5b     | + 0.05% per side costs                                                                     |     0.27 |      0.53  |
| 6a     | + walk-forward retraining every quarter, shallow forest (before costs)                     |     0.21 |      0.514 |
| 6b     | same, after 0.05% per side costs  <- the corrected script                                  |    -0    |      0.514 |
