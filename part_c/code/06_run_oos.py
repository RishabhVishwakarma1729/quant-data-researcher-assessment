# 06_run_oos.py
# the one and only run on the locked 2022-2025 data, using the rules frozen by 05_freeze_rules.py
#   python 06_run_oos.py --dry-run   -> runs the exact same code on RESEARCH data to check it doesn't crash (no locked data touched)
#   python 06_run_oos.py             -> the real thing. checks the freeze hashes, writes a lock file, refuses to run twice

import os                                                   # paths + env variable
import sys                                                  # to quit with a message
import json                                                 # frozen rules file
import hashlib                                              # file hashes
import argparse                                             # command line option
import datetime as dt                                       # timestamps
import numpy as np                                          # maths
import pandas as pd                                         # tables
import statsmodels.api as sm                                # regressions
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common                                               # so i can reach the paths
from common import (clean_pair, add_returns, backtest, trades_from_bt, perf_stats, bootstrap_dd_sharpe,
                    load_raw, OUT_DIR, FIG_DIR, TAB_DIR, HERE, COST_PER_SIDE, TDAYS)
from strategy import make_positions

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true", help="use research data instead of the locked data")
args = ap.parse_args()
DRY = args.dry_run

FROZEN_FILE = os.path.join(OUT_DIR, "frozen_rules.json")
LOCK_FILE = os.path.join(OUT_DIR, "oos_run.lock")


