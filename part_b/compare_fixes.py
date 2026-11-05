# compare_fixes.py
# applies the suggested fixes one at a time (each step keeps the previous fixes) and prints the Sharpe after every step
# so it is easy to see how much each point was adding to the original result. research data only (2012-2021)

import os                                              # for making the output folder
import numpy as np                                      # maths
import pandas as pd                                     # tables
from sklearn.ensemble import RandomForestClassifier     # the model from the original script
from sklearn.model_selection import train_test_split    # the original random split

COST = 0.0005                                           # 0.05% per side

raw = pd.read_csv("nifty_daily.csv", parse_dates=["date"]).set_index("date").sort_index()   # the same file as before


def sharpe(x):
    # annualised sharpe, risk free = 0, NaN days (not traded) are ignored just like in the original script
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(252)


def base_frame(clean_volume):
    # builds the columns used by every step. clean_volume=False reproduces the original full-sample volume z-score
    df = raw.copy()
    df["ret"] = df["close"].pct_change()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["dist_ma"] = (df["close"] - df["ma_20"]) / df["ma_20"]
    df["vol_20"] = df["ret"].rolling(20).std()
    if clean_volume:
        v = df["volume"].replace(0, np.nan)                          # zero volume = missing
        df["z_volume"] = (v - v.rolling(60, min_periods=40).mean()) / v.rolling(60, min_periods=40).std()   # past 60 days only
    else:
        df["z_volume"] = (df["volume"] - df["volume"].mean()) / df["volume"].std()   # whole sample mean and std = uses the future
    df["ret_lag1"] = df["ret"].shift(1)
    return df


rows = []                                               # one line per step for the final table


def add(step, what, sh, acc=np.nan):
    rows.append({"step": step, "what changed": what, "Sharpe": round(sh, 2), "accuracy": acc})
    print("%-4s %-72s Sharpe %6.2f   accuracy %s" % (step, what, sh, "" if np.isnan(acc) else "%.3f" % acc))


# ---------------------------------------------------------------- step 0: the original, exactly
df = base_frame(clean_volume=False)
df["target"] = (df["ret"] > 0).astype(int)              # "is today's return positive"
d = df.dropna()
X, y = d[["dist_ma", "vol_20", "z_volume", "ret"]], d["target"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42)
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)
add("0", "original script (same-day target, 'ret' as a feature, random split, trade at same close)", sharpe(sig * d.loc[Xte.index, "ret"]),
    (m.predict(Xte) == yte).mean())

# ---------------------------------------------------------------- step 1: take today's return out of the features
X1 = d[["dist_ma", "vol_20", "z_volume"]]
Xtr, Xte, ytr, yte = train_test_split(X1, y, test_size=0.3, random_state=42)
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)
add("1", "+ remove 'ret' from the features (target is still today's return)", sharpe(sig * d.loc[Xte.index, "ret"]), (m.predict(Xte) == yte).mean())

# ---------------------------------------------------------------- step 2: predict TOMORROW, score on tomorrow's return
df["target"] = (df["ret"].shift(-1) > 0).astype(int)    # tomorrow's direction
df["next_ret"] = df["ret"].shift(-1)                    # the profit or loss of a position taken at today's close is tomorrow's return
d = df.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1", "next_ret"])
f2 = ["dist_ma", "vol_20", "z_volume", "ret"]
Xtr, Xte, ytr, yte = train_test_split(d[f2], d["target"], test_size=0.3, random_state=42)
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(Xtr, ytr)
sig = pd.Series(m.predict(Xte) * 2 - 1, index=Xte.index)
add("2", "+ predict tomorrow's direction and score the trade on tomorrow's return (random split still on)",
    sharpe(sig * d.loc[Xte.index, "next_ret"]), (m.predict(Xte) == yte).mean())

# ---------------------------------------------------------------- step 3: split by time instead of shuffling
cut = int(len(d) * 0.7)                                 # first 70% of the dates for training, last 30% for testing
tr, te = d.iloc[:cut - 2], d.iloc[cut:]                 # 2 days purged between them
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target"])
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)
add("3", "+ chronological train/test split (no shuffling, 2 days purged)", sharpe(sig * te["next_ret"]), (m.predict(te[f2]) == te["target"]).mean())

# ---------------------------------------------------------------- step 4: volume z-score from the past only, zero volume = missing
df4 = base_frame(clean_volume=True)
df4["target"] = (df4["ret"].shift(-1) > 0).astype(int)
df4["next_ret"] = df4["ret"].shift(-1)
d4 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "next_ret"])
cut = int(len(d4) * 0.7)
tr, te = d4.iloc[:cut - 2], d4.iloc[cut:]
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target"])
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)
add("4", "+ volume z-score uses only past 60 days, zero volume treated as missing", sharpe(sig * te["next_ret"]), (m.predict(te[f2]) == te["target"]).mean())

# ---------------------------------------------------------------- step 5: realistic execution + costs
df4["fwd_ret"] = df4["open"].shift(-2) / df4["open"].shift(-1) - 1        # buy at tomorrow's open, sell at the open after
df4["target5"] = (df4["fwd_ret"] > 0).astype(int)
d5 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "fwd_ret"])
cut = int(len(d5) * 0.7)
tr, te = d5.iloc[:cut - 2], d5.iloc[cut:]
m = RandomForestClassifier(n_estimators=500, random_state=0).fit(tr[f2], tr["target5"])
sig = pd.Series(m.predict(te[f2]) * 2 - 1, index=te.index)
turn = sig.diff().abs()
turn.iloc[0] = 1
gross = sig * te["fwd_ret"]
add("5a", "+ execution at next open (still no costs)", sharpe(gross), (m.predict(te[f2]) == te["target5"]).mean())
add("5b", "+ 0.05% per side costs", sharpe(gross - COST * turn), (m.predict(te[f2]) == te["target5"]).mean())

# ---------------------------------------------------------------- step 6: walk-forward + a model that is not allowed to memorise
d6 = df4.dropna(subset=["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1", "fwd_ret"])
f6 = ["dist_ma", "vol_20", "z_volume", "ret", "ret_lag1"]
signal = pd.Series(np.nan, index=d6.index)
for start in range(750, len(d6), 63):
    tr = d6.iloc[:start - 2]
    te = d6.iloc[start:start + 63]
    m = RandomForestClassifier(n_estimators=300, max_depth=3, min_samples_leaf=50, random_state=0).fit(tr[f6], tr["target5"])
    signal.loc[te.index] = np.where(m.predict_proba(te[f6])[:, 1] > 0.5, 1, -1)
r = d6.loc[signal.notna()].copy()
r["signal"] = signal[signal.notna()]
turn = r["signal"].diff().abs()
turn.iloc[0] = 1
gross = r["signal"] * r["fwd_ret"]
acc = (np.sign(r["signal"]) == np.where(r["fwd_ret"] > 0, 1, -1)).mean()
add("6a", "+ walk-forward retraining every quarter, shallow forest (before costs)", sharpe(gross), acc)
add("6b", "  same, after 0.05% per side costs  <- the corrected script", sharpe(gross - COST * turn), acc)

out = pd.DataFrame(rows)
out["accuracy"] = out["accuracy"].round(3)
os.makedirs("outputs/markdown", exist_ok=True)      # the table is saved in outputs/markdown
with open("outputs/markdown/ladder.md", "w") as f:
    f.write(out.to_markdown(index=False) + "\n")
print("\nsaved outputs/markdown/ladder.md")
