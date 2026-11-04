# 04_strategy_research.py
# steps 3-5 on the research period only (2012-2021):
#   - try a small fixed grid of the "gap momentum" rule, pick one by a rule i wrote down BEFORE running
#   - check it for data snooping (white's reality check), parameter sensitivity (+-20%) and bootstrap drawdown
# nothing from 2022-2025 is read here
#   python 04_strategy_research.py --nse-filled  -> side check: only the grid, the selection and the reality check, on research data plus NSE's own bars for the days
#                                                   Yahoo lacks. it appends a section to outputs/markdown/nse_filled_side_check.md and overwrites nothing submitted

import os                                               # paths
import sys                                              # to stop after the side check
import argparse                                         # command line option
import json                                             # to save the chosen parameters
import itertools                                        # for the grid
import numpy as np                                      # maths
import pandas as pd                                     # tables
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import (load_raw, clean_pair, add_returns, backtest, trades_from_bt, perf_stats,
                    stationary_bootstrap_idx, max_drawdown_paths, reality_check,
                    MUHURAT_DAYS, DATA_DIR, OUT_DIR, FIG_DIR, TAB_DIR, COST_PER_SIDE, TDAYS)
from strategy import make_positions

ap = argparse.ArgumentParser()
ap.add_argument("--nse-filled", action="store_true", help="side check: grid, selection and reality check on research data plus NSE's bars for the days Yahoo lacks")
args = ap.parse_args()

# ---------------------------------------------------------------- data (research only)
nifty, bank = load_raw("research")
if args.nse_filled:
    # side check: add NSE's own bars for the real trading days Yahoo lacks (same days as in section 7 of the data quality report, muhurat evenings left out)
    off = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_index_ohlc_2012_2021.csv"), parse_dates=["date"])

    def with_nse(tab, lab):
        o = off[off["index"] == lab].set_index("date")
        days = o.index.difference(tab.index).difference(MUHURAT_DAYS)
        add = o.loc[days, ["open", "high", "low", "close"]].copy()
        add.columns = ["Open", "High", "Low", "Close"]
        add["Volume"] = 0.0                                 # volume is not used anywhere
        return pd.concat([tab, add]).sort_index()

    nifty, bank = with_nse(nifty, "Nifty 50"), with_nse(bank, "Bank Nifty")
px, _ = clean_pair(nifty, bank)
px = add_returns(px)
H1_END = "2016-12-31"                                   # halves of the research period

lines = []                                              # markdown report, built as we go


def say(t=""):
    print(t)
    lines.append(t)


def run(p, k, w, h, side, cost=COST_PER_SIDE):
    # one full backtest of one parameter set, returns (daily table, trades)
    pos = make_positions(px, p, k, w, h, side)
    bt = backtest(px[p + "_open"], pos, cost)
    return bt, trades_from_bt(bt, cost)


# ---------------------------------------------------------------- the grid i decided on before running
# k = threshold (in std of gaps), h = holding days, side = long/short or long only. window w is fixed at 60 days
GRID_K = [0.5, 1.0, 1.5]
GRID_H = [1, 2, 3]
GRID_SIDE = ["both", "long"]
W = 60
MIN_TRADES = 100                                        # rule: need at least this many trades to trust a variant

# selection rule (written in the plan before the run): highest full-period net Sharpe among variants that have
# >= MIN_TRADES trades AND positive net Sharpe in both 2012-2016 and 2017-2021

say("# Strategy research (research period 2012-2021 only)")
say("")
say("## 1. The grid I tried (every variant, nothing hidden)")
say("")
rows, series = [], {}
for k, h, side in itertools.product(GRID_K, GRID_H, GRID_SIDE):
    bt, tr = run("n", k, W, h, side)
    st = perf_stats(bt["net"], tr)
    sh1 = perf_stats(bt.loc[:H1_END, "net"])["Sharpe"]
    sh2 = perf_stats(bt.loc["2017-01-01":, "net"])["Sharpe"]
    gross_sh = bt["gross"].mean() / bt["gross"].std() * np.sqrt(TDAYS)
    rows.append({"k": k, "hold": h, "side": side, "gross Sharpe": gross_sh, "net Sharpe": st["Sharpe"],
                 "Sharpe 12-16": sh1, "Sharpe 17-21": sh2, "CAGR %": st["CAGR %"],
                 "MaxDD %": st["Max drawdown %"], "trades": st["Trades"],
                 "time in market %": 100 * (bt["pos"] != 0).mean()})
    series["k=%s,h=%d,%s" % (k, h, side)] = bt["net"]
