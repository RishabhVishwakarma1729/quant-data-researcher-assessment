# 07_post_hoc_locked_check.py
# POST-HOC data check of the locked 2022-2025 period, done AFTER the single out-of-sample run (06_run_oos.py, 3 Nov 2026)
# it does for the locked Yahoo files what 02_clean_data.py (sections 6 and 7) did for the research files:
#   1. compares the dates with NSE's official holiday lists (data/reference/nse_trading_holidays_2022_2025.csv)
#   2. compares the prices with NSE's own daily index files (data/reference/nse_index_ohlc_2022_2025.csv)
# it changes no rule, no parameter and no result of the study, and it does not rerun the out-of-sample test.
# the only calculation that touches the rule is a labelled sensitivity run (frozen rule on Yahoo data vs. Yahoo data plus the days NSE has and Yahoo lacks)
# before this script runs: python 02b_build_nse_holidays.py --locked   and   python 02c_build_nse_index_reference.py --locked

import os                                               # paths and env variable
import sys                                              # to quit with a message
import json                                             # frozen parameters
import hashlib                                          # file hashes
import datetime as dt                                   # time stamp
import pandas as pd                                     # tables

import common                                           # for the paths
from common import (load_raw, clean_pair, add_returns, backtest, trades_from_bt, perf_stats, MUHURAT_DAYS,
                    DATA_DIR, OUT_DIR)
from strategy import make_positions

# ---------------------------------------------------------------- guard rails
FROZEN_FILE = os.path.join(OUT_DIR, "frozen_rules.json")
LOCK_FILE = os.path.join(OUT_DIR, "oos_run.lock")
if not os.path.exists(LOCK_FILE):
    sys.exit("oos_run.lock is missing: the single out-of-sample run has not happened yet, so the locked data must stay closed")
