# 02_clean_data.py
# step 1 of the case study: clean + align the two series and write a data quality report
# only the research period (2012-2021) is used here

import os                                   # paths
import json                                 # to read the frozen parameters
import numpy as np                          # maths
import pandas as pd                         # tables
import matplotlib
matplotlib.use("Agg")                       # no pop-up windows, the figure is simply saved to a file
import matplotlib.pyplot as plt             # plotting

from common import (load_raw, clean_pair, add_returns, backtest, trades_from_bt, perf_stats, MUHURAT_DAYS,
                    DATA_DIR, FIG_DIR, TAB_DIR, OUT_DIR)
from strategy import make_positions         # only used in section 7, to see whether the result depends on the days Yahoo is missing

os.makedirs(FIG_DIR, exist_ok=True)         # make sure output folders exist
os.makedirs(TAB_DIR, exist_ok=True)

# ---------------------------------------------------------------- load raw
nifty, bank = load_raw("research")          # raw tables straight from the download
lines = []                                  # i collect the markdown report line by line in here


def say(text=""):
    # small helper: print to screen and keep for the report file
    print(text)
    lines.append(text)


say("# Data quality report (research period 2012-2021)")
say("")
say("Source: Yahoo Finance (tickers ^NSEI and ^NSEBANK) through the yfinance package. Raw, unadjusted daily bars.")
say("Indices have no splits or dividends so no adjustment is needed. Section 3 compares the volume with NSE's own numbers, section 6 checks the dates against NSE's holiday lists and section 7 checks the prices against NSE's own index files.")
say("")

# ---------------------------------------------------------------- 1. rows per year vs weekdays
say("## 1. How many days do we have")
weekdays = pd.bdate_range("2012-01-01", "2021-12-31")               # every Mon-Fri in the period
wk_per_year = pd.Series(1, index=weekdays).groupby(weekdays.year).sum()
tab = pd.DataFrame({
    "weekdays": wk_per_year,
    "nifty_rows": nifty.groupby(nifty.index.year).size(),
    "bank_rows": bank.groupby(bank.index.year).size(),
})
# weekdays that are missing from BOTH series, these should be exchange holidays
union = nifty.index.union(bank.index)
missing_both = weekdays.difference(union)
tab["weekdays_missing_in_both"] = pd.Series(1, index=missing_both).groupby(missing_both.year).sum()
tab = tab.fillna(0).astype(int)
say(tab.to_markdown())
say("")
say("NSE had between 12 and 19 weekday trading holidays a year in this period (section 6 checks every date against the official lists).")
say("Nearly all of the 'missing in both' days are official holidays, but not all of them: three are real trading days that Yahoo is missing in both series.")
say("")

# ---------------------------------------------------------------- 2. dates that only one series has
say("## 2. Dates in one series but not the other")
only_b = bank.index.difference(nifty.index)
only_n = nifty.index.difference(bank.index)
say("Nifty-only dates: %d. Bank-Nifty-only dates: %d." % (len(only_n), len(only_b)))
say("")
say(pd.DataFrame({"date": only_b.date, "weekday": only_b.day_name(),
                  "bank_close": bank.loc[only_b, "Close"].round(1).values,
                  "bank_volume": bank.loc[only_b, "Volume"].values}).to_markdown(index=False))
say("")
say("Six of these are 1 January. NSE trades on 1 January, and these Bank Nifty rows have normal looking ranges,")
say("so my reading was that Yahoo's Nifty series is the one with holes (it also misses 2-Jan-2012 and 12-Aug-2016, both ordinary trading days).")
say("Section 6 confirms this against NSE's official holiday lists: none of these 12 dates is an NSE holiday, so all 12 are real trading days missing from Yahoo's Nifty series.")
say("What I did: keep only dates present in both series. The cost is that the first return after a missing day covers two sessions.")
say("")

# ---------------------------------------------------------------- 3. zero volume
say("## 3. Volume")
vol = pd.DataFrame({
    "nifty_zero_volume_days": (nifty["Volume"] == 0).groupby(nifty.index.year).sum(),
    "bank_zero_volume_days": (bank["Volume"] == 0).groupby(bank.index.year).sum(),
})
say(vol.to_markdown())
say("")

