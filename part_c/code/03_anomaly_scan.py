# 03_anomaly_scan.py
# step 2: look for behaviour that a random walk would not produce
# every test i run goes into one big table (including the boring ones), then i adjust for multiple testing
# only research data (2012-2021) is used
#   python 03_anomaly_scan.py               -> the scan as submitted (Yahoo data)
#   python 03_anomaly_scan.py --nse-filled  -> side check: the same scan on research data with NSE's own bars added for the real trading days Yahoo lacks
#                                              (writes only outputs/tables/anomaly_scan_nse_filled.csv and outputs/markdown/nse_filled_side_check.md)

import os                                                   # paths
import sys                                                  # to stop after the side check
import argparse                                             # command line option
import warnings                                             # to hide some verbose statsmodels warnings
import numpy as np                                          # maths
import pandas as pd                                         # tables
import statsmodels.api as sm                                # regressions
from scipy import stats                                     # classical tests
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch   # autocorrelation and ARCH tests
from statsmodels.stats.multitest import multipletests       # bonferroni / BH
from statsmodels.sandbox.stats.runs import runstest_1samp   # runs test
from statsmodels.tsa.stattools import adfuller, coint       # unit root / cointegration
from sklearn.mixture import GaussianMixture                 # regimes (ML method 1)
from sklearn.ensemble import IsolationForest, GradientBoostingClassifier  # outliers (ML 2) + classifier (ML 3)
from sklearn.linear_model import LogisticRegression         # the simple classifier
from sklearn.preprocessing import StandardScaler            # puts features on the same scale
from sklearn.pipeline import make_pipeline                  # chains the scaler and the model
from sklearn.metrics import roc_auc_score                   # how well a classifier ranks up days above down days
import matplotlib                                           # plotting library
matplotlib.use("Agg")                                       # no pop-up windows, figures are saved to files
import matplotlib.pyplot as plt                             # the plotting commands

from common import load_raw, clean_pair, add_returns, MUHURAT_DAYS, DATA_DIR, OUT_DIR, FIG_DIR, TAB_DIR   # the shared loading and cleaning code, plus folder paths

ap = argparse.ArgumentParser()                              # reads the options typed after the script name
ap.add_argument("--nse-filled", action="store_true", help="side check on research data plus NSE's bars for the days Yahoo lacks")   # the only option
args = ap.parse_args()                                      # args.nse_filled is True if the option was given

warnings.filterwarnings("ignore")                           # statsmodels prints many routine warnings here, none of them affect the results
np.random.seed(7)                                           # fixed seed so reruns give the same numbers
os.makedirs(FIG_DIR, exist_ok=True)                         # make sure the figures folder exists
os.makedirs(TAB_DIR, exist_ok=True)                         # and the tables folder

# ---------------------------------------------------------------- data
nifty, bank = load_raw("research")                          # research period only
if args.nse_filled:                                         # side-check mode
    # side check: add NSE's own bars for the real trading days Yahoo lacks (the same days that section 7 of the data quality report lists).
    # muhurat evenings are left out, they are dropped by the cleaning anyway
    off = pd.read_csv(os.path.join(DATA_DIR, "reference", "nse_index_ohlc_2012_2021.csv"), parse_dates=["date"])   # NSE's own prices

    def with_nse(tab, lab):                                 # adds NSE's bars to a Yahoo table
        o = off[off["index"] == lab].set_index("date")      # NSE's rows for this index
        days = o.index.difference(tab.index).difference(MUHURAT_DAYS)   # days NSE has, Yahoo lacks, and that are not muhurat evenings
        add = o.loc[days, ["open", "high", "low", "close"]].copy()      # NSE's prices for those days
        add.columns = ["Open", "High", "Low", "Close"]      # name the columns the way Yahoo does
        add["Volume"] = 0.0                                     # volume is not used anywhere
        print("added %d NSE days to %s" % (len(add), lab))  # say how many days were added
        return pd.concat([tab, add]).sort_index()           # the combined table in date order

    nifty, bank = with_nse(nifty, "Nifty 50"), with_nse(bank, "Bank Nifty")   # add the days to both tables
px, _ = clean_pair(nifty, bank)                             # same cleaning as step 1
px = add_returns(px)                                        # log returns, gaps, intraday, forward returns
NAMES = {"n": "Nifty50", "b": "BankNifty"}                  # pretty names
H1_END = "2016-12-31"                                       # first half = 2012-2016, second half = 2017-2021

