# common.py
# helper functions used by all the other scripts in part C
# (loading data, cleaning it, performance numbers, the backtest engine)

import os                               # paths and env variables
import numpy as np                      # number crunching
import pandas as pd                     # tables

# folder paths, all relative to this file so the repo can be moved anywhere
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "outputs"))
FIG_DIR = os.path.join(OUT_DIR, "figures")
TAB_DIR = os.path.join(OUT_DIR, "tables")

# costs from the brief: 0.05% per side (brokerage + taxes + slippage all together)
COST_PER_SIDE = 0.0005
# trading days in a year, used for annualising (NSE is about 245-250, 252 is the usual convention)
TDAYS = 252

# diwali "muhurat" evening sessions, they are 1 hour long and happen on a market holiday
# so they are not a normal day. i know these dates from the NSE holiday circulars (public info)
MUHURAT_DAYS = pd.to_datetime([
    "2012-11-13", "2013-11-03", "2014-10-23", "2015-11-11", "2016-10-30",
    "2017-10-19", "2018-11-07", "2019-10-27", "2020-11-14", "2021-11-04",
    "2022-10-24", "2023-11-12", "2024-11-01", "2025-10-21"])


def load_raw(which):
    # which is "research" or "locked"
    # the locked folder is only readable if the env variable is set, and only 06_run_oos.py sets it
    if which == "locked" and os.environ.get("ALLOW_LOCKED_OOS") != "yes":
        raise PermissionError("locked out-of-sample data is off limits until the rules are frozen")
    folder = os.path.join(DATA_DIR, "research" if which == "research" else "locked_oos")
    suffix = "_research.csv" if which == "research" else "_locked.csv"
    out = {}
    for name in ["nifty50", "banknifty"]:
        # read the csv with the date as the index
        df = pd.read_csv(os.path.join(folder, name + suffix), parse_dates=["date"], index_col="date")
        out[name] = df.sort_index()
    return out["nifty50"], out["banknifty"]


def clean_pair(nifty, bank):
    # takes the two raw tables, returns one clean aligned table and a log of what was removed
    # the same function is used for research and for the locked period (no tuning on either)
    log = []                                                   # (rule, index, how many rows, which dates)
    cleaned = {}
    for name, df in [("nifty", nifty), ("bank", bank)]:
        df = df.copy()                                         # don't touch the caller's table
        n0 = len(df)                                           # rows we started with

        # rule 1: duplicated dates, keep the first one
        dup = df.index.duplicated()
        if dup.any():
            log.append(("duplicate date", name, int(dup.sum()), list(df.index[dup].date)))
        df = df[~dup]

        # rule 2: missing or non-positive prices
        price_cols = ["Open", "High", "Low", "Close"]
        bad = df[price_cols].isna().any(axis=1) | (df[price_cols] <= 0).any(axis=1)
        if bad.any():
            log.append(("missing/zero price", name, int(bad.sum()), list(df.index[bad].date)))
        df = df[~bad]

        # rule 3: high/low that don't contain open and close (impossible bar)
        body_hi = df[["Open", "Close"]].max(axis=1)
        body_lo = df[["Open", "Close"]].min(axis=1)
        bad = (df["High"] < body_hi) | (df["Low"] > body_lo)
        if bad.any():
            log.append(("high/low inconsistent with open/close", name, int(bad.sum()), list(df.index[bad].date)))
        df = df[~bad]

        # rule 4: frozen bar, all four prices identical and no volume = a placeholder, not a real session
        bad = (df["Open"] == df["High"]) & (df["High"] == df["Low"]) & (df["Low"] == df["Close"]) & (df["Volume"] == 0)
        if bad.any():
            log.append(("frozen bar (O=H=L=C, volume 0)", name, int(bad.sum()), list(df.index[bad].date)))
        df = df[~bad]

        # rule 5: muhurat evening sessions
        bad = df.index.isin(MUHURAT_DAYS)
        if bad.any():
            log.append(("muhurat session (1 hour, holiday)", name, int(bad.sum()), list(df.index[bad].date)))
        df = df[~bad]

        log.append(("rows kept after single-series rules", name, len(df), "started with %d" % n0))
        cleaned[name] = df

    # rule 6: keep only dates that exist in BOTH series (inner join)
    only_n = cleaned["nifty"].index.difference(cleaned["bank"].index)
    only_b = cleaned["bank"].index.difference(cleaned["nifty"].index)
    if len(only_n):
        log.append(("date only in nifty (dropped)", "nifty", len(only_n), list(only_n.date)))
    if len(only_b):
        log.append(("date only in banknifty (dropped)", "bank", len(only_b), list(only_b.date)))
    common = cleaned["nifty"].index.intersection(cleaned["bank"].index)

    # one wide table, prefix says which index the column belongs to
    n = cleaned["nifty"].loc[common].add_prefix("n_")
    b = cleaned["bank"].loc[common].add_prefix("b_")
    out = pd.concat([n, b], axis=1)
    # lower-case the column names, i find them easier to type
    out.columns = [c.lower() for c in out.columns]
    return out, log