# NSE's own volume for the same days (02d_build_nse_volume_reference.py reads the daily files saved for section 7)
nvol = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_volume_2012_2021.csv"), parse_dates=["date"])
nvol_by = {lab: nvol[nvol["index"] == lab].set_index("date")["volume_shares"].dropna() for lab in ["Nifty 50", "Bank Nifty"]}
nse_vol_start = nvol["date"].min()                                      # NSE's files start here
zero_rows, no_source, unit_stats, odd_units = [], {}, {}, {}
for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]:
    zero = yahoo.index[yahoo["Volume"] == 0]                            # days where Yahoo shows no volume
    can_fill = zero.intersection(nvol_by[lab].index)                    # NSE has a number for these
    no_source[lab] = zero.difference(nvol_by[lab].index)                # neither source has one
    zero_rows.append({"index": lab, "days with zero volume in Yahoo": len(zero), "NSE has the volume for": len(can_fill), "no volume from either": len(no_source[lab])})
    both = yahoo.index[yahoo["Volume"] > 0].intersection(nvol_by[lab].index)         # days where both sources have a number
    ratio = yahoo.loc[both, "Volume"] / (nvol_by[lab].loc[both] / 1000.0)           # Yahoo divided by NSE in thousands of shares
    odd_units[lab] = ratio.index[ratio > 100]                           # Yahoo wrote raw shares instead of thousands on these days
    ratio = ratio.drop(odd_units[lab]) - 1                              # relative difference, 0.03 = Yahoo is 3% above NSE
    low_years = [int(y) for y, m in ratio.groupby(ratio.index.year).median().items() if m < -0.02]     # years where Yahoo sits clearly below NSE
    unit_stats[lab] = {"first": both[0], "within5": (ratio.abs() <= 0.05).mean(), "off10": int((ratio.abs() > 0.10).sum()),
                       "low_years": low_years, "low_gap": -ratio[ratio.index.year.isin(low_years)].median() if low_years else 0.0}
say("**NSE has the volume that Yahoo lacks.** NSE's index files carry the volume too (data/reference/nse_volume_2012_2021.csv, built by 02d_build_nse_volume_reference.py). "
    "From %s on it has a number for every day, with no blank and no zero. Yahoo's zero volume is therefore missing data and not a day without trading, and NSE can fill most of it:" % nse_vol_start.date())
say("")
say(pd.DataFrame(zero_rows).to_markdown(index=False))
say("")
early_vol = [d for d in no_source["Nifty 50"] if d < nse_vol_start]                          # the stretch before NSE's files begin
late_vol = sorted(set(no_source["Nifty 50"]).union(no_source["Bank Nifty"]) - set(early_vol))   # days NSE's archive lacks
say("The days without a volume from either source are the %d trading days from %s to %s, before NSE's files begin%s." % (
    len(early_vol), early_vol[0].date(), early_vol[-1].date(),
    (", and %d later Bank Nifty days that NSE's archive lacks (%s)" % (len(late_vol), ", ".join(str(d.date()) for d in late_vol))) if late_vol else ""))