grid = pd.DataFrame(rows)
say(grid.round(2).to_markdown(index=False))
say("")

# apply the selection rule
ok = grid[(grid["trades"] >= MIN_TRADES) & (grid["Sharpe 12-16"] > 0) & (grid["Sharpe 17-21"] > 0)]
if len(ok):
    best = ok.sort_values("net Sharpe", ascending=False).iloc[0]
    say("Variants passing the rule (>= %d trades, positive net Sharpe in both halves): %d of %d" % (MIN_TRADES, len(ok), len(grid)))
else:
    best = grid.sort_values("net Sharpe", ascending=False).iloc[0]
    say("NO variant passed the rule. Taking the best net Sharpe anyway, but this already says the idea is weak.")
K, H, SIDE = float(best["k"]), int(best["hold"]), best["side"]
say("**Chosen: k=%.1f, hold=%d day(s), side=%s, window=%d**" % (K, H, SIDE, W))
say("")

# ---------------------------------------------------------------- data snooping check
rc_p = reality_check(pd.DataFrame(series))
say("## 2. Did I just pick the luckiest of %d variants? (White's Reality Check)" % len(grid))
say("")
say("Bootstrap p-value that the best of the %d variants is no better than zero-edge luck: **%.3f**" % (len(grid), rc_p))
say("(small = the best variant is hard to explain by selection luck alone)")
say("")

# ---------------------------------------------------------------- side check: compare with the submitted grid, then stop
if args.nse_filled:
    base_grid = pd.read_csv(os.path.join(TAB_DIR, "grid_research.csv"))                  # as submitted, Yahoo only
    base_prm = json.load(open(os.path.join(TAB_DIR, "selected_params.json")))
    cmp_ = base_grid.merge(grid, on=["k", "hold", "side"], suffixes=(" sub", " filled"))
    assert len(cmp_) == len(base_grid) == len(grid)
    rep = ["## 2. The grid, the choice of rule and the reality check", "",
           "Same grid of %d variants, the same selection rule (written before the run) and the same bootstrap seed, on the research data plus NSE's bars. "
           "Nothing in `grid_research.csv` or `selected_params.json` is touched." % len(grid), ""]
    tab_ = pd.DataFrame({"k": cmp_["k"].astype(str), "hold": cmp_["hold"].astype(str), "side": cmp_["side"],
                         "net Sharpe sub / filled": cmp_["net Sharpe sub"].map("{:.3f}".format) + " / " + cmp_["net Sharpe filled"].map("{:.3f}".format),
                         "Sharpe 12-16 sub / filled": cmp_["Sharpe 12-16 sub"].map("{:.2f}".format) + " / " + cmp_["Sharpe 12-16 filled"].map("{:.2f}".format),
                         "Sharpe 17-21 sub / filled": cmp_["Sharpe 17-21 sub"].map("{:.2f}".format) + " / " + cmp_["Sharpe 17-21 filled"].map("{:.2f}".format),
                         "trades sub / filled": cmp_["trades sub"].astype(int).astype(str) + " / " + cmp_["trades filled"].astype(int).astype(str)})
    rep += [tab_.to_markdown(index=False, disable_numparse=True), ""]
    same = (float(base_prm["k"]) == K and int(base_prm["h"]) == H and base_prm["side"] == SIDE)
    rep.append("**Chosen variant:** as submitted k=%.1f, hold=%d, side=%s; with NSE's bars added k=%.1f, hold=%d, side=%s (%s). "
               "**Reality check p-value:** %.3f as submitted, %.3f with NSE's bars added. "
               "Largest change in a variant's net Sharpe: %.3f." % (
                   float(base_prm["k"]), int(base_prm["h"]), base_prm["side"], K, H, SIDE, "the same variant" if same else "a DIFFERENT variant",
                   base_prm["reality_check_p"], rc_p, (cmp_["net Sharpe filled"] - cmp_["net Sharpe sub"]).abs().max()))
    rep.append("")
    md_path = os.path.join(OUT_DIR, "markdown", "nse_filled_side_check.md")
    if os.path.exists(md_path):
        old_md = open(md_path, encoding="utf-8").read()
        head = old_md.split("## 2. The grid")[0].rstrip("\n") + "\n\n"          # keep section 1 (written by 03_anomaly_scan.py --nse-filled), replace any older section 2
    else:
        head = "# Side check: research results on data with NSE's own bars added\n\n"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(rep) + "\n")
    print("\n".join(rep))
    print("side check done")
    sys.exit(0)