def sha(path):
    # sha256 of a file's bytes (reading bytes is not "looking" at the data)
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- guard rails for the real run
if not DRY:
    if not os.path.exists(FROZEN_FILE):
        sys.exit("no frozen_rules.json, run 05_freeze_rules.py first")
    if os.path.exists(LOCK_FILE):
        sys.exit("oos_run.lock exists: the locked data has already been used once. Not running again.")
    frozen = json.load(open(FROZEN_FILE))
    for rel, h in frozen["code_hashes"].items():            # code must be byte-for-byte what was frozen
        if sha(os.path.join(HERE, rel)) != h:
            sys.exit("code file %s changed after the freeze, refusing to run" % rel)
    for rel, h in frozen["locked_data_hashes"].items():     # and the data must be what i downloaded
        if sha(os.path.join(HERE, "..", "data", "locked_oos", rel)) != h:
            sys.exit("locked data file %s changed after the freeze, refusing to run" % rel)
    # write the lock BEFORE reading any locked data, so even a crash counts as "used"
    with open(LOCK_FILE, "w") as f:
        f.write("oos run started %s\n" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    os.environ["ALLOW_LOCKED_OOS"] = "yes"                  # this is the only place that unlocks the data
    params = frozen["params"]
    tag, out_name = "oos", "oos_results.md"
else:
    params = json.load(open(os.path.join(TAB_DIR, "selected_params.json")))
    tag, out_name = "dryrun", "oos_dryrun_results.md"

P, K, W, H, SIDE = params["p"], params["k"], params["w"], params["h"], params["side"]
H1_NOTE = "DRY RUN on research data, numbers are meaningless" if DRY else "locked out-of-sample 2022-2025"
lines = []


def say(t=""):
    print(t)
    lines.append(t)


def run(px, p, k, w, h, side, cost=COST_PER_SIDE):
    pos = make_positions(px, p, k, w, h, side)
    bt = backtest(px[p + "_open"], pos, cost)
    return bt, trades_from_bt(bt, cost)


# ---------------------------------------------------------------- load + clean both periods
rs_n, rs_b = load_raw("research")
px_is, _ = clean_pair(rs_n, rs_b)
px_is = add_returns(px_is)                                  # in-sample table, to compare with
if DRY:
    px_oos, log_oos = clean_pair(rs_n, rs_b)                # dry run: pretend research is the oos set
else:
    lk_n, lk_b = load_raw("locked")
    px_oos, log_oos = clean_pair(lk_n, lk_b)
px_oos = add_returns(px_oos)

say("# Out-of-sample results (%s)" % H1_NOTE)
say("")
say("Frozen parameters: instrument=%s, k=%.1f, window=%d, hold=%d days, side=%s, cost=%.2f%% per side." % (
    "Nifty50" if P == "n" else "BankNifty", K, W, H, SIDE, 100 * COST_PER_SIDE))
say("Run at %s." % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
say("")

# ---------------------------------------------------------------- 1. data quality of the locked period (same cleaning function)
say("## 1. Data quality of the locked period (same cleaning function, nothing tuned)")
say("")
rows = [{"rule": r, "series": s, "rows": n, "details": str(d)[:110]} for r, s, n, d in log_oos]
say(pd.DataFrame(rows).to_markdown(index=False))
say("")
say("Clean table: %d rows, %s to %s." % (len(px_oos), px_oos.index.min().date(), px_oos.index.max().date()))
big = int(((px_oos["n_ret"].abs() > 0.05) | (px_oos["b_ret"].abs() > 0.05)).sum())
say("Days with a move above 5%% in either index: %d." % big)
say("")

# ---------------------------------------------------------------- 2. headline performance
bt_is, tr_is = run(px_is, P, K, W, H, SIDE)
bt_o, tr_o = run(px_oos, P, K, W, H, SIDE)
bh_is = backtest(px_is[P + "_open"], pd.Series(1.0, index=px_is.index))
bh_o = backtest(px_oos[P + "_open"], pd.Series(1.0, index=px_oos.index))
bt_ob, tr_ob = run(px_oos, "b", K, W, H, SIDE)              # bank nifty, same parameters, no re-tuning

say("## 2. In-sample vs out-of-sample, same rule, same parameters")
say("")
tab = pd.DataFrame({"In-sample 2012-21": perf_stats(bt_is["net"], tr_is),
                    "Out-of-sample": perf_stats(bt_o["net"], tr_o),
                    "Buy & hold Nifty, in-sample": perf_stats(bh_is["net"]),
                    "Buy & hold Nifty, out-of-sample": perf_stats(bh_o["net"]),
                    "Same rule on Bank Nifty, out-of-sample": perf_stats(bt_ob["net"], tr_ob)})
say(tab.round(2).to_markdown())
say("")
g_o = bt_o["gross"].mean() / bt_o["gross"].std() * np.sqrt(TDAYS)
say("Out-of-sample gross Sharpe (before costs) %.2f, net %.2f. Costs paid: %.1f%% of capital. Time in market: %.0f%% of days." % (
    g_o, perf_stats(bt_o["net"])["Sharpe"], 100 * bt_o["cost"].sum(), 100 * (bt_o["pos"] != 0).mean()))
say("")
yr = bt_o["net"].groupby(bt_o.index.year).apply(lambda s: (1 + s).prod() - 1) * 100
yr_bh = bh_o["net"].groupby(bh_o.index.year).apply(lambda s: (1 + s).prod() - 1) * 100
say(pd.DataFrame({"strategy net %": yr, "buy & hold %": yr_bh}).round(1).T.to_markdown())
say("")
mkt = (px_oos[P + "_open"].shift(-1) / px_oos[P + "_open"] - 1).reindex(bt_o.index)
ab = sm.OLS(bt_o["net"], sm.add_constant(mkt)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
say("Alpha / beta vs always-long Nifty, out-of-sample: average exposure %.2f, beta %.2f, alpha %.1f%% a year (t=%.2f)." % (
    bt_o["pos"].mean(), ab.params.iloc[1], ab.params.iloc[0] * TDAYS * 100, ab.tvalues.iloc[0]))
say("")

# ---------------------------------------------------------------- 3. is the anomaly itself still there?
say("## 3. Is the underlying anomaly still there? (yesterday's gap -> next tradable day)")
say("")
rows = []
for lab, d in [("research 2012-21", px_is), ("out-of-sample", px_oos)]:
    for p, nm in [("n", "Nifty50"), ("b", "BankNifty")]:
        s = d[[p + "_fwd", p + "_gap"]].dropna()
        res = sm.OLS(s[p + "_fwd"], sm.add_constant(s[p + "_gap"])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        rows.append({"period": lab, "index": nm, "effect bps per 1sd gap": res.params.iloc[1] * s[p + "_gap"].std() * 1e4,
                     "t-stat": res.tvalues.iloc[1], "n": len(s)})
say(pd.DataFrame(rows).round(2).to_markdown(index=False))
say("")
q = pd.qcut(px_oos[P + "_gap"], 5, labels=["Q1 (big gap down)", "Q2", "Q3", "Q4", "Q5 (big gap up)"])
qt = (px_oos.groupby(q, observed=True)[P + "_fwd"].mean() * 1e4).round(1)
say("Out-of-sample mean next tradable day return (bps) by gap quintile:")
say(qt.to_frame("bps").T.to_markdown())
say("")

# ---------------------------------------------------------------- 4. parameter sensitivity, informational only
say("## 4. Parameter sensitivity out-of-sample (information only, nothing is re-tuned from this)")
say("")
vrows = [("base", K, W, H), ("k -20%", K * 0.8, W, H), ("k +20%", K * 1.2, W, H),
         ("window -20%", K, int(round(W * 0.8)), H), ("window +20%", K, int(round(W * 1.2)), H),
         ("hold -1", K, W, max(H - 1, 1)), ("hold +1", K, W, H + 1)]
srows = []
for name, kk, ww, hh in vrows:
    b2, t2 = run(px_oos, P, kk, ww, hh, SIDE)
    s2 = perf_stats(b2["net"], t2)
    srows.append({"variant": name, "k": round(kk, 2), "window": ww, "hold": hh, "net Sharpe": s2["Sharpe"],
                  "CAGR %": s2["CAGR %"], "MaxDD %": s2["Max drawdown %"], "trades": s2["Trades"]})
say(pd.DataFrame(srows).round(2).to_markdown(index=False))
say("")

# costs
crow = []
for c in [0.0, 0.00025, 0.0005, 0.00075, 0.001]:
    b2, t2 = run(px_oos, P, K, W, H, SIDE, cost=c)
    crow.append({"cost per side %": c * 100, "net Sharpe": perf_stats(b2["net"])["Sharpe"], "CAGR %": perf_stats(b2["net"])["CAGR %"]})
say("Cost sensitivity out-of-sample:")
say("")
say(pd.DataFrame(crow).round(2).to_markdown(index=False))
say("")

# ---------------------------------------------------------------- 5. drawdown vs what the bootstrap said
say("## 5. Was the out-of-sample drawdown within what the research-period bootstrap predicted?")
say("")
net_is = bt_is["net"].values
n_days = len(bt_o)
half = net_is - 0.5 * net_is.mean()                         # scenario 2: only half of the measured edge is real
mdd1, sh_paths1 = bootstrap_dd_sharpe(net_is, n_days)       # scenario 1: edge as measured
mdd2, sh_paths2 = bootstrap_dd_sharpe(half, n_days)
actual = perf_stats(bt_o["net"])["Max drawdown %"]
act_sh = perf_stats(bt_o["net"])["Sharpe"]
say("Actual out-of-sample max drawdown: %.1f%% over %d days." % (actual, n_days))
say("- Scenario 1 (edge as measured): median predicted max drawdown %.1f%%, worst 5%% %.1f%%. Share of simulated paths with a drawdown at least as bad as the actual one: %.0f%%." % (
    np.median(mdd1), np.percentile(mdd1, 5), 100 * (mdd1 <= actual).mean()))
say("- Scenario 2 (half the edge): median %.1f%%, worst 5%% %.1f%%. Share at least as bad as the actual one: %.0f%%." % (
    np.median(mdd2), np.percentile(mdd2, 5), 100 * (mdd2 <= actual).mean()))
say("")
say("Actual out-of-sample Sharpe %.2f. Share of simulated paths with a Sharpe at least this LOW: scenario 1 %.0f%%, scenario 2 %.0f%%." % (
    act_sh, 100 * (sh_paths1 <= act_sh).mean(), 100 * (sh_paths2 <= act_sh).mean()))
say("")
# bootstrap confidence interval for the oos sharpe itself (resampling the oos days)
_, sh_oos = bootstrap_dd_sharpe(bt_o["net"].values, n_days, seed=3)
sh_ci = np.percentile(sh_oos, [2.5, 50, 97.5])
say("Bootstrap 95%% confidence interval for the out-of-sample Sharpe (resampling the out-of-sample days): %.2f to %.2f (median %.2f)." % (sh_ci[0], sh_ci[2], sh_ci[1]))
say("")

# ---------------------------------------------------------------- figures
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=False, gridspec_kw={"height_ratios": [3, 1]})
full_net = pd.concat([bt_is["net"], bt_o["net"]])
eq = (1 + full_net).cumprod()
bh_full = pd.concat([bh_is["net"], bh_o["net"]])
eq_bh = (1 + bh_full).cumprod()
ax[0].plot(eq.index, eq, label="strategy, net of costs", color="tab:blue")
ax[0].plot(eq_bh.index, eq_bh, label="buy & hold Nifty", color="grey")
if not DRY:
    ax[0].axvline(pd.Timestamp("2022-01-01"), color="red", ls="--", label="start of locked out-of-sample")
ax[0].set_yscale("log")
ax[0].set_ylabel("growth of 1 (log scale)")
ax[0].set_title("Strategy and buy & hold, in-sample then out-of-sample (%s)" % ("DRY RUN" if DRY else "real run"))
ax[0].legend()
dd_full = eq / eq.cummax() - 1
ax[1].fill_between(dd_full.index, dd_full * 100, 0, color="tab:red", alpha=0.5)
ax[1].set_ylabel("drawdown %")
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "07_equity_%s.png" % tag), dpi=130)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
eq_o = (1 + bt_o["net"]).cumprod()
ax[0].plot(eq_o.index, eq_o, label="strategy net", color="tab:blue")
ax[0].plot(eq_o.index, (1 + bt_o["gross"]).cumprod(), label="strategy gross", color="tab:blue", ls=":")
ax[0].plot(eq_o.index, (1 + bh_o["net"]).cumprod().reindex(eq_o.index), label="buy & hold", color="grey")
ax[0].set_title("Out-of-sample period only" if not DRY else "dry run")
ax[0].legend()
ax[1].hist(mdd1, bins=40, alpha=0.6, label="scenario 1 (edge as measured)", color="steelblue")
ax[1].hist(mdd2, bins=40, alpha=0.6, label="scenario 2 (half the edge)", color="orange")
ax[1].axvline(actual, color="red", lw=2, label="actual")
ax[1].set_xlabel("max drawdown %")
ax[1].legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "08_oos_only_%s.png" % tag), dpi=130)

with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwritten", out_name)
