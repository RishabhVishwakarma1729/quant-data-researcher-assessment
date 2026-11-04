# Side check: research results on data with NSE's own bars added

## 1. The 98-test scan

Done after the data check against NSE (section 7 of the data quality report), as a labelled side check. It is not the study itself: the submitted scan (`outputs/tables/anomaly_scan_all_tests.csv`), the grid and every number built on them are unchanged. Here the same code, the same seeds and the same cleaning run on the Yahoo research data with the real trading days that Yahoo lacks put back from NSE's files (the days listed in section 7 of the data quality report; Muhurat evenings left out). Research period only.

| scan                      | cleaned days   | tests   | tradable tests   | tradable with raw p<0.05   | BH<0.05   | Bonferroni<0.05   |
|:--------------------------|:---------------|:--------|:-----------------|:---------------------------|:----------|:------------------|
| as submitted (Yahoo only) | 2445           | 98      | 43               | 3                          | 14        | 12                |
| NSE days added            | 2459           | 98      | 43               | 3                          | 14        | 12                |

**Tests that survive the multiple-testing correction (BH 5%) in either scan:**

| family       | test                                     | index     | effect sub / filled   | t sub / filled   | raw p sub / filled   | BH p sub / filled   | Bonferroni p sub / filled   |
|:-------------|:-----------------------------------------|:----------|:----------------------|:-----------------|:---------------------|:--------------------|:----------------------------|
| volatility   | Ljung-Box on squared returns (10 lags)   | Nifty50   | - / -                 | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| distribution | Jarque-Bera normality                    | BankNifty | 12.51 / 12.6          | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| distribution | Jarque-Bera normality                    | Nifty50   | 18.23 / 18.36         | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| volatility   | Ljung-Box on squared returns (10 lags)   | BankNifty | - / -                 | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| volatility   | ARCH-LM (5 lags)                         | Nifty50   | 424.16 / 426.85       | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| volatility   | ARCH-LM (5 lags)                         | BankNifty | 277.07 / 279.5        | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| gaps         | average overnight (close to open) return | Nifty50   | 12.58 / 12.57         | 9.23 / 9.28      | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| gaps         | average overnight (close to open) return | BankNifty | 12.88 / 12.75         | 7.38 / 7.36      | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| random walk  | Ljung-Box on returns (10 lags)           | Nifty50   | - / -                 | - / -            | 0.00000 / 0.00000    | 0.0000 / 0.0000     | 0.0000 / 0.0000             |
| gaps         | average intraday (open to close) return  | Nifty50   | -7.21 / -7.23         | -4.35 / -4.37    | 0.00001 / 0.00001    | 0.0001 / 0.0001     | 0.0014 / 0.0012             |
| gaps         | yesterday's gap -> next tradable day     | Nifty50   | 12.84 / 12.34         | 3.91 / 3.76      | 0.00009 / 0.00017    | 0.0008 / 0.0015     | 0.0091 / 0.0170             |
| random walk  | Ljung-Box on returns (10 lags)           | BankNifty | - / -                 | - / -            | 0.00019 / 0.00019    | 0.0015 / 0.0016     | 0.0185 / 0.0189             |
| random walk  | Runs test (up/down closes)               | Nifty50   | -3.21 / -3.39         | - / -            | 0.00132 / 0.00069    | 0.0100 / 0.0052     | 0.1297 / 0.0675             |
| gaps         | yesterday's gap -> next tradable day     | BankNifty | 18.9 / 18.37          | 3.05 / 2.95      | 0.00232 / 0.00316    | 0.0163 / 0.0221     | 0.2276 / 0.3094             |

Tests whose BH-significance changed: 0. Tests whose raw p-value crossed 0.05: 0.
Largest change in a raw p-value across all 98 tests: 0.449 (ML walk-forward, gradient boosting (depth 2) direction accuracy 2016-2021, BankNifty).

The eight largest changes in raw p-value:

