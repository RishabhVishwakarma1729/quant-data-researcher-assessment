import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("nifty_daily.csv", parse_dates=["date"]).set_index("date")
df["ret"] = df["close"].pct_change()

# Features
df["ma_20"] = df["close"].rolling(20).mean()
df["dist_ma"] = (df["close"] - df["ma_20"]) / df["ma_20"]
df["vol_20"] = df["ret"].rolling(20).std()
df["z_volume"] = (df["volume"] - df["volume"].mean()) / df["volume"].std()

# Target: is today's return positive?
df["target"] = (df["ret"] > 0).astype(int)
df = df.dropna()

X = df[["dist_ma", "vol_20", "z_volume", "ret"]]
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = RandomForestClassifier(n_estimators=500).fit(X_train, y_train)
df.loc[X_test.index, "signal"] = model.predict(X_test) * 2 - 1

# Strategy: trade at today's close using today's signal
df["strat_ret"] = df["signal"] * df["ret"]
sharpe = df["strat_ret"].mean() / df["strat_ret"].std() * np.sqrt(252)
print("Sharpe:", sharpe)