# ---------------------------------------------------------------- performance of the chosen rule
bt, tr = run("n", K, W, H, SIDE)
bt_gross_only = bt["gross"]
st_all = perf_stats(bt["net"], tr)
bh_pos = pd.Series(1.0, index=px.index)                  # buy and hold nifty from the first open, same cost model
bh = backtest(px["n_open"], bh_pos)
st_bh = perf_stats(bh["net"])
say("## 3. Chosen rule, research period")
say("")
tab = pd.DataFrame({"Strategy (net of costs)": st_all,
                    "Strategy 2012-16": perf_stats(bt.loc[:H1_END, "net"], trades_from_bt(bt.loc[:H1_END])),
                    "Strategy 2017-21": perf_stats(bt.loc["2017-01-01":, "net"], trades_from_bt(bt.loc["2017-01-01":])),
                    "Buy & hold Nifty (open to open)": st_bh})
say(tab.round(2).to_markdown())
say("")
gross_sharpe = bt["gross"].mean() / bt["gross"].std() * np.sqrt(TDAYS)
say("Gross Sharpe (before costs): %.2f. Total costs paid over the period: %.1f%% of capital (simple sum of daily costs)." % (gross_sharpe, 100 * bt["cost"].sum()))
say("Time in the market: %.0f%% of days. Average trade: %.2f%% net." % (100 * (bt["pos"] != 0).mean(), 100 * tr.mean()))
say("")

# by year and by side
yr = bt["net"].groupby(bt.index.year).apply(lambda s: (1 + s).prod() - 1) * 100
say("Net return by calendar year (%):")
say(yr.round(1).to_frame("net return %").T.to_markdown())
say("")
long_part = (bt["pos"].clip(lower=0) * (px["n_open"].shift(-1) / px["n_open"] - 1).reindex(bt.index))
short_part = (bt["pos"].clip(upper=0) * (px["n_open"].shift(-1) / px["n_open"] - 1).reindex(bt.index))
say("Gross P&L split: long side %.1f%% of capital, short side %.1f%% of capital (sum of daily gross, no compounding)." % (100 * long_part.sum(), 100 * short_part.sum()))
no20 = bt.loc[bt.index.year != 2020, "net"]
say("Net Sharpe excluding 2020: %.2f (full period %.2f)" % (perf_stats(no20)["Sharpe"], st_all["Sharpe"]))
say("")

# the same rule on bank nifty, fixed parameters, no re-tuning (a free replication)
bt_b, tr_b = run("b", K, W, H, SIDE)
st_b = perf_stats(bt_b["net"], tr_b)
say("Same rule, same parameters on **Bank Nifty** (no re-tuning): net Sharpe %.2f, CAGR %.1f%%, max DD %.1f%%, %d trades."
    % (st_b["Sharpe"], st_b["CAGR %"], st_b["Max drawdown %"], st_b["Trades"]))
say("")

# cost sensitivity
say("## 4. How much do costs matter?")
say("")
crow = []
for c in [0.0, 0.00025, 0.0005, 0.00075, 0.001]:
    b2, t2 = run("n", K, W, H, SIDE, cost=c)
    s2 = perf_stats(b2["net"], t2)
    crow.append({"cost per side %": c * 100, "net Sharpe": s2["Sharpe"], "CAGR %": s2["CAGR %"]})
say(pd.DataFrame(crow).round(2).to_markdown(index=False))
say("")

