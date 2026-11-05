# Post-hoc check of the locked 2022-2025 data against NSE

**Read this first.** This check was done after the single out-of-sample run, not before it. The run (3 Nov 2026) used the Yahoo files as downloaded. Afterwards I compared them with NSE's own holiday lists and index files, the same checks that sections 6 and 7 of the data quality report make for 2012-2021. Nothing in the study was changed because of this: no rule, no parameter, no cleaning step and no out-of-sample number. The out-of-sample test was not rerun. The one calculation that touches the rule (section 4) is a labelled sensitivity run, not a new test, and the verdict does not depend on it.

Run at 2026-11-05 15:44:42.

## Summary

- **Dates:** 56 of the 56 weekdays missing from both Yahoo series are official holidays, and 0 are real trading days. Yahoo has a bar for every real weekday session NSE had (0 missing from Nifty, 0 from Bank Nifty).
- **Prices:** the Nifty open and close are identical to NSE's on all 988 compared bars, and Bank Nifty's on 987 of 987. 3 highs or lows differ, by at most 7.65 points, and none of them is an open or a close.
- **Volume:** Yahoo's zero volume (8 Nifty and 6 Bank Nifty days) is missing data, and NSE has the volume for 8 and 6 of those days. The study does not use volume.
- **Effect on the result:** nothing to put back, so the out-of-sample result stands exactly as submitted (net Sharpe 0.82, 263 trades).
- **What I found on the way:** four calendar changes that the yearly NSE circulars do not show (Bakri Id 2023 moved a day, extra closures on 22-Jan-2024, 20-May-2024 and 20-Nov-2024), and three NSE files with the date written month-first. Both are handled and described below.

## 1. Dates against NSE's official holiday lists

data/reference/nse_trading_holidays_2022_2025.csv has every weekday trading holiday of 2022-2025 from NSE's four yearly circulars (NSE/CMTR/50560, 54757, 59722 and 65587, saved in data/reference/sources/), plus the changes NSE announced later: the Bakri Id holiday of 2023 moved from 28 to 29 June, and extra closures on 22-Jan-2024 (Ram Mandir consecration), 20-May-2024 (parliamentary elections in Mumbai) and 20-Nov-2024 (assembly elections in Maharashtra). The Bakri Id move and 22-Jan-2024 turned up because the Yahoo data and NSE's own files disagreed with the yearly circulars; I looked up the two election closures beforehand. All four are confirmed in press reports that quote NSE's circulars, and NSE has no index file for any of those closed days.

| year   | official weekday holidays   | expected sessions   | nifty rows   | bank rows   | open days missing from Nifty   | open days missing from Bank Nifty   | rows on official holidays   |
|:-------|:----------------------------|:--------------------|:-------------|:------------|:-------------------------------|:------------------------------------|:----------------------------|
| 2022   | 13                          | 247                 | 248          | 248         | 0                              | 0                                   | 1                           |
| 2023   | 15                          | 245                 | 245          | 245         | 0                              | 0                                   | 0                           |
| 2024   | 17                          | 245                 | 246          | 246         | 0                              | 0                                   | 1                           |
| 2025   | 14                          | 247                 | 249          | 248         | 0                              | 0                                   | 1                           |

**Open days missing from Nifty only (0):** none.
**Open days missing from Bank Nifty only (0):** none.
**Open days missing from both series (0):** none.
**Rows dated on an official holiday (3):** 2022-10-24, 2024-11-01, 2025-10-21. Those that are Diwali Laxmi Pujan days with an evening Muhurat session are dropped by cleaning rule 5; the file common.py lists them.
**Weekend rows in the Yahoo files (1):** 2025-02-01. 2025-02-01 is in Nifty only. A date that exists in only one of the two series is dropped by the cleaning (inner join).

Of the 56 weekdays missing from both series, 56 are official holidays and 0 are real trading days.

## 2. Prices against NSE's own index files

