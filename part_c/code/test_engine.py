# test_engine.py
# sanity checks for the strategy code and the backtester. run with:  python test_engine.py
# i wrote these before trusting any backtest number, using research data and tiny made-up examples only

import numpy as np                                      # maths
import pandas as pd                                     # tables

from common import load_raw, clean_pair, add_returns, backtest, trades_from_bt, COST_PER_SIDE
from strategy import make_positions

# ---------------------------------------------------------------- test 1: no look-ahead in the signal
nifty, bank = load_raw("research")                      # research data only
px, _ = clean_pair(nifty, bank)
px = add_returns(px)

cut = px.index[1500]                                    # pick some date in the middle
base = make_positions(px, "n", k=1.0, w=60, h=2)        # positions using the full history

# (a) throw away everything after the cut date: positions up to the cut must not change
short = px.loc[:cut].copy()
pos_short = make_positions(short, "n", k=1.0, w=60, h=2)
same = np.allclose(base.loc[:cut].values, pos_short.values)
print("test 1a - positions identical when the future is deleted:", same)
assert same

# (b) scramble all prices AFTER the cut date: position on the cut day itself (decided at yesterday's close)
# and positions the day after (decided at the cut day's close) must still be identical
scrambled = px.copy()
future = scrambled.index > cut
rng = np.random.default_rng(0)
for c in ["n_open", "n_high", "n_low", "n_close", "b_open", "b_high", "b_low", "b_close"]:
    scrambled.loc[future, c] = scrambled.loc[future, c].values * rng.uniform(0.5, 1.5, future.sum())
scrambled = add_returns(scrambled)                       # recompute gaps etc. from the scrambled prices
pos_scr = make_positions(scrambled, "n", k=1.0, w=60, h=2)
nxt = px.index[px.index.get_loc(cut) + 1]               # the day after the cut
same = np.allclose(base.loc[:nxt].values, pos_scr.loc[:nxt].values)
print("test 1b - positions up to the day after the cut ignore scrambled future prices:", same)
assert same

# ---------------------------------------------------------------- test 2: backtest accounting on a made-up example
dates = pd.date_range("2020-01-01", periods=6, freq="B")
opens = pd.Series([100.0, 102.0, 101.0, 103.0, 104.0, 105.0], index=dates)
pos = pd.Series([0, 1, 1, -1, 0, 0], index=dates, dtype=float)   # long for 2 days, then flip short for 1 day, then flat
bt = backtest(opens, pos)

# day 1: long from open 102 to open 101 -> -0.98%, entry costs 1 side
# day 2: long from 101 to 103 -> +1.98%, no trade so no cost
# day 3: short from 103 to 104 -> -0.97%, flip from +1 to -1 = 2 sides of cost
# day 4: flat, closing the short costs 1 side
exp_gross = [0, 101 / 102 - 1, 103 / 101 - 1, -(104 / 103 - 1), 0]
exp_cost = [0, COST_PER_SIDE, 0, 2 * COST_PER_SIDE, COST_PER_SIDE]
ok_g = np.allclose(bt["gross"].values, exp_gross)
ok_c = np.allclose(bt["cost"].values, exp_cost)
print("test 2a - gross returns match hand calculation:", ok_g)
print("test 2b - costs match hand calculation (flip = 2 sides):", ok_c)
assert ok_g and ok_c

# ---------------------------------------------------------------- test 3: trades
tr = trades_from_bt(bt)
# trade 1 = long over days 1-2, trade 2 = short on day 3
exp_t1 = (101 / 102) * (103 / 101) - 1 - 2 * COST_PER_SIDE
exp_t2 = -(104 / 103 - 1) - 2 * COST_PER_SIDE
ok = len(tr) == 2 and np.allclose(tr, [exp_t1, exp_t2])
print("test 3 - trade list (2 trades, net of entry and exit costs):", ok)
assert ok

# ---------------------------------------------------------------- test 4: zero-edge sanity check on real prices
# a random position that has nothing to do with the data should earn about zero before costs and lose money after
rng = np.random.default_rng(3)
rand_pos = pd.Series(rng.choice([-1.0, 0.0, 1.0], size=len(px)), index=px.index)
bt = backtest(px["n_open"], rand_pos)
print("test 4 - random positions: gross Sharpe %.2f (should be near 0), net Sharpe %.2f (should be clearly negative)" % (
    bt["gross"].mean() / bt["gross"].std() * np.sqrt(252), bt["net"].mean() / bt["net"].std() * np.sqrt(252)))
assert bt["net"].mean() < bt["gross"].mean()

print("\nall checks passed")