# ---------------------------------------------------------------- parameter sensitivity (+-20%)
say("## 5. Parameter sensitivity (each parameter moved by -20% / +20%)")
say("")
say("Hold days is an integer so I moved it by one day (h-1, h+1); with a 1-3 day hold, 20% is less than a day. The window is rounded to whole days.")
say("")


def variants():
    # one-at-a-time changes, then all eight corners together
    out = [("base", K, W, H)]
    out += [("k -20%", K * 0.8, W, H), ("k +20%", K * 1.2, W, H),
            ("window -20%", K, int(round(W * 0.8)), H), ("window +20%", K, int(round(W * 1.2)), H),
            ("hold -1", K, W, max(H - 1, 1)), ("hold +1", K, W, H + 1)]
    for kk, ww, hh in itertools.product([0.8, 1.2], [0.8, 1.2], [-1, 1]):
        out.append(("corner k%+d%% w%+d%% h%+d" % (round((kk - 1) * 100), round((ww - 1) * 100), hh),
                    K * kk, int(round(W * ww)), max(H + hh, 1)))
    return out


srows = []
for name, kk, ww, hh in variants():
    b2, t2 = run("n", kk, ww, hh, SIDE)
    s2 = perf_stats(b2["net"], t2)
    srows.append({"variant": name, "k": round(kk, 2), "window": ww, "hold": hh, "net Sharpe": s2["Sharpe"],
                  "CAGR %": s2["CAGR %"], "MaxDD %": s2["Max drawdown %"], "trades": s2["Trades"]})
sens = pd.DataFrame(srows)
say(sens.round(2).to_markdown(index=False))
share_pos = (sens["net Sharpe"] > 0).mean()
say("")
say("Net Sharpe is positive in %.0f%% of these %d variants. Range: %.2f to %.2f." % (100 * share_pos, len(sens), sens["net Sharpe"].min(), sens["net Sharpe"].max()))
say("")

# ---------------------------------------------------------------- bootstrap drawdown
say("## 6. Drawdown I should realistically expect (stationary bootstrap, 10,000 paths)")
say("")
rng = np.random.default_rng(11)
net = bt["net"].values
H_DAYS = 1000                                           # about 4 years of trading, same length as the locked period
idx = stationary_bootstrap_idx(len(net), 10000, 20, rng)[:, :H_DAYS]   # blocks of ~20 days keep some vol clustering


def mc_table(returns, label):
    # resample the daily returns, report how large the 4 year max drawdown and how low the 4 year Sharpe can get
    paths = returns[idx]
    mdd = max_drawdown_paths(paths) * 100                # these are negative numbers (-15 = a 15% drawdown)
    sharpe_paths = paths.mean(axis=1) / paths.std(axis=1) * np.sqrt(TDAYS)
    ann_ret = ((1 + paths).prod(axis=1) ** (TDAYS / H_DAYS) - 1) * 100
    # "worst x%" = the percentile from the unfavourable end, so for drawdown (negative) that is the LOW percentile
    out = pd.DataFrame({"max drawdown %": np.percentile(mdd, [50, 25, 10, 5, 1]),
                        "annualised return %": np.percentile(ann_ret, [50, 25, 10, 5, 1]),
                        "Sharpe": np.percentile(sharpe_paths, [50, 25, 10, 5, 1])},
                       index=["typical (median)", "bad (worst 25%)", "worse (worst 10%)", "very bad (worst 5%)", "extreme (worst 1%)"])
    say("**%s**" % label)
    say("")
    say(out.round(1).to_markdown())
    say("")
    say("P(4-year max drawdown worse than 10%%) = %.0f%%, worse than 15%% = %.0f%%, worse than 20%% = %.0f%%, worse than 25%% = %.0f%%. P(4-year Sharpe <= 0) = %.1f%%." % (
        100 * (mdd < -10).mean(), 100 * (mdd < -15).mean(), 100 * (mdd < -20).mean(), 100 * (mdd < -25).mean(), 100 * (sharpe_paths <= 0).mean()))
    say("")
    return mdd