# ---------------------------------------------------------------- extra columns (all use only past data)
for p in ["n", "b"]:                                        # once for each index
    r = px[p + "_ret"]                                      # its daily close-to-close return
    px[p + "_up"] = (r > 0).astype(int)                     # 1 if the close was up
    # length of the current streak of up closes / down closes
    for name, flag in [("uprun", r > 0), ("dnrun", r < 0)]:   # one streak counter for up days, one for down days
        grp = (~flag).cumsum()                              # new group number every time the streak breaks
        px[p + "_" + name] = flag.astype(int).groupby(grp).cumsum()   # count 1, 2, 3 ... inside each streak
    px[p + "_vol20"] = r.rolling(20).std()                  # trailing 20 day volatility
    px[p + "_ret20"] = r.rolling(20).sum()                  # trailing 20 day return
    px[p + "_ret5"] = r.rolling(5).sum()                    # trailing 5 day return
    px[p + "_ma20gap"] = np.log(px[p + "_close"] / px[p + "_close"].rolling(20).mean())   # how far the close is from its 20 day average

# weekday of each date (0 = monday)
px["dow"] = px.index.dayofweek                              # 0 = monday ... 4 = friday
DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]             # names for the numbers above

# monthly expiry = last thursday of the month, or the trading day before if that thursday was a holiday
exp_days = []                                               # the expiry day of every month goes here
for (yr, mo), grp in px.groupby([px.index.year, px.index.month]):   # one month at a time
    month_end = grp.index.max() + pd.offsets.MonthEnd(0)   # last calendar day of the month
    cal = pd.date_range(month_end - pd.Timedelta(days=6), month_end)   # last 7 calendar days
    last_thu = cal[cal.dayofweek == 3][0]                  # the last thursday
    ok = grp.index[grp.index <= last_thu]                  # trading days up to and including it
    exp_days.append(ok.max())                              # the last trading day on or before that thursday
exp_days = pd.DatetimeIndex(exp_days)                       # as a proper list of dates
px["exp_day"] = px.index.isin(exp_days).astype(int)         # 1 on expiry days
# expiry week = monday of that week up to the expiry day
px["exp_week"] = 0                                          # start with zero everywhere
for d in exp_days:                                          # each expiry day
    wk_start = d - pd.Timedelta(days=d.dayofweek)          # monday of that week
    px.loc[(px.index >= wk_start) & (px.index <= d), "exp_week"] = 1   # mark monday up to expiry
# the first trading day after expiry
pos = px.index.get_indexer(exp_days) + 1                    # the row number after each expiry day
pos = pos[pos < len(px)]                                    # drop the ones that fall past the end of the data
px["after_exp"] = 0                                         # start with zero everywhere
px.iloc[pos, px.columns.get_loc("after_exp")] = 1           # mark the day after expiry

# turn of month = last trading day of a month + first 3 trading days of the next one
ym = px.index.to_period("M")                                # the month of every date
rank_from_start = px.groupby(ym).cumcount()                # 0 for first trading day of the month
rank_from_end = px.groupby(ym).cumcount(ascending=False)   # 0 for the last trading day of the month
px["tom"] = ((rank_from_start < 3) | (rank_from_end < 1)).astype(int)   # 1 on the first three and the last trading day

# relative performance of bank nifty vs nifty
beta = np.polyfit(px["n_ret"].dropna(), px["b_ret"].dropna(), 1)[0]   # fixed beta, only used for discovery
px["rel"] = px["b_ret"] - beta * px["n_ret"]               # daily relative return of bank nifty
px["rel5"] = px["rel"].rolling(5).sum()                    # last 5 days of relative return
px["rel_z"] = (px["rel5"] - px["rel5"].rolling(60).mean()) / px["rel5"].rolling(60).std()   # z-score, past data only
print("beta of bank nifty on nifty (research):", round(beta, 3))   # show the beta used

# ---------------------------------------------------------------- test registry
results = []                                                # every test ends up as one row here


def hac_fit(y, X, lags=5):                                  # a regression with robust standard errors
    # ols with newey-west (HAC) standard errors, used everywhere so overlapping / autocorrelated data is handled
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})   # straight-line fit with an intercept


def f_mean_diff(ycol, mask):                                # builds a "difference in means" test
    # returns a function: difference in mean of ycol when mask==1 vs mask==0, in bps per day
    def f(d):                                               # the test itself, applied to a table d
        s = d[[ycol, mask]].dropna()                        # the outcome and the 0/1 flag, complete rows only
        if s[mask].sum() < 5 or (1 - s[mask]).sum() < 5:     # not enough events, skip
            return np.nan, np.nan, np.nan                   # no result
        res = hac_fit(s[ycol], s[mask].astype(float))       # regress the outcome on the flag
        return res.params.iloc[1] * 1e4, res.tvalues.iloc[1], res.pvalues.iloc[1]   # effect in basis points, t-stat, p-value
    return f                                                # hand the test function back


