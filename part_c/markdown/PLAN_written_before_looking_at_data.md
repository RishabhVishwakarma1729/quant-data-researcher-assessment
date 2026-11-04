# Plan (written on 3 Nov 2026, before downloading any data)

I'm writing the rules down first so I can't quietly change them later when I see results.
This file is not edited after the research starts. If I change my mind about something, it goes in the research note as a deviation.

## 1. The split

- Research data: 1 Jan 2012 to 31 Dec 2021. I can look at this as much as I want.
- Locked out-of-sample (OOS): 1 Jan 2022 to 31 Dec 2025. Nothing gets run on it until the rules are frozen.
- The download script saves the two periods into two different folders (`data/research` and `data/locked_oos`).
  The loader that all the research code uses only knows about the research folder. Only `06_run_oos.py` is allowed to touch the locked folder.
- I will not print, plot or peek at the OOS file while building anything.

## 2. How I will count tests (multiple testing)

- Every statistical test I run in the anomaly scan goes into one table, including the ones that fail.
- I report raw p-values, Bonferroni-adjusted and Benjamini-Hochberg (FDR 5%) adjusted p-values across the whole table, not per family.
- t-stats on returns use Newey-West errors where it matters (overlapping or autocorrelated data).

## 3. How I will pick the one anomaly (Step 3)

I will pick it by rule, not by feel. It has to:

1. be about something I can actually trade (a direction or a position size), not just "returns are not normal";
2. have the smallest adjusted p-value among the tradable ones;
3. keep the same sign in both halves of the research period (2012-2016 and 2017-2021);
4. still leave something positive after 0.05% per side costs (rough check on the research data only);
5. have a story about who is on the other side of the trade.

If nothing survives 2-4, the honest answer is "no tradable anomaly found". I would still write down the least-bad rule and test it on OOS, because the brief asks for a strategy, but the verdict would say it probably doesn't work.

## 4. Strategy rules

- Signals only from data up to the close of day t. Entry at the open of day t+1. Costs 0.05% per side on every change in position.
- No leverage above 1x of capital. Parameters chosen on the research period only.
- Parameter sensitivity: every parameter moved by -20% and +20% (one at a time and also all together), on research data.
- Drawdown risk: block bootstrap of the daily strategy returns (research period) with 10,000 paths.

## 5. Freeze and OOS protocol

- When I'm done, `05_freeze_rules.py` writes `frozen_rules.json` with the final parameters and a hash of the code files that define the strategy.
- `06_run_oos.py` refuses to run if the hash doesn't match, and I run it once.
- If there turns out to be a bug after OOS has been seen, I do NOT quietly fix it and rerun. I report the original result, then the fixed result, and say clearly which is which.

## 6. What I can't un-know

I know in general terms that Indian markets rallied a lot after 2020 (everybody does). I have not looked at any actual 2022-2025 numbers from this dataset, and I'm not choosing rules based on that general memory, but I'm saying it here so it's not hidden.