| family          | test                                                      | index     | raw p sub   | raw p filled   | BH p sub   | BH p filled   |
|:----------------|:----------------------------------------------------------|:----------|:------------|:---------------|:-----------|:--------------|
| ML walk-forward | gradient boosting (depth 2) direction accuracy 2016-2021  | BankNifty | 0.9598      | 0.5105         | 0.998      | 0.922         |
| ML walk-forward | logistic (L2) direction accuracy 2016-2021                | BankNifty | 0.7596      | 0.5928         | 0.989      | 0.922         |
| streaks         | after 3+ down closes -> next tradable day                 | Nifty50   | 0.3778      | 0.2275         | 0.904      | 0.758         |
| expiry          | day after expiry close-to-close                           | BankNifty | 0.6941      | 0.5590         | 0.986      | 0.922         |
| expiry          | day after expiry open-to-open                             | BankNifty | 0.7519      | 0.6339         | 0.989      | 0.922         |
| streaks         | after 4+ up closes -> next tradable day                   | BankNifty | 0.4753      | 0.5693         | 0.904      | 0.922         |
| day of week     | Wed close-to-close vs other days                          | Nifty50   | 0.7727      | 0.8666         | 0.989      | 0.998         |
| ML outliers     | after isolation-forest outlier day -> next tradable Nifty | Nifty50   | 0.9071      | 0.9979         | 0.998      | 0.998         |

## 2. The grid, the choice of rule and the reality check

Same grid of 18 variants, the same selection rule (written before the run) and the same bootstrap seed, on the research data plus NSE's bars. Nothing in `grid_research.csv` or `selected_params.json` is touched.

| k   | hold   | side   | net Sharpe sub / filled   | Sharpe 12-16 sub / filled   | Sharpe 17-21 sub / filled   | trades sub / filled   |
|:----|:-------|:-------|:--------------------------|:----------------------------|:----------------------------|:----------------------|
| 0.5 | 1      | both   | 0.968 / 0.938             | 1.16 / 1.09                 | 0.82 / 0.83                 | 860 / 863             |
| 0.5 | 1      | long   | 0.955 / 0.955             | 1.19 / 1.16                 | 0.78 / 0.81                 | 563 / 564             |
| 0.5 | 2      | both   | 1.246 / 1.227             | 1.21 / 1.23                 | 1.28 / 1.24                 | 661 / 663             |
| 0.5 | 2      | long   | 1.169 / 1.179             | 1.19 / 1.23                 | 1.16 / 1.15                 | 385 / 385             |
| 0.5 | 3      | both   | 1.086 / 1.084             | 1.11 / 1.14                 | 1.07 / 1.04                 | 578 / 584             |
| 0.5 | 3      | long   | 0.994 / 0.985             | 0.97 / 0.97                 | 1.02 / 1.00                 | 318 / 320             |
| 1.0 | 1      | both   | 1.069 / 1.048             | 1.21 / 1.15                 | 0.98 / 0.99                 | 511 / 514             |
| 1.0 | 1      | long   | 1.081 / 1.102             | 1.03 / 1.08                 | 1.13 / 1.13                 | 340 / 342             |
| 1.0 | 2      | both   | 1.130 / 1.118             | 1.01 / 0.96                 | 1.24 / 1.26                 | 430 / 429             |
| 1.0 | 2      | long   | 1.159 / 1.162             | 1.10 / 1.10                 | 1.22 / 1.22                 | 273 / 272             |
| 1.0 | 3      | both   | 0.899 / 0.881             | 0.94 / 0.89                 | 0.87 / 0.89                 | 381 / 381             |
| 1.0 | 3      | long   | 0.991 / 0.982             | 1.21 / 1.17                 | 0.83 / 0.84                 | 233 / 233             |
| 1.5 | 1      | both   | 0.656 / 0.550             | 0.74 / 0.47                 | 0.62 / 0.62                 | 269 / 269             |
| 1.5 | 1      | long   | 0.759 / 0.715             | 0.57 / 0.45                 | 0.91 / 0.92                 | 167 / 169             |
| 1.5 | 2      | both   | 0.998 / 0.968             | 0.98 / 0.88                 | 1.03 / 1.06                 | 244 / 243             |
| 1.5 | 2      | long   | 1.025 / 0.982             | 1.19 / 1.06                 | 0.90 / 0.93                 | 147 / 148             |
| 1.5 | 3      | both   | 0.875 / 0.843             | 1.08 / 0.96                 | 0.75 / 0.78                 | 223 / 222             |
| 1.5 | 3      | long   | 0.903 / 0.864             | 1.16 / 1.05                 | 0.72 / 0.73                 | 132 / 134             |

**Chosen variant:** as submitted k=0.5, hold=2, side=both; with NSE's bars added k=0.5, hold=2, side=both (the same variant). **Reality check p-value:** 0.003 as submitted, 0.004 with NSE's bars added. Largest change in a variant's net Sharpe: 0.106.

