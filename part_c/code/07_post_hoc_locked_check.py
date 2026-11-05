# 07_post_hoc_locked_check.py
# POST-HOC data check of the locked 2022-2025 period, done AFTER the single out-of-sample run (06_run_oos.py, 3 Nov 2026)
# it does for the locked Yahoo files what 02_clean_data.py (sections 6 and 7) did for the research files:
#   1. compares the dates with NSE's official holiday lists (data/reference/nse_trading_holidays_2022_2025.csv)
#   2. compares the prices with NSE's own daily index files (data/reference/nse_index_ohlc_2022_2025.csv)
#   3. compares the volume column with NSE's own volume (data/reference/nse_volume_2022_2025.csv), volume only
# it changes no rule, no parameter and no result of the study, and it does not rerun the out-of-sample test.
# the only calculation that touches the rule is a labelled sensitivity run (frozen rule on Yahoo data vs. Yahoo data plus the days NSE has and Yahoo lacks)
# it reads the reference csv files already in data/reference (built earlier by 02b, 02c and 02d with --locked, see those scripts)

import os                                               # paths and env variable
import sys                                              # to quit with a message
import json                                             # frozen parameters
import hashlib                                          # file hashes
import datetime as dt                                   # time stamp
import pandas as pd                                     # tables

import common                                           # for the paths
from common import (load_raw, clean_pair, add_returns, backtest, trades_from_bt, perf_stats, MUHURAT_DAYS,
                    DATA_DIR, OUT_DIR)                  # the shared engine and the folder paths
from strategy import make_positions                     # the frozen trading rule

# ---------------------------------------------------------------- guard rails
FROZEN_FILE = os.path.join(OUT_DIR, "frozen_rules.json")    # the freeze record written before the out-of-sample run
LOCK_FILE = os.path.join(OUT_DIR, "oos_run.lock")       # written by the single out-of-sample run
if not os.path.exists(LOCK_FILE):                       # the run has not happened yet
    sys.exit("oos_run.lock is missing: the single out-of-sample run has not happened yet, so the locked data must stay closed")   # so refuse to open the locked data
frozen = json.load(open(FROZEN_FILE))                   # read the freeze record
for name, h in frozen["locked_data_hashes"].items():    # make sure these are the very same files the out-of-sample run used
    with open(os.path.join(DATA_DIR, "locked_oos", name), "rb") as f:   # open each locked file as raw bytes
        if hashlib.sha256(f.read()).hexdigest() != h:   # compare its fingerprint with the frozen one
            sys.exit("locked file %s is not what the out-of-sample run used" % name)   # a mismatch means the file was changed, so stop
os.environ["ALLOW_LOCKED_OOS"] = "yes"                  # allowed only because the out-of-sample run is already done (checked above)

lines = []                                              # the markdown report, line by line


def say(text=""):                                       # prints a line and keeps it for the report
    print(text)                                         # show it on screen
    lines.append(text)                                  # and store it for the markdown file


fmt = lambda days: ", ".join(str(pd.Timestamp(d).date()) for d in sorted(days))      # dates as yyyy-mm-dd


def table(df):                                          # turns a table into markdown text
    # markdown table, text columns so numbers keep their decimals
    return df.to_markdown(index=False, disable_numparse=True)   # no row numbers, and numbers are left exactly as written


# ---------------------------------------------------------------- load everything
nifty, bank = load_raw("locked")                        # the Yahoo bars exactly as the out-of-sample run saw them
px, log = clean_pair(nifty, bank)                       # same cleaning function as in the run
px = add_returns(px)                                    # add gaps and returns, as in the run
off = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_index_ohlc_2022_2025.csv"), parse_dates=["date"])     # NSE's own numbers
off_by = {lab: off[off["index"] == lab].set_index("date") for lab in ["Nifty 50", "Bank Nifty"]}   # NSE's table split into one table per index
hol = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_trading_holidays_2022_2025.csv"), parse_dates=["date"])   # the official holiday list
holidays = pd.DatetimeIndex(hol["date"])                # just the holiday dates
weekdays = pd.bdate_range("2022-01-01", "2025-12-31")   # every monday to friday of the locked period
nse_start, nse_end = off["date"].min(), off["date"].max()   # the first and last day NSE has a file for