say("")
n_st, b_st = unit_stats["Nifty 50"], unit_stats["Bank Nifty"]
n_day = n_st["first"]                                                   # first day on which Nifty has a number in both sources
b_day = bank.index[(bank["Volume"] > 0) & (bank.index.year == 2012)].intersection(nvol_by["Bank Nifty"].index)[0]      # a small 2012 Bank Nifty number we can check
yrs = [str(y) for y in n_st["low_years"]]
yrs_text = (", ".join(yrs[:-1]) + " and " + yrs[-1]) if len(yrs) > 1 else "".join(yrs)           # "2015, 2016 and 2017"
low_text = "Nifty runs about %.0f%% below NSE in %s" % (100 * n_st["low_gap"], yrs_text) if yrs else "Nifty has no clear gap"
raw_days = ", ".join(str(d.date()) for d in odd_units["Bank Nifty"])    # days Yahoo wrote raw shares instead of thousands
say(f"**What Yahoo's non-zero volume is.** It is in thousands of shares, not shares: on {n_day.date()} Yahoo has {nifty.loc[n_day, 'Volume']:,.0f} for Nifty "
    f"and NSE has {nvol_by['Nifty 50'].loc[n_day]:,.0f}. Against NSE's number divided by 1,000, Yahoo is within 5% on {100 * n_st['within5']:.1f}% of the Nifty days "
    f"and {100 * b_st['within5']:.1f}% of the Bank Nifty days. It is not clean, though: {low_text}; Bank Nifty is written in raw shares on "
    f"{len(odd_units['Bank Nifty'])} days ({raw_days}); and {n_st['off10']} Nifty and {b_st['off10']} Bank Nifty days are more than 10% off. "
    f"So the small non-zero numbers in 2012 are real and not unreliable (Bank Nifty on {b_day.date()}: Yahoo {bank.loc[b_day, 'Volume']:,.0f}, NSE {nvol_by['Bank Nifty'].loc[b_day]:,.0f} shares).")
say("")
say("**I decided not to use volume anywhere in the study.** Price-only, so none of this changes a result. If volume were ever needed, NSE's file is the better source.")
say("")

# ---------------------------------------------------------------- 4. run the cleaning rules
px, log = clean_pair(nifty, bank)
say("## 4. Cleaning rules and what they removed")
rows = []
for rule, idx, n, detail in log:
    # a list of dates is shown as plain yyyy-mm-dd text, python's list-of-dates format is hard to read in a table
    if isinstance(detail, list):
        detail = ", ".join(str(d) for d in detail)
    rows.append({"rule": rule, "series": idx, "rows": n, "details": detail})
say(pd.DataFrame(rows).to_markdown(index=False))
say("")
say("Bad print: Bank Nifty on 10-Nov-2016 has open = high = low = close = 20200.25 and zero volume. It's a placeholder row.")
say("Muhurat sessions are one hour long evening sessions on Diwali. Their open-to-close move isn't comparable to a normal day, so I dropped them.")
say("Final clean table: %d rows, %s to %s." % (len(px), px.index.min().date(), px.index.max().date()))
say("")

# ---------------------------------------------------------------- 5. returns + outliers
px = add_returns(px)
say("## 5. Outliers")
big = px[(px["n_ret"].abs() > 0.05) | (px["b_ret"].abs() > 0.05)][["n_ret", "b_ret", "n_gap", "b_gap"]] * 100
big = big.round(2)


def explain(d):
    # i only label what i'm sure about, everything else in the covid window gets a generic label
    d = pd.Timestamp(d)
    known = {"2013-09-05": "RBI governor change (Rajan), banks rally",
             "2015-08-24": "global sell-off (China), 'Black Monday'",
             "2016-11-09": "day after demonetisation announcement",
             "2019-09-20": "corporate tax cut announced",
             "2021-02-01": "union budget day",
             "2021-04-12": "second covid wave in India",
             "2013-08-16": "rupee sell-off, 2013", "2013-08-27": "rupee sell-off, 2013",
             "2013-09-03": "rupee sell-off, 2013"}
    if str(d.date()) in known:
        return known[str(d.date())]
    if pd.Timestamp("2020-03-01") <= d <= pd.Timestamp("2020-06-30"):
        return "covid crash / lockdown period"
    return "not labelled"


big["what happened"] = [explain(d) for d in big.index]
big.index = big.index.date
big.columns = ["nifty ret %", "bank ret %", "nifty gap %", "bank gap %", "what happened"]
say("Days where either index moved more than 5% close to close:")
say("")
say(big.to_markdown())
say("")
say("On every one of these days Nifty and Bank Nifty moved in the same direction, which is what a real market event looks like")
say("and not what a bad print looks like. I can name the cause for some of the days (see last column) but not all of them.")
say("**I did not remove or winsorise them.** Removing the crash days would make risk look much smaller than it really is,")
say("and fat tails are one of the things the brief asks about. Where an outlier could drive a test, I show the result with and without 2020.")
say("")