def f_drift(ycol):                                          # builds a "is the average different from zero" test
    # returns a function: average of ycol in bps per day, tested against zero
    def f(d):                                               # the test itself, applied to a table d
        s = d[ycol].dropna()                                # the outcome, complete days only
        res = sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": 5})   # intercept only
        return res.params.iloc[0] * 1e4, res.tvalues.iloc[0], res.pvalues.iloc[0]   # average in basis points, t-stat, p-value
    return f                                                # hand the test function back


def f_slope(ycol, xcol):                                    # builds a "does x predict y" test
    # returns a function: effect on ycol (bps) of a 1 std move in xcol
    def f(d):                                               # the test itself, applied to a table d
        s = d[[ycol, xcol]].dropna()                        # both columns, complete rows only
        res = hac_fit(s[ycol], s[xcol])                     # regress y on x
        return res.params.iloc[1] * s[xcol].std() * 1e4, res.tvalues.iloc[1], res.pvalues.iloc[1]   # effect of a 1 std move in x, t-stat, p-value
    return f                                                # hand the test function back


def record(family, name, index, func, tradable, halves=True):   # runs one test and stores its row
    # run a test on the full research period and on both halves, store one row
    eff, t, p = func(px)                                    # the test on the whole research period
    row = {"family": family, "test": name, "index": index, "tradable": tradable,
           "effect": eff, "t_stat": t, "p_value": p}        # the basic row
    if halves:                                              # also check each half separately
        e1, t1, _ = func(px.loc[:H1_END])                   # 2012-2016
        e2, t2, _ = func(px.loc["2017-01-01":])             # 2017-2021
        row.update({"effect_h1": e1, "t_h1": t1, "effect_h2": e2, "t_h2": t2,
                    "same_sign": bool(np.sign(e1) == np.sign(e2)) if not np.isnan(e1 + e2) else False})   # add the two halves and whether they agree in sign
    results.append(row)                                     # keep the row


def record_raw(family, name, index, stat, p, note=""):      # stores a test that is not a regression
    # for tests that don't come from a regression (classical tests, ML), no half split
    results.append({"family": family, "test": name, "index": index, "tradable": False,
                    "effect": stat, "t_stat": np.nan, "p_value": p, "note": note})   # one row, never marked tradable


# ================================================================ F1 random walk / volatility tests
print("running F1 random walk tests")                       # progress message


def variance_ratio(r, q):                                   # variance ratio test for q-day returns
    # lo-mackinlay variance ratio with heteroskedasticity-robust z statistic
    r = np.asarray(r)                                       # plain numbers
    T = len(r)                                              # number of days
    mu = r.mean()                                           # average daily return
    d = r - mu                                              # returns minus their average
    var1 = (d ** 2).sum() / (T - 1)                         # one-day variance
    rq = pd.Series(r).rolling(q).sum().dropna().values      # overlapping q-day returns
    m = q * (T - q + 1) * (1 - q / T)                       # the divisor that makes the q-day variance unbiased
    varq = ((rq - q * mu) ** 2).sum() / m                   # q-day variance
    vr = varq / var1                                        # the variance ratio itself (1 = random walk)
    theta = 0.0                                             # robust variance of the estimator
    for j in range(1, q):                                   # add up the terms for each lag
        delta = (d[j:] ** 2 * d[:-j] ** 2).sum() / ((d ** 2).sum() ** 2)   # weight from squared returns j days apart
        theta += (2 * (q - j) / q) ** 2 * delta             # accumulate the robust variance
    z = (vr - 1) / np.sqrt(theta)                           # how many standard errors the ratio is from 1
    return vr, z, 2 * (1 - stats.norm.cdf(abs(z)))          # the ratio, the z-score and the two-sided p-value


for p in ["n", "b"]:                                        # once for each index
    r = px[p + "_ret"].dropna()                             # its daily returns
    nm = NAMES[p]                                           # its readable name
    lb1 = acorr_ljungbox(r, lags=[10])["lb_pvalue"].iloc[0]          # autocorrelation in returns
    record_raw("random walk", "Ljung-Box on returns (10 lags)", nm, np.nan, lb1, "linear predictability")   # store it
    lb2 = acorr_ljungbox(r ** 2, lags=[10])["lb_pvalue"].iloc[0]     # autocorrelation in squared returns
    record_raw("volatility", "Ljung-Box on squared returns (10 lags)", nm, np.nan, lb2, "vol clustering, not a direction signal")   # store it
    lm, lmp, _, _ = het_arch(r, nlags=5)                              # ARCH effects
    record_raw("volatility", "ARCH-LM (5 lags)", nm, lm, lmp, "vol clustering, not a direction signal")   # store it
    for q in [2, 5, 10]:                                    # variance ratios over 2, 5 and 10 days
        vr, z, pv = variance_ratio(r, q)                    # compute one
        record_raw("random walk", "Variance ratio q=%d" % q, nm, vr, pv, "VR>1 momentum, VR<1 mean reversion")   # store it
    z, pv = runstest_1samp((r > 0).astype(int), cutoff=0.5)           # runs test on up/down signs
    record_raw("random walk", "Runs test (up/down closes)", nm, z, pv, "streak structure")   # store it
    jb, pv = stats.jarque_bera(r)                                     # normality
    record_raw("distribution", "Jarque-Bera normality", nm, stats.kurtosis(r), pv, "effect column = excess kurtosis")   # store it

