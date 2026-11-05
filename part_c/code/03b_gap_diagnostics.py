# 03b_gap_diagnostics.py
# the scan said "yesterday's overnight gap predicts the next tradable day" (survives multiple testing)
# before i believe it i want to know where it comes from: which part of the day, is it just 2020, is it every year?
# research data only

import os                                           # paths
import numpy as np                                  # maths
import pandas as pd                                 # tables
import statsmodels.api as sm                        # regressions
from scipy import stats                             # spearman
import matplotlib                                   # plotting library
matplotlib.use("Agg")                               # no pop-up windows, the figure is simply saved to a file
import matplotlib.pyplot as plt                     # the plotting commands

from common import OUT_DIR, FIG_DIR                 # output folders

px = pd.read_pickle(os.path.join(OUT_DIR, "research_features.pkl"))   # saved by 03_anomaly_scan.py
lines = []                                          # for the markdown output


def say(t=""):                                      # prints a line and keeps it for the report
    print(t)                                        # show it on screen
    lines.append(t)                                 # and store it for the markdown file


def slope(y, x, lags=5):                            # regression slope of y on x, with a t-stat that allows for autocorrelation
    # slope of y on x (bps per 1 std of x) with newey-west t-stat
    s = pd.concat([y, x], axis=1).dropna()          # put both series side by side and drop the days where either is missing
    s.columns = ["y", "x"]                          # simple names for the two columns
    res = sm.OLS(s["y"], sm.add_constant(s["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})   # straight-line fit, HAC = newey-west standard errors
    return res.params["x"] * s["x"].std() * 1e4, res.tvalues["x"], len(s)   # effect of a 1 std move in x in basis points, its t-stat, and the number of days


say("# Gap diagnostics (research period only)")      # the report title
say("")                                             # blank line
for p, nm in [("n", "Nifty50"), ("b", "BankNifty")]:   # the same checks for both indices
    say("## " + nm)                                 # a heading for this index
    gap = px[p + "_gap"]                                       # overnight move into day t
    # the tradable return is open(t+1) -> open(t+2). split it in two pieces:
    intra_next = px[p + "_intra"].shift(-1)                    # open(t+1) -> close(t+1)
    gap_next2 = px[p + "_gap"].shift(-2)                       # close(t+1) -> open(t+2)
    rows = []                                       # one table row per outcome
    for lab, y in [("next tradable day (open t+1 to open t+2)", px[p + "_fwd"]),
                   ("  part 1: intraday of day t+1", intra_next),
                   ("  part 2: overnight into t+2", gap_next2)]:   # the whole move, then its two pieces
        e, t, n = slope(y, gap)                     # how much does today's gap explain of that outcome?
        rows.append({"outcome": lab, "effect bps per 1sd gap": round(e, 2), "t-stat": round(t, 2), "n": n})   # store the result
    say(pd.DataFrame(rows).to_markdown(index=False))   # show the three results as a table
    say("")                                         # blank line

    # robustness 1: drop 2020
    no20 = px.index.year != 2020                    # True for every day outside 2020
    e, t, n = slope(px.loc[no20, p + "_fwd"], gap[no20])   # the same regression without the covid year
    say("Excluding 2020: effect %.2f bps per 1sd, t=%.2f (n=%d)" % (e, t, n))   # report it
    # robustness 2: winsorise gap and outcome at 1%/99%
    g_w = gap.clip(gap.quantile(0.01), gap.quantile(0.99))   # cap the gap at its 1st and 99th percentile so extremes cannot dominate
    y_w = px[p + "_fwd"].clip(px[p + "_fwd"].quantile(0.01), px[p + "_fwd"].quantile(0.99))   # same cap for the outcome
    e, t, n = slope(y_w, g_w)                       # regression on the capped series
    say("Winsorised at 1%%/99%%: effect %.2f bps per 1sd, t=%.2f" % (e, t))   # report it
    # robustness 3: rank correlation (not sensitive to outliers at all)
    s = pd.concat([gap, px[p + "_fwd"]], axis=1).dropna()   # gap and outcome side by side, complete days only
    rho, pv = stats.spearmanr(s.iloc[:, 0], s.iloc[:, 1])   # rank correlation and its p-value
    say("Spearman rank correlation gap(t) vs next tradable day: %.3f (p=%.4f)" % (rho, pv))   # report it
    say("")                                         # blank line

    # quintiles of the gap
    q = pd.qcut(gap, 5, labels=["Q1 (big down gap)", "Q2", "Q3", "Q4", "Q5 (big up gap)"])   # split the days into five equal groups by gap size
    qt = px.groupby(q)[p + "_fwd"].agg(["mean", "count"])   # average next-day return and number of days in each group
    qt["mean"] = (qt["mean"] * 1e4).round(1)        # convert to basis points, one decimal
    qt.columns = ["mean next tradable day (bps)", "days"]   # readable column names
    say("By gap quintile:")                         # a small heading
    say(qt.to_markdown())                           # the five groups as a table
    say("")                                         # blank line

    # year by year slope
    yr_rows = []                                    # one table row per year
    for yr in range(2012, 2022):                    # each research year
        m = px.index.year == yr                     # True for the days of that year
        e, t, n = slope(px.loc[m, p + "_fwd"], gap[m])   # the regression inside that year only
        yr_rows.append({"year": yr, "effect bps per 1sd gap": round(e, 1), "t": round(t, 2)})   # store the result
    yt = pd.DataFrame(yr_rows)                      # all years as a table
    say("By calendar year:")                        # a small heading
    say(yt.to_markdown(index=False))                # the ten years as a table
    say("positive in %d of 10 years" % int((yt["effect bps per 1sd gap"] > 0).sum()))   # in how many years the effect is above zero
    say("")                                         # blank line

# is it about the gap or about the whole day? compare gap vs close-to-close vs intraday as predictors, nifty
say("## Which piece of yesterday predicts tomorrow? (Nifty, joint regression)")   # a heading for this section
d = px[["n_fwd", "n_gap", "n_intra"]].dropna()      # the outcome and the two candidate predictors, complete days only
res = sm.OLS(d["n_fwd"], sm.add_constant(d[["n_gap", "n_intra"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})   # both predictors in one regression
say("n_fwd on gap and intraday together:")          # a small heading
say(pd.DataFrame({"coef": res.params, "t": res.tvalues}).round(3).to_markdown())   # coefficients and t-stats as a table
say("")                                             # blank line

# picture: mean next-day return by gap quintile, both indices
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)   # two side-by-side charts sharing the vertical axis
for a, (p, nm) in zip(ax, [("n", "Nifty50"), ("b", "BankNifty")]):   # one chart per index
    q = pd.qcut(px[p + "_gap"], 5, labels=False)    # quintile number 0-4 for every day
    m = px.groupby(q)[p + "_fwd"].mean() * 1e4      # average next-day return per quintile, in basis points
    a.bar(range(1, 6), m.values, color=["tab:red" if v < 0 else "tab:green" for v in m.values])   # bars, red if negative and green if positive
    a.axhline(0, color="black", lw=0.5)             # a thin line at zero
    a.set_title(nm)                                 # the index name above the chart
    a.set_xlabel("quintile of yesterday's overnight gap (1 = biggest gap down)")   # what the horizontal axis means
ax[0].set_ylabel("next tradable day return (bps)")  # vertical axis label on the left chart
fig.tight_layout()                                  # stop labels from overlapping
fig.savefig(os.path.join(FIG_DIR, "04_gap_quintiles.png"), dpi=130)   # save the picture

os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)     # the written reports live in outputs/markdown
with open(os.path.join(OUT_DIR, "markdown", "gap_diagnostics.md"), "w", encoding="utf-8") as f:   # open the report file
    f.write("\n".join(lines) + "\n")                # write every collected line