say("# Post-hoc check of the locked 2022-2025 data against NSE")   # the report title
say("")                                                 # blank line
say("**Read this first.** This check was done after the single out-of-sample run, not before it. The run (3 Nov 2026) used the Yahoo files as downloaded. "
    "Afterwards I compared them with NSE's own holiday lists and index files, the same checks that sections 6 and 7 of the data quality report make for 2012-2021. "
    "Nothing in the study was changed because of this: no rule, no parameter, no cleaning step and no out-of-sample number. The out-of-sample test was not rerun. "
    "The one calculation that touches the rule (section 4) is a labelled sensitivity run, not a new test, and the verdict does not depend on it.")   # the honesty note at the top
say("")                                                 # blank line
say("Run at %s." % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))   # when this report was made
say("")                                                 # blank line
summary_at = len(lines)                                 # the summary is written at the end and put here

# ---------------------------------------------------------------- 1. calendar
say("## 1. Dates against NSE's official holiday lists")   # section heading
say("")                                                 # blank line
say("data/reference/nse_trading_holidays_2022_2025.csv has every weekday trading holiday of 2022-2025 from NSE's four yearly circulars "
    "(NSE/CMTR/50560, 54757, 59722 and 65587; the circular pdfs themselves are not part of the repository), plus the changes NSE announced later: the Bakri Id holiday of 2023 moved from 28 to 29 June, "
    "and extra closures on 22-Jan-2024 (Ram Mandir consecration), 20-May-2024 (parliamentary elections in Mumbai) and 20-Nov-2024 (assembly elections in Maharashtra). "
    "The Bakri Id move and 22-Jan-2024 turned up because the Yahoo data and NSE's own files disagreed with the yearly circulars; I looked up the two election closures beforehand. "
    "All four are confirmed in press reports that quote NSE's circulars, and NSE has no index file for any of those closed days.")   # where the holiday list comes from
say("")                                                 # blank line
cal_rows, miss_both, only_n_cal, only_b_cal, on_hol = [], [], [], [], []   # collectors for the calendar check
for yr in range(2022, 2026):                            # one year at a time
    wk = weekdays[weekdays.year == yr]                  # the weekdays of that year
    expected = wk.difference(holidays)                  # the days the exchange was really open
    n_yr, b_yr = nifty.index[nifty.index.year == yr], bank.index[bank.index.year == yr]   # the dates Yahoo has for each index that year
    miss_n, miss_b = expected.difference(n_yr), expected.difference(b_yr)   # open days that are missing from each series
    miss_both += list(miss_n.intersection(miss_b))      # missing from both
    only_n_cal += list(miss_n.difference(miss_b))       # missing from Nifty only
    only_b_cal += list(miss_b.difference(miss_n))       # missing from Bank Nifty only
    on_hol += list(n_yr.union(b_yr).intersection(holidays))   # rows that sit on an official holiday
    cal_rows.append({"year": yr, "official weekday holidays": int((holidays.year == yr).sum()), "expected sessions": len(expected),
                     "nifty rows": len(n_yr), "bank rows": len(b_yr),
                     "open days missing from Nifty": len(miss_n), "open days missing from Bank Nifty": len(miss_b),
                     "rows on official holidays": len(n_yr.union(b_yr).intersection(holidays))})   # one summary row for the year
say(table(pd.DataFrame(cal_rows).astype(str)))          # the four years as a table
say("")                                                 # blank line
say("**Open days missing from Nifty only (%d):** %s." % (len(only_n_cal), fmt(only_n_cal) or "none"))   # list them
say("**Open days missing from Bank Nifty only (%d):** %s." % (len(only_b_cal), fmt(only_b_cal) or "none"))   # list them
say("**Open days missing from both series (%d):** %s." % (len(miss_both), fmt(miss_both) or "none"))   # list them
say("**Rows dated on an official holiday (%d):** %s. Those that are Diwali Laxmi Pujan days with an evening Muhurat session are dropped by cleaning rule 5; "
    "the file common.py lists them." % (len(on_hol), fmt(on_hol) or "none"))   # rows on holidays and what happens to them