# ================================================================ F2 day of week
print("running F2 day-of-week tests")                       # progress message
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    for k, dn in enumerate(DOW_NAMES):                      # monday to friday
        px["is_" + dn] = (px["dow"] == k).astype(int)       # 1 on that weekday, 0 on the others
        record("day of week", dn + " close-to-close vs other days", nm, f_mean_diff(p + "_ret", "is_" + dn), False)   # test close-to-close returns
        record("day of week", dn + " open-to-open vs other days", nm, f_mean_diff(p + "_oo", "is_" + dn), True)      # test open-to-open returns (tradable)
    for ycol, lab, trad in [(p + "_ret", "close-to-close", False), (p + "_oo", "open-to-open", True)]:   # both kinds of return
        groups = [px.loc[px["dow"] == k, ycol].dropna() for k in range(5)]   # the returns of each weekday as five groups
        h, pv = stats.kruskal(*groups)                                 # do all 5 weekdays have the same distribution?
        record_raw("day of week", "Kruskal-Wallis across weekdays (%s)" % lab, nm, h, pv)   # store it

# ================================================================ F3 expiry and turn of month
print("running F3 expiry / turn of month tests")            # progress message
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    for mask, lab in [("exp_day", "monthly expiry day"), ("exp_week", "expiry week (Mon to expiry)"), ("after_exp", "day after expiry")]:   # three expiry flags
        record("expiry", lab + " close-to-close", nm, f_mean_diff(p + "_ret", mask), False)   # test close-to-close returns
        record("expiry", lab + " open-to-open", nm, f_mean_diff(p + "_oo", mask), True)       # test open-to-open returns (tradable)
    record("turn of month", "turn of month close-to-close", nm, f_mean_diff(p + "_ret", "tom"), False)   # turn of month, close-to-close
    record("turn of month", "turn of month open-to-open", nm, f_mean_diff(p + "_oo", "tom"), True)       # turn of month, open-to-open

# ================================================================ F4 gap behaviour
print("running F4 gap tests")                               # progress message
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    # same day: does the intraday move fade or follow the overnight gap? (not tradable, you only see the gap at the open)
    record("gaps", "same-day: intraday return on overnight gap", nm, f_slope(p + "_intra", p + "_gap"), False)
    # lagged: does yesterday's gap / intraday move predict the tradable next-day return?
    record("gaps", "yesterday's gap -> next tradable day", nm, f_slope(p + "_fwd", p + "_gap"), True)   # the test that later survives
    record("gaps", "yesterday's intraday move -> next tradable day", nm, f_slope(p + "_fwd", p + "_intra"), True)   # the same idea with the intraday move
    # big gaps: top and bottom decile of the gap
    hi, lo = px[p + "_gap"].quantile(0.9), px[p + "_gap"].quantile(0.1)   # the 90th and 10th percentile of the gap
    px["big_up_gap"] = (px[p + "_gap"] >= hi).astype(int)   # 1 on the biggest gap-up days
    px["big_dn_gap"] = (px[p + "_gap"] <= lo).astype(int)   # 1 on the biggest gap-down days
    record("gaps", "same-day: intraday after top-decile gap up", nm, f_mean_diff(p + "_intra", "big_up_gap"), False)      # what happens after a big gap up
    record("gaps", "same-day: intraday after bottom-decile gap down", nm, f_mean_diff(p + "_intra", "big_dn_gap"), False) # what happens after a big gap down
    # drift split into overnight and intraday part
    record("gaps", "average overnight (close to open) return", nm, f_drift(p + "_gap"), False)     # the average overnight move
    record("gaps", "average intraday (open to close) return", nm, f_drift(p + "_intra"), False)   # the average intraday move

# ================================================================ F5 streaks
print("running F5 streak tests")                            # progress message
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    for k in [2, 3, 4]:                                     # streaks of at least 2, 3 and 4 days
        px["up_k"] = (px[p + "_uprun"] >= k).astype(int)    # 1 after k or more up closes in a row
        px["dn_k"] = (px[p + "_dnrun"] >= k).astype(int)    # 1 after k or more down closes in a row
        record("streaks", "after %d+ up closes -> next tradable day" % k, nm, f_mean_diff(p + "_fwd", "up_k"), True)     # what follows an up streak
        record("streaks", "after %d+ down closes -> next tradable day" % k, nm, f_mean_diff(p + "_fwd", "dn_k"), True)   # what follows a down streak

