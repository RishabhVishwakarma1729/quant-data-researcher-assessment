# How I found the rule (research period 2012-2021 only)

The brief's Step 2 asks what I tested and how. This document tells the story in order, from the plan to the chosen rule, with the numbers taken from my own output files. Everything here uses the research data only. The locked 2022-2025 data appears only in the last section, as something I learned afterwards.

## In one paragraph

I wrote the rules for testing and for picking an idea before I downloaded any data. I then ran **98 tests** on 2012-2021 and counted every one of them. Only 43 of them could be traded with next-open entry. Of those, 3 had a raw p-value below 0.05 (luck alone would give about 2), and only **2 survived the correction for having tried so many**: the overnight-gap tests for Nifty and Bank Nifty. The Nifty one was the clear winner under my written selection rule. I checked it from several angles, turned it into a trading rule, and chose its settings from a small fixed grid of 18 variants.

## 1. The plan I wrote first

Before downloading any data I wrote `markdown/PLAN_written_before_looking_at_data.md`, so that I could not quietly change the rules after seeing results. It fixed three things:

- **Counting.** Every test goes into one table, including the failures. P-values are adjusted for the whole table (Bonferroni and Benjamini-Hochberg), not family by family. Returns are tested with Newey-West errors, which allow for overlapping and autocorrelated days.
- **Picking.** The idea to trade is chosen by rule, not by feel. It must be (1) something I can trade, (2) the one with the smallest adjusted p-value among the tradable tests, (3) the same sign in both halves of the research period (2012-2016 and 2017-2021), (4) still positive after 0.05% costs per side, and (5) have a story about who is on the other side of the trade.
- **Protecting the test.** 2012-2021 is research data, 2022-2025 is locked, and nothing is run on the locked data until the rules are frozen.

## 2. The scan: what I tested

The scan is `code/03_anomaly_scan.py`. It writes one row per test to `outputs/tables/anomaly_scan_all_tests.csv`. The tests come in seven groups, with at least one classical test and at least one machine-learning method, as the brief asks:

| group                                    | tests   | tradable   | what                                                                                      | smallest raw p   |
|:-----------------------------------------|:--------|:-----------|:------------------------------------------------------------------------------------------|:-----------------|
| F1 random walk, volatility, distribution | 16      | 0          | Ljung-Box, ARCH-LM, variance ratios, runs test, Jarque-Bera                               | 0.0000           |
| F2 day of week                           | 24      | 10         | each weekday against the rest, Kruskal-Wallis across weekdays                             | 0.0453           |
| F3 expiry and turn of month              | 16      | 8          | expiry day, expiry week, day after expiry, turn of month                                  | 0.2573           |
| F4 gaps                                  | 14      | 4          | overnight gap, intraday move, big gaps, average overnight and intraday drift              | 0.0000           |
| F5 streaks                               | 12      | 12         | 2, 3 and 4 or more up or down closes in a row                                             | 0.0681           |
| F6 Nifty against Bank Nifty              | 8       | 5          | ADF, Engle-Granger, relative return, lead and lag                                         | 0.0239           |
| F7 machine learning                      | 8       | 4          | Gaussian-mixture regimes, isolation forest, walk-forward logistic and boosted classifiers | 0.4629           |

Many tests are about risk, not direction (for example volatility clustering and fat tails). They are very significant, but they cannot be traded with next-open entry, so they cannot be the rule. That is why the plan's first criterion matters.

## 3. How the gap test works

- **The overnight gap** of day t is how far the market opens from the previous close: gap = ln(open of day t / close of day t-1). One standard deviation of the Nifty gap is about 63 basis points (1 basis point = 0.01%).
- **What I can trade** after seeing the gap is the move from the open of day t+1 to the open of day t+2: I see the gap, decide at the close of day t, and can only enter at the next open. The brief says to assume entry at the next session's open.

