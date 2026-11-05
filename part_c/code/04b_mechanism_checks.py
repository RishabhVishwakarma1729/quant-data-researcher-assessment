# 04b_mechanism_checks.py
# the gap rule came out with a net Sharpe above 1 in the research period, which deserves a careful look before accepting it
# so before freezing anything i try to find out WHERE the money comes from
# research data only

import os                                           # paths
import numpy as np                                  # maths
import pandas as pd                                 # tables
import statsmodels.api as sm                        # regressions

from common import load_raw, clean_pair, add_returns, backtest, trades_from_bt, perf_stats, OUT_DIR, TDAYS   # the shared engine
from strategy import make_positions                 # the trading rule itself

nifty, bank = load_raw("research")                  # raw research data only
px, _ = clean_pair(nifty, bank)                     # clean and align the two series (the log of removed rows is not needed here)
px = add_returns(px)                                # add gaps, intraday and close-to-close returns
lines = []                                          # the markdown report is collected here


def say(t=""):                                      # prints a line and keeps it for the report
    print(t)                                        # show it on screen
    lines.append(t)                                 # and store it for the markdown file


say("# Mechanism checks (research period only)")   # the report title
say("")                                             # blank line

# ---- 1. autocorrelation of the pieces of the day
say("## 1. Autocorrelation of overnight and intraday returns (Nifty)")   # section heading
rows = []                                           # one table row per lag
for lag in range(1, 6):                             # look 1 to 5 days back
    rows.append({"lag": lag,
                 "overnight (gap)": px["n_gap"].autocorr(lag),                 # does today's gap resemble the gap `lag` days ago?
                 "intraday": px["n_intra"].autocorr(lag),                      # same for the open-to-close move
                 "close-to-close": px["n_ret"].autocorr(lag),                  # same for the full-day return
                 "corr(gap_t, intraday_t+lag)": px["n_gap"].corr(px["n_intra"].shift(-lag)),       # does a gap predict a later intraday move?
                 "corr(intraday_t, gap_t+lag)": px["n_intra"].corr(px["n_gap"].shift(-lag))})      # and the other way round
say(pd.DataFrame(rows).round(3).to_markdown(index=False))   # the five lags as a table, three decimals
say("")                                             # blank line
say("same-day correlation of gap and intraday: %.3f" % px["n_gap"].corr(px["n_intra"]))   # how the two pieces of one day relate
say("")                                             # blank line
by_half = []                                        # one table row per sub-period
for lab, d in [("2012-2016", px.loc[:"2016-12-31"]), ("2017-2021", px.loc["2017-01-01":]), ("excl. 2020", px[px.index.year != 2020])]:   # two halves, and without the covid year
    by_half.append({"period": lab, "gap lag1": d["n_gap"].autocorr(1), "gap lag2": d["n_gap"].autocorr(2),
                    "close-to-close lag1": d["n_ret"].autocorr(1)})   # the same autocorrelations inside that period
say(pd.DataFrame(by_half).round(3).to_markdown(index=False))   # the three periods as a table
say("")                                             # blank line

# ---- 2. joint regression with several lags
d = pd.DataFrame({"fwd": px["n_fwd"], "gap0": px["n_gap"], "gap1": px["n_gap"].shift(1), "gap2": px["n_gap"].shift(2),
                  "intra0": px["n_intra"], "intra1": px["n_intra"].shift(1)}).dropna()   # the outcome and today's and older pieces of the day side by side