# ================================================================ F6 nifty vs bank nifty
print("running F6 divergence tests")                        # progress message
spread = np.log(px["b_close"] / px["n_close"])              # log of the price ratio of the two indices
adf_p = adfuller(spread)[1]                                 # is the log price ratio stationary?
record_raw("divergence", "ADF on log(BankNifty/Nifty)", "pair", adfuller(spread)[0], adf_p, "low p = ratio mean reverts")   # store it
eg_p = coint(np.log(px["n_close"]), np.log(px["b_close"]))[1]   # do the two log prices move together long term?
record_raw("divergence", "Engle-Granger cointegration of log prices", "pair", np.nan, eg_p, "low p = cointegrated")   # store it
record("divergence", "5d relative return -> next tradable BankNifty", "BankNifty", f_slope("b_fwd", "rel5"), True)    # does a recent relative move predict Bank Nifty?
record("divergence", "5d relative return -> next tradable Nifty", "Nifty50", f_slope("n_fwd", "rel5"), True)         # and Nifty?
record("divergence", "relative z-score -> next tradable BankNifty", "BankNifty", f_slope("b_fwd", "rel_z"), True)    # the same with a z-score
# lead lag: does one index's close-to-close move predict the other's next tradable day?
record("divergence", "Nifty today -> BankNifty next tradable day", "BankNifty", f_slope("b_fwd", "n_ret"), True)    # Nifty leads Bank Nifty?
record("divergence", "BankNifty today -> Nifty next tradable day", "Nifty50", f_slope("n_fwd", "b_ret"), True)      # Bank Nifty leads Nifty?
px["rel_next"] = px["rel"].shift(-1)                        # tomorrow's relative return (close based, so not tradable at the open)
record("divergence", "daily relative return autocorrelation (lag 1)", "pair", f_slope("rel_next", "rel"), False)    # does the relative return repeat?

# ================================================================ F7 machine learning methods
print("running F7 ML tests")                                # progress message

# ---- (a) regimes with a gaussian mixture on trailing vol and trailing return
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    feat = px[[p + "_vol20", p + "_ret20"]].dropna()        # the two features, complete days only
    Z = StandardScaler().fit_transform(feat)                # scale so both features count equally
    gm = GaussianMixture(n_components=3, covariance_type="full", n_init=5, random_state=0).fit(Z)   # find three regimes
    lab = pd.Series(gm.predict(Z), index=feat.index)        # which regime each day belongs to
    # rank the regimes by their average volatility so label 2 is always "high vol"
    order = feat.groupby(lab)[p + "_vol20"].mean().sort_values().index   # regimes from calm to wild
    remap = {old: new for new, old in enumerate(order)}     # old label -> rank
    px[p + "_regime"] = lab.map(remap)                      # store the ranked regime
    px["hivol_" + p] = (px[p + "_regime"] == 2).astype(int).where(px[p + "_regime"].notna())   # 1 on high-volatility days
    record("ML regimes", "GMM high-vol regime -> next tradable day", nm, f_mean_diff(p + "_fwd", "hivol_" + p), True)   # does the regime predict tomorrow?
    share = (px[p + "_regime"] == 2).mean()                 # how often the high-vol regime occurs
    print("  %s: high-vol regime is %.1f%% of days" % (nm, 100 * share))   # show it

# ---- (b) isolation forest on one-day features of both indices
feat = px[["n_ret", "n_gap", "n_range", "b_ret", "b_gap", "b_range"]].dropna()   # six one-day features of both indices
iso = IsolationForest(n_estimators=300, contamination=0.02, random_state=0).fit(feat)   # flag the 2% most unusual days
px["iso_out"] = pd.Series((iso.predict(feat) == -1).astype(int), index=feat.index)   # 1 on a flagged day
px["iso_out"] = px["iso_out"].fillna(0)                     # days without features count as not flagged
n_out = int(px["iso_out"].sum())                            # how many days were flagged
share_2020 = px.loc[px["iso_out"] == 1].index.year.isin([2020]).mean()   # the share of flagged days that fall in 2020
print("  isolation forest flagged %d days, %.0f%% of them in 2020" % (n_out, 100 * share_2020))   # show it
record("ML outliers", "after isolation-forest outlier day -> next tradable Nifty", "Nifty50", f_mean_diff("n_fwd", "iso_out"), True)         # does a flagged day predict Nifty?
record("ML outliers", "after isolation-forest outlier day -> next tradable BankNifty", "BankNifty", f_mean_diff("b_fwd", "iso_out"), True)   # and Bank Nifty?

