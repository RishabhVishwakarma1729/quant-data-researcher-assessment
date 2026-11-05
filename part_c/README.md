# Part C: Nifty 50 / Bank Nifty case study

Read `pdf/research_note.pdf` first (5 pages). This file is only a map of the folder.

## Folder map

```
pdf/
  research_note.pdf          the research note (hypothesis, method, results, verdict)
markdown/
  research_note.md           source of the note
  PLAN_written_before_looking_at_data.md   rules written before the data was downloaded
code/
  common.py                  loading, cleaning, backtest engine, performance numbers, bootstrap
  strategy.py                the trading rule (hashed at the freeze)
  01_download_data.py        downloads research and locked periods into separate folders
  02_clean_data.py           step 1: data quality report (includes the checks against NSE's holiday lists and NSE's own index files)
  02b_build_nse_holidays.py  shows how data/reference/nse_trading_holidays_2012_2021.csv was built from NSE's circulars (--locked: the 2022-2025 list); the circulars are not in the repository
  02c_build_nse_index_reference.py  rebuilds data/reference/nse_index_ohlc_2012_2021.csv from NSE's daily index files; it downloads them from NSE because the repository does not include them (--locked: 2022-2025)
  02d_build_nse_volume_reference.py  rebuilds data/reference/nse_volume_2012_2021.csv (volume and turnover of both indices as published by NSE) from the daily files that 02c downloaded (--locked: 2022-2025)
  03_anomaly_scan.py         step 2: 98 tests, multiple-testing adjustment (--nse-filled: side check on research data plus NSE's bars for the days Yahoo lacks)
  03b_gap_diagnostics.py     robustness checks on the gap effect
  03c_how_the_rule_was_found.py  writes outputs/markdown/how_the_rule_was_found.md (the story of how the rule was found, with every number read from my own output files; run it after 03, 03b and 04)
  test_engine.py             no-look-ahead and cost-accounting tests
  04_strategy_research.py    steps 4-5 on the research period (grid, reality check, sensitivity, bootstrap); --nse-filled: grid + reality check side check
  04b_mechanism_checks.py    where the edge comes from, alpha/beta, baselines
  05_freeze_rules.py         writes frozen_rules.json (parameters + hashes). Already run.
  06_run_oos.py              the single out-of-sample run. Already run, refuses to run again. (It starts its 60-gap window on the first locked day, see "Known limitation" below.)
  07_post_hoc_locked_check.py  data check of the locked 2022-2025 files against NSE, made AFTER the out-of-sample run (post-hoc, changes no result;
                             refuses to run unless oos_run.lock exists and the locked files still match their frozen hashes)
data/
  research/                  2012-2021 raw and cleaned csv
  locked_oos/                2022-2025 raw csv, opened by 06_run_oos.py for the single run and, after it, by 07_post_hoc_locked_check.py
  reference/                 nse_trading_holidays_2012_2021.csv (every weekday trading holiday, source on each row)
                             nse_index_ohlc_2012_2021.csv (open/high/low/close of both indices as published by NSE, 2012-02-21 to 2021-12-31)
                             nse_volume_2012_2021.csv (volume in shares and turnover in Rs crore as published by NSE, 2012-02-21 to 2021-12-31; Yahoo's volume is empty or zero on many days)
                             nse_trading_holidays_2022_2025.csv, nse_index_ohlc_2022_2025.csv and nse_volume_2022_2025.csv: the same three files for the locked period (post-hoc check only)
                             The raw files these were built from (NSE's circulars, archived NSE pages, broker copies and about 3,400 daily index files) are not in the repository;
                             the holiday csv names its source on every row, and 02c downloads the daily files again.
  download_log.txt
outputs/
  pdf/                       the eight reports as PDF (data quality, how the rule was found, strategy research, out-of-sample results, gap diagnostics, mechanism checks,
                             post-hoc check of the locked data against NSE, side check on research data with NSE's bars added)
  markdown/                  the same eight reports as markdown
  tables/anomaly_scan_all_tests.csv   every test, raw / Bonferroni / BH p-values
  frozen_rules.json, oos_run.lock     freeze record
  figures/                   charts used in the note
```

