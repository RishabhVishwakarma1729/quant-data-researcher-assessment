# corrected_script.py
# a revised version of the original script, with my suggested changes (the reasons are explained in issues.md)
# needs nifty_daily.csv with date, open, high, low, close, volume. i ran it on the 2012-2021 research data only
# source of that file: nifty 50 (yahoo ticker ^NSEI) daily bars from yahoo finance, downloaded with the yfinance package on 3 nov 2026,
# a copy of part_c/data/research/nifty50_research.csv with lower-case column names (all data sources are listed in the top-level README.md)

import numpy as np                                      # maths
import pandas as pd                                     # tables
from sklearn.ensemble import RandomForestClassifier     # same model family as the original, kept deliberately simple

COST = 0.0005                                           # 0.05% per side, the number given in the brief
FIRST_TRAIN = 750                                       # first ~3 years are only used for training, no trading
STEP = 63                                               # retrain once a quarter (63 trading days)
PURGE = 2                                               # label of row t uses prices up to the open of t+2, so drop the last 2 train rows

df = pd.read_csv("nifty_daily.csv", parse_dates=["date"]).set_index("date").sort_index()   # sort so rolling windows go forward in time
df["volume"] = df["volume"].replace(0, np.nan)          # a volume of 0 is missing data (yahoo has none for 2012), not "no trading"
df["ret"] = df["close"].pct_change()                    # today's close-to-close return, known at today's close

# ---- features, every one of them only uses data up to and including today's close
df["ma_20"] = df["close"].rolling(20).mean()            # 20 day moving average
df["dist_ma"] = (df["close"] - df["ma_20"]) / df["ma_20"]   # how far the close is from its average
df["vol_20"] = df["ret"].rolling(20).std()              # 20 day volatility
vol_mean = df["volume"].rolling(60, min_periods=40).mean()  # volume average over the PAST 60 days only (not the whole sample)
vol_std = df["volume"].rolling(60, min_periods=40).std()    # same for the spread
df["z_volume"] = (df["volume"] - vol_mean) / vol_std    # volume z-score without using the future
df["ret_lag1"] = df["ret"].shift(1)                     # yesterday's return as one more feature

# ---- target: what we can actually earn AFTER today's close
# we see the close, send the order, get filled at TOMORROW's open and leave at the open after that
df["fwd_ret"] = df["open"].shift(-2) / df["open"].shift(-1) - 1   # return from tomorrow's open to the open after (shift(-1) = tomorrow, shift(-2) = day after)
df["target"] = (df["fwd_ret"] > 0).astype(int)          # 1 if that trade would have made money

feats = ["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1"]    # today's return is fine as a feature now, the target is tomorrow's
data = df.dropna(subset=feats + ["fwd_ret"]).copy()     # drop rows where a feature or the target does not exist yet

# ---- walk-forward: train on the past, predict the next block, move forward
signal = pd.Series(np.nan, index=data.index)            # +1 long, -1 short, NaN = not traded (training period)
for start in range(FIRST_TRAIN, len(data), STEP):       # start of each test block
    train = data.iloc[:start - PURGE]                   # everything before the block, minus the purged rows
    test = data.iloc[start:start + STEP]                # the next quarter
    model = RandomForestClassifier(n_estimators=300, max_depth=3, min_samples_leaf=50,
                                   random_state=0)      # shallow trees and big leaves, there is very little signal to fit
    model.fit(train[feats], train["target"])            # learn from the past only
    p_up = model.predict_proba(test[feats])[:, 1]       # probability that the next trade makes money
    signal.loc[test.index] = np.where(p_up > 0.5, 1, -1)    # long if more likely up, short otherwise

# ---- strategy returns, with costs
res = data.loc[signal.notna()].copy()                   # only the days where the model had no future information
res["signal"] = signal[signal.notna()]                  # attach the long/short positions to those days
res["gross"] = res["signal"] * res["fwd_ret"]           # what the position earns from open t+1 to open t+2
turnover = res["signal"].diff().abs()                   # how much we trade: flip from long to short = 2 sides
turnover.iloc[0] = abs(res["signal"].iloc[0])           # the very first trade starts from flat
res["net"] = res["gross"] - COST * turnover             # take the costs off


def sharpe(x):                                          # yearly sharpe ratio of a series of daily returns
    # annualised sharpe, risk free rate taken as 0 to keep it simple
    return x.mean() / x.std() * np.sqrt(252)            # average / spread, times sqrt(252) to make it yearly


def boot_ci(x, n=2000, block=20, seed=0):               # bootstrap interval for the sharpe, n resamples of 20 day blocks
    # rough 95% interval for the sharpe: resample blocks of days so that clusters of volatility stay together
    rng = np.random.default_rng(seed)                   # random numbers with a fixed seed so the interval repeats
    x = x.values                                        # plain numbers instead of a pandas series
    out = []                                            # the sharpe of every resample goes in here
    for _ in range(n):                                  # repeat n times
        starts = rng.integers(0, len(x) - block, size=len(x) // block + 1)      # random block starts
        sample = np.concatenate([x[s:s + block] for s in starts])[:len(x)]      # glue the blocks together
        out.append(sharpe(pd.Series(sample)))           # sharpe of this resampled history
    return np.percentile(out, [2.5, 97.5])              # the middle 95% of those sharpes is the interval


acc = (np.sign(res["signal"]) == np.where(res["fwd_ret"] > 0, 1, -1)).mean()    # share of days the direction was right
base = max((res["fwd_ret"] > 0).mean(), (res["fwd_ret"] <= 0).mean())           # accuracy of always guessing the more common direction
lo, hi = boot_ci(res["net"])                            # lower and upper end of the bootstrap interval, after costs
print("test days:", len(res), "from", res.index[0].date(), "to", res.index[-1].date())   # how many days were really tested, and when
print("direction accuracy: %.3f  (always guessing the majority side: %.3f)" % (acc, base))   # model accuracy next to the lazy baseline
print("position changes per year: %.0f" % (turnover.sum() / (len(res) / 252)))   # how often the position flips, per year
print("Sharpe before costs: %.2f" % sharpe(res["gross"]))   # the sharpe without costs
print("Sharpe after costs:  %.2f   (95%% bootstrap interval %.2f to %.2f)" % (sharpe(res["net"]), lo, hi))   # the headline number, with its interval
print("annual cost drag: %.1f%% of capital" % (100 * (COST * turnover).sum() / (len(res) / 252)))   # what the costs take away each year
