# Technical Assessment: Quantitative Data Researcher (ML), Grain Digits

Rishabh Vishwakarma

Thank you for reviewing my submission. A short guide to the folders follows.

## What is in here

| Part | Where | What |
|---|---|---|
| A | `part_a/pdf/part_a_answers.pdf` | six short answers (all under 200 words) |
| B | `part_b/` | `pdf/issues.pdf` (review of the script, with suggested fixes), `outputs/pdf/ladder.pdf` (Sharpe after each fix), `original_script.py` (the original script, untouched), `corrected_script.py`, `compare_fixes.py` (applies the fixes one at a time and shows the Sharpe after each) |
| C | `part_c/` | `pdf/research_note.pdf` (5 pages), the code, the data, all outputs (reports in `outputs/pdf/`), and its own `README.md` |

Layout: wherever a folder holds both formats, the PDFs are in a `pdf/` sub-folder and the markdown sources are in a `markdown/` sub-folder (`part_a`, `part_b`, `part_b/outputs`, `part_c`, `part_c/outputs`). The two `README.md` files stay at the top of their folders.

## Data sources

The brief says to use the dataset it shares or, if none is attached, to download one from a free public source and state it. No dataset was attached, so everything below comes from free public sources. I did not use any paid data, any data from the company, or any other source.

| Data | Source | How and when I got it | Where it is |
|---|---|---|---|
| Daily open, high, low, close and volume of the Nifty 50 and Nifty Bank indices, January 2012 to December 2025 (the data of the whole study) | **Yahoo Finance**, tickers `^NSEI` (Nifty 50) and `^NSEBANK` (Nifty Bank), raw unadjusted daily bars | Downloaded with the open-source `yfinance` package (version 0.2.55) by `part_c/code/01_download_data.py` on 3 Nov 2026, in two separate calls: 2012-2021 (research) and 2022-2025 (locked out-of-sample) | `part_c/data/research/`, `part_c/data/locked_oos/`, and the log `part_c/data/download_log.txt` |
| The Nifty 50 file used in Part B | The same Yahoo download, 2012-2021 only | A copy of `nifty50_research.csv` with lower-case column names | `part_b/nifty_daily.csv` |
| A check of the prices and volume | **NSE's own daily index files**, one file per trading day (`https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv`), available from 21 Feb 2012 | Downloaded on 4 Nov 2026 by `part_c/code/02c_build_nse_index_reference.py` (about 3,400 files); only the Nifty 50 and Bank Nifty rows are kept | `part_c/data/reference/nse_index_ohlc_*.csv` and `nse_volume_*.csv` |
| NSE trading holidays | NSE's yearly holiday **circulars** (2017-2025), **NSE's website as archived** on web.archive.org (2012, 2015, 2016), **Zerodha's copy** of the exchange list (2013, 2014), and news and NSE circulars for closures announced later | Read by `part_c/code/02b_build_nse_holidays.py`; the source is named on every row | `part_c/data/reference/nse_trading_holidays_*.csv` |

Yahoo Finance is not the exchange file, so I checked it against NSE's own files (see `part_c/outputs/pdf/data_quality_report.pdf`). `yfinance` is an independent open-source tool and is not affiliated with Yahoo. The data is public and is used here only for this assessment; Yahoo's and NSE's own terms of use apply to it. The full list of sources, with every circular, is in `part_c/README.md`.

## Short version of the results

- **Part B:** the original script prints a Sharpe of 13.7 on my 2012-2021 Nifty file. The main reasons are that the label is also a feature, features use today's close, the trade cannot be executed as written, and the train/test split is shuffled. After fixing everything the Sharpe is about 0 (0.21 before costs, 0.00 after).
- **Part C:** I found one effect that survives multiple-testing correction in 2012-2021 (a big overnight gap predicts the next open-to-open return). It did not hold up in the locked 2022-2025 period (Sharpe 1.25 research, 0.82 out of sample, buy and hold 0.78, same rule on Bank Nifty -0.17). My verdict is that I would not trade it with real money.

## How to run

Python 3.12, `pip install -r requirements.txt`. From `part_c/code/`:

```
python 01_download_data.py       # only needed to re-download; the csv files are already included
python 02_clean_data.py          # step 1, data quality report (checks the dates against NSE's holiday lists and the prices against NSE's own index files)
python 02b_build_nse_holidays.py # optional, shows how the NSE holiday csv was built (needs NSE's circulars, which are not in the repository)
python 02c_build_nse_index_reference.py   # optional: rebuilds the NSE index price csv by downloading NSE's daily index files (a few minutes; the raw files are not in the repository)
python 02d_build_nse_volume_reference.py  # optional: rebuilds the NSE volume csv from the daily files that 02c downloaded (run 02c first)
python 03_anomaly_scan.py        # step 2, all 98 tests
python 03b_gap_diagnostics.py    # checks on the one effect that survived
python test_engine.py            # sanity tests for the backtester
python 04_strategy_research.py   # steps 4-5 on the research period
python 04b_mechanism_checks.py   # where does the edge come from
python 03_anomaly_scan.py --nse-filled && python 04_strategy_research.py --nse-filled   # optional side check: scan, grid and reality check on research data plus NSE's own bars (writes only outputs/markdown/nse_filled_side_check.md)
python 07_post_hoc_locked_check.py   # optional, post-hoc: checks the locked 2022-2025 data against NSE (reads the reference csv files that are already in data/reference; refuses to run before the out-of-sample run)
```

`05_freeze_rules.py` and `06_run_oos.py` are part of the record but are **not meant to be re-run**. The freeze script wrote `outputs/frozen_rules.json` and the out-of-sample script wrote `outputs/oos_run.lock`, after which it refuses to run again (it also checks hashes of the code and data). `outputs/pdf/oos_results.pdf` (markdown in `outputs/markdown/`) is the output of the one real run (after the run I added a short reading note at the top of it about the April 2022 start; no number was changed). The script itself is hash-locked, so it still writes that report into `outputs/` if it is ever run again; I moved the file afterwards. `python 06_run_oos.py --dry-run` runs the same code on research data if you want to see that it works.

Part B: from `part_b/`, `python original_script.py`, `python corrected_script.py`, `python compare_fixes.py`.

## Notes

- The honest-out-of-sample details (what I looked at and when) are in section 2 of the research note and in `part_c/markdown/PLAN_written_before_looking_at_data.md`.
- After the single out-of-sample run I also compared the locked data with NSE's own holiday lists and index files. This was a post-hoc check made after the result was known: it found nothing to correct, changed no result, and the test was not rerun. See `part_c/outputs/pdf/post_hoc_locked_data_check.pdf`.
- **A limitation of the out-of-sample run:** the rule needs the previous 60 overnight gaps to judge what a big gap is, and the run counted them from the first locked day (3 January 2022) instead of using the end of 2021. So it could not hold a position before 4 April 2022. The effective out-of-sample trading period is April 2022 to December 2025, the CAGR and Sharpe include the flat start, and I cannot say whether it helped or hurt. It could not be corrected without rerunning the test. Details in `part_c/README.md` (section "Known limitation") and in section 8 of the research note.
- The 14 trading days that Yahoo's research data lacks (NSE's own files have them) do not matter for the findings: the scan, the grid and the reality check give the same answers with them added. See `part_c/outputs/pdf/nse_filled_side_check.pdf`.
- Kaggle GPU was not needed: the data is about 2,500 rows per index and the whole project runs in a few minutes on a CPU.