# unchanged closes
same = px[px["n_close"].diff() == 0].index
say("Nifty closed at exactly the same level as the previous day on %d days (%s)." % (len(same), ", ".join(str(d.date()) for d in same)))
say("Their ranges and volumes look normal. With a 0.05 tick and daily moves of ~60 points I'd expect about one such coincidence in 10 years,")
say("so three is a bit high but not alarming. I left them in (they are real bars, just with an unchanged close).")
say("")

# ---------------------------------------------------------------- 6. check against nse's official holiday lists
say("## 6. Check against NSE's official holiday lists")
say("")
say("The file data/reference/nse_trading_holidays_2012_2021.csv has every weekday trading holiday of 2012-2021 with its source on each row.")
say("2012, 2015 and 2016 come from NSE's own website (archived pages), 2017-2021 from NSE's yearly circulars, and 2013 and 2014 from Zerodha's copy of the exchange list")
say("(NSE's archived pages for those two years load their tables with scripts, so I could not read them). Closures announced later are included with a note:")
say("the Muharram move in 2013, the two 2014 and two 2019 election days, and 11-Nov-2015 (Diwali, Muhurat session only). Section 7 checks the lists again, 2013 and 2014 included, against NSE's own index files.")
say("")
ref = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_trading_holidays_2012_2021.csv"), parse_dates=["date"])   # official weekday holidays
holidays = pd.DatetimeIndex(ref["date"])                    # just the dates
cal_rows = []                                               # one line per year for the table
miss_both, only_n_cal, only_b_cal, on_hol = [], [], [], []  # the exceptions, collected over all years
for yr in range(2012, 2022):
    wk = weekdays[weekdays.year == yr]                      # every Mon-Fri of the year
    expected = wk.difference(holidays)                      # the days the exchange was really open
    n_yr = nifty.index[nifty.index.year == yr]              # raw nifty dates of that year
    b_yr = bank.index[bank.index.year == yr]                # raw bank nifty dates of that year
    miss_n, miss_b = expected.difference(n_yr), expected.difference(b_yr)     # open days that a series does not have
    miss_both += list(miss_n.intersection(miss_b))
    only_n_cal += list(miss_n.difference(miss_b))
    only_b_cal += list(miss_b.difference(miss_n))
    on_hol += list(n_yr.union(b_yr).intersection(holidays))                  # rows dated on a day the exchange was closed
    cal_rows.append({"year": yr, "official weekday holidays": int((holidays.year == yr).sum()), "expected sessions": len(expected),
                     "nifty rows": len(n_yr), "bank rows": len(b_yr),
                     "open days missing from Nifty": len(miss_n), "open days missing from Bank Nifty": len(miss_b),
                     "rows on official holidays": len(n_yr.union(b_yr).intersection(holidays))})
say(pd.DataFrame(cal_rows).to_markdown(index=False))
say("")
fmt = lambda days: ", ".join(str(d.date()) for d in sorted(days))
say("**Open days missing from Nifty only (%d):** %s." % (len(only_n_cal), fmt(only_n_cal)))
say("These are exactly the 12 dates found in section 2. None is an NSE holiday, so Yahoo's Nifty series is missing 12 real trading days and Bank Nifty has them.")
say("")
say("**Open days missing from both series (%d):** %s." % (len(miss_both), fmt(miss_both)))
say("The exchange was open on all three (news reports give the Nifty close as 5,664.30 on 26-Oct-2012, 10,793.65 on 13-Feb-2019 and 11,623.90 on 29-Mar-2019),")
say("so these are gaps in Yahoo's data and not holidays. My earlier reading of every 'missing in both' day as a holiday was wrong for these three.")
say("")
say("**Rows dated on an official holiday (%d):** %s." % (len(on_hol), fmt(on_hol)))
say("All of these are Diwali Laxmi Pujan days with an evening Muhurat session, which section 4 already drops.")
say("")
all_missing = weekdays.difference(nifty.index.union(bank.index))        # weekdays that neither series has
say("Of the %d weekdays missing from both series, %d are official holidays and %d are real trading days (listed above)." % (
    len(all_missing), len(all_missing.intersection(holidays)), len(all_missing.difference(holidays))))