# ---- (c) walk-forward classifier for direction of the next tradable day
FEATS = ["ret", "gap", "intra", "range", "ret5", "ret20", "vol20", "ma20gap"]   # the features used for each index
for p in ["n", "b"]:                                        # once for each index
    nm = NAMES[p]                                           # its readable name
    X = pd.DataFrame({f: px[p + "_" + f] for f in FEATS})   # the feature table
    X["rel5"] = px["rel5"]                                  # divergence feature
    X["ret_other"] = px["b_ret"] if p == "n" else px["n_ret"]   # the other index's close to close
    X["ret_lag1"] = px[p + "_ret"].shift(1)                 # two more lags of own return
    X["ret_lag2"] = px[p + "_ret"].shift(2)                 # the second lag
    y = (px[p + "_fwd"] > 0).astype(int)                    # label: is the next tradable day positive?
    ok = X.notna().all(axis=1) & px[p + "_fwd"].notna()     # rows where everything exists
    X, y = X[ok], y[ok]                                     # keep only those rows
    for mname, make in [("logistic (L2)", lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))),
                        ("gradient boosting (depth 2)", lambda: GradientBoostingClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.7, random_state=0))]:   # two models: a simple one and a boosted one
        preds, probs, ys = [], [], []                       # collectors for each year's predictions
        for yr in range(2016, 2022):                        # retrain once a year, predict the next year
            test_idx = X.index[X.index.year == yr]          # the days of the test year
            train_idx = X.index[X.index < pd.Timestamp(str(yr) + "-01-01") - pd.Timedelta(days=7)]   # gap of a week = purge/embargo
            model = make().fit(X.loc[train_idx], y.loc[train_idx])   # train on the past only
            probs.append(pd.Series(model.predict_proba(X.loc[test_idx])[:, 1], index=test_idx))   # the predicted chance of an up day
            ys.append(y.loc[test_idx])                      # what really happened
        prob, ytrue = pd.concat(probs), pd.concat(ys)       # glue the six test years together
        pred = (prob > 0.5).astype(int)                     # predict up if the chance is above 50%
        acc = (pred == ytrue).mean()                        # share of days predicted correctly
        base = max(ytrue.mean(), 1 - ytrue.mean())          # accuracy of always guessing the majority class
        k, n_obs = int((pred == ytrue).sum()), len(ytrue)   # number of correct days and number of test days
        pv = stats.binomtest(k, n_obs, base, alternative="greater").pvalue   # is accuracy really above the baseline?
        auc = roc_auc_score(ytrue, prob)                    # how well the probabilities rank up days above down days
        record_raw("ML walk-forward", "%s direction accuracy 2016-2021" % mname, nm, acc, pv,
                   "accuracy %.3f vs majority baseline %.3f, AUC %.3f, n=%d" % (acc, base, auc, n_obs))   # store it

# ================================================================ multiple testing adjustment
tab = pd.DataFrame(results)                                 # every test as one big table
tab["p_value"] = tab["p_value"].astype(float)               # make sure the p-values are numbers
valid = tab["p_value"].notna()                              # the tests that produced a p-value
m = int(valid.sum())                                        # number of tests actually run
tab.loc[valid, "p_bonferroni"] = multipletests(tab.loc[valid, "p_value"], method="bonferroni")[1]   # strict correction: multiply by the number of tests
tab.loc[valid, "p_bh_fdr"] = multipletests(tab.loc[valid, "p_value"], method="fdr_bh")[1]           # gentler correction: controls the share of false discoveries
tab = tab.sort_values("p_value").reset_index(drop=True)     # smallest p-value first
tab.to_csv(os.path.join(TAB_DIR, "anomaly_scan_nse_filled.csv" if args.nse_filled else "anomaly_scan_all_tests.csv"), index=False)   # save every test
print("\nnumber of tests:", m)                              # show how many tests were run

# how many tests would we expect to pass at 5% just by luck?
direction = tab[tab["tradable"] & tab["p_value"].notna()]   # only the tests that could be traded
print("tradable tests:", len(direction), " with raw p<0.05:", int((direction["p_value"] < 0.05).sum()),
      " (luck alone would give about %.1f)" % (0.05 * len(direction)))   # how many pass, against what luck alone gives
print("tests with BH-adjusted p<0.05 (all):", int((tab["p_bh_fdr"] < 0.05).sum()),
      " Bonferroni<0.05:", int((tab["p_bonferroni"] < 0.05).sum()))   # how many survive each correction

pd.set_option("display.width", 250)                         # wide screen output
pd.set_option("display.max_colwidth", 70)                   # do not cut long test names
print("\n--- top 25 by raw p-value")                        # heading for the next table
cols = ["family", "test", "index", "tradable", "effect", "t_stat", "p_value", "p_bh_fdr", "p_bonferroni", "same_sign"]   # the columns to show
print(tab[cols].head(25).round(4).to_string())              # the 25 smallest p-values
print("\n--- top 15 TRADABLE tests")                        # heading for the next table
print(direction[cols].head(15).round(4).to_string())        # the 15 best tradable tests
print("\n--- ML walk-forward rows")                         # heading for the next table
print(tab.loc[tab["family"] == "ML walk-forward", ["index", "test", "effect", "p_value", "note"]].round(4).to_string())   # the machine learning results