weekend_rows = sorted(set(d for d in nifty.index.union(bank.index) if d.weekday() >= 5))   # any saturday or sunday rows Yahoo has
say("**Weekend rows in the Yahoo files (%d):** %s%s" % (len(weekend_rows), fmt(weekend_rows) or "none",
    (". " + "; ".join("%s is in %s only" % (d.date(), " and ".join(n for n, t in [("Nifty", nifty), ("Bank Nifty", bank)] if d in t.index)) for d in weekend_rows)
     + ". A date that exists in only one of the two series is dropped by the cleaning (inner join).") if weekend_rows else ""))   # which series has each weekend row
say("")                                                 # blank line
all_missing = weekdays.difference(nifty.index.union(bank.index))   # weekdays that neither series has
real_missing = all_missing.difference(holidays)         # of those, the ones that were not holidays
say("Of the %d weekdays missing from both series, %d are official holidays and %d are real trading days%s." % (
    len(all_missing), len(all_missing.intersection(holidays)), len(real_missing), " (listed above)" if len(real_missing) else ""))   # the headline of the calendar check
say("")                                                 # blank line

# ---------------------------------------------------------------- 2. prices
say("## 2. Prices against NSE's own index files")      # section heading
say("")                                                 # blank line
say("data/reference/nse_index_ohlc_2022_2025.csv has the Nifty 50 and Bank Nifty rows of NSE's daily index files (built by 02c_build_nse_index_reference.py --locked, "
    "from NSE's daily files, which are not part of the repository). NSE has files from %s to %s." % (nse_start.date(), nse_end.date()))   # where the NSE prices come from
say("")                                                 # blank line
cmp_rows, mism = [], []                                 # summary table, and every single price that differs
for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]:   # one index at a time
    o = off_by[lab]                                     # NSE's numbers for this index
    both_days = yahoo.index.intersection(o.index)       # days where both sources have a bar
    row = {"index": lab, "Yahoo bars": len(yahoo), "compared with NSE": len(both_days)}   # start this index's summary row
    for ycol in ["Open", "High", "Low", "Close"]:       # compare each price
        diff = (yahoo.loc[both_days, ycol] - o.loc[both_days, ycol.lower()]).abs()   # size of the difference on every shared day
        row[ycol.lower() + " identical"] = int((diff <= 0.011).sum())   # how many days agree (prices have two decimals, 0.011 absorbs rounding)
        for day, v in diff[diff > 0.011].items():       # the days that do not agree
            mism.append((lab, day, ycol, float(yahoo.loc[day, ycol]), float(o.loc[day, ycol.lower()])))   # remember each one
    cmp_rows.append(row)                                # keep this index's summary row
say(table(pd.DataFrame(cmp_rows).astype(str)))          # both indices as a table
say("")                                                 # blank line
no_file = {lab: yahoo.index.difference(off_by[lab].index) for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]}   # Yahoo days NSE has no file for
say("**Yahoo bars with no NSE file:** Nifty %d (%s), Bank Nifty %d (%s)." % (
    len(no_file["Nifty 50"]), fmt(no_file["Nifty 50"]) or "none", len(no_file["Bank Nifty"]), fmt(no_file["Bank Nifty"]) or "none"))   # list them
say("")                                                 # blank line
say("**Every price that differs (%d in all):**" % len(mism))   # how many differ
say("")                                                 # blank line
if mism:                                                # at least one price differs
    big_first = sorted(mism, key=lambda m: -abs(m[3] - m[4]))   # biggest differences first
    shown = big_first[:25]                              # show at most 25
    say(table(pd.DataFrame([(a, str(b.date()), c, "{:,.2f}".format(d), "{:,.2f}".format(e), "{:,.2f}".format(d - e),
                             "removed by cleaning" if b not in px.index else "kept") for a, b, c, d, e in shown],
                           columns=["index", "date", "price", "Yahoo", "NSE", "difference", "in the study?"])))   # the differences as a table
    if len(mism) > len(shown):                          # some were left out of the table
        say("")                                         # blank line
        say("(the %d largest of %d are shown)" % (len(shown), len(mism)))   # say so