say("")
say("Also worth noting:")
say("- In 2013 the exchanges moved the Muharram holiday from 14 Nov to 15 Nov (announced on 13 Nov 2013). Yahoo has 14 Nov and not 15 Nov, which matches the revised list.")
say("- I also tried two python calendar libraries (exchange_calendars and holidays). They disagree with each other on 6 dates and both still have the old 2013 Muharram date, so I used the official lists.")
say("- This section covers the research period only. The locked 2022-2025 dates were compared with NSE's calendar after the out-of-sample run (post_hoc_locked_data_check.pdf).")
say("")

# ---------------------------------------------------------------- 7. check against nse's own index files
say("## 7. Check against NSE's own index files")
say("")
say("NSE puts one file per trading day on its archive site with the open, high, low and close of all its indices (nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv).")
say("The file data/reference/nse_index_ohlc_2012_2021.csv has the Nifty 50 and Bank Nifty rows of those files (built by 02c_build_nse_index_reference.py, the saved files are in data/reference/sources/nse_index_files/).")
say("Yahoo stays the data source of the study; this section is a check on it and not a replacement.")
say("")
off = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_index_ohlc_2012_2021.csv"), parse_dates=["date"])    # NSE's own numbers
off_by = {lab: off[off["index"] == lab].set_index("date") for lab in ["Nifty 50", "Bank Nifty"]}
cmp_rows, mism = [], []                                         # summary table, and every single price that differs
for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]:
    o = off_by[lab]
    both_days = yahoo.index.intersection(o.index)               # days where both sources have a bar
    row = {"index": lab, "Yahoo bars": len(yahoo), "compared with NSE": len(both_days)}
    for ycol in ["Open", "High", "Low", "Close"]:
        diff = (yahoo.loc[both_days, ycol] - o.loc[both_days, ycol.lower()]).abs()
        row[ycol.lower() + " identical"] = int((diff <= 0.011).sum())       # prices have two decimals, 0.011 absorbs float rounding
        for day, v in diff[diff > 0.011].items():
            mism.append((lab, day, ycol, float(yahoo.loc[day, ycol]), float(o.loc[day, ycol.lower()])))
    cmp_rows.append(row)
say(pd.DataFrame(cmp_rows).to_markdown(index=False))
say("")
nse_start = off["date"].min()                                   # NSE's files start here
unchecked = {lab: yahoo.index.difference(off_by[lab].index) for lab, yahoo in [("Nifty 50", nifty), ("Bank Nifty", bank)]}
early = [d for d in unchecked["Nifty 50"] if d < nse_start]     # the stretch before NSE's files begin
later = [d for d in unchecked["Nifty 50"] if d >= nse_start]    # days NSE's archive lacks although the exchange was open
say("**What could not be checked.** NSE's files start on %s, so %d Nifty bars before that date have no official file to compare with. "
    "NSE's archive also lacks %d later days on which Yahoo has a bar: %s. These bars stay unchecked. The locked 2022-2025 period is covered separately, after the out-of-sample run, in post_hoc_locked_data_check.pdf." % (
        nse_start.date(), len(early), len(later), fmt(later)))
say("")
say("**Result.** The Nifty open and close are identical to NSE's on all %d compared days. The open is the price the strategy trades at, so this is the number that matters most. "
    "Bank Nifty differs on %d of %d opens and %d of %d closes." % (
        cmp_rows[0]["compared with NSE"], cmp_rows[1]["compared with NSE"] - cmp_rows[1]["open identical"], cmp_rows[1]["compared with NSE"],
        cmp_rows[1]["compared with NSE"] - cmp_rows[1]["close identical"], cmp_rows[1]["compared with NSE"]))