| when                 | what happens                                                                         |
|:---------------------|:-------------------------------------------------------------------------------------|
| Day t, at the open   | The gap is known (today's open against yesterday's close)                            |
| Day t, at the close  | I decide: long after a big gap up, short after a big gap down                        |
| Day t+1, at the open | I enter the trade (the next session's open, as the brief says)                       |
| Day t+2, at the open | I leave. The result of the trade is the move from the open of t+1 to the open of t+2 |

- **The test** is a regression of that tradable return on the gap, with the gap scaled by its standard deviation, so the answer reads as "basis points earned for each 1 standard deviation of gap". The t-statistic and p-value use Newey-West errors with 5 lags. A positive effect means gaps tend to continue; a negative one would mean they tend to fade.
- **The same test is run on the two halves** of the research period (2012-2016 and 2017-2021), which gives the sign check in criterion 3.

## 4. Correcting for having tried 98 things

If you test 98 ideas, some will look good by chance. A raw p-value of 0.05 means a no-effect idea passes 1 time in 20, so about 5 of 98 tests pass with no real effect. So every p-value is adjusted for the size of the table. **Bonferroni** multiplies by the number of tests (strict). **Benjamini-Hochberg** controls the share of false discoveries among the tests that pass (gentler). In the whole table, 19 tests have a raw p below 0.05, 14 survive Benjamini-Hochberg and 12 survive Bonferroni. Of the 14 that survive Benjamini-Hochberg, 12 cannot be traded with next-open entry (volatility clustering, fat tails, the average overnight and intraday drift and similar), so only 2 are candidates for a rule.

The gap tests, which are tradable:

| test           | effect (bps per 1 sd)   | t    | raw p   | Benjamini-Hochberg   | Bonferroni   |
|:---------------|:------------------------|:-----|:--------|:---------------------|:-------------|
| Nifty 50 gap   | 12.8                    | 3.91 | 0.0001  | 0.0008               | 0.0091       |
| Bank Nifty gap | 18.9                    | 3.05 | 0.0023  | 0.0163               | 0.2276       |

## 5. What survived among the tradable tests

| test                                           | index     | raw p   | Benjamini-Hochberg   |
|:-----------------------------------------------|:----------|:--------|:---------------------|
| yesterday's gap -> next tradable day           | Nifty50   | 0.0001  | 0.0008               |
| yesterday's gap -> next tradable day           | BankNifty | 0.0023  | 0.0163               |
| yesterday's intraday move -> next tradable day | Nifty50   | 0.0360  | 0.1961               |
| after 3+ up closes -> next tradable day        | Nifty50   | 0.0681  | 0.3108               |
| after 4+ up closes -> next tradable day        | Nifty50   | 0.0977  | 0.4161               |

Out of 43 tradable tests, 3 had a raw p below 0.05 (chance alone would give about 2) and 2 survive the correction: the two gap tests. Nothing else survives, including every machine-learning method:

| model                                                    | index     | result                                                       | p vs baseline   |
|:---------------------------------------------------------|:----------|:-------------------------------------------------------------|:----------------|
| gradient boosting (depth 2) direction accuracy 2016-2021 | BankNifty | accuracy 0.498 vs majority baseline 0.520, AUC 0.497, n=1470 | 0.960           |
| logistic (L2) direction accuracy 2016-2021               | BankNifty | accuracy 0.512 vs majority baseline 0.520, AUC 0.524, n=1470 | 0.760           |
| gradient boosting (depth 2) direction accuracy 2016-2021 | Nifty50   | accuracy 0.514 vs majority baseline 0.546, AUC 0.513, n=1470 | 0.994           |
| logistic (L2) direction accuracy 2016-2021               | Nifty50   | accuracy 0.546 vs majority baseline 0.546, AUC 0.523, n=1470 | 0.532           |

The 4 regime and outlier tests (Gaussian mixture and isolation forest) found nothing either: their smallest raw p-value is 0.46.

## 6. The five criteria, applied to the Nifty gap test

| criterion                                         | check                                                                                                                                                 | result             |
|:--------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------|
| 1. Something I can trade                          | Uses the gap known at day t to predict the open-to-open return from t+1 to t+2, so entry is at the next open                                          | Yes                |
| 2. Smallest adjusted p-value among tradable tests | Benjamini-Hochberg p = 0.0008; the next tradable test is yesterday's gap -> next tradable day on BankNifty at 0.0163                                  | Yes (rank 1 of 43) |
| 3. Same sign in both halves                       | 2012-2016: +11.6 bps (t=3.29). 2017-2021: +14.0 bps (t=2.69)                                                                                          | Yes                |
| 4. Still positive after 0.05% per side            | The chosen rule on research data: net Sharpe 1.25 after costs (1.68 before)                                                                           | Yes                |
| 5. A story about who is on the other side         | Explained in section 5 of the research note. I wrote it up after the out-of-sample run, so it is an explanation that fits, not a pre-registered claim | Partly             |

## 7. Checking the effect from several angles before believing it

This is `code/03b_gap_diagnostics.py`. All numbers are for the Nifty gap and the research period.

| check                                         | effect (bps per 1 sd)     | t          | what it tells me                                                                  |
|:----------------------------------------------|:--------------------------|:-----------|:----------------------------------------------------------------------------------|
| All days                                      | 12.8                      | 3.91       | The headline result (2442 days)                                                   |
| Without 2020                                  | 8.7                       | 3.34       | The covid year does not carry it                                                  |
| Gap and outcome capped at 1st/99th percentile | 11.0                      | 3.98       | A few extreme days do not carry it                                                |
| Rank correlation                              | rho = 0.100               | p < 0.0001 | No outlier-sensitive step in the result                                           |
| Year by year                                  | positive in 9 of 10 years | -          | Not one lucky stretch (the weak spot is 2017-2019, where the effect is near zero) |
| Part 1: intraday move of day t+1              | 5.2                       | 1.87       | About 40% of the effect: the follow-through during day t+1                        |
| Part 2: overnight move into day t+2           | 7.7                       | 2.34       | About 60% of the effect: a second overnight move in the same direction            |

Splitting the days into five equal groups by gap size shows the shape of the effect:

| gap group         | average next tradable return (bps)   | days   |
|:------------------|:-------------------------------------|:-------|
| Q1 (big down gap) | -6.4                                 | 489    |
| Q2                | -1.1                                 | 488    |
| Q3                | 0.2                                  | 487    |
| Q4                | 8.0                                  | 489    |
| Q5 (big up gap)   | 25.6                                 | 489    |

The average rises from group to group: the biggest gap-downs are followed by losses and the biggest gap-ups by gains. That regular shape is more convincing than a single t-statistic.

## 8. From the effect to a rule, and choosing its settings

The rule is described in section 6 of the research note: compute the gap at the close of day t, divide it by the standard deviation of the previous 60 gaps (z), go long if z is at least +k and short if at most -k, keep the signal for h days, and enter at the next open. The threshold k, the holding days h and long-and-short against long-only were not known in advance, so I tried a **fixed grid of 18 variants** (k = 0.5, 1.0, 1.5; h = 1, 2, 3 days; long and short, or long only) and wrote the selection rule before running it:

*The highest net Sharpe among variants with at least 100 trades and a positive net Sharpe in both 2012-2016 and 2017-2021.* 18 of the 18 variants passed that filter, so it did not remove anything; the highest net Sharpe decided.

| k   | hold (days)   | side   | net Sharpe   | Sharpe 12-16   | Sharpe 17-21   | trades   |           |
|:----|:--------------|:-------|:-------------|:---------------|:---------------|:---------|:----------|
| 0.5 | 1             | both   | 0.97         | 1.16           | 0.82           | 860      |           |
| 0.5 | 1             | long   | 0.96         | 1.19           | 0.78           | 563      |           |
| 0.5 | 2             | both   | 1.25         | 1.21           | 1.28           | 661      | <- chosen |
| 0.5 | 2             | long   | 1.17         | 1.19           | 1.16           | 385      |           |
| 0.5 | 3             | both   | 1.09         | 1.11           | 1.07           | 578      |           |
| 0.5 | 3             | long   | 0.99         | 0.97           | 1.02           | 318      |           |
| 1.0 | 1             | both   | 1.07         | 1.21           | 0.98           | 511      |           |
| 1.0 | 1             | long   | 1.08         | 1.03           | 1.13           | 340      |           |
| 1.0 | 2             | both   | 1.13         | 1.01           | 1.24           | 430      |           |
| 1.0 | 2             | long   | 1.16         | 1.10           | 1.22           | 273      |           |
| 1.0 | 3             | both   | 0.90         | 0.94           | 0.87           | 381      |           |
| 1.0 | 3             | long   | 0.99         | 1.21           | 0.83           | 233      |           |
| 1.5 | 1             | both   | 0.66         | 0.74           | 0.62           | 269      |           |
| 1.5 | 1             | long   | 0.76         | 0.57           | 0.91           | 167      |           |
| 1.5 | 2             | both   | 1.00         | 0.98           | 1.03           | 244      |           |
| 1.5 | 2             | long   | 1.03         | 1.19           | 0.90           | 147      |           |
| 1.5 | 3             | both   | 0.88         | 1.08           | 0.75           | 223      |           |
| 1.5 | 3             | long   | 0.90         | 1.16           | 0.72           | 132      |           |

The chosen variant is k=0.5, hold=2 days, long and short, window 60, with a net Sharpe of 1.25 after costs. Because I chose the best of 18, I checked whether it is just the luckiest of them with White's Reality Check: the p-value is **0.003**. Moving each parameter by -20% and +20% (one at a time and all together) kept the net Sharpe positive in 100% of 15 variants, between 0.73 and 1.32.

## 9. What this does and does not show

- **It was the best of 98 tests.** The selection method was fixed in advance; the idea that gaps continue was not. It came out of the scan, so chance remains a possible explanation, and the Reality Check above only covers the grid of rule settings, not the whole scan.
- **The explanation came afterwards.** The story in section 5 of the research note (foreign institutions splitting large orders over several days) was written after the out-of-sample run, and I have no flow data to test it.
- **I learned later that it did not repeat.** On the locked 2022-2025 data, which I looked at once after freezing the rule, the gap effect was about zero (t = -0.04), the rule's Sharpe of 0.82 was about the same as buy and hold (0.78), and the same rule on Bank Nifty lost money (-0.17). The out-of-sample run also could not trade before April 2022 (see the README). These numbers come from `outputs/pdf/oos_results.pdf`. That is why my verdict is not to trade it.

## 10. Where everything is

| What | Where |
|---|---|
| The plan, written first | `markdown/PLAN_written_before_looking_at_data.md` |
| Every test of the scan | `outputs/tables/anomaly_scan_all_tests.csv` (code: `code/03_anomaly_scan.py`) |
| The checks on the gap effect | `outputs/pdf/gap_diagnostics.pdf` (code: `code/03b_gap_diagnostics.py`) |
| Where the edge comes from | `outputs/pdf/mechanism_checks.pdf` (code: `code/04b_mechanism_checks.py`) |
| The grid, the choice, the Reality Check, the sensitivity | `outputs/pdf/strategy_research.pdf` (code: `code/04_strategy_research.py`) |
| This document | `code/03c_how_the_rule_was_found.py` |