# ================================================================ side check: compare with the scan as submitted, then stop (no figures, nothing submitted is overwritten)
if args.nse_filled:                                         # only in side-check mode
    base = pd.read_csv(os.path.join(TAB_DIR, "anomaly_scan_all_tests.csv"))     # the scan as submitted, on Yahoo data
    key = ["family", "test", "index"]                       # what identifies one test
    cmp_ = base.merge(tab, on=key, suffixes=("_sub", "_fill"))   # the two scans side by side
    assert len(cmp_) == len(base) == len(tab), "the two scans do not have the same set of tests"   # every test must match one-to-one
    n_sub = len(clean_pair(*load_raw("research"))[0])           # days in the cleaned table of the submitted scan
    rep = []                                                # the side-check report, line by line

    def out(t=""):                                          # prints a line and keeps it for the report
        print(t)                                            # show it on screen
        rep.append(t)                                       # and store it for the markdown file

    dash = lambda x: x.round(2).astype(str).replace("nan", "-")            # a dash where a test has no effect size or t-stat

    def counts(t, n_days, label):                           # summary numbers of one scan
        d = t[t["tradable"] & t["p_value"].notna()]         # its tradable tests
        return {"scan": label, "cleaned days": n_days, "tests": int(t["p_value"].notna().sum()), "tradable tests": len(d),
                "tradable with raw p<0.05": int((d["p_value"] < 0.05).sum()), "BH<0.05": int((t["p_bh_fdr"] < 0.05).sum()),
                "Bonferroni<0.05": int((t["p_bonferroni"] < 0.05).sum())}   # the counts as one table row

    out("# Side check: research results on data with NSE's own bars added")   # the report title
    out("")                                                 # blank line
    out("## 1. The 98-test scan")                          # section heading
    out("")                                                 # blank line
    out("Done after the data check against NSE (section 7 of the data quality report), as a labelled side check. It is not the study itself: "
        "the submitted scan (`outputs/tables/anomaly_scan_all_tests.csv`), the grid and every number built on them are unchanged. "
        "Here the same code, the same seeds and the same cleaning run on the Yahoo research data with the real trading days that Yahoo lacks put back from NSE's files "
        "(the days listed in section 7 of the data quality report; Muhurat evenings left out). Research period only.")   # what this side check is
    out("")                                                 # blank line
    out(pd.DataFrame([counts(base.assign(tradable=base["tradable"].astype(bool)), n_sub, "as submitted (Yahoo only)"),
                      counts(tab, len(px), "NSE days added")]).to_markdown(index=False, disable_numparse=True))   # the two scans' counts side by side
    out("")                                                 # blank line
    surv = cmp_[(cmp_["p_bh_fdr_sub"] < 0.05) | (cmp_["p_bh_fdr_fill"] < 0.05)]   # tests that survive the correction in either scan
    out("**Tests that survive the multiple-testing correction (BH 5%) in either scan:**")   # a small heading
    out("")                                                 # blank line
    show = pd.DataFrame({"family": surv["family"], "test": surv["test"], "index": surv["index"],
                         "effect sub / filled": dash(surv["effect_sub"]) + " / " + dash(surv["effect_fill"]),
                         "t sub / filled": dash(surv["t_stat_sub"]) + " / " + dash(surv["t_stat_fill"]),
                         "raw p sub / filled": surv["p_value_sub"].map("{:.5f}".format) + " / " + surv["p_value_fill"].map("{:.5f}".format),
                         "BH p sub / filled": surv["p_bh_fdr_sub"].map("{:.4f}".format) + " / " + surv["p_bh_fdr_fill"].map("{:.4f}".format),
                         "Bonferroni p sub / filled": surv["p_bonferroni_sub"].map("{:.4f}".format) + " / " + surv["p_bonferroni_fill"].map("{:.4f}".format)})   # submitted and filled numbers as text
    out(show.to_markdown(index=False, disable_numparse=True))   # the survivors as a table
    out("")                                                 # blank line
    bh_flip = cmp_[(cmp_["p_bh_fdr_sub"] < 0.05) != (cmp_["p_bh_fdr_fill"] < 0.05)]   # tests whose significance changed
    raw_flip = cmp_[(cmp_["p_value_sub"] < 0.05) != (cmp_["p_value_fill"] < 0.05)]    # tests whose raw p crossed 0.05
    out("Tests whose BH-significance changed: %d. Tests whose raw p-value crossed 0.05: %d%s." % (
        len(bh_flip), len(raw_flip),
        (" (" + "; ".join("%s, %s, %s: p %.3f to %.3f" % (r["family"], r["test"], r["index"], r["p_value_sub"], r["p_value_fill"]) for _, r in raw_flip.iterrows()) + ")") if len(raw_flip) else ""))   # how many changed, and which
    dp = (cmp_["p_value_fill"] - cmp_["p_value_sub"]).abs() # how much each raw p-value moved
    out("Largest change in a raw p-value across all %d tests: %.3f (%s, %s, %s)." % (
        len(cmp_), dp.max(), cmp_.loc[dp.idxmax(), "family"], cmp_.loc[dp.idxmax(), "test"], cmp_.loc[dp.idxmax(), "index"]))   # the biggest move
    out("")                                                 # blank line
    top = cmp_.loc[dp.sort_values(ascending=False).index[:8]]   # the eight tests that moved most
    out("The eight largest changes in raw p-value:")        # a small heading
    out("")                                                 # blank line
    out(pd.DataFrame({"family": top["family"], "test": top["test"], "index": top["index"],
                      "raw p sub": top["p_value_sub"].map("{:.4f}".format), "raw p filled": top["p_value_fill"].map("{:.4f}".format),
                      "BH p sub": top["p_bh_fdr_sub"].map("{:.3f}".format), "BH p filled": top["p_bh_fdr_fill"].map("{:.3f}".format)}).to_markdown(index=False, disable_numparse=True))   # those eight as a table
    out("")                                                 # blank line
    os.makedirs(os.path.join(OUT_DIR, "markdown"), exist_ok=True)   # make sure the report folder exists
    with open(os.path.join(OUT_DIR, "markdown", "nse_filled_side_check.md"), "w", encoding="utf-8") as f:   # open the report file
        f.write("\n".join(rep) + "\n")                      # write every collected line
    print("side check done")                                # say it is finished
    sys.exit(0)                                             # the side check ends here, nothing submitted is overwritten

