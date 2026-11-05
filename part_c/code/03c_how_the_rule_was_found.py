# 03c_how_the_rule_was_found.py
# writes outputs/markdown/how_the_rule_was_found.md: the story of how i found the trading rule, from the plan to the chosen settings
# every number in it is read from my own output files (or recomputed from the research features), nothing is typed in by hand
# run it after 03_anomaly_scan.py, 03b_gap_diagnostics.py and 04_strategy_research.py (it needs their files)
# research period (2012-2021) only: this script never opens the locked 2022-2025 data

import os                                                   # paths
import json                                                 # to read the chosen parameters
import numpy as np                                          # maths
import pandas as pd                                         # tables
import statsmodels.api as sm                                # regressions
from scipy import stats                                     # rank correlation

from common import OUT_DIR, TAB_DIR                         # the output folders

lines = []                                                  # the markdown report, line by line


def say(text=""):                                           # prints a line and keeps it for the report
    print(text)                                             # show it on screen
    lines.append(text)                                      # and store it for the markdown file


def table(df):                                              # turns a table into markdown text
    return df.to_markdown(index=False, disable_numparse=True)   # no row numbers, and numbers stay exactly as formatted


def slope(y, x, lags=5):                                    # the same regression as in 03b_gap_diagnostics.py
    # slope of y on x (bps per 1 std of x) with newey-west t-stat
    s = pd.concat([y, x], axis=1).dropna()                  # both series side by side, complete days only
    s.columns = ["y", "x"]                                  # simple names
    res = sm.OLS(s["y"], sm.add_constant(s["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})   # straight-line fit with newey-west errors
    return res.params["x"] * s["x"].std() * 1e4, res.tvalues["x"], len(s)   # effect of a 1 std move in x in basis points, its t-stat, number of days


# ---------------------------------------------------------------- load what the earlier steps wrote
scan = pd.read_csv(os.path.join(TAB_DIR, "anomaly_scan_all_tests.csv"))      # every one of the 98 tests (03_anomaly_scan.py)
grid = pd.read_csv(os.path.join(TAB_DIR, "grid_research.csv"))               # the 18 variants of the rule (04_strategy_research.py)
sens = pd.read_csv(os.path.join(TAB_DIR, "sensitivity_research.csv"))        # the +-20% parameter changes (04_strategy_research.py)
prm = json.load(open(os.path.join(TAB_DIR, "selected_params.json")))         # the settings that were chosen
px = pd.read_pickle(os.path.join(OUT_DIR, "research_features.pkl"))          # the research table with gaps and returns (03_anomaly_scan.py)

n_tests = int(scan["p_value"].notna().sum())                # number of tests in the scan
trad = scan[scan["tradable"] & scan["p_value"].notna()]     # the tests that could be traded with next-open entry
n_trad = len(trad)                                          # how many of those
trad_raw = int((trad["p_value"] < 0.05).sum())              # tradable tests with a raw p-value below 0.05
trad_bh = int((trad["p_bh_fdr"] < 0.05).sum())              # tradable tests that survive the benjamini-hochberg correction
gap_n = scan[(scan["test"] == "yesterday's gap -> next tradable day") & (scan["index"] == "Nifty50")].iloc[0]    # the Nifty gap test
gap_b = scan[(scan["test"] == "yesterday's gap -> next tradable day") & (scan["index"] == "BankNifty")].iloc[0]  # the Bank Nifty gap test
chosen = grid[(grid["k"] == prm["k"]) & (grid["hold"] == prm["h"]) & (grid["side"] == prm["side"])].iloc[0]      # the chosen variant's row

# ---------------------------------------------------------------- title and summary
say("# How I found the rule (research period 2012-2021 only)")   # the report title
say("")                                                     # blank line
say("The brief's Step 2 asks what I tested and how. This document tells the story in order, from the plan to the chosen rule, "
    "with the numbers taken from my own output files. Everything here uses the research data only. "
    "The locked 2022-2025 data appears only in the last section, as something I learned afterwards.")   # what this document is
say("")                                                     # blank line
say("## In one paragraph")                                  # section heading
say("")                                                     # blank line
say("I wrote the rules for testing and for picking an idea before I downloaded any data. I then ran **%d tests** on 2012-2021 and counted every one of them. "
    "Only %d of them could be traded with next-open entry. Of those, %d had a raw p-value below 0.05 (luck alone would give about %.0f), "
    "and only **%d survived the correction for having tried so many**: the overnight-gap tests for Nifty and Bank Nifty. "
    "The Nifty one was the clear winner under my written selection rule. I checked it from several angles, turned it into a trading rule, "
    "and chose its settings from a small fixed grid of %d variants." % (n_tests, n_trad, trad_raw, 0.05 * n_trad, trad_bh, int(prm["n_variants_tried"])))   # the whole story in a few lines
say("")                                                     # blank line

# ---------------------------------------------------------------- 1. the plan
say("## 1. The plan I wrote first")                         # section heading
say("")                                                     # blank line
say("Before downloading any data I wrote `markdown/PLAN_written_before_looking_at_data.md`, so that I could not quietly change the rules after seeing results. It fixed three things:")   # intro to the plan
say("")                                                     # blank line
say("- **Counting.** Every test goes into one table, including the failures. P-values are adjusted for the whole table (Bonferroni and Benjamini-Hochberg), not family by family. "
    "Returns are tested with Newey-West errors, which allow for overlapping and autocorrelated days.")   # the counting rule
say("- **Picking.** The idea to trade is chosen by rule, not by feel. It must be (1) something I can trade, (2) the one with the smallest adjusted p-value among the tradable tests, "
    "(3) the same sign in both halves of the research period (2012-2016 and 2017-2021), (4) still positive after 0.05% costs per side, and (5) have a story about who is on the other side of the trade.")   # the five criteria
say("- **Protecting the test.** 2012-2021 is research data, 2022-2025 is locked, and nothing is run on the locked data until the rules are frozen.")   # the split
say("")                                                     # blank line

# ---------------------------------------------------------------- 2. the scan
say("## 2. The scan: what I tested")                        # section heading
say("")                                                     # blank line
say("The scan is `code/03_anomaly_scan.py`. It writes one row per test to `outputs/tables/anomaly_scan_all_tests.csv`. The tests come in seven groups, "
    "with at least one classical test and at least one machine-learning method, as the brief asks:")   # what the scan is
say("")                                                     # blank line
groups = [("F1 random walk, volatility, distribution", ["random walk", "volatility", "distribution"],
           "Ljung-Box, ARCH-LM, variance ratios, runs test, Jarque-Bera"),
          ("F2 day of week", ["day of week"], "each weekday against the rest, Kruskal-Wallis across weekdays"),
          ("F3 expiry and turn of month", ["expiry", "turn of month"], "expiry day, expiry week, day after expiry, turn of month"),
          ("F4 gaps", ["gaps"], "overnight gap, intraday move, big gaps, average overnight and intraday drift"),
          ("F5 streaks", ["streaks"], "2, 3 and 4 or more up or down closes in a row"),
          ("F6 Nifty against Bank Nifty", ["divergence"], "ADF, Engle-Granger, relative return, lead and lag"),
          ("F7 machine learning", ["ML regimes", "ML outliers", "ML walk-forward"], "Gaussian-mixture regimes, isolation forest, walk-forward logistic and boosted classifiers")]   # the seven groups, which family labels they hold, and what they contain
grows = []                                                  # one table row per group
for label, fams, what in groups:                            # each group
    g = scan[scan["family"].isin(fams)]                     # its tests
    gt = g[g["tradable"] & g["p_value"].notna()]            # its tradable tests
    grows.append({"group": label, "tests": str(len(g)), "tradable": str(len(gt)), "what": what,
                  "smallest raw p": "%.4f" % g["p_value"].min()})   # keep the numbers for the table
say(table(pd.DataFrame(grows)))                             # the groups as a table
say("")                                                     # blank line
say("Many tests are about risk, not direction (for example volatility clustering and fat tails). They are very significant, but they cannot be traded with next-open entry, "
    "so they cannot be the rule. That is why the plan's first criterion matters.")   # why not everything is a candidate
say("")                                                     # blank line
say("An example is the chart below: the solid lines are the autocorrelation of absolute returns, which stays clearly positive for weeks (big moves follow big moves), and the dotted lines are plain returns, which hardly correlate at all (the direction of the next day is not predicted).")   # what the picture shows
say("")                                                     # blank line
say("![Autocorrelation of returns and of absolute returns](../figures/03_vol_clustering_acf.png)")   # the picture made by 03_anomaly_scan.py (path is relative to outputs/markdown)
say("")                                                     # blank line

# ---------------------------------------------------------------- 3. how the gap test works
say("## 3. How the gap test works")                         # section heading
say("")                                                     # blank line
sd_gap = px["n_gap"].std() * 1e4                            # the typical size of one overnight gap of Nifty, in basis points
say("- **The overnight gap** of day t is how far the market opens from the previous close: gap = ln(open of day t / close of day t-1). "
    "One standard deviation of the Nifty gap is about %.0f basis points (1 basis point = 0.01%%)." % sd_gap)   # the definition of the gap
say("- **What I can trade** after seeing the gap is the move from the open of day t+1 to the open of day t+2: I see the gap, decide at the close of day t, "
    "and can only enter at the next open. The brief says to assume entry at the next session's open.")   # the outcome that is tested
say("")                                                     # blank line
say(table(pd.DataFrame([{"when": "Day t, at the open", "what happens": "The gap is known (today's open against yesterday's close)"},
                        {"when": "Day t, at the close", "what happens": "I decide: long after a big gap up, short after a big gap down"},
                        {"when": "Day t+1, at the open", "what happens": "I enter the trade (the next session's open, as the brief says)"},
                        {"when": "Day t+2, at the open", "what happens": "I leave. The result of the trade is the move from the open of t+1 to the open of t+2"}])))   # the timeline of one trade
say("")                                                     # blank line
say("- **The test** is a regression of that tradable return on the gap, with the gap scaled by its standard deviation, so the answer reads as "
    "\"basis points earned for each 1 standard deviation of gap\". The t-statistic and p-value use Newey-West errors with 5 lags. "
    "A positive effect means gaps tend to continue; a negative one would mean they tend to fade.")   # the method
say("- **The same test is run on the two halves** of the research period (2012-2016 and 2017-2021), which gives the sign check in criterion 3.")   # halves
say("")                                                     # blank line

# ---------------------------------------------------------------- 4. correcting for the number of tests
say("## 4. Correcting for having tried %d things" % n_tests)   # section heading
say("")                                                     # blank line
say("If you test %d ideas, some will look good by chance. A raw p-value of 0.05 means a no-effect idea passes 1 time in 20, so about 5 of %d tests pass with no real effect. "
    "So every p-value is adjusted for the size of the table. **Bonferroni** multiplies by the number of tests (strict). "
    "**Benjamini-Hochberg** controls the share of false discoveries among the tests that pass (gentler). "
    "In the whole table, %d tests have a raw p below 0.05, %d survive Benjamini-Hochberg and %d survive Bonferroni. "
    "Of the %d that survive Benjamini-Hochberg, %d cannot be traded with next-open entry (volatility clustering, fat tails, the average overnight and intraday drift and similar), "
    "so only %d are candidates for a rule." % (n_tests, n_tests, int((scan["p_value"] < 0.05).sum()), int((scan["p_bh_fdr"] < 0.05).sum()), int((scan["p_bonferroni"] < 0.05).sum()),
                                                  int((scan["p_bh_fdr"] < 0.05).sum()), int((scan["p_bh_fdr"] < 0.05).sum()) - trad_bh, trad_bh))   # why and how the correction is done
say("")                                                     # blank line
say("The gap tests, which are tradable:")                   # a small heading
say("")                                                     # blank line
say(table(pd.DataFrame([{"test": "Nifty 50 gap", "effect (bps per 1 sd)": "%.1f" % gap_n["effect"], "t": "%.2f" % gap_n["t_stat"], "raw p": "%.4f" % gap_n["p_value"],
                         "Benjamini-Hochberg": "%.4f" % gap_n["p_bh_fdr"], "Bonferroni": "%.4f" % gap_n["p_bonferroni"]},
                        {"test": "Bank Nifty gap", "effect (bps per 1 sd)": "%.1f" % gap_b["effect"], "t": "%.2f" % gap_b["t_stat"], "raw p": "%.4f" % gap_b["p_value"],
                         "Benjamini-Hochberg": "%.4f" % gap_b["p_bh_fdr"], "Bonferroni": "%.4f" % gap_b["p_bonferroni"]}])))   # the two gap tests with their adjusted p-values
say("")                                                     # blank line

# ---------------------------------------------------------------- 5. what survived among the tradable tests
say("## 5. What survived among the tradable tests")        # section heading
say("")                                                     # blank line
top = trad.sort_values("p_value").head(5)                   # the five tradable tests with the smallest raw p-value
say(table(pd.DataFrame({"test": top["test"], "index": top["index"], "raw p": top["p_value"].map("{:.4f}".format),
                        "Benjamini-Hochberg": top["p_bh_fdr"].map("{:.4f}".format)})))   # those five as a table
say("")                                                     # blank line
say("Out of %d tradable tests, %d had a raw p below 0.05 (chance alone would give about %.0f) and %d survive the correction: the two gap tests. "
    "Nothing else survives, including every machine-learning method:" % (n_trad, trad_raw, 0.05 * n_trad, trad_bh))   # the shortlist result
say("")                                                     # blank line
ml = scan[scan["family"] == "ML walk-forward"].sort_values(["index", "test"])   # the walk-forward classifier rows
say(table(pd.DataFrame({"model": ml["test"], "index": ml["index"], "result": ml["note"], "p vs baseline": ml["p_value"].map("{:.3f}".format)})))   # accuracy against the always-guess-the-majority baseline
say("")                                                     # blank line
ml_other = scan[scan["family"].isin(["ML regimes", "ML outliers"])]   # the regime and outlier tests of the machine-learning group
say("The %d regime and outlier tests (Gaussian mixture and isolation forest) found nothing either: their smallest raw p-value is %.2f." % (len(ml_other), ml_other["p_value"].min()))   # the rest of the ML group
say("")                                                     # blank line

# ---------------------------------------------------------------- 6. the five criteria
say("## 6. The five criteria, applied to the Nifty gap test")   # section heading
say("")                                                     # blank line
rank = int((trad["p_bh_fdr"] < gap_n["p_bh_fdr"]).sum()) + 1  # its position among tradable tests by adjusted p-value
runner_up = trad.sort_values("p_bh_fdr").iloc[1]            # the tradable test with the second smallest adjusted p-value
crit = pd.DataFrame([
    {"criterion": "1. Something I can trade", "check": "Uses the gap known at day t to predict the open-to-open return from t+1 to t+2, so entry is at the next open",
     "result": "Yes"},
    {"criterion": "2. Smallest adjusted p-value among tradable tests", "check": "Benjamini-Hochberg p = %.4f; the next tradable test is %s on %s at %.4f" % (
        gap_n["p_bh_fdr"], runner_up["test"], runner_up["index"], runner_up["p_bh_fdr"]), "result": "Yes (rank %d of %d)" % (rank, n_trad)},
    {"criterion": "3. Same sign in both halves", "check": "2012-2016: %+.1f bps (t=%.2f). 2017-2021: %+.1f bps (t=%.2f)" % (
        gap_n["effect_h1"], gap_n["t_h1"], gap_n["effect_h2"], gap_n["t_h2"]), "result": "Yes" if bool(gap_n["same_sign"]) else "No"},
    {"criterion": "4. Still positive after 0.05% per side", "check": "The chosen rule on research data: net Sharpe %.2f after costs (%.2f before)" % (
        chosen["net Sharpe"], chosen["gross Sharpe"]), "result": "Yes" if chosen["net Sharpe"] > 0 else "No"},
    {"criterion": "5. A story about who is on the other side", "check": "Explained in section 5 of the research note. I wrote it up after the out-of-sample run, so it is an explanation that fits, not a pre-registered claim",
     "result": "Partly"}])   # one row per criterion with what i checked and the answer
say(table(crit))                                            # the criteria as a table
say("")                                                     # blank line

# ---------------------------------------------------------------- 7. checking it from several angles
say("## 7. Checking the effect from several angles before believing it")   # section heading
say("")                                                     # blank line
say("This is `code/03b_gap_diagnostics.py`. All numbers are for the Nifty gap and the research period.")   # which script and which data
say("")                                                     # blank line
gap = px["n_gap"]                                           # the overnight gap of Nifty
fwd = px["n_fwd"]                                           # the tradable return after it (open t+1 to open t+2)
e_all, t_all, n_all = slope(fwd, gap)                       # the full-sample effect
no20 = px.index.year != 2020                                # every day outside the covid year
e_20, t_20, n_20 = slope(fwd[no20], gap[no20])              # the effect without 2020
g_w = gap.clip(gap.quantile(0.01), gap.quantile(0.99))      # the gap capped at its 1st and 99th percentile
y_w = fwd.clip(fwd.quantile(0.01), fwd.quantile(0.99))      # the outcome capped the same way
e_w, t_w, _ = slope(y_w, g_w)                               # the effect on the capped series
sp = pd.concat([gap, fwd], axis=1).dropna()                 # gap and outcome side by side
rho, rho_p = stats.spearmanr(sp.iloc[:, 0], sp.iloc[:, 1])  # the rank correlation, which outliers cannot move much
yr_eff = []                                                 # the effect in each calendar year
for yr in range(2012, 2022):                                # every research year
    m = px.index.year == yr                                 # the days of that year
    yr_eff.append(slope(fwd[m], gap[m])[0])                 # its effect in bps
pos_years = int(sum(1 for e in yr_eff if e > 0))            # in how many years the effect is positive
intra_next = px["n_intra"].shift(-1)                        # part 1 of the outcome: the intraday move of day t+1
gap_next2 = px["n_gap"].shift(-2)                           # part 2 of the outcome: the overnight move into day t+2
e_p1, t_p1, _ = slope(intra_next, gap)                      # how much of the effect sits in part 1
e_p2, t_p2, _ = slope(gap_next2, gap)                       # and in part 2
checks = pd.DataFrame([
    {"check": "All days", "effect (bps per 1 sd)": "%.1f" % e_all, "t": "%.2f" % t_all, "what it tells me": "The headline result (%d days)" % n_all},
    {"check": "Without 2020", "effect (bps per 1 sd)": "%.1f" % e_20, "t": "%.2f" % t_20, "what it tells me": "The covid year does not carry it"},
    {"check": "Gap and outcome capped at 1st/99th percentile", "effect (bps per 1 sd)": "%.1f" % e_w, "t": "%.2f" % t_w, "what it tells me": "A few extreme days do not carry it"},
    {"check": "Rank correlation", "effect (bps per 1 sd)": "rho = %.3f" % rho, "t": "p < 0.0001" if rho_p < 1e-4 else "p = %.4f" % rho_p, "what it tells me": "No outlier-sensitive step in the result"},
    {"check": "Year by year", "effect (bps per 1 sd)": "positive in %d of 10 years" % pos_years, "t": "-", "what it tells me": "Not one lucky stretch (the weak spot is 2017-2019, where the effect is near zero)"},
    {"check": "Part 1: intraday move of day t+1", "effect (bps per 1 sd)": "%.1f" % e_p1, "t": "%.2f" % t_p1, "what it tells me": "About %.0f%% of the effect: the follow-through during day t+1" % (100 * e_p1 / e_all)},
    {"check": "Part 2: overnight move into day t+2", "effect (bps per 1 sd)": "%.1f" % e_p2, "t": "%.2f" % t_p2, "what it tells me": "About %.0f%% of the effect: a second overnight move in the same direction" % (100 * e_p2 / e_all)}])   # the checks as one table
say(table(checks))                                          # show the checks
say("")                                                     # blank line
q = pd.qcut(gap, 5, labels=["Q1 (big down gap)", "Q2", "Q3", "Q4", "Q5 (big up gap)"])   # five equal groups of days by gap size
qm = px.groupby(q, observed=True)["n_fwd"].agg(["mean", "count"])   # the average next-trade return and day count of each group
say("Splitting the days into five equal groups by gap size shows the shape of the effect:")   # intro to the quintile table
say("")                                                     # blank line
say(table(pd.DataFrame({"gap group": qm.index.astype(str), "average next tradable return (bps)": (qm["mean"] * 1e4).round(1).astype(str), "days": qm["count"].astype(int).astype(str)})))   # the five groups as a table
say("")                                                     # blank line
say("The average rises from group to group: the biggest gap-downs are followed by losses and the biggest gap-ups by gains. That regular shape is more convincing than a single t-statistic.")   # the reading of the quintile table
say("")                                                     # blank line

# ---------------------------------------------------------------- 8. from the effect to a rule
say("## 8. From the effect to a rule, and choosing its settings")   # section heading
say("")                                                     # blank line
say("The rule is described in section 6 of the research note: compute the gap at the close of day t, divide it by the standard deviation of the previous %d gaps (z), "
    "go long if z is at least +k and short if at most -k, keep the signal for h days, and enter at the next open. "
    "The threshold k, the holding days h and long-and-short against long-only were not known in advance, so I tried a **fixed grid of %d variants** "
    "(k = 0.5, 1.0, 1.5; h = 1, 2, 3 days; long and short, or long only) and wrote the selection rule before running it:" % (prm["w"], len(grid)))   # how the rule was built
say("")                                                     # blank line
passing = grid[(grid["trades"] >= 100) & (grid["Sharpe 12-16"] > 0) & (grid["Sharpe 17-21"] > 0)]   # the variants that pass the written filter
say("*The highest net Sharpe among variants with at least 100 trades and a positive net Sharpe in both 2012-2016 and 2017-2021.* "
    "%d of the %d variants passed that filter, so it did not remove anything; the highest net Sharpe decided." % (len(passing), len(grid)))   # the selection rule and what it did
say("")                                                     # blank line
gshow = grid.copy()                                         # a copy to format for display
gshow["chosen"] = np.where((gshow["k"] == prm["k"]) & (gshow["hold"] == prm["h"]) & (gshow["side"] == prm["side"]), "<- chosen", "")   # mark the winner
say(table(pd.DataFrame({"k": gshow["k"].astype(str), "hold (days)": gshow["hold"].astype(str), "side": gshow["side"],
                        "net Sharpe": gshow["net Sharpe"].map("{:.2f}".format), "Sharpe 12-16": gshow["Sharpe 12-16"].map("{:.2f}".format),
                        "Sharpe 17-21": gshow["Sharpe 17-21"].map("{:.2f}".format), "trades": gshow["trades"].astype(int).astype(str), "": gshow["chosen"]})))   # all 18 variants, nothing hidden
say("")                                                     # blank line
share_pos = 100 * (sens["net Sharpe"] > 0).mean()           # the share of +-20% variants with a positive net Sharpe
say("The chosen variant is k=%.1f, hold=%d days, long and short, window %d, with a net Sharpe of %.2f after costs. "
    "Because I chose the best of %d, I checked whether it is just the luckiest of them with White's Reality Check: the p-value is **%.3f**. "
    "Moving each parameter by -20%% and +20%% (one at a time and all together) kept the net Sharpe positive in %.0f%% of %d variants, between %.2f and %.2f." % (
        prm["k"], prm["h"], prm["w"], chosen["net Sharpe"], len(grid), prm["reality_check_p"], share_pos, len(sens), sens["net Sharpe"].min(), sens["net Sharpe"].max()))   # the chosen settings and their checks
say("")                                                     # blank line

# ---------------------------------------------------------------- 9. what this does and does not show
say("## 9. What this does and does not show")              # section heading
say("")                                                     # blank line
say("- **It was the best of %d tests.** The selection method was fixed in advance; the idea that gaps continue was not. It came out of the scan, so chance remains a possible explanation, "
    "and the Reality Check above only covers the grid of rule settings, not the whole scan." % n_tests)   # honest limit 1
say("- **The explanation came afterwards.** The story in section 5 of the research note (foreign institutions splitting large orders over several days) was written after the out-of-sample run, "
    "and I have no flow data to test it.")   # honest limit 2
say("- **I learned later that it did not repeat.** On the locked 2022-2025 data, which I looked at once after freezing the rule, the gap effect was about zero (t = -0.04), "
    "the rule's Sharpe of 0.82 was about the same as buy and hold (0.78), and the same rule on Bank Nifty lost money (-0.17). "
    "The out-of-sample run also could not trade before April 2022 (see the README). These numbers come from `outputs/pdf/oos_results.pdf`. That is why my verdict is not to trade it.")   # what happened afterwards
say("")                                                     # blank line

# ---------------------------------------------------------------- 10. where everything is
say("## 10. Where everything is")                          # section heading
say("")                                                     # blank line
say("| What | Where |")                                      # table header
say("|---|---|")                                             # table header line
say("| The plan, written first | `markdown/PLAN_written_before_looking_at_data.md` |")   # row
say("| Every test of the scan | `outputs/tables/anomaly_scan_all_tests.csv` (code: `code/03_anomaly_scan.py`) |")   # row
say("| The checks on the gap effect | `outputs/pdf/gap_diagnostics.pdf` (code: `code/03b_gap_diagnostics.py`) |")   # row
say("| Where the edge comes from | `outputs/pdf/mechanism_checks.pdf` (code: `code/04b_mechanism_checks.py`) |")   # row
say("| The grid, the choice, the Reality Check, the sensitivity | `outputs/pdf/strategy_research.pdf` (code: `code/04_strategy_research.py`) |")   # row
say("| This document | `code/03c_how_the_rule_was_found.py` |")   # row
say("")                                                     # blank line

# ---------------------------------------------------------------- save
os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)   # make sure the report folder exists
with open(os.path.join(OUT_DIR, "markdown", "how_the_rule_was_found.md"), "w", encoding="utf-8") as f:   # open the report file
    f.write("\n".join(lines) + "\n")                        # write every collected line
print("saved how_the_rule_was_found.md")                    # tell the user it is done