res = sm.OLS(d["fwd"], sm.add_constant(d[["gap0", "gap1", "gap2", "intra0", "intra1"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})   # all of them in one regression, newey-west errors
say("## 2. next tradable day on several lags at once (Nifty)")   # section heading
say(pd.DataFrame({"coef": res.params, "t": res.tvalues}).round(3).to_markdown())   # coefficients and t-stats
say("")                                             # blank line

# ---- 3. same rule but driven by something else
say("## 3. Same trading rule, different signal (k=0.5, w=60, h=2, long/short, costs 0.05% a side)")   # section heading
say("")                                             # blank line


def alt_held(sig_series, k=0.5, w=60, h=2):         # the rule's "signal alive" series, for any input series
    # same machinery as strategy.py but the signal comes from any series, result = signal alive on day t (known at close t)
    sigma = sig_series.rolling(w).std().shift(1)    # spread of the previous w values, not including today's
    z = sig_series / sigma                          # how many spreads today's value is from zero
    s = (np.sign(z) * (z.abs() >= k)).fillna(0.0)   # +1 / -1 if the move is big enough, else 0
    held = s.replace(0, np.nan)                     # blank out the days with no signal
    if h > 1:                                       # ffill does not accept limit=0
        held = held.ffill(limit=h - 1)              # keep a signal alive for h days in total
    return held.fillna(0.0)                         # days with no signal mean no position


def alt_positions(sig_series, k=0.5, w=60, h=2):    # turns that signal into positions
    # position held from the next open
    return alt_held(sig_series, k, w, h).shift(1).fillna(0.0)   # shift(1): the signal is known at the close, the trade starts at the next open


rows = []                                           # one table row per signal
for lab, series in [("overnight gap (the real rule)", px["n_gap"]),
                    ("close-to-close return", px["n_ret"]),
                    ("intraday return (open to close)", px["n_intra"]),
                    ("gap minus intraday", px["n_gap"] - px["n_intra"]),
                    ("overnight gap of BANK NIFTY", px["b_gap"]),
                    ("pure noise (shuffled gaps)", pd.Series(np.random.default_rng(5).permutation(px["n_gap"].values), index=px.index))]:   # the real signal and five alternatives
    bt = backtest(px["n_open"], alt_positions(series))   # run the same engine with this signal
    st = perf_stats(bt["net"], trades_from_bt(bt))  # performance numbers after costs
    rows.append({"signal": lab, "net Sharpe": st["Sharpe"], "CAGR %": st["CAGR %"], "trades": st["Trades"],
                 "time in market %": 100 * (bt["pos"] != 0).mean()})   # keep the headline numbers for the table
say(pd.DataFrame(rows).round(2).to_markdown(index=False))   # all six signals as a table
say("")                                             # blank line

# ---- 4. is it just being long in a bull market?
say("## 4. Baselines (Nifty, open to open, same costs)")   # section heading
say("")                                             # blank line
rows = []                                           # one table row per baseline
for lab, pos in [("always long", pd.Series(1.0, index=px.index)),
                 ("long 78% of days at random (no signal)", pd.Series((np.random.default_rng(9).random(len(px)) < 0.78).astype(float), index=px.index)),
                 ("long only after an up close (momentum, 1 day)", (px["n_ret"] > 0).astype(float).shift(1).fillna(0)),
                 ("long only after an up gap (no threshold, 1 day)", (px["n_gap"] > 0).astype(float).shift(1).fillna(0))]:   # simple do-nothing-clever positions
    bt = backtest(px["n_open"], pos)                # run the engine on them
    st = perf_stats(bt["net"], trades_from_bt(bt))  # performance numbers after costs
    rows.append({"baseline": lab, "net Sharpe": st["Sharpe"], "CAGR %": st["CAGR %"], "MaxDD %": st["Max drawdown %"]})   # keep the headline numbers
say(pd.DataFrame(rows).round(2).to_markdown(index=False))   # the baselines as a table
say("")                                             # blank line

# ---- 5. does the edge need the opening print?
say("## 5. Does the edge survive if no opening price is used for trading?")   # section heading
say("")                                             # blank line
say("Same gap signal (k=0.5, w=60, h=2). Variant A enters at the CLOSE of the day after the signal day, variant B enters at the close of the signal day itself "
    "(not allowed by the brief, which says next open, shown only to see if the edge is about the opening print). Both trade close to close.")   # explains the two variants
say("")                                             # blank line
held = alt_held(px["n_gap"])                        # the real gap signal, alive on the days it is known at the close
rows = []                                           # one table row per variant
for lab, pos in [("A: enter close t+1, close-to-close", held.shift(1).fillna(0.0)),
                 ("B: enter close t, close-to-close (not allowed, for diagnosis)", held)]:   # A is allowed, B only for diagnosis
    bt = backtest(px["n_close"], pos)                    # backtest() earns pos[d] from price[d] to price[d+1], here the prices are closes
    st = perf_stats(bt["net"], trades_from_bt(bt))  # performance numbers after costs
    rows.append({"variant": lab, "net Sharpe": st["Sharpe"], "CAGR %": st["CAGR %"], "trades": st["Trades"]})   # keep the headline numbers
say(pd.DataFrame(rows).round(2).to_markdown(index=False))   # both variants as a table
say("")                                             # blank line

# ---- 6. how much is market exposure and how much is alpha?
say("## 6. Alpha and beta of the chosen rule against always-long Nifty (open to open)")   # section heading
say("")                                             # blank line
pos = make_positions(px, "n", 0.5, 60, 2, "both")   # the real rule's positions
bt = backtest(px["n_open"], pos)                    # run the engine on them
mkt = (px["n_open"].shift(-1) / px["n_open"] - 1).reindex(bt.index)   # what plain buy-and-hold earns over the same open-to-open days
res = sm.OLS(bt["net"], sm.add_constant(mkt)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})   # strategy return = alpha + beta x market return
say("average net exposure (long minus short): %.2f of capital" % bt["pos"].mean())   # how much of the time, net, we are long
say("beta to Nifty: %.2f (t=%.1f)" % (res.params.iloc[1], res.tvalues.iloc[1]))     # how strongly the strategy moves with the market
say("alpha: %.1f%% per year (t=%.2f)" % (res.params.iloc[0] * TDAYS * 100, res.tvalues.iloc[0]))   # the part not explained by the market, per year
say("")                                             # blank line

os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)     # the written reports live in outputs/markdown
with open(os.path.join(OUT_DIR, "markdown", "mechanism_checks.md"), "w", encoding="utf-8") as f:   # open the report file
    f.write("\n".join(lines) + "\n")                # write every collected line