def backtest(open_px, pos, cost=COST_PER_SIDE):
    # open_px: series of daily open prices
    # pos: series, pos[d] = position held from the OPEN of day d to the OPEN of day d+1
    #      (so it must already be decided with data up to the close of day d-1, the caller does the shift)
    # returns a table with gross and net daily returns of the strategy
    pos = pos.reindex(open_px.index).fillna(0.0)                 # no signal = flat
    oo = open_px.shift(-1) / open_px - 1                         # simple return open(d) -> open(d+1)
    gross = pos * oo                                             # what the position earns that day
    change = pos.diff().abs()                                    # how much we traded at the open of day d
    change.iloc[0] = abs(pos.iloc[0])                            # first day: we start flat, so entering costs too
    cost_paid = change * cost                                    # 0.05% per side, flipping long to short = 2 sides
    net = gross - cost_paid
    # the very last day has no next open, so there is no return for it; drop it
    out = pd.DataFrame({"pos": pos, "gross": gross, "cost": cost_paid, "net": net}).iloc[:-1]
    return out


def trades_from_bt(bt, cost=COST_PER_SIDE):
    # turn the daily table into a list of trades (a trade = consecutive days with the same direction)
    pos, gross = bt["pos"].values, bt["gross"].values
    trades = []                                                  # one number per trade: net return
    i, n = 0, len(pos)
    while i < n:
        if pos[i] == 0:                                          # flat, nothing to do
            i += 1
            continue
        j = i
        while j + 1 < n and np.sign(pos[j + 1]) == np.sign(pos[i]):   # keep going while direction is the same
            j += 1
        # compound the daily gross returns of the trade, then take off entry and exit costs
        gross_trade = np.prod(1 + gross[i:j + 1]) - 1
        entry_cost = cost * abs(pos[i])
        exit_cost = cost * abs(pos[j])
        trades.append(gross_trade - entry_cost - exit_cost)
        i = j + 1
    return np.array(trades)


def perf_stats(net, trades=None):
    # standard performance numbers from a daily net return series (rf = 0)
    net = net.dropna()
    n = len(net)
    equity = (1 + net).cumprod()
    years = n / TDAYS
    cagr = equity.iloc[-1] ** (1 / years) - 1 if equity.iloc[-1] > 0 else -1.0
    vol = net.std() * np.sqrt(TDAYS)
    sharpe = net.mean() / net.std() * np.sqrt(TDAYS) if net.std() > 0 else np.nan
    dd = equity / equity.cummax() - 1                            # drawdown at each day
    out = {"CAGR %": 100 * cagr, "Ann vol %": 100 * vol, "Sharpe": sharpe,
           "Max drawdown %": 100 * dd.min(), "Days": n}
    if trades is not None:
        wins, losses = trades[trades > 0], trades[trades <= 0]
        out.update({"Trades": len(trades),
                    "Win rate %": 100 * len(wins) / max(len(trades), 1),
                    "Avg win %": 100 * wins.mean() if len(wins) else np.nan,
                    "Avg loss %": 100 * losses.mean() if len(losses) else np.nan})
    return out