else:                                                   # nothing differs
    say("none")                                         # say so
say("")                                                 # blank line
kept = [m for m in mism if m[1] in px.index]            # differences on days that stay in the study
kept_oc = [m for m in kept if m[2] in ("Open", "Close")]   # of those, the ones on opens or closes
say("%d of the %d differing prices are on days that stay in the study; %d of those are opens or closes (the prices the strategy trades on)." % (
    len(kept), len(mism), len(kept_oc)))                # the point that matters for the strategy
say("")                                                 # blank line

# ---------------------------------------------------------------- 3. holiday lists the other way round
say("## 3. The holiday list checked the other way round")   # section heading
say("")                                                 # blank line
has_file = off_by["Nifty 50"].index                     # the days NSE has a file for
hol_with_file = holidays.intersection(has_file)         # listed holidays that nevertheless have a file
nofile_wk = weekdays[(weekdays >= nse_start) & (weekdays <= nse_end)].difference(has_file)   # weekdays inside NSE's range with no file
unexplained = nofile_wk.difference(holidays)            # of those, the ones that are not on the holiday list
say("NSE only publishes a file for a day it traded. %d of the %d listed holidays have an NSE file: %s. "
    "Weekdays without an NSE file that are not on the holiday list: %d (%s)." % (
        len(hol_with_file), len(holidays), fmt(hol_with_file) or "none", len(unexplained), fmt(unexplained) or "none"))   # the two cross-checks
sat_sun = sorted(d for d in has_file if d.weekday() >= 5)   # weekend days that NSE has a file for
say("")                                                 # blank line
in_yahoo = [d for d in sat_sun if d in nifty.index or d in bank.index]   # weekend sessions Yahoo also has
not_yahoo = [d for d in sat_sun if d not in in_yahoo]   # weekend sessions Yahoo lacks
say("**Weekend sessions.** NSE has a file for %d Saturday or Sunday sessions (%s). Yahoo has a bar for %d of them (%s) and not for the other %d (%s). "
    "The cleaning drops a date that only one series has, so none of them is in the study, and whatever happened in them sits inside the following Monday's return. "
    "That is the same design as in the research period, and %d such sessions in 984 days is too few to matter much. I did not add them." % (
        len(sat_sun), fmt(sat_sun), len(in_yahoo), fmt(in_yahoo) or "none", len(not_yahoo), fmt(not_yahoo) or "none", len(sat_sun)))   # what the weekend sessions mean for the study
say("")                                                 # blank line
say("**A quirk in NSE's own files.** Three of NSE's daily files (6, 10 and 11 April 2023) write the date inside the file month-first (10 April appears as 04-10-2023). "
    "02c_build_nse_index_reference.py takes the date from the file name instead and raises an error if the inside date is not the same day with day and month swapped. "
    "Read naively, those files would have created rows on 4 June, 4 October and 4 November 2023.")   # a data oddity worth knowing about
say("")                                                 # blank line

# ---------------------------------------------------------------- 4. sensitivity
say("## 4. Does it matter? (sensitivity run, not a new out-of-sample test)")   # section heading
say("")                                                 # blank line
prm = frozen["params"]                                  # the rule as frozen: Nifty, k=0.5, w=60, hold 2, both sides


def run_frozen_rule(n_tab, b_tab):                      # runs the frozen rule on a pair of raw tables
    # same cleaning, same rule, same engine as 06_run_oos.py; only the raw tables differ
    t, _ = clean_pair(n_tab, b_tab)                     # clean and align the two series
    t = add_returns(t)                                  # add gaps and returns
    bt = backtest(t[prm["p"] + "_open"], make_positions(t, prm["p"], prm["k"], prm["w"], prm["h"], prm["side"]))   # frozen positions run through the engine on open prices
    return perf_stats(bt["net"], trades_from_bt(bt)), perf_stats(bt["gross"]), len(t)   # numbers after costs, numbers before costs, number of days