## Data sources

The brief says to use the dataset it shares or, if none is attached, to download one from a free public source and state it. No dataset was attached, so all data comes from the free public sources below. I did not use paid data, data from the company, order-flow or fund-flow data, or any other source. The first source is the data of the study; the NSE sources are only used to check it.

**1. Prices and volume of the study: Yahoo Finance**

- Tickers `^NSEI` (Nifty 50) and `^NSEBANK` (Nifty Bank), daily open, high, low, close and volume, raw and unadjusted (indices have no splits or dividends).
- Downloaded with the open-source `yfinance` package (version 0.2.55, pinned in `requirements.txt`) by `code/01_download_data.py` on 3 Nov 2026. The two periods were fetched in separate calls and saved in separate folders: `data/research/` (2012-01-02 to 2021-12-31; 2,449 Nifty rows and 2,461 Bank Nifty rows) and `data/locked_oos/` (2022-2025). The run is recorded in `data/download_log.txt`.
- `yfinance` is an independent tool and is not affiliated with Yahoo. Yahoo data is not versioned, so downloading again later can return slightly different history or gaps. The saved files are what every result in this repository was computed on.
- Yahoo is not the exchange file. Its known problems (missing trading days, empty or zero volume, volume written in thousands of shares) are described in `outputs/pdf/data_quality_report.pdf`.

**2. A check of prices and volume: NSE's own daily index files**

- NSE publishes one file per trading day with the open, high, low, close, volume and turnover of all its indices, at `https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv`. The files start on 21 Feb 2012.
- I downloaded them on 4 Nov 2026 with `code/02c_build_nse_index_reference.py` (2,421 files for 2012-2021 and 992 for 2022-2025) and kept the Nifty 50 and Bank Nifty rows in `data/reference/nse_index_ohlc_*.csv` (prices, from `02c`) and `data/reference/nse_volume_*.csv` (volume and turnover, from `02d`). The raw files are not in the repository.
- They are used to check Yahoo and to fill its gaps in side checks. They never replace Yahoo in the study.

**3. NSE trading holidays**

Every row of `data/reference/nse_trading_holidays_*.csv` names its own source. The sources are:

| Year | Source |
|---|---|
| 2012, 2015, 2016 | NSE website page "Holidays for the calendar year ...", as archived on web.archive.org (2 May 2012, 17 Nov 2015 and 7 May 2016) |
| 2013 | Zerodha's reproduction of the exchange list (`zerodha.com/z-connect/?p=60`), with the Muharram date as revised by NSE and BSE on 13 Nov 2013 (reported by Business Standard) |
| 2014 | Zerodha's reproduction of the exchange list (`zerodha.com/z-connect/?p=2740`), which includes the two election closures |
| 2017 to 2021 | NSE circulars NSE/FAOP/33750 (5 Dec 2016), NSE/CMTR/36475 (12 Dec 2017), 39612 (7 Dec 2018), 42877 (11 Dec 2019) and 46623 (11 Dec 2020) |
| 2022 to 2025 | NSE circulars NSE/CMTR/50560 (10 Dec 2021), 54757 (8 Dec 2022), 59722 (12 Dec 2023) and 65587 (13 Dec 2024) |

Closures announced after the yearly lists: 11 Nov 2015 (Diwali, Muhurat session only, from a Business Standard report), 29 Apr 2019 and 21 Oct 2019 (election days, NSE circulars), the Bakri Id move of 2023 (NSE/CMTR/57285 of 27 Jun 2023), and 22 Jan, 20 May and 20 Nov 2024. For the four changes of 2023-2024 I relied on press reports that quote the circulars, and NSE's own index files agree with each of them; I did not read those circulars themselves. The circular PDFs and archived pages are not in the repository.

