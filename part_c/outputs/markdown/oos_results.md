# Out-of-sample results (locked out-of-sample 2022-2025)

Frozen parameters: instrument=Nifty50, k=0.5, window=60, hold=2 days, side=both, cost=0.05% per side.
Run at 2026-11-03 15:49:24.

**Reading note, added after the run (5 Nov 2026). Every number below is exactly as the run wrote it.** The locked data starts on 3 Jan 2022, but the rule needs the previous 60 overnight gaps to judge what a big gap is, and the run counted them from that first day instead of using the end of 2021. The window was full on 31 Mar 2022, the first signal was possible on 1 Apr and the first entry on 4 Apr 2022, so the first 62 of the 984 days held no position. The effective trading period is April 2022 to December 2025, the CAGR, Sharpe and drawdown below include those flat days, and buy and hold covers the whole of 2022. I cannot say whether the late start helped or hurt, and the test was not rerun. See "Known limitation" in `part_c/README.md` and section 8 of the research note.

## 1. Data quality of the locked period (same cleaning function, nothing tuned)

| rule                                | series   |   rows | details                                                                                |
|:------------------------------------|:---------|-------:|:---------------------------------------------------------------------------------------|
| muhurat session (1 hour, holiday)   | nifty    |      3 | [datetime.date(2022, 10, 24), datetime.date(2024, 11, 1), datetime.date(2025, 10, 21)] |
| rows kept after single-series rules | nifty    |    985 | started with 988                                                                       |
| muhurat session (1 hour, holiday)   | bank     |      3 | [datetime.date(2022, 10, 24), datetime.date(2024, 11, 1), datetime.date(2025, 10, 21)] |
| rows kept after single-series rules | bank     |    984 | started with 987                                                                       |
| date only in nifty (dropped)        | nifty    |      1 | [datetime.date(2025, 2, 1)]                                                            |

Clean table: 984 rows, 2022-01-03 to 2025-12-31.
Days with a move above 5% in either index: 2.

## 2. In-sample vs out-of-sample, same rule, same parameters

|                |   In-sample 2012-21 |   Out-of-sample |   Buy & hold Nifty, in-sample |   Buy & hold Nifty, out-of-sample |   Same rule on Bank Nifty, out-of-sample |
|:---------------|--------------------:|----------------:|------------------------------:|----------------------------------:|-----------------------------------------:|
| CAGR %         |               20.19 |            9.64 |                         14.4  |                             10.82 |                                    -3.54 |
| Ann vol %      |               15.76 |           12.11 |                         17.64 |                             14.6  |                                    14.74 |
| Sharpe         |                1.25 |            0.82 |                          0.85 |                              0.78 |                                    -0.17 |
| Max drawdown % |              -16.74 |          -16.38 |                        -37.77 |                            -17.11 |                                   -37.7  |
| Days           |             2444    |          983    |                       2444    |                            983    |                                   983    |
| Trades         |              661    |          263    |                        nan    |                            nan    |                                   279    |
| Win rate %     |               51.89 |           49.05 |                        nan    |                            nan    |                                    44.09 |
| Avg win %      |                1.55 |            1.3  |                        nan    |                            nan    |                                     1.38 |
| Avg loss %     |               -1.07 |           -0.96 |                        nan    |                            nan    |                                    -1.15 |

Out-of-sample gross Sharpe (before costs) 1.38, net 0.82. Costs paid: 26.3% of capital. Time in market: 73% of days.

|                |   2022 |   2023 |   2024 |   2025 |
|:---------------|-------:|-------:|-------:|-------:|
| strategy net % |   16.4 |    1   |    4.9 |   16.1 |
| buy & hold %   |    4.2 |   19.8 |    8.8 |    9.9 |

Alpha / beta vs always-long Nifty, out-of-sample: average exposure 0.20, beta 0.05, alpha 9.3% a year (t=1.37).

## 3. Is the underlying anomaly still there? (yesterday's gap -> next tradable day)

| period           | index     |   effect bps per 1sd gap |   t-stat |    n |
|:-----------------|:----------|-------------------------:|---------:|-----:|
| research 2012-21 | Nifty50   |                    12.84 |     3.91 | 2442 |
| research 2012-21 | BankNifty |                    18.9  |     3.05 | 2442 |
| out-of-sample    | Nifty50   |                    -0.18 |    -0.04 |  981 |
| out-of-sample    | BankNifty |                    -5.25 |    -0.88 |  981 |

Out-of-sample mean next tradable day return (bps) by gap quintile:
|     |   Q1 (big gap down) |   Q2 |   Q3 |   Q4 |   Q5 (big gap up) |
|:----|--------------------:|-----:|-----:|-----:|------------------:|
| bps |                  -5 |  6.2 | 10.3 |  3.5 |               4.2 |

## 4. Parameter sensitivity out-of-sample (information only, nothing is re-tuned from this)

| variant     |   k |   window |   hold |   net Sharpe |   CAGR % |   MaxDD % |   trades |
|:------------|----:|---------:|-------:|-------------:|---------:|----------:|---------:|
| base        | 0.5 |       60 |      2 |         0.82 |     9.64 |    -16.38 |      263 |
| k -20%      | 0.4 |       60 |      2 |         0.44 |     4.88 |    -15.66 |      286 |
| k +20%      | 0.6 |       60 |      2 |         0.52 |     5.5  |    -19.32 |      250 |
| window -20% | 0.5 |       48 |      2 |         0.68 |     7.95 |    -21.55 |      268 |
| window +20% | 0.5 |       72 |      2 |         0.66 |     7.53 |    -15.05 |      255 |
| hold -1     | 0.5 |       60 |      1 |        -0.21 |    -2.66 |    -24.26 |      336 |
| hold +1     | 0.5 |       60 |      3 |         0.78 |     9.53 |    -18.49 |      243 |

Cost sensitivity out-of-sample:

|   cost per side % |   net Sharpe |   CAGR % |
|------------------:|-------------:|---------:|
|              0    |         1.38 |    17.29 |
|              0.02 |         1.1  |    13.4  |
|              0.05 |         0.82 |     9.64 |
|              0.08 |         0.54 |     6.01 |
|              0.1  |         0.26 |     2.49 |

## 5. Was the out-of-sample drawdown within what the research-period bootstrap predicted?

Actual out-of-sample max drawdown: -16.4% over 983 days.
- Scenario 1 (edge as measured): median predicted max drawdown -14.9%, worst 5% -24.3%. Share of simulated paths with a drawdown at least as bad as the actual one: 36%.
- Scenario 2 (half the edge): median -19.7%, worst 5% -34.1%. Share at least as bad as the actual one: 72%.

Actual out-of-sample Sharpe 0.82. Share of simulated paths with a Sharpe at least this LOW: scenario 1 16%, scenario 2 66%.

Bootstrap 95% confidence interval for the out-of-sample Sharpe (resampling the out-of-sample days): -0.22 to 1.83 (median 0.82).