say("Over a %d-day (~4 year) horizon, resampling this strategy's own daily net returns." % H_DAYS)
say("")
mdd = mc_table(net, "Scenario 1: the edge is exactly what I measured in the research period")
# scenario 2: assume half of the average daily return was luck / overfit
haircut = net - 0.5 * net.mean()
mdd_half = mc_table(haircut, "Scenario 2: only half of the measured edge is real (daily mean return cut by 50%)")
say("Historical max drawdown of the rule in the research period: %.1f%%." % st_all["Max drawdown %"])
say("")
say("Caveat: the bootstrap only captures sampling noise. It cannot see regime change or the selection bias of picking this rule out of many ideas, so scenario 2 is the one i would plan around.")
say("")

# alpha / beta against always-long nifty
mkt = (px["n_open"].shift(-1) / px["n_open"] - 1).reindex(bt.index)
import statsmodels.api as sm
ab = sm.OLS(bt["net"], sm.add_constant(mkt)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
say("## 7. How much is just market exposure?")
say("")
say("Average net exposure %.2f of capital. Beta to always-long Nifty %.2f (t=%.1f). Alpha %.1f%% a year (t=%.2f)." % (
    bt["pos"].mean(), ab.params.iloc[1], ab.tvalues.iloc[1], ab.params.iloc[0] * TDAYS * 100, ab.tvalues.iloc[0]))
say("")

# ---------------------------------------------------------------- figures
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
eq_net = (1 + bt["net"]).cumprod()
eq_gross = (1 + bt["gross"]).cumprod()
eq_bh = (1 + bh["net"]).cumprod().reindex(bt.index)
ax[0].plot(eq_net.index, eq_net, label="strategy, net of 0.05%/side costs", color="tab:blue")
ax[0].plot(eq_gross.index, eq_gross, label="strategy, before costs", color="tab:blue", ls=":")
ax[0].plot(eq_bh.index, eq_bh, label="buy & hold Nifty", color="grey")
ax[0].axvline(pd.Timestamp("2017-01-01"), color="black", lw=0.5, ls="--")
ax[0].set_ylabel("growth of 1")
ax[0].set_title("Research period: chosen rule k=%.1f, hold=%d, %s" % (K, H, SIDE))
ax[0].legend()
dd = eq_net / eq_net.cummax() - 1
ax[1].fill_between(dd.index, dd * 100, 0, color="tab:red", alpha=0.5)
ax[1].set_ylabel("drawdown %")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "05_equity_research.png"), dpi=130)

fig, ax = plt.subplots(1, 3, figsize=(12, 3.8))
for a, side in zip(ax[:2], GRID_SIDE):
    g = grid[grid["side"] == side].pivot(index="k", columns="hold", values="net Sharpe")
    im = a.imshow(g.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
    a.set_xticks(range(len(g.columns)))
    a.set_xticklabels(g.columns)
    a.set_yticks(range(len(g.index)))
    a.set_yticklabels(g.index)
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            a.text(j, i, "%.2f" % g.values[i, j], ha="center", va="center", fontsize=8)
    a.set_xlabel("hold (days)")
    a.set_ylabel("threshold k")
    a.set_title("net Sharpe, %s" % side)
ax[2].hist(mdd, bins=40, color="steelblue", edgecolor="white")
ax[2].axvline(np.percentile(mdd, 5), color="red", ls="--", label="worst 5%")
ax[2].set_xlabel("max drawdown % over ~4 years")
ax[2].set_title("bootstrap drawdown")
ax[2].legend()
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "06_grid_and_drawdown.png"), dpi=130)

# ---------------------------------------------------------------- save
os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)     # the written reports live in outputs/markdown
with open(os.path.join(OUT_DIR, "markdown", "strategy_research.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
grid.to_csv(os.path.join(TAB_DIR, "grid_research.csv"), index=False)
sens.to_csv(os.path.join(TAB_DIR, "sensitivity_research.csv"), index=False)
with open(os.path.join(TAB_DIR, "selected_params.json"), "w") as f:
    json.dump({"p": "n", "k": K, "w": W, "h": H, "side": SIDE, "cost_per_side": COST_PER_SIDE,
               "n_variants_tried": len(grid), "reality_check_p": rc_p}, f, indent=2)
print("saved")