**Facts that did not come from a data file**

- The Diwali Muhurat dates of 2022-2025 in `code/common.py` came from public knowledge and not from the data; NSE's circulars confirmed them afterwards.
- The Nifty closes of the three real trading days missing from Yahoo (26 Oct 2012, 13 Feb 2019, 29 Mar 2019) were checked against news reports, quoted in the data quality report, and match NSE's own files.
- I compared two Python calendar libraries (`exchange_calendars` and `holidays`) with the official lists. They disagree with each other and with NSE, so they are not a source of any data here.

The data is public and is used only for this assessment. Yahoo's and NSE's own terms of use apply to it.

## The brief, step by step

| Step | Where |
|---|---|
| 1 Data structuring | `outputs/pdf/data_quality_report.pdf`, `code/02_clean_data.py` |
| 2 Anomaly discovery (classical + ML, including what failed) | `code/03_anomaly_scan.py`, `outputs/tables/anomaly_scan_all_tests.csv`, note section 4; **how the rule was found, step by step: `outputs/pdf/how_the_rule_was_found.pdf`** |
| 3 Hypothesis | note section 5; how the one anomaly was picked (the five criteria applied): `outputs/pdf/how_the_rule_was_found.pdf`, section 6 |
| 4 Strategy | `code/strategy.py`, note section 6 |
| 5 Validation (in and out of sample, equity curve, +/-20% sensitivity, bootstrap drawdown) | `outputs/pdf/strategy_research.pdf`, `outputs/pdf/oos_results.pdf`, note section 6 |
| 6 Verdict | note section 7 |

## Honest-out-of-sample protocol in one paragraph

Plan first, data second. The 2022-2025 data was downloaded in a separate call and saved in `data/locked_oos/`; `common.load_raw("locked")` raises an error unless an environment variable is set, and only `06_run_oos.py` sets it. I never opened or plotted that file during research. Before the final run, `05_freeze_rules.py` saved the parameters and sha256 hashes of the code and the locked files; `06_run_oos.py` checks them, writes `oos_run.lock` before reading any locked data, and then runs once. Before the freeze I ran it with `--dry-run` on research data to catch bugs. After the run, once the result was known, I opened the locked files a second time to check them against NSE's holiday lists and index files (`07_post_hoc_locked_check.py`, report `outputs/pdf/post_hoc_locked_data_check.pdf`). It found nothing to correct and changed no result; it is labelled post-hoc and the test was not rerun. One known limitation of the run itself is described in the next section.

## Known limitation of the out-of-sample run: no position before 4 April 2022

The locked data starts on 3 January 2022, but the rule could not trade from that day. It decides whether an overnight gap is "big" by comparing it with the standard deviation of the previous 60 gaps (`code/strategy.py`, function `gap_signal`: days without enough history stay flat). The out-of-sample run read only the locked file, so it counted those 60 gaps from 3 January 2022 instead of using the last 60 days of 2021, which were already known history and would have been a legitimate warm-up. The consequences:

- The 60-gap window is full on 31 March 2022, the first signal can exist on 1 April, and the first entry is at the open of 4 April 2022. So the first 62 of the 984 days (6.3%) held no position.
- The effective out-of-sample trading period is April 2022 to December 2025, about 3.75 years, not the four years of the locked file.
- The CAGR, Sharpe and drawdown of the run include those flat days, while buy and hold covers the whole of 2022, so that comparison is not exactly like for like.
- I cannot say whether the late start helped or hurt, because the trades that were missing were never computed. I did not rerun, to keep to the plan of a single look at the locked data, and `06_run_oos.py` is hash-locked, so it could not be changed after the freeze in any case.

The same point is made in section 8 of the research note, and a short reading note was added at the top of `outputs/markdown/oos_results.md` (and its PDF) after the run. No number in that report was changed.
