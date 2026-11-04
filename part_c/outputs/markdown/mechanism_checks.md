# Mechanism checks (research period only)

## 1. Autocorrelation of overnight and intraday returns (Nifty)
|   lag |   overnight (gap) |   intraday |   close-to-close |   corr(gap_t, intraday_t+lag) |   corr(intraday_t, gap_t+lag) |
|------:|------------------:|-----------:|-----------------:|------------------------------:|------------------------------:|
|     1 |            -0.034 |     -0.051 |           -0.001 |                         0.057 |                         0.038 |
|     2 |             0.123 |     -0.063 |            0.001 |                         0.026 |                        -0.018 |
|     3 |             0.025 |     -0.012 |            0.005 |                        -0.014 |                         0.025 |
|     4 |            -0.036 |      0.036 |           -0.019 |                        -0.07  |                         0.003 |
|     5 |             0.153 |     -0.019 |            0.089 |                         0.02  |                         0.088 |

same-day correlation of gap and intraday: -0.029

| period     |   gap lag1 |   gap lag2 |   close-to-close lag1 |
|:-----------|-----------:|-----------:|----------------------:|
| 2012-2016  |      0.034 |      0.04  |                 0.077 |
| 2017-2021  |     -0.073 |      0.164 |                -0.055 |
| excl. 2020 |      0.021 |      0.02  |                 0.076 |

## 2. next tradable day on several lags at once (Nifty)
|        |   coef |      t |
|:-------|-------:|-------:|
| const  |  0     |  0.503 |
| gap0   |  0.217 |  3.906 |
| gap1   |  0.07  |  0.686 |
| gap2   | -0.074 | -0.64  |
| intra0 | -0.063 | -2.054 |
| intra1 | -0.05  | -0.908 |

## 3. Same trading rule, different signal (k=0.5, w=60, h=2, long/short, costs 0.05% a side)

| signal                          |   net Sharpe |   CAGR % |   trades |   time in market % |
|:--------------------------------|-------------:|---------:|---------:|-------------------:|
| overnight gap (the real rule)   |         1.25 |    20.19 |      661 |              77.7  |
| close-to-close return           |        -0.28 |    -5.54 |      756 |              78.44 |
| intraday return (open to close) |        -1.14 |   -17.91 |      801 |              78.97 |
| gap minus intraday              |         0.7  |    10.55 |      786 |              78.89 |
| overnight gap of BANK NIFTY     |         0.98 |    15.18 |      687 |              72.67 |
| pure noise (shuffled gaps)      |        -0.45 |    -7.82 |      613 |              69.03 |

## 4. Baselines (Nifty, open to open, same costs)

| baseline                                        |   net Sharpe |   CAGR % |   MaxDD % |
|:------------------------------------------------|-------------:|---------:|----------:|
| always long                                     |         0.85 |    14.4  |    -37.77 |
| long 78% of days at random (no signal)          |         0.7  |    10.49 |    -34.87 |
| long only after an up close (momentum, 1 day)   |         0.19 |     1.6  |    -30.63 |
| long only after an up gap (no threshold, 1 day) |         0.91 |    12.5  |    -18.67 |

## 5. Does the edge survive if no opening price is used for trading?

Same gap signal (k=0.5, w=60, h=2). Variant A enters at the CLOSE of the day after the signal day, variant B enters at the close of the signal day itself (not allowed by the brief, which says next open, shown only to see if the edge is about the opening print). Both trade close to close.

| variant                                                       |   net Sharpe |   CAGR % |   trades |
|:--------------------------------------------------------------|-------------:|---------:|---------:|
| A: enter close t+1, close-to-close                            |         0.39 |     4.87 |      661 |
| B: enter close t, close-to-close (not allowed, for diagnosis) |         1.17 |    18.23 |      661 |

## 6. Alpha and beta of the chosen rule against always-long Nifty (open to open)

average net exposure (long minus short): 0.37 of capital
beta to Nifty: 0.33 (t=4.6)
alpha: 14.7% per year (t=3.02)