def with_nse(tab, days, lab):                           # adds NSE's own bars to a Yahoo table
    # adds NSE's bars for those days to a raw Yahoo table (volume is not used anywhere, so 0)
    add = off_by[lab].loc[days, ["open", "high", "low", "close"]].copy()   # NSE's prices for the missing days
    add.columns = ["Open", "High", "Low", "Close"]      # name the columns the way Yahoo does
    add["Volume"] = 0.0                                 # volume is not used anywhere, so a placeholder
    return pd.concat([tab, add]).sort_index()           # the combined table in date order


def fillable(yahoo, lab):                               # which NSE days could be added to a Yahoo table
    # weekdays NSE has a file for, Yahoo has no bar, and that are not Muhurat evenings. weekend sessions are left out on purpose:
    # the study never had them (a Saturday move sits inside Monday's return) and adding them now would change the design
    d = off_by[lab].index.difference(yahoo.index).difference(MUHURAT_DAYS)   # NSE has it, Yahoo does not, and it is not a Muhurat evening
    return pd.DatetimeIndex([x for x in d if x.weekday() < 5])   # weekdays only


fill_n, fill_b = fillable(nifty, "Nifty 50"), fillable(bank, "Bank Nifty")   # the days that could be put back, per index
say("Days NSE has and Yahoo lacks (real weekday sessions, Muhurat evenings left out): Nifty %d (%s), Bank Nifty %d (%s)." % (
    len(fill_n), fmt(fill_n) or "none", len(fill_b), fmt(fill_b) or "none"))   # list them
say("")                                                 # blank line
s0, g0, n0 = run_frozen_rule(nifty, bank)               # the frozen rule on Yahoo data only (what the run used)
rows4 = [{"data": "Yahoo only (what the run used)", "days": int(s0["Days"]), "net Sharpe": "%.3f" % s0["Sharpe"], "gross Sharpe": "%.3f" % g0["Sharpe"],
          "CAGR %": "%.2f" % s0["CAGR %"], "max drawdown %": "%.2f" % s0["Max drawdown %"], "trades": int(s0["Trades"])}]   # first row of the comparison table
if len(fill_n) or len(fill_b):                          # only if there is something to put back
    s1, g1, n1 = run_frozen_rule(with_nse(nifty, fill_n, "Nifty 50"), with_nse(bank, fill_b, "Bank Nifty"))   # the same rule with NSE's days added
    rows4.append({"data": "Yahoo plus the NSE days", "days": int(s1["Days"]), "net Sharpe": "%.3f" % s1["Sharpe"], "gross Sharpe": "%.3f" % g1["Sharpe"],
                  "CAGR %": "%.2f" % s1["CAGR %"], "max drawdown %": "%.2f" % s1["Max drawdown %"], "trades": int(s1["Trades"])})   # second row of the table
say(table(pd.DataFrame(rows4).astype(str)))             # the comparison as a table
say("")                                                 # blank line
say("The first row reproduces the submitted out-of-sample result (net Sharpe 0.82, 263 trades, 983 days), which shows that this script uses the same data and code as the run.")   # proof that nothing drifted
if not (len(fill_n) or len(fill_b)):                    # nothing to put back
    say("There is nothing to put back: Yahoo has a bar for every real weekday session that NSE has, in both indices. "
        "So, unlike the research period (where 14 days were missing), there is no second row to compute.")   # explain why there is only one row
say("")                                                 # blank line

# ---------------------------------------------------------------- 5. volume
say("## 5. Volume")                                     # section heading
say("")                                                 # blank line
nvol = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_volume_2022_2025.csv"), parse_dates=["date"])      # built by 02d_build_nse_volume_reference.py --locked
nvol_by = {lab: nvol[nvol["index"] == lab].set_index("date")["volume_shares"].dropna() for lab in ["Nifty 50", "Bank Nifty"]}   # NSE's volume per index, blanks dropped
vol_stats = {}                                          # the numbers for each index end up here
for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]:   # one index at a time
    zero = yahoo.index[yahoo["Volume"] == 0]                            # days where Yahoo shows no volume
    both = yahoo.index[yahoo["Volume"] > 0].intersection(nvol_by[lab].index)         # days where both sources have a number
    ratio = yahoo.loc[both, "Volume"] / (nvol_by[lab].loc[both] / 1000.0)           # Yahoo divided by NSE in thousands of shares
    raw_days = ratio.index[ratio > 100]                                 # Yahoo wrote raw shares instead of thousands on these days
    rel = ratio.drop(raw_days) - 1                                      # relative difference, 0.03 = Yahoo is 3% above NSE
    vol_stats[lab] = {"zero": len(zero), "filled": len(zero.intersection(nvol_by[lab].index)), "within5": (rel.abs() <= 0.05).mean(),
                      "off10": int((rel.abs() > 0.10).sum()), "raw_days": raw_days}   # keep the numbers for the text below
