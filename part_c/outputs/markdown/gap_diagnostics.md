# Gap diagnostics (research period only)

## Nifty50
| outcome                                  |   effect bps per 1sd gap |   t-stat |    n |
|:-----------------------------------------|-------------------------:|---------:|-----:|
| next tradable day (open t+1 to open t+2) |                    12.84 |     3.91 | 2442 |
| part 1: intraday of day t+1              |                     5.15 |     1.87 | 2443 |
| part 2: overnight into t+2               |                     7.68 |     2.34 | 2442 |

Excluding 2020: effect 8.71 bps per 1sd, t=3.34 (n=2192)
Winsorised at 1%/99%: effect 10.97 bps per 1sd, t=3.98
Spearman rank correlation gap(t) vs next tradable day: 0.100 (p=0.0000)

By gap quintile:
| n_gap             |   mean next tradable day (bps) |   days |
|:------------------|-------------------------------:|-------:|
| Q1 (big down gap) |                           -6.4 |    489 |
| Q2                |                           -1.1 |    488 |
| Q3                |                            0.2 |    487 |
| Q4                |                            8   |    489 |
| Q5 (big up gap)   |                           25.6 |    489 |

By calendar year:
|   year |   effect bps per 1sd gap |     t |
|-------:|-------------------------:|------:|
|   2012 |                     10.8 |  1.16 |
|   2013 |                     15.4 |  1.4  |
|   2014 |                      4.2 |  0.9  |
|   2015 |                     13.5 |  2.33 |
|   2016 |                     12.5 |  2.15 |
|   2017 |                      0.1 |  0.03 |
|   2018 |                     -3.1 | -0.38 |
|   2019 |                      4.3 |  0.83 |
|   2020 |                     31.4 |  2.56 |
|   2021 |                     14.8 |  2.14 |
positive in 9 of 10 years

## BankNifty
| outcome                                  |   effect bps per 1sd gap |   t-stat |    n |
|:-----------------------------------------|-------------------------:|---------:|-----:|
| next tradable day (open t+1 to open t+2) |                    18.9  |     3.05 | 2442 |
| part 1: intraday of day t+1              |                    10.86 |     2.58 | 2443 |
| part 2: overnight into t+2               |                     8.02 |     2.11 | 2442 |

Excluding 2020: effect 9.53 bps per 1sd, t=2.26 (n=2192)
Winsorised at 1%/99%: effect 15.29 bps per 1sd, t=3.79
Spearman rank correlation gap(t) vs next tradable day: 0.085 (p=0.0000)

By gap quintile:
| b_gap             |   mean next tradable day (bps) |   days |
|:------------------|-------------------------------:|-------:|
| Q1 (big down gap) |                          -12   |    489 |
| Q2                |                            2.9 |    488 |
| Q3                |                            0.8 |    487 |
| Q4                |                           10.1 |    489 |
| Q5 (big up gap)   |                           27.4 |    489 |

By calendar year:
|   year |   effect bps per 1sd gap |     t |
|-------:|-------------------------:|------:|
|   2012 |                     14.6 |  1.21 |
|   2013 |                     15   |  0.7  |
|   2014 |                      2   |  0.26 |
|   2015 |                     22.2 |  2.8  |
|   2016 |                     14.6 |  1.95 |
|   2017 |                     -1.3 | -0.24 |
|   2018 |                     -5.2 | -0.51 |
|   2019 |                      1.4 |  0.17 |
|   2020 |                     58.6 |  2.52 |
|   2021 |                     10.7 |  1.23 |
positive in 8 of 10 years

## Which piece of yesterday predicts tomorrow? (Nifty, joint regression)
n_fwd on gap and intraday together:
|         |   coef |      t |
|:--------|-------:|-------:|
| const   |  0     |  0.978 |
| n_gap   |  0.203 |  3.812 |
| n_intra | -0.059 | -2.038 |