def stationary_bootstrap_idx(n, n_paths, mean_block, rng, length=None):
    # politis-romano stationary bootstrap: random block lengths (geometric), wraps around the sample
    # n = size of the sample we draw from, length = how many days each fake path has (default: same as n)
    # returns an array of indexes shape (n_paths, length)
    length = n if length is None else length
    p = 1.0 / mean_block                                         # chance that a new block starts at each step
    idx = np.empty((n_paths, length), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_paths)                      # random start
    new_block = rng.random((n_paths, length)) < p                # where blocks restart
    jumps = rng.integers(0, n, (n_paths, length))                # where they restart to
    for t in range(1, length):
        idx[:, t] = np.where(new_block[:, t], jumps[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def bootstrap_dd_sharpe(values, length, n_paths=10000, mean_block=20, seed=11, chunk=1000):
    # resample a daily return series in chunks (the machine does not have much RAM) and return
    # the max drawdown (in %, negative) and the annualised Sharpe of every fake path
    rng = np.random.default_rng(seed)
    dds, shs = [], []
    for _ in range(n_paths // chunk):
        idx = stationary_bootstrap_idx(len(values), chunk, mean_block, rng, length=length)
        paths = values[idx]
        dds.append(max_drawdown_paths(paths) * 100)
        shs.append(paths.mean(axis=1) / paths.std(axis=1) * np.sqrt(TDAYS))
    return np.concatenate(dds), np.concatenate(shs)


def max_drawdown_paths(ret_paths):
    # max drawdown for every row of a (paths x days) array of simple returns
    equity = np.cumprod(1 + ret_paths, axis=1)
    peak = np.maximum.accumulate(equity, axis=1)
    return (equity / peak - 1).min(axis=1)


def reality_check(ret_matrix, n_boot=2000, mean_block=20, seed=1):
    # white's reality check: how often does the BEST of G tried strategies look this good if none has any edge?
    # ret_matrix: DataFrame, one column per strategy tried, rows = days (net daily returns)
    rng = np.random.default_rng(seed)
    X = ret_matrix.dropna().values
    T, G = X.shape
    obs = np.sqrt(T) * X.mean(axis=0)                            # observed scaled mean of each strategy
    best_obs = obs.max()
    Xc = X - X.mean(axis=0)                                      # impose the null: every strategy has mean zero
    idx = stationary_bootstrap_idx(T, n_boot, mean_block, rng)
    best_boot = np.empty(n_boot)
    for b in range(n_boot):
        best_boot[b] = (np.sqrt(T) * Xc[idx[b]].mean(axis=0)).max()   # best strategy in this fake world
    return float((best_boot >= best_obs).mean())                 # share of fake worlds that beat what we saw


def add_returns(px):
    # adds the return columns i use everywhere (log returns), for both indices
    px = px.copy()
    for p in ["n", "b"]:
        o, h, l, c = px[p + "_open"], px[p + "_high"], px[p + "_low"], px[p + "_close"]
        px[p + "_ret"] = np.log(c / c.shift(1))                # close to close
        px[p + "_gap"] = np.log(o / c.shift(1))                # overnight: yesterday's close to today's open
        px[p + "_intra"] = np.log(c / o)                       # intraday: today's open to today's close
        px[p + "_range"] = np.log(h / l)                       # high-low range, a rough daily volatility measure
        # open to next open: what you earn holding from today's open to tomorrow's open
        px[p + "_oo"] = np.log(o.shift(-1) / o)
        # the return i can actually trade after a signal at today's close:
        # buy at TOMORROW's open, sell at the open after that (so it is the oo return shifted one day back)
        px[p + "_fwd"] = px[p + "_oo"].shift(-1)
    return px
