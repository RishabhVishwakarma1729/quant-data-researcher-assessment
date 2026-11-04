# strategy.py
# the trading rule, written once so research and the final out-of-sample run use exactly the same code
# (05_freeze_rules.py hashes this file, so if it changes after the freeze the oos script refuses to run)

import numpy as np                                      # maths
import pandas as pd                                     # tables


def gap_signal(px, p, k, w):
    # signal computed at the CLOSE of day t, using only data up to and including day t
    # p = "n" (nifty) or "b" (bank nifty), k = threshold in std units, w = window for the gap std
    gap = px[p + "_gap"]                                # overnight move: yesterday's close -> today's open
    sigma = gap.rolling(w).std().shift(1)               # std of the previous w gaps (not including today's)
    z = gap / sigma                                     # today's gap measured in "normal gap sizes"
    sig = np.sign(z) * (z.abs() >= k)                   # +1 after a big gap up, -1 after a big gap down, else 0
    return sig.fillna(0.0)                              # early days without enough history stay flat


def make_positions(px, p, k, w, h, side="both"):
    # turns the signal into the position held from each day's OPEN
    # h = how many days to hold after a signal, side = "both" (long and short) or "long" (long only)
    sig = gap_signal(px, p, k, w)
    # a signal stays alive for h days: fill the next h-1 zero days with the last non-zero signal
    held = sig.replace(0, np.nan)                       # zeros become blanks so ffill can carry signals forward
    if h > 1:                                           # (ffill refuses limit=0, and h=1 needs no carrying anyway)
        held = held.ffill(limit=h - 1)
    held = held.fillna(0.0)                             # blanks left over = flat
    if side == "long":
        held = held.clip(lower=0.0)                     # throw away the short signals
    # decided at the close of day t, so we are in the trade from the open of day t+1
    return held.shift(1).fillna(0.0)