say("")
say("Every price that differs (%d in all):" % len(mism))
say("")
say(pd.DataFrame([(a, str(b.date()), c, "{:,.2f}".format(d), "{:,.2f}".format(e), "removed by cleaning" if b not in px.index else "kept") for a, b, c, d, e in mism],
                 columns=["index", "date", "price", "Yahoo", "NSE", "in the study?"]).to_markdown(index=False, disable_numparse=True))   # text columns, so 20,200.25 keeps both decimals
say("")
kept_fields = sorted(set(m[2] for m in mism if m[1] in px.index))
say("The Bank Nifty bar of 10-Nov-2016 is the placeholder from section 4 (Yahoo has 20,200.25 in all four prices), and 7-Nov-2018 is a Diwali Muhurat session; "
    "the cleaning rules remove both. The rows marked 'kept' differ only in %s. The strategy trades on opens and closes, so none of them touches a signal or a return. "
    "I did not try to find out which source has the right high or low." % " and ".join(k.lower() + "s" for k in kept_fields))
say("")
# ---- what the days Yahoo is missing are worth: put them back from NSE's files and rerun the frozen rule
fill_n = off_by["Nifty 50"].index.difference(nifty.index).difference(MUHURAT_DAYS)     # real trading days Yahoo's Nifty lacks
fill_b = off_by["Bank Nifty"].index.difference(bank.index).difference(MUHURAT_DAYS)    # same for Bank Nifty
has_file = off_by["Nifty 50"].index                             # days for which NSE has a file
hol_in = holidays[holidays >= nse_start]                        # listed holidays that fall inside NSE's coverage
hol_with_file = hol_in.intersection(has_file)                   # a holiday with a file would mean the list is wrong (apart from Muhurat evenings)
no_file = weekdays[weekdays >= nse_start].difference(has_file)  # weekdays without a file
unexplained = no_file.difference(holidays)                      # no file and not on the holiday list
both_yahoo = nifty.index.intersection(bank.index)
say("**The holiday lists, checked the other way round.** NSE only publishes a file for a day it traded. From %s on, %d holidays of my list fall inside NSE's coverage and "
    "only %d of them have a file, all Diwali Muhurat evenings (%s). Every other weekday without an NSE file is on the holiday list, except %d days (%s); "
    "Yahoo has a bar for both indices on %d of them, so they look like holes in NSE's archive and not closures. "
    "No holiday on my list is contradicted, including the 2013 and 2014 ones that came from a broker's copy.%s" % (
        nse_start.date(), len(hol_in), len(hol_with_file), fmt(hol_with_file), len(unexplained), fmt(unexplained),
        int(unexplained.isin(both_yahoo).sum()),
        " The Muharram move of 2013 shows too: NSE has a file for 2013-11-14 and none for 2013-11-15."
        if (pd.Timestamp("2013-11-14") in has_file and pd.Timestamp("2013-11-15") not in has_file) else ""))
say("")
say("**Days NSE has and Yahoo lacks.** NSE's files contain %d of the real trading days that Yahoo's Nifty lacks (%s) and the %d that Bank Nifty lacks. "
    "The three days missing from both series (section 6) are among them, and NSE's own Nifty closes for them are %s, equal to the news figures quoted in section 6. "
    "One of the 12 Nifty-only dates from section 6, 2012-01-02, is before NSE's files begin, so it stays missing." % (
        len(fill_n), fmt(fill_n), len(fill_b),
        ", ".join("{:,.2f}".format(off_by["Nifty 50"].loc[pd.Timestamp(d), "close"]) for d in ["2012-10-26", "2019-02-13", "2019-03-29"])))