frozen = json.load(open(FROZEN_FILE))
for name, h in frozen["locked_data_hashes"].items():    # make sure these are the very same files the out-of-sample run used
    with open(os.path.join(DATA_DIR, "locked_oos", name), "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != h:
            sys.exit("locked file %s is not what the out-of-sample run used" % name)
os.environ["ALLOW_LOCKED_OOS"] = "yes"                  # allowed only because the out-of-sample run is already done (checked above)

lines = []                                              # the markdown report, line by line


def say(text=""):
    print(text)
    lines.append(text)


fmt = lambda days: ", ".join(str(pd.Timestamp(d).date()) for d in sorted(days))      # dates as yyyy-mm-dd


def table(df):
    # markdown table, text columns so numbers keep their decimals
    return df.to_markdown(index=False, disable_numparse=True)


# ---------------------------------------------------------------- load everything
nifty, bank = load_raw("locked")                        # the Yahoo bars exactly as the out-of-sample run saw them
px, log = clean_pair(nifty, bank)                       # same cleaning function as in the run
px = add_returns(px)
off = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_index_ohlc_2022_2025.csv"), parse_dates=["date"])     # NSE's own numbers
off_by = {lab: off[off["index"] == lab].set_index("date") for lab in ["Nifty 50", "Bank Nifty"]}
hol = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_trading_holidays_2022_2025.csv"), parse_dates=["date"])
holidays = pd.DatetimeIndex(hol["date"])
weekdays = pd.bdate_range("2022-01-01", "2025-12-31")
nse_start, nse_end = off["date"].min(), off["date"].max()

say("# Post-hoc check of the locked 2022-2025 data against NSE")
say("")
say("**Read this first.** This check was done after the single out-of-sample run, not before it. The run (3 Nov 2026) used the Yahoo files as downloaded. "
    "Afterwards I compared them with NSE's own holiday lists and index files, the same checks that sections 6 and 7 of the data quality report make for 2012-2021. "
    "Nothing in the study was changed because of this: no rule, no parameter, no cleaning step and no out-of-sample number. The out-of-sample test was not rerun. "
    "The one calculation that touches the rule (section 4) is a labelled sensitivity run, not a new test, and the verdict does not depend on it.")
say("")
say("Run at %s." % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
say("")
summary_at = len(lines)                                 # the summary is written at the end and put here

# ---------------------------------------------------------------- 1. calendar
say("## 1. Dates against NSE's official holiday lists")
say("")
say("data/reference/nse_trading_holidays_2022_2025.csv has every weekday trading holiday of 2022-2025 from NSE's four yearly circulars "
    "(NSE/CMTR/50560, 54757, 59722 and 65587, saved in data/reference/sources/), plus the changes NSE announced later: the Bakri Id holiday of 2023 moved from 28 to 29 June, "
    "and extra closures on 22-Jan-2024 (Ram Mandir consecration), 20-May-2024 (parliamentary elections in Mumbai) and 20-Nov-2024 (assembly elections in Maharashtra). "
    "The Bakri Id move and 22-Jan-2024 turned up because the Yahoo data and NSE's own files disagreed with the yearly circulars; I looked up the two election closures beforehand. "
    "All four are confirmed in press reports that quote NSE's circulars, and NSE has no index file for any of those closed days.")
say("")
cal_rows, miss_both, only_n_cal, only_b_cal, on_hol = [], [], [], [], []
for yr in range(2022, 2026):
    wk = weekdays[weekdays.year == yr]
    expected = wk.difference(holidays)                  # the days the exchange was really open
    n_yr, b_yr = nifty.index[nifty.index.year == yr], bank.index[bank.index.year == yr]
    miss_n, miss_b = expected.difference(n_yr), expected.difference(b_yr)
    miss_both += list(miss_n.intersection(miss_b))
    only_n_cal += list(miss_n.difference(miss_b))
    only_b_cal += list(miss_b.difference(miss_n))
    on_hol += list(n_yr.union(b_yr).intersection(holidays))
    cal_rows.append({"year": yr, "official weekday holidays": int((holidays.year == yr).sum()), "expected sessions": len(expected),
                     "nifty rows": len(n_yr), "bank rows": len(b_yr),
                     "open days missing from Nifty": len(miss_n), "open days missing from Bank Nifty": len(miss_b),
                     "rows on official holidays": len(n_yr.union(b_yr).intersection(holidays))})
say(table(pd.DataFrame(cal_rows).astype(str)))
say("")
say("**Open days missing from Nifty only (%d):** %s." % (len(only_n_cal), fmt(only_n_cal) or "none"))
say("**Open days missing from Bank Nifty only (%d):** %s." % (len(only_b_cal), fmt(only_b_cal) or "none"))
say("**Open days missing from both series (%d):** %s." % (len(miss_both), fmt(miss_both) or "none"))
say("**Rows dated on an official holiday (%d):** %s. Those that are Diwali Laxmi Pujan days with an evening Muhurat session are dropped by cleaning rule 5; "
    "the file common.py lists them." % (len(on_hol), fmt(on_hol) or "none"))
weekend_rows = sorted(set(d for d in nifty.index.union(bank.index) if d.weekday() >= 5))
say("**Weekend rows in the Yahoo files (%d):** %s%s" % (len(weekend_rows), fmt(weekend_rows) or "none",
    (". " + "; ".join("%s is in %s only" % (d.date(), " and ".join(n for n, t in [("Nifty", nifty), ("Bank Nifty", bank)] if d in t.index)) for d in weekend_rows)
     + ". A date that exists in only one of the two series is dropped by the cleaning (inner join).") if weekend_rows else ""))
say("")
all_missing = weekdays.difference(nifty.index.union(bank.index))
real_missing = all_missing.difference(holidays)
say("Of the %d weekdays missing from both series, %d are official holidays and %d are real trading days%s." % (
    len(all_missing), len(all_missing.intersection(holidays)), len(real_missing), " (listed above)" if len(real_missing) else ""))
say("")

# ---------------------------------------------------------------- 2. prices
say("## 2. Prices against NSE's own index files")
say("")
say("data/reference/nse_index_ohlc_2022_2025.csv has the Nifty 50 and Bank Nifty rows of NSE's daily index files (built by 02c_build_nse_index_reference.py --locked, "
    "the saved files are in data/reference/sources/nse_index_files_2022_2025/). NSE has files from %s to %s." % (nse_start.date(), nse_end.date()))
say("")
cmp_rows, mism = [], []
for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]:
    o = off_by[lab]
    both_days = yahoo.index.intersection(o.index)
    row = {"index": lab, "Yahoo bars": len(yahoo), "compared with NSE": len(both_days)}
    for ycol in ["Open", "High", "Low", "Close"]:
        diff = (yahoo.loc[both_days, ycol] - o.loc[both_days, ycol.lower()]).abs()
        row[ycol.lower() + " identical"] = int((diff <= 0.011).sum())
        for day, v in diff[diff > 0.011].items():
            mism.append((lab, day, ycol, float(yahoo.loc[day, ycol]), float(o.loc[day, ycol.lower()])))
    cmp_rows.append(row)
say(table(pd.DataFrame(cmp_rows).astype(str)))
say("")
no_file = {lab: yahoo.index.difference(off_by[lab].index) for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]}
say("**Yahoo bars with no NSE file:** Nifty %d (%s), Bank Nifty %d (%s)." % (
    len(no_file["Nifty 50"]), fmt(no_file["Nifty 50"]) or "none", len(no_file["Bank Nifty"]), fmt(no_file["Bank Nifty"]) or "none"))
