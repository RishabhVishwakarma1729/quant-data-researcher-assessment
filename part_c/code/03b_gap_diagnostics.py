# 03b_gap_diagnostics.py
# the scan said "yesterday's overnight gap predicts the next tradable day" (survives multiple testing)
# before i believe it i want to know where it comes from: which part of the day, is it just 2020, is it every year?
# research data only

import os                                           # paths
import numpy as np                                  # maths
import pandas as pd                                 # tables
import statsmodels.api as sm                        # regressions
from scipy import stats                             # spearman
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import OUT_DIR, FIG_DIR

px = pd.read_pickle(os.path.join(OUT_DIR, "research_features.pkl"))   # saved by 03_anomaly_scan.py
lines = []                                          # for the markdown output


def say(t=""):
    print(t)
    lines.append(t)


def slope(y, x, lags=5):
    # slope of y on x (bps per 1 std of x) with newey-west t-stat
    s = pd.concat([y, x], axis=1).dropna()
    s.columns = ["y", "x"]
    res = sm.OLS(s["y"], sm.add_constant(s["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return res.params["x"] * s["x"].std() * 1e4, res.tvalues["x"], len(s)


say("# Gap diagnostics (research period only)")
say("")
for p, nm in [("n", "Nifty50"), ("b", "BankNifty")]:
    say("## " + nm)
    gap = px[p + "_gap"]                                       # overnight move into day t
    # the tradable return is open(t+1) -> open(t+2). split it in two pieces:
    intra_next = px[p + "_intra"].shift(-1)                    # open(t+1) -> close(t+1)
    gap_next2 = px[p + "_gap"].shift(-2)                       # close(t+1) -> open(t+2)
    rows = []
    for lab, y in [("next tradable day (open t+1 to open t+2)", px[p + "_fwd"]),
                   ("  part 1: intraday of day t+1", intra_next),
                   ("  part 2: overnight into t+2", gap_next2)]:
        e, t, n = slope(y, gap)
        rows.append({"outcome": lab, "effect bps per 1sd gap": round(e, 2), "t-stat": round(t, 2), "n": n})
    say(pd.DataFrame(rows).to_markdown(index=False))
    say("")

    # robustness 1: drop 2020
    no20 = px.index.year != 2020
    e, t, n = slope(px.loc[no20, p + "_fwd"], gap[no20])
    say("Excluding 2020: effect %.2f bps per 1sd, t=%.2f (n=%d)" % (e, t, n))
    # robustness 2: winsorise gap and outcome at 1%/99%
    g_w = gap.clip(gap.quantile(0.01), gap.quantile(0.99))
    y_w = px[p + "_fwd"].clip(px[p + "_fwd"].quantile(0.01), px[p + "_fwd"].quantile(0.99))
    e, t, n = slope(y_w, g_w)
    say("Winsorised at 1%%/99%%: effect %.2f bps per 1sd, t=%.2f" % (e, t))
    # robustness 3: rank correlation (not sensitive to outliers at all)
    s = pd.concat([gap, px[p + "_fwd"]], axis=1).dropna()
    rho, pv = stats.spearmanr(s.iloc[:, 0], s.iloc[:, 1])
    say("Spearman rank correlation gap(t) vs next tradable day: %.3f (p=%.4f)" % (rho, pv))
    say("")

    # quintiles of the gap
    q = pd.qcut(gap, 5, labels=["Q1 (big down gap)", "Q2", "Q3", "Q4", "Q5 (big up gap)"])
    qt = px.groupby(q)[p + "_fwd"].agg(["mean", "count"])
    qt["mean"] = (qt["mean"] * 1e4).round(1)
    qt.columns = ["mean next tradable day (bps)", "days"]
    say("By gap quintile:")
    say(qt.to_markdown())
    say("")

    # year by year slope
    yr_rows = []
    for yr in range(2012, 2022):
        m = px.index.year == yr
        e, t, n = slope(px.loc[m, p + "_fwd"], gap[m])
        yr_rows.append({"year": yr, "effect bps per 1sd gap": round(e, 1), "t": round(t, 2)})
    yt = pd.DataFrame(yr_rows)
    say("By calendar year:")
    say(yt.to_markdown(index=False))
    say("positive in %d of 10 years" % int((yt["effect bps per 1sd gap"] > 0).sum()))
    say("")

# is it about the gap or about the whole day? compare gap vs close-to-close vs intraday as predictors, nifty
say("## Which piece of yesterday predicts tomorrow? (Nifty, joint regression)")
d = px[["n_fwd", "n_gap", "n_intra"]].dropna()
res = sm.OLS(d["n_fwd"], sm.add_constant(d[["n_gap", "n_intra"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
say("n_fwd on gap and intraday together:")
say(pd.DataFrame({"coef": res.params, "t": res.tvalues}).round(3).to_markdown())
say("")

# picture: mean next-day return by gap quintile, both indices
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
for a, (p, nm) in zip(ax, [("n", "Nifty50"), ("b", "BankNifty")]):
    q = pd.qcut(px[p + "_gap"], 5, labels=False)
    m = px.groupby(q)[p + "_fwd"].mean() * 1e4
    a.bar(range(1, 6), m.values, color=["tab:red" if v < 0 else "tab:green" for v in m.values])
    a.axhline(0, color="black", lw=0.5)
    a.set_title(nm)
    a.set_xlabel("quintile of yesterday's overnight gap (1 = biggest gap down)")
ax[0].set_ylabel("next tradable day return (bps)")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "04_gap_quintiles.png"), dpi=130)

os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)     # the written reports live in outputs/markdown
with open(os.path.join(OUT_DIR, "markdown", "gap_diagnostics.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