say("")
frozen_path = os.path.join(OUT_DIR, "frozen_rules.json")
if os.path.exists(frozen_path):
    prm = json.load(open(frozen_path))["params"]                # the rule as frozen (Nifty, k, w, h, both sides)

    def run_frozen_rule(n_tab, b_tab):
        # same cleaning, same rule, same engine as the study; only the raw tables differ
        t, _ = clean_pair(n_tab, b_tab)
        t = add_returns(t)
        bt = backtest(t[prm["p"] + "_open"], make_positions(t, prm["p"], prm["k"], prm["w"], prm["h"], prm["side"]))
        return perf_stats(bt["net"], trades_from_bt(bt)), perf_stats(bt["gross"]), len(t)

    def with_nse(tab, days, lab):
        # adds the NSE bars for those days to a raw Yahoo table (volume is not used anywhere, so 0)
        add = off_by[lab].loc[days, ["open", "high", "low", "close"]].copy()
        add.columns = ["Open", "High", "Low", "Close"]
        add["Volume"] = 0.0
        return pd.concat([tab, add]).sort_index()

    s0, g0, n0 = run_frozen_rule(nifty, bank)
    s1, g1, n1 = run_frozen_rule(with_nse(nifty, fill_n, "Nifty 50"), with_nse(bank, fill_b, "Bank Nifty"))
    say("**Does it matter?** I put those days back and reran the frozen rule on the research period (Nifty, threshold %.1f, %d-day window, hold %d days, %.2f%% per side):" % (
        prm["k"], prm["w"], prm["h"], 100 * prm["cost_per_side"]))
    say("")
    say(pd.DataFrame([{"data": "Yahoo only (as in the study)", "days": n0, "net Sharpe": round(s0["Sharpe"], 3), "gross Sharpe": round(g0["Sharpe"], 3),
                       "CAGR %": round(s0["CAGR %"], 2), "max drawdown %": round(s0["Max drawdown %"], 2), "trades": s0["Trades"]},
                      {"data": "Yahoo plus the NSE days", "days": n1, "net Sharpe": round(s1["Sharpe"], 3), "gross Sharpe": round(g1["Sharpe"], 3),
                       "CAGR %": round(s1["CAGR %"], 2), "max drawdown %": round(s1["Max drawdown %"], 2), "trades": s1["Trades"]}]).to_markdown(index=False))
    say("")
    say("The result moves by %.2f of Sharpe, so the missing days do not carry the finding. I kept the Yahoo-only series in the study on purpose: the frozen rules "
        "and the locked 2022-2025 file are built on it, and mixing two sources across the research and out-of-sample periods would be worse than losing %d days. "
        "This table is only a side check; every other number in the study stays as it was. I also reran the 98-test scan, the grid and the reality check on the filled data "
        "(nse_filled_side_check.pdf): the same tests survive the correction and the same rule is chosen." % (abs(s1["Sharpe"] - s0["Sharpe"]), len(fill_n)))
else:
    say("(The sensitivity run is skipped because outputs/frozen_rules.json does not exist yet.)")
say("")

# ---------------------------------------------------------------- 8. known limitations
say("## 8. Known limitations")
say("- Saturday special sessions (budget days 28-Feb-2015 and 1-Feb-2020) are not in the Yahoo data, so their moves sit inside the following Monday's return.")
say("- Open prices are the index value at 9:15. They can't be traded exactly (index futures or ETFs open slightly differently), which is one reason for costs.")
say("- The first return after a holiday covers more than one calendar day. I don't scale it; vol is slightly overstated on Mondays and post-holiday days.")
say("")

# ---------------------------------------------------------------- save things
px.to_csv(os.path.join(DATA_DIR, "research", "clean_research.csv"))
os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)     # the written reports live in outputs/markdown
with open(os.path.join(OUT_DIR, "markdown", "data_quality_report.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

# a quick figure: both indices, and the daily returns with 5% days marked
fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
ax[0].plot(px.index, px["n_close"], label="Nifty 50", lw=1)
ax[0].plot(px.index, px["b_close"] / 2, label="Bank Nifty / 2", lw=1)      # halved so both fit on one scale
ax[0].set_ylabel("index level")
ax[0].legend()
ax[0].set_title("Research period, cleaned")
ax[1].plot(px.index, px["n_ret"] * 100, lw=0.6, color="grey")
ax[1].scatter(big.index, [px.loc[pd.Timestamp(d), "n_ret"] * 100 for d in big.index], color="red", s=10, label="move > 5% in either index")
ax[1].set_ylabel("Nifty daily return %")
ax[1].legend()
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "01_data_overview.png"), dpi=130)
print("saved clean data and report")
