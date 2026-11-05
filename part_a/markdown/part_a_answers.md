# Part A: Statistics and ML concepts

> **1.** You test 200 different trading rules on 10 years of daily data. Eight of them show a t-statistic above 2. How many would you expect to pass by pure chance? How would you decide which, if any, are real?

**By chance**

- Imagine 200 people tossing a coin 10 times. A few will get 9 heads by chance.
- Trading rules with no real edge are similar. Their t values follow a bell curve, and about 95.5% land between -2 and +2.
- So 4.5% land outside, and half of that, about 2.3%, is above t = 2.
- Then 200 x 0.023 = 4.6, so about 4 or 5 passes (about 9 if negative t counts too).
- We got 8, close to what chance gives. So it is likely that none is real.

**How I would decide**

- Raise the bar: 200 tries almost guarantee some winners by chance. Split the 5% across 200: 0.05 / 200 = 0.00025, which needs about t = 3.5, not 2.
- Luck alone can push the best rule to t = 2.7. Over 10 years, that is 2.7 / sqrt(10) = 0.85 return-for-risk, which looks good but is chance.
- Test the best rules once on fresh, untouched data, as the old data already holds their luck.
- Keep a rule only if it works in both halves of the data and makes sense, as luck rarely repeats. If not, use a small size, or none.

> **2.** A classifier predicting next-day Nifty direction reaches 54% accuracy out of sample. Is this good or bad? What else do you need to know before deciding whether it is tradeable?

**Good or bad?**

- On its own, 54% tells us little, because Nifty rises on about 53 to 54% of days and a model that always says "up" would reach that with no skill.
- The sample matters as well. One year is about 250 days, so the standard error is about 3 points and 54% cannot be separated from 50%.
- I would want 1,000 or more out-of-sample days with a binomial test against the baseline, and confirmation that there was no leakage or tuning on the test set.

**Is it tradeable?**

- Accuracy ignores the size of the moves. A 54% hit rate on moves of about 0.8% a day gives (0.54 - 0.46) x 0.8% = 0.06% per trade, which is below a 0.10% round-trip cost.
- I would also look at average win against average loss, profit after costs, turnover, results by year, drawdown and capacity.

> **3.** Explain the difference between K-fold cross-validation and walk-forward validation. Why is standard K-fold dangerous on financial time series? What are purging and embargo?

**The difference**

- K-fold splits the data into K chunks, trains on K-1 of them, tests on the remaining one and rotates, so every row is tested once and time order is ignored.
- Walk-forward trains on an initial window, tests on the next block and then moves forward in time, so the model never sees the future, as in real trading.

**Why standard K-fold is dangerous**

- It trains on data from after the test fold.
- Labels and features also overlap in time (a 5-day forward return, a 20-day average), so training rows next to the test fold share information with it and the score is inflated.

**Purging and embargo (Lopez de Prado)**

- Purging removes the training rows whose label period overlaps the test period.
- Embargo drops a buffer of rows just after the test fold, because serial correlation still links them to the test period.
- Even with both, K-fold gives only one path through history, so walk-forward is the more realistic simulation.

> **4.** Daily stock returns are often described as “fat-tailed”. What does that mean, how would you test for it, and how does it change the way you measure risk?

**Meaning**

- Fat-tailed means extreme moves happen much more often than a normal curve suggests, so the excess kurtosis is above zero.
- For example, Nifty fell about 13% on 23 March 2020 (a 13.9% log return), which is about 13 standard deviations under a normal model.

**How I would test**

- I would use a QQ plot and the excess kurtosis (I measured 18.2 for Nifty and 12.5 for Bank Nifty over 2012-2021).
- I would add the Jarque-Bera test, which rejects normality with p near 0 on both indices, or Anderson-Darling.
- I would also use a Hill estimator for the tail index, and compare a fitted Student-t with the normal.

**Effect on risk**

- A normal VaR is too small, so I would use historical or Student-t/extreme value estimates, report expected shortfall, scale by current volatility and run stress tests such as March 2020.
- Sharpe and maximum drawdown can look better than they are in a calm sample, so leverage should be sized for the tail rather than the average day.

> **5.** A backtest shows a Sharpe ratio of 3.2 and a maximum drawdown of 6% over 4 years. List the first five things you would check before believing it.

1. **Look-ahead and leakage:** when the signal is computed and when the fill happens, and whether any normalisation was fitted on the full sample.
2. **Costs and fills:** whether the prices are tradable, and the effect of spread, slippage, market impact, turnover and capacity.
3. **How many things were tried:** the number of variants and parameters behind this result, and whether any of it is truly out of sample (deflated Sharpe).
4. **Shape of the returns:** whether it is a short-volatility or carry profile that looks smooth until a crash, whether prices are stale or marked to model, and whether a few days make most of the profit.
5. **Data and period:** four years is a single regime, so I would check bad prints, missing days, sub-period stability, parameter sensitivity and another market. A Sharpe of 3 is rare even for the best funds, so I would treat it with caution until these checks are done.

> **6.** When would you choose a simple linear or logistic model over a gradient-boosted tree or a neural network for a trading signal? Give a concrete reason, not a general one.

**When I would prefer a simple model**

- When the signal is small compared with the noise and the sample is limited, for example next-day returns from 5 to 10 features with about 2,500 daily rows, where the true R-squared is under 1%.

**Why**

- A boosted tree or network has enough capacity to fit the noise and usually does worse in walk-forward testing.
- A logistic regression with an L2 penalty fits only a smooth, roughly monotone relationship that I can sanity-check (is the momentum coefficient positive, did it change sign this year).
- It is also easier to monitor, cheaper to retrain when the regime changes, and has few parameters that can overfit.

**Evidence from Part B**

- A flexible forest on about 2,400 rows had no skill once the leakage was removed (51% accuracy against a 54% baseline).
- Trees and networks earn their place with thousands of stocks and many years of data.