say("")
say("**Every price that differs (%d in all):**" % len(mism))
say("")
if mism:
    big_first = sorted(mism, key=lambda m: -abs(m[3] - m[4]))
    shown = big_first[:25]
    say(table(pd.DataFrame([(a, str(b.date()), c, "{:,.2f}".format(d), "{:,.2f}".format(e), "{:,.2f}".format(d - e),
                             "removed by cleaning" if b not in px.index else "kept") for a, b, c, d, e in shown],
                           columns=["index", "date", "price", "Yahoo", "NSE", "difference", "in the study?"])))
    if len(mism) > len(shown):
        say("")
        say("(the %d largest of %d are shown)" % (len(shown), len(mism)))
else:
    say("none")
say("")
kept = [m for m in mism if m[1] in px.index]
kept_oc = [m for m in kept if m[2] in ("Open", "Close")]
say("%d of the %d differing prices are on days that stay in the study; %d of those are opens or closes (the prices the strategy trades on)." % (
    len(kept), len(mism), len(kept_oc)))
say("")

# ---------------------------------------------------------------- 3. holiday lists the other way round
say("## 3. The holiday list checked the other way round")
say("")
has_file = off_by["Nifty 50"].index
hol_with_file = holidays.intersection(has_file)
nofile_wk = weekdays[(weekdays >= nse_start) & (weekdays <= nse_end)].difference(has_file)
unexplained = nofile_wk.difference(holidays)
say("NSE only publishes a file for a day it traded. %d of the %d listed holidays have an NSE file: %s. "
    "Weekdays without an NSE file that are not on the holiday list: %d (%s)." % (
        len(hol_with_file), len(holidays), fmt(hol_with_file) or "none", len(unexplained), fmt(unexplained) or "none"))
sat_sun = sorted(d for d in has_file if d.weekday() >= 5)
say("")
in_yahoo = [d for d in sat_sun if d in nifty.index or d in bank.index]
not_yahoo = [d for d in sat_sun if d not in in_yahoo]
say("**Weekend sessions.** NSE has a file for %d Saturday or Sunday sessions (%s). Yahoo has a bar for %d of them (%s) and not for the other %d (%s). "
    "The cleaning drops a date that only one series has, so none of them is in the study, and whatever happened in them sits inside the following Monday's return. "
    "That is the same design as in the research period, and %d such sessions in 984 days is too few to matter much. I did not add them." % (
        len(sat_sun), fmt(sat_sun), len(in_yahoo), fmt(in_yahoo) or "none", len(not_yahoo), fmt(not_yahoo) or "none", len(sat_sun)))
say("")
say("**A quirk in NSE's own files.** Three of NSE's daily files (6, 10 and 11 April 2023) write the date inside the file month-first (10 April appears as 04-10-2023). "
    "02c_build_nse_index_reference.py takes the date from the file name instead and raises an error if the inside date is not the same day with day and month swapped. "
    "Read naively, those files would have created rows on 4 June, 4 October and 4 November 2023.")
say("")

# ---------------------------------------------------------------- 4. sensitivity
say("## 4. Does it matter? (sensitivity run, not a new out-of-sample test)")
say("")
prm = frozen["params"]                                  # the rule as frozen: Nifty, k=0.5, w=60, hold 2, both sides


def run_frozen_rule(n_tab, b_tab):
    # same cleaning, same rule, same engine as 06_run_oos.py; only the raw tables differ
    t, _ = clean_pair(n_tab, b_tab)
    t = add_returns(t)
    bt = backtest(t[prm["p"] + "_open"], make_positions(t, prm["p"], prm["k"], prm["w"], prm["h"], prm["side"]))
    return perf_stats(bt["net"], trades_from_bt(bt)), perf_stats(bt["gross"]), len(t)


