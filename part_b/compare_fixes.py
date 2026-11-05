# compare_fixes.py
# applies the suggested fixes one at a time (each step keeps the previous fixes) and prints the Sharpe after every step
# so it is easy to see how much each point was adding to the original result. research data only (2012-2021)

import os                                              # for making the output folder
import numpy as np                                      # maths
import pandas as pd                                     # tables
from sklearn.ensemble import RandomForestClassifier     # the model from the original script
from sklearn.model_selection import train_test_split    # the original random split

COST = 0.0005                                           # 0.05% per side, written as a decimal (0.05 / 100)

raw = pd.read_csv("nifty_daily.csv", parse_dates=["date"]).set_index("date").sort_index()   # the same file as before, dates as the index and sorted oldest first


def sharpe(x):                                          # yearly sharpe ratio of a series of daily returns
    # annualised sharpe, risk free = 0, NaN days (not traded) are ignored just like in the original script
    x = x.dropna()                                      # throw away the days with no return
    return x.mean() / x.std() * np.sqrt(252)            # average / spread, times sqrt(252 trading days) to make it yearly


def base_frame(clean_volume):                           # builds the feature table, with the old or the fixed volume feature
    # builds the columns used by every step. clean_volume=False reproduces the original full-sample volume z-score
    df = raw.copy()                                     # work on a copy so the raw table is never changed
    df["ret"] = df["close"].pct_change()                # today's close-to-close return
    df["ma_20"] = df["close"].rolling(20).mean()        # average close of the last 20 days
    df["dist_ma"] = (df["close"] - df["ma_20"]) / df["ma_20"]   # how far today's close is from that average, as a fraction
    df["vol_20"] = df["ret"].rolling(20).std()          # how much the returns wiggled over the last 20 days
    if clean_volume:                                    # the fixed version of the volume feature
        v = df["volume"].replace(0, np.nan)                          # zero volume = missing
        df["z_volume"] = (v - v.rolling(60, min_periods=40).mean()) / v.rolling(60, min_periods=40).std()   # past 60 days only
    else:                                               # the original version of the volume feature
        df["z_volume"] = (df["volume"] - df["volume"].mean()) / df["volume"].std()   # whole sample mean and std = uses the future
    df["ret_lag1"] = df["ret"].shift(1)                 # yesterday's return (shift(1) moves every value one row down)
    return df                                           # hand the finished table back


rows = []                                               # one line per step for the final table


def add(step, what, sh, acc=np.nan):                    # one row of the ladder: step name, what changed, Sharpe, accuracy
    # stores one step of the ladder and prints it straight away
    rows.append({"step": step, "what changed": what, "Sharpe": round(sh, 2), "accuracy": acc})   # keep it for the table at the end
    print("%-4s %-72s Sharpe %6.2f   accuracy %s" % (step, what, sh, "" if np.isnan(acc) else "%.3f" % acc))   # same line on the screen


# ---------------------------------------------------------------- step 0: the original, exactly
df = base_frame(clean_volume=False)                     # the original feature table, with the full-sample volume z-score
df["target"] = (df["ret"] > 0).astype(int)              # "is today's return positive" -> 1 or 0
d = df.dropna()                                         # drop the first rows where the rolling windows are not full yet
X, y = d[["dist_ma", "vol_20", "z_volume", "ret"]], d["target"]   # the four original features and the label
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42)   # the original random 70/30 split (shuffled)
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)    # the original forest, with a fixed seed so results repeat
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)   # 0/1 prediction turned into -1 (short) or +1 (long)
add("0", "original script (same-day target, 'ret' as a feature, random split, trade at same close)", sharpe(sig * d.loc[Xte.index, "ret"]),
    (m.predict(Xte) == yte).mean())                     # position times today's return, and the share of days the direction was right

# ---------------------------------------------------------------- step 1: take today's return out of the features
X1 = d[["dist_ma", "vol_20", "z_volume"]]               # same features but without 'ret', because the label is 'ret > 0' itself
Xtr, Xte, ytr, yte = train_test_split(X1, y, test_size=0.3, random_state=42)   # same random split as before
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)     # retrain on the smaller feature set
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)   # again -1 / +1 positions
add("1", "+ remove 'ret' from the features (target is still today's return)", sharpe(sig * d.loc[Xte.index, "ret"]), (m.predict(Xte) == yte).mean())   # still scored on today's return

# ---------------------------------------------------------------- step 2: predict TOMORROW, score on tomorrow's return
df["target"] = (df["ret"].shift(-1) > 0).astype(int)    # tomorrow's direction (shift(-1) pulls tomorrow's value up to today's row)
df["next_ret"] = df["ret"].shift(-1)                    # the profit or loss of a position taken at today's close is tomorrow's return
d = df.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1", "next_ret"])   # keep only rows where everything we need exists
f2 = ["dist_ma", "vol_20", "z_volume", "ret"]           # 'ret' is back in the features: that is fine now, the label is tomorrow's and today's return is known at the close
Xtr, Xte, ytr, yte = train_test_split(d[f2], d["target"], test_size=0.3, random_state=42)   # still the random split in this step
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)    # retrain with the new label
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)   # -1 / +1 positions
add("2", "+ predict tomorrow's direction and score the trade on tomorrow's return (random split still on)",
    sharpe(sig * d.loc[Xte.index, "next_ret"]), (m.predict(Xte) == yte).mean())   # position times TOMORROW's return this time

