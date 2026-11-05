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
  02b_build_nse_holidays.py  rebuilds data/reference/nse_trading_holidays_2012_2021.csv from the saved official sources (--locked: the 2022-2025 list)
  02c_build_nse_index_reference.py  rebuilds data/reference/nse_index_ohlc_2012_2021.csv from NSE's daily index files, downloading only what is missing (--locked: 2022-2025)
  02d_build_nse_volume_reference.py  rebuilds data/reference/nse_volume_2012_2021.csv (volume and turnover of both indices as published by NSE) from the saved daily files, downloading nothing (--locked: 2022-2025)
  03_anomaly_scan.py         step 2: 98 tests, multiple-testing adjustment (--nse-filled: side check on research data plus NSE's bars for the days Yahoo lacks)
  03b_gap_diagnostics.py     robustness checks on the gap effect
  test_engine.py             no-look-ahead and cost-accounting tests
  04_strategy_research.py    steps 4-5 on the research period (grid, reality check, sensitivity, bootstrap); --nse-filled: grid + reality check side check
  04b_mechanism_checks.py    where the edge comes from, alpha/beta, baselines
  05_freeze_rules.py         writes frozen_rules.json (parameters + hashes). Already run.
  06_run_oos.py              the single out-of-sample run. Already run, refuses to run again.
  07_post_hoc_locked_check.py  data check of the locked 2022-2025 files against NSE, made AFTER the out-of-sample run (post-hoc, changes no result;
                             refuses to run unless oos_run.lock exists and the locked files still match their frozen hashes)
data/
  research/                  2012-2021 raw and cleaned csv
  locked_oos/                2022-2025 raw csv, opened by 06_run_oos.py for the single run and, after it, by 07_post_hoc_locked_check.py
  reference/                 nse_trading_holidays_2012_2021.csv (every weekday trading holiday, source on each row)
                             nse_index_ohlc_2012_2021.csv (open/high/low/close of both indices as published by NSE, 2012-02-21 to 2021-12-31)
                             nse_volume_2012_2021.csv (volume in shares and turnover in Rs crore as published by NSE, 2012-02-21 to 2021-12-31; Yahoo's volume is empty or zero on many days)
                             nse_trading_holidays_2022_2025.csv, nse_index_ohlc_2022_2025.csv and nse_volume_2022_2025.csv: the same three files for the locked period (post-hoc check only)
                             sources/ = the NSE circulars (pdf), archived NSE web pages and broker copies the holiday lists were built from,
                             and nse_index_files/ (2012-2021) and nse_index_files_2022_2025/ = NSE's daily index files (one per trading day) behind the price csv files
  download_log.txt
outputs/
  pdf/                       the seven reports as PDF (data quality, strategy research, out-of-sample results, gap diagnostics, mechanism checks,
                             post-hoc check of the locked data against NSE, side check on research data with NSE's bars added)
  markdown/                  the same seven reports as markdown
  tables/anomaly_scan_all_tests.csv   every test, raw / Bonferroni / BH p-values
  frozen_rules.json, oos_run.lock     freeze record
  figures/                   charts used in the note
```

## The brief, step by step

| Step | Where |
|---|---|
| 1 Data structuring | `outputs/pdf/data_quality_report.pdf`, `code/02_clean_data.py` |
| 2 Anomaly discovery (classical + ML, including what failed) | `code/03_anomaly_scan.py`, `outputs/tables/anomaly_scan_all_tests.csv`, note section 4 |
| 3 Hypothesis | note section 5 |
| 4 Strategy | `code/strategy.py`, note section 6 |
| 5 Validation (in and out of sample, equity curve, +/-20% sensitivity, bootstrap drawdown) | `outputs/pdf/strategy_research.pdf`, `outputs/pdf/oos_results.pdf`, note section 6 |
| 6 Verdict | note section 7 |

## Honest-out-of-sample protocol in one paragraph

Plan first, data second. The 2022-2025 data was downloaded in a separate call and saved in `data/locked_oos/`; `common.load_raw("locked")` raises an error unless an environment variable is set, and only `06_run_oos.py` sets it. I never opened or plotted that file during research. Before the final run, `05_freeze_rules.py` saved the parameters and sha256 hashes of the code and the locked files; `06_run_oos.py` checks them, writes `oos_run.lock` before reading any locked data, and then runs once. Before the freeze I ran it with `--dry-run` on research data to catch bugs. After the run, once the result was known, I opened the locked files a second time to check them against NSE's holiday lists and index files (`07_post_hoc_locked_check.py`, report `outputs/pdf/post_hoc_locked_data_check.pdf`). It found nothing to correct and changed no result; it is labelled post-hoc and the test was not rerun. Known limitation: the out-of-sample run starts its 60-day volatility window at the start of 2022, so the first ~60 trading days of 2022 had no signal.