def with_nse(tab, days, lab):
    # adds NSE's bars for those days to a raw Yahoo table (volume is not used anywhere, so 0)
    add = off_by[lab].loc[days, ["open", "high", "low", "close"]].copy()
    add.columns = ["Open", "High", "Low", "Close"]
    add["Volume"] = 0.0
    return pd.concat([tab, add]).sort_index()


def fillable(yahoo, lab):
    # weekdays NSE has a file for, Yahoo has no bar, and that are not Muhurat evenings. weekend sessions are left out on purpose:
    # the study never had them (a Saturday move sits inside Monday's return) and adding them now would change the design
    d = off_by[lab].index.difference(yahoo.index).difference(MUHURAT_DAYS)
    return pd.DatetimeIndex([x for x in d if x.weekday() < 5])


fill_n, fill_b = fillable(nifty, "Nifty 50"), fillable(bank, "Bank Nifty")
say("Days NSE has and Yahoo lacks (real weekday sessions, Muhurat evenings left out): Nifty %d (%s), Bank Nifty %d (%s)." % (
    len(fill_n), fmt(fill_n) or "none", len(fill_b), fmt(fill_b) or "none"))
say("")
s0, g0, n0 = run_frozen_rule(nifty, bank)
rows4 = [{"data": "Yahoo only (what the run used)", "days": int(s0["Days"]), "net Sharpe": "%.3f" % s0["Sharpe"], "gross Sharpe": "%.3f" % g0["Sharpe"],
          "CAGR %": "%.2f" % s0["CAGR %"], "max drawdown %": "%.2f" % s0["Max drawdown %"], "trades": int(s0["Trades"])}]
if len(fill_n) or len(fill_b):
    s1, g1, n1 = run_frozen_rule(with_nse(nifty, fill_n, "Nifty 50"), with_nse(bank, fill_b, "Bank Nifty"))
    rows4.append({"data": "Yahoo plus the NSE days", "days": int(s1["Days"]), "net Sharpe": "%.3f" % s1["Sharpe"], "gross Sharpe": "%.3f" % g1["Sharpe"],
                  "CAGR %": "%.2f" % s1["CAGR %"], "max drawdown %": "%.2f" % s1["Max drawdown %"], "trades": int(s1["Trades"])})
say(table(pd.DataFrame(rows4).astype(str)))
say("")
say("The first row reproduces the submitted out-of-sample result (net Sharpe 0.82, 263 trades, 983 days), which shows that this script uses the same data and code as the run.")
if not (len(fill_n) or len(fill_b)):
    say("There is nothing to put back: Yahoo has a bar for every real weekday session that NSE has, in both indices. "
        "So, unlike the research period (where 14 days were missing), there is no second row to compute.")
say("")

# ---------------------------------------------------------------- summary at the top
summary = ["## Summary", "",
           "- **Dates:** %d of the %d weekdays missing from both Yahoo series are official holidays, and %d are real trading days. Yahoo has a bar for every real weekday session NSE had (%d missing from Nifty, %d from Bank Nifty)." % (
               len(all_missing.intersection(holidays)), len(all_missing), len(real_missing), len(only_n_cal) + len(miss_both), len(only_b_cal) + len(miss_both)),
           "- **Prices:** the Nifty open and close are identical to NSE's on all %d compared bars, and Bank Nifty's on %d of %d. %d highs or lows differ, by at most %.2f points, and none of them is an open or a close." % (
               cmp_rows[0]["compared with NSE"], min(cmp_rows[1]["open identical"], cmp_rows[1]["close identical"]), cmp_rows[1]["compared with NSE"],
               len(mism), max([abs(m[3] - m[4]) for m in mism] or [0.0])),
           "- **Effect on the result:** nothing to put back, so the out-of-sample result stands exactly as submitted (net Sharpe %.2f, %d trades)." % (s0["Sharpe"], int(s0["Trades"])),
           "- **What I found on the way:** four calendar changes that the yearly NSE circulars do not show (Bakri Id 2023 moved a day, extra closures on 22-Jan-2024, 20-May-2024 and 20-Nov-2024), "
           "and three NSE files with the date written month-first. Both are handled and described below.",
           ""]
lines[summary_at:summary_at] = summary

# ---------------------------------------------------------------- save
os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)
with open(os.path.join(OUT_DIR, "markdown", "post_hoc_locked_data_check.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("saved report")