# ---------------------------------------------------------------- step 3: split by time instead of shuffling
cut = int(len(d) * 0.7)                                 # first 70% of the dates for training, last 30% for testing
tr, te = d.iloc[:cut - 2], d.iloc[cut:]                 # 2 days purged between them
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target"])   # train on the past block only
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)   # -1 / +1 positions on the later block
add("3", "+ chronological train/test split (no shuffling, 2 days purged)", sharpe(sig * te["next_ret"]), (m.predict(te[f2]) == te["target"]).mean())   # Sharpe and accuracy on the test block

# ---------------------------------------------------------------- step 4: volume z-score from the past only, zero volume = missing
df4 = base_frame(clean_volume=True)                     # rebuild the features with the fixed volume z-score
df4["target"] = (df4["ret"].shift(-1) > 0).astype(int)  # tomorrow's direction, as in step 2
df4["next_ret"] = df4["ret"].shift(-1)                  # tomorrow's return, as in step 2
d4 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "next_ret"])   # keep complete rows only
cut = int(len(d4) * 0.7)                                # 70% point of the dates
tr, te = d4.iloc[:cut - 2], d4.iloc[cut:]               # chronological split with a 2 day gap
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target"])   # train on the earlier block
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)   # -1 / +1 positions on the later block
add("4", "+ volume z-score uses only past 60 days, zero volume treated as missing", sharpe(sig * te["next_ret"]), (m.predict(te[f2]) == te["target"]).mean())   # score it

# ---------------------------------------------------------------- step 5: realistic execution + costs
df4["fwd_ret"] = df4["open"].shift(-2) / df4["open"].shift(-1) - 1        # buy at tomorrow's open, sell at the open after
df4["target5"] = (df4["fwd_ret"] > 0).astype(int)       # label: would that trade have made money?
d5 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "fwd_ret"])   # keep complete rows only
cut = int(len(d5) * 0.7)                                # 70% point of the dates
tr, te = d5.iloc[:cut - 2], d5.iloc[cut:]               # chronological split with a 2 day gap
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target5"])   # train on the new label
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)   # -1 / +1 positions
turn = sig.diff().abs()                                 # how much the position changed each day (long to short = 2)
turn.iloc[0] = 1                                        # the very first trade starts from flat, so it counts as 1
gross = sig * te["fwd_ret"]                             # return of each position before costs
add("5a", "+ execution at next open (still no costs)", sharpe(gross), (m.predict(te[f2]) == te["target5"]).mean())   # Sharpe before costs
add("5b", "+ 0.05% per side costs", sharpe(gross - COST * turn), (m.predict(te[f2]) == te["target5"]).mean())   # same, with the cost taken off every change

# ---------------------------------------------------------------- step 6: walk-forward + a model that is not allowed to memorise
d6 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1", "fwd_ret"])   # rows where the extra lag feature exists too
f6 = ["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1"]   # the final feature list
signal = pd.Series(np.nan, index=d6.index)              # empty signal column, filled block by block (NaN = not traded)
for start in range(750, len(d6), 63):                   # first test block after about 3 years, then a new block every 63 days (one quarter)
    tr = d6.iloc[:start - 2]                            # everything before the block, minus a 2 day gap
    te = d6.iloc[start:start + 63]                      # the next quarter, which the model has not seen
    m = RandomForestClassifier(n_estimators=300, max_depth=3, min_samples_leaf=50, random_state=0).fit(tr[f6], tr["target5"])   # shallow forest, it cannot memorise the noise
    signal.loc[te.index] = np.where(m.predict_proba(te[f6])[:, 1] > 0.5, 1, -1)   # long if the chance of up is above 50%, else short
r = d6.loc[signal.notna()].copy()                       # keep only the days that were really predicted out of sample
r["signal"] = signal[signal.notna()]                    # attach the positions to those days
turn = r["signal"].diff().abs()                         # position change each day
turn.iloc[0] = 1                                        # first trade starts from flat
gross = r["signal"] * r["fwd_ret"]                      # return before costs
acc = (np.sign(r["signal"]) == np.where(r["fwd_ret"] > 0, 1, -1)).mean()   # share of days the direction was right
add("6a", "+ walk-forward retraining every quarter, shallow forest (before costs)", sharpe(gross), acc)   # Sharpe before costs
add("6b", "  same, after 0.05% per side costs  <- the corrected script", sharpe(gross - COST * turn), acc)   # after costs: the corrected script's number

out = pd.DataFrame(rows)                                # the whole ladder as one table
out["accuracy"] = out["accuracy"].round(3)              # three decimals are enough for the accuracy
os.makedirs("outputs/markdown", exist_ok=True)      # the table is saved in outputs/markdown
with open("outputs/markdown/ladder.md", "w") as f:      # open the output file for writing
    f.write(out.to_markdown(index=False) + "\n")        # write the table as markdown
print("\nsaved outputs/markdown/ladder.md")              # tell the user where it went