# ================================================================ figures
fig, ax = plt.subplots(1, 2, figsize=(11, 4))               # two charts side by side
ax[0].hist(tab["p_value"].dropna(), bins=20, color="steelblue", edgecolor="white")   # all p-values in 20 bars
ax[0].axhline(m / 20, color="red", ls="--", label="flat line = what 'no effects' looks like")   # the flat line a no-effect world would give
ax[0].set_xlabel("raw p-value")                             # horizontal axis label
ax[0].set_ylabel("number of tests")                         # vertical axis label
ax[0].set_title("All %d tests in the scan" % m)             # chart title
ax[0].legend(fontsize=8)                                    # explain the red line
d2 = direction["p_value"].dropna()                          # p-values of the tradable tests only
ax[1].hist(d2, bins=10, color="darkorange", edgecolor="white")   # those in 10 bars
ax[1].axhline(len(d2) / 10, color="red", ls="--")           # the flat line for a no-effect world
ax[1].set_xlabel("raw p-value")                             # horizontal axis label
ax[1].set_title("Only the %d tests I could actually trade" % len(d2))   # chart title
fig.tight_layout()                                          # stop labels from overlapping
fig.savefig(os.path.join(FIG_DIR, "02_pvalue_histograms.png"), dpi=130)   # save the picture

# acf of abs returns, the clearest anomaly in the data
fig, ax = plt.subplots(figsize=(6, 3.5))                    # one small chart
for p, c in [("n", "tab:blue"), ("b", "tab:orange")]:       # one colour per index
    a = np.abs(px[p + "_ret"].dropna())                     # absolute returns (the size of each move)
    ax.plot(range(1, 41), [a.autocorr(l) for l in range(1, 41)], label=NAMES[p] + " |return|", color=c)   # their autocorrelation at lags 1 to 40
    r = px[p + "_ret"].dropna()                             # the returns themselves
    ax.plot(range(1, 41), [r.autocorr(l) for l in range(1, 41)], ls=":", color=c, label=NAMES[p] + " return")   # their autocorrelation, dotted
ax.axhline(0, color="black", lw=0.5)                        # a thin line at zero
ax.set_xlabel("lag (days)")                                 # horizontal axis label
ax.set_ylabel("autocorrelation")                            # vertical axis label
ax.set_title("Returns have none, absolute returns have lots")   # chart title
ax.legend(fontsize=7)                                       # show which line is which
fig.tight_layout()                                          # stop labels from overlapping
fig.savefig(os.path.join(FIG_DIR, "03_vol_clustering_acf.png"), dpi=130)   # save the picture

# save the enriched frame so later steps don't have to rebuild it
px.to_pickle(os.path.join(TAB_DIR, "..", "research_features.pkl"))   # later scripts read this file
print("done")                                               # tell the user it is done