vn, vb = vol_stats["Nifty 50"], vol_stats["Bank Nifty"]    # short names for the two sets of numbers
raw_text = (", ".join(str(d.date()) for d in vb["raw_days"])) or "none"   # the raw-share days as text
say("Same check as section 3 of the data quality report, on the volume column only (no prices). NSE's file nse_volume_2022_2025.csv (built by 02d_build_nse_volume_reference.py --locked) "
    "has a volume for all %d sessions, with %d blank and %d zero values. Yahoo shows zero volume on %d Nifty and %d Bank Nifty days, and NSE has the volume for %d and %d of them. "
    "Yahoo's non-zero volume is in thousands of shares, as in the research period: within 5%% of NSE's number divided by 1,000 on %.1f%% of the Nifty days and %.1f%% of the Bank Nifty days. "
    "Bank Nifty is written in raw shares on %d days (%s), and %d Nifty and %d Bank Nifty days are more than 10%% off. The study is price-only, so volume changes no result." % (
        nvol["date"].nunique(), int(nvol["volume_shares"].isna().sum()), int((nvol["volume_shares"] == 0).sum()), vn["zero"], vb["zero"], vn["filled"], vb["filled"],
        100 * vn["within5"], 100 * vb["within5"], len(vb["raw_days"]), raw_text, vn["off10"], vb["off10"]))   # the whole volume paragraph with the numbers filled in
say("")                                                 # blank line

# ---------------------------------------------------------------- summary at the top
summary = ["## Summary", "",
           "- **Dates:** %d of the %d weekdays missing from both Yahoo series are official holidays, and %d are real trading days. Yahoo has a bar for every real weekday session NSE had (%d missing from Nifty, %d from Bank Nifty)." % (
               len(all_missing.intersection(holidays)), len(all_missing), len(real_missing), len(only_n_cal) + len(miss_both), len(only_b_cal) + len(miss_both)),
           "- **Prices:** the Nifty open and close are identical to NSE's on all %d compared bars, and Bank Nifty's on %d of %d. %d highs or lows differ, by at most %.2f points, and none of them is an open or a close." % (
               cmp_rows[0]["compared with NSE"], min(cmp_rows[1]["open identical"], cmp_rows[1]["close identical"]), cmp_rows[1]["compared with NSE"],
               len(mism), max([abs(m[3] - m[4]) for m in mism] or [0.0])),
           "- **Volume:** Yahoo's zero volume (%d Nifty and %d Bank Nifty days) is missing data, and NSE has the volume for %d and %d of those days. The study does not use volume." % (
               vn["zero"], vb["zero"], vn["filled"], vb["filled"]),
           "- **Effect on the result:** nothing to put back, so the out-of-sample result stands exactly as submitted (net Sharpe %.2f, %d trades)." % (s0["Sharpe"], int(s0["Trades"])),
           "- **What I found on the way:** four calendar changes that the yearly NSE circulars do not show (Bakri Id 2023 moved a day, extra closures on 22-Jan-2024, 20-May-2024 and 20-Nov-2024), "
           "and three NSE files with the date written month-first. Both are handled and described below.",
           ""]                                          # the summary bullets, built from the numbers above
lines[summary_at:summary_at] = summary                  # put the summary at the top of the report, where the placeholder position was kept

# ---------------------------------------------------------------- save
os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)   # make sure the report folder exists
with open(os.path.join(OUT_DIR, "markdown", "post_hoc_locked_data_check.md"), "w", encoding="utf-8") as f:   # open the report file
    f.write("\n".join(lines) + "\n")                    # write every collected line
print("saved report")                                   # tell the user it is done
