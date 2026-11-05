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

## Short version of the results

- **Part B:** the original script prints a Sharpe of 13.7 on my 2012-2021 Nifty file. The main reasons are that the label is also a feature, features use today's close, the trade cannot be executed as written, and the train/test split is shuffled. After fixing everything the Sharpe is about 0 (0.21 before costs, 0.00 after).
- **Part C:** I found one effect that survives multiple-testing correction in 2012-2021 (a big overnight gap predicts the next open-to-open return). It did not hold up in the locked 2022-2025 period (Sharpe 1.25 research, 0.82 out of sample, buy and hold 0.78, same rule on Bank Nifty -0.17). My verdict is that I would not trade it with real money.

## How to run

Python 3.12, `pip install -r requirements.txt`. From `part_c/code/`:

```
python 01_download_data.py       # only needed to re-download; the csv files are already included
python 02_clean_data.py          # step 1, data quality report (checks the dates against NSE's holiday lists and the prices against NSE's own index files)
python 02b_build_nse_holidays.py # optional: rebuilds the NSE holiday reference file from data/reference/sources
python 02c_build_nse_index_reference.py   # optional: rebuilds the NSE index price reference file (uses the saved daily files, downloads only missing ones)
python 02d_build_nse_volume_reference.py  # optional: rebuilds the NSE volume reference file from the same saved daily files (downloads nothing)
python 03_anomaly_scan.py        # step 2, all 98 tests
python 03b_gap_diagnostics.py    # checks on the one effect that survived
python test_engine.py            # sanity tests for the backtester
python 04_strategy_research.py   # steps 4-5 on the research period
python 04b_mechanism_checks.py   # where does the edge come from
python 03_anomaly_scan.py --nse-filled && python 04_strategy_research.py --nse-filled   # optional side check: scan, grid and reality check on research data plus NSE's own bars (writes only outputs/markdown/nse_filled_side_check.md)
python 07_post_hoc_locked_check.py   # optional, post-hoc: checks the locked 2022-2025 data against NSE (needs 02b, 02c and 02d with --locked first; refuses to run before the out-of-sample run)
```

`05_freeze_rules.py` and `06_run_oos.py` are part of the record but are **not meant to be re-run**. The freeze script wrote `outputs/frozen_rules.json` and the out-of-sample script wrote `outputs/oos_run.lock`, after which it refuses to run again (it also checks hashes of the code and data). `outputs/pdf/oos_results.pdf` (markdown in `outputs/markdown/`) is the output of the one real run. The script itself is hash-locked, so it still writes that report into `outputs/` if it is ever run again; I moved the file afterwards. `python 06_run_oos.py --dry-run` runs the same code on research data if you want to see that it works.

Part B: from `part_b/`, `python original_script.py`, `python corrected_script.py`, `python compare_fixes.py`.

## Notes

- The honest-out-of-sample details (what I looked at and when) are in section 2 of the research note and in `part_c/markdown/PLAN_written_before_looking_at_data.md`.
- After the single out-of-sample run I also compared the locked data with NSE's own holiday lists and index files. This was a post-hoc check made after the result was known: it found nothing to correct, changed no result, and the test was not rerun. See `part_c/outputs/pdf/post_hoc_locked_data_check.pdf`.
- The 14 trading days that Yahoo's research data lacks (NSE's own files have them) do not matter for the findings: the scan, the grid and the reality check give the same answers with them added. See `part_c/outputs/pdf/nse_filled_side_check.pdf`.
- Kaggle GPU was not needed: the data is about 2,500 rows per index and the whole project runs in a few minutes on a CPU.