data/reference/nse_index_ohlc_2022_2025.csv has the Nifty 50 and Bank Nifty rows of NSE's daily index files (built by 02c_build_nse_index_reference.py --locked, the saved files are in data/reference/sources/nse_index_files_2022_2025/). NSE has files from 2022-01-03 to 2025-12-31.

| index      | Yahoo bars   | compared with NSE   | open identical   | high identical   | low identical   | close identical   |
|:-----------|:-------------|:--------------------|:-----------------|:-----------------|:----------------|:------------------|
| Nifty 50   | 988          | 988                 | 988              | 987              | 987             | 988               |
| Bank Nifty | 987          | 987                 | 987              | 987              | 986             | 987               |

**Yahoo bars with no NSE file:** Nifty 0 (none), Bank Nifty 0 (none).

**Every price that differs (3 in all):**

| index      | date       | price   | Yahoo     | NSE       | difference   | in the study?   |
|:-----------|:-----------|:--------|:----------|:----------|:-------------|:----------------|
| Bank Nifty | 2025-12-15 | Low     | 59,052.30 | 59,044.65 | 7.65         | kept            |
| Nifty 50   | 2025-09-19 | High    | 25,428.75 | 25,431.40 | -2.65        | kept            |
| Nifty 50   | 2023-09-08 | Low     | 19,727.05 | 19,728.05 | -1.00        | kept            |

3 of the 3 differing prices are on days that stay in the study; 0 of those are opens or closes (the prices the strategy trades on).

## 3. The holiday list checked the other way round

NSE only publishes a file for a day it traded. 3 of the 59 listed holidays have an NSE file: 2022-10-24, 2024-11-01, 2025-10-21. Weekdays without an NSE file that are not on the holiday list: 0 (none).

**Weekend sessions.** NSE has a file for 5 Saturday or Sunday sessions (2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01). Yahoo has a bar for 1 of them (2025-02-01) and not for the other 4 (2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18). The cleaning drops a date that only one series has, so none of them is in the study, and whatever happened in them sits inside the following Monday's return. That is the same design as in the research period, and 5 such sessions in 984 days is too few to matter much. I did not add them.

**A quirk in NSE's own files.** Three of NSE's daily files (6, 10 and 11 April 2023) write the date inside the file month-first (10 April appears as 04-10-2023). 02c_build_nse_index_reference.py takes the date from the file name instead and raises an error if the inside date is not the same day with day and month swapped. Read naively, those files would have created rows on 4 June, 4 October and 4 November 2023.

## 4. Does it matter? (sensitivity run, not a new out-of-sample test)

Days NSE has and Yahoo lacks (real weekday sessions, Muhurat evenings left out): Nifty 0 (none), Bank Nifty 0 (none).

| data                           | days   | net Sharpe   | gross Sharpe   | CAGR %   | max drawdown %   | trades   |
|:-------------------------------|:-------|:-------------|:---------------|:---------|:-----------------|:---------|
| Yahoo only (what the run used) | 983    | 0.821        | 1.382          | 9.64     | -16.38           | 263      |

The first row reproduces the submitted out-of-sample result (net Sharpe 0.82, 263 trades, 983 days), which shows that this script uses the same data and code as the run.
There is nothing to put back: Yahoo has a bar for every real weekday session that NSE has, in both indices. So, unlike the research period (where 14 days were missing), there is no second row to compute.

## 5. Volume

Same check as section 3 of the data quality report, on the volume column only (no prices). NSE's file nse_volume_2022_2025.csv (built by 02d_build_nse_volume_reference.py --locked) has a volume for all 992 sessions, with 0 blank and 0 zero values. Yahoo shows zero volume on 8 Nifty and 6 Bank Nifty days, and NSE has the volume for 8 and 6 of them. Yahoo's non-zero volume is in thousands of shares, as in the research period: within 5% of NSE's number divided by 1,000 on 98.6% of the Nifty days and 99.6% of the Bank Nifty days. Bank Nifty is written in raw shares on 2 days (2023-01-02, 2024-04-01), and 7 Nifty and 3 Bank Nifty days are more than 10% off. The study is price-only, so volume changes no result.

