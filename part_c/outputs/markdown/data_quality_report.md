# Data quality report (research period 2012-2021)

Source: Yahoo Finance (tickers ^NSEI and ^NSEBANK) through the yfinance package. Raw, unadjusted daily bars.
Indices have no splits or dividends so no adjustment is needed. Section 3 compares the volume with NSE's own numbers, section 6 checks the dates against NSE's holiday lists and section 7 checks the prices against NSE's own index files.

## 1. How many days do we have
|      |   weekdays |   nifty_rows |   bank_rows |   weekdays_missing_in_both |
|-----:|-----------:|-------------:|------------:|---------------------------:|
| 2012 |        261 |          242 |         245 |                         16 |
| 2013 |        261 |          247 |         248 |                         13 |
| 2014 |        261 |          240 |         242 |                         19 |
| 2015 |        261 |          244 |         246 |                         15 |
| 2016 |        261 |          244 |         246 |                         15 |
| 2017 |        260 |          248 |         248 |                         12 |
| 2018 |        261 |          245 |         246 |                         15 |
| 2019 |        261 |          241 |         242 |                         19 |
| 2020 |        262 |          250 |         250 |                         12 |
| 2021 |        261 |          248 |         248 |                         13 |

NSE had between 12 and 19 weekday trading holidays a year in this period (section 6 checks every date against the official lists).
Nearly all of the 'missing in both' days are official holidays, but not all of them: three are real trading days that Yahoo is missing in both series.

## 2. Dates in one series but not the other
Nifty-only dates: 0. Bank-Nifty-only dates: 12.

| date       | weekday   |   bank_close |   bank_volume |
|:-----------|:----------|-------------:|--------------:|
| 2012-01-02 | Monday    |       7995   |         11200 |
| 2012-05-21 | Monday    |       9412   |         18400 |
| 2012-08-28 | Tuesday   |      10059.4 |         18000 |
| 2013-01-01 | Tuesday   |      12654.2 |         14500 |
| 2014-01-01 | Wednesday |      11385.6 |         12100 |
| 2014-02-17 | Monday    |      10326.5 |         20000 |
| 2015-01-01 | Thursday  |      18750.4 |         20500 |
| 2015-04-15 | Wednesday |      18716.3 |             0 |
| 2016-01-01 | Friday    |      17039.2 |         29200 |
| 2016-08-12 | Friday    |      18963.7 |        198800 |
| 2018-01-01 | Monday    |      25318.1 |         57600 |
| 2019-01-01 | Tuesday   |      27392.4 |        116400 |

Six of these are 1 January. NSE trades on 1 January, and these Bank Nifty rows have normal looking ranges,
so my reading was that Yahoo's Nifty series is the one with holes (it also misses 2-Jan-2012 and 12-Aug-2016, both ordinary trading days).
Section 6 confirms this against NSE's official holiday lists: none of these 12 dates is an NSE holiday, so all 12 are real trading days missing from Yahoo's Nifty series.
What I did: keep only dates present in both series. The cost is that the first return after a missing day covers two sessions.

## 3. Volume
|   date |   nifty_zero_volume_days |   bank_zero_volume_days |
|-------:|-------------------------:|------------------------:|
|   2012 |                      242 |                     241 |
|   2013 |                       13 |                      61 |
|   2014 |                        0 |                      13 |
|   2015 |                        0 |                     189 |
|   2016 |                        0 |                      11 |
|   2017 |                        1 |                     244 |
|   2018 |                       13 |                     233 |
|   2019 |                        0 |                     189 |
|   2020 |                        2 |                      98 |
|   2021 |                        4 |                     136 |

**NSE has the volume that Yahoo lacks.** NSE's index files carry the volume too (data/reference/nse_volume_2012_2021.csv, built by 02d_build_nse_volume_reference.py). From 2012-02-21 on it has a number for every day, with no blank and no zero. Yahoo's zero volume is therefore missing data and not a day without trading, and NSE can fill most of it:

| index      |   days with zero volume in Yahoo |   NSE has the volume for |   no volume from either |
|:-----------|---------------------------------:|-------------------------:|------------------------:|
| Nifty 50   |                              275 |                      242 |                      33 |
| Bank Nifty |                             1415 |                     1375 |                      40 |

The days without a volume from either source are the 33 trading days from 2012-01-03 to 2012-02-17, before NSE's files begin, and 7 later Bank Nifty days that NSE's archive lacks (2014-12-15, 2015-02-02, 2015-03-12, 2015-03-13, 2015-05-19, 2015-07-08, 2015-10-16).

**What Yahoo's non-zero volume is.** It is in thousands of shares, not shares: on 2013-01-21 Yahoo has 130,900 for Nifty and NSE has 130,866,385. Against NSE's number divided by 1,000, Yahoo is within 5% on 99.1% of the Nifty days and 99.3% of the Bank Nifty days. It is not clean, though: Nifty runs about 3% below NSE in 2015, 2016, 2017 and 2018; Bank Nifty is written in raw shares on 2 days (2013-10-28, 2019-07-04); and 10 Nifty and 5 Bank Nifty days are more than 10% off. So the small non-zero numbers in 2012 are real and not unreliable (Bank Nifty on 2012-05-21: Yahoo 18,400, NSE 18,434,691 shares).

**I decided not to use volume anywhere in the study.** Price-only, so none of this changes a result. If volume were ever needed, NSE's file is the better source.

## 4. Cleaning rules and what they removed
| rule                                | series   |   rows | details                                                                                                                                        |
|:------------------------------------|:---------|-------:|:-----------------------------------------------------------------------------------------------------------------------------------------------|
| muhurat session (1 hour, holiday)   | nifty    |      3 | 2017-10-19, 2018-11-07, 2021-11-04                                                                                                             |
| rows kept after single-series rules | nifty    |   2446 | started with 2449                                                                                                                              |
| frozen bar (O=H=L=C, volume 0)      | bank     |      1 | 2016-11-10                                                                                                                                     |
| muhurat session (1 hour, holiday)   | bank     |      3 | 2017-10-19, 2018-11-07, 2021-11-04                                                                                                             |
| rows kept after single-series rules | bank     |   2457 | started with 2461                                                                                                                              |
| date only in nifty (dropped)        | nifty    |      1 | 2016-11-10                                                                                                                                     |
| date only in banknifty (dropped)    | bank     |     12 | 2012-01-02, 2012-05-21, 2012-08-28, 2013-01-01, 2014-01-01, 2014-02-17, 2015-01-01, 2015-04-15, 2016-01-01, 2016-08-12, 2018-01-01, 2019-01-01 |

Bad print: Bank Nifty on 10-Nov-2016 has open = high = low = close = 20200.25 and zero volume. It's a placeholder row.
Muhurat sessions are one hour long evening sessions on Diwali. Their open-to-close move isn't comparable to a normal day, so I dropped them.
Final clean table: 2445 rows, 2012-01-03 to 2021-12-31.

## 5. Outliers
Days where either index moved more than 5% close to close:

|            |   nifty ret % |   bank ret % |   nifty gap % |   bank gap % | what happened                            |
|:-----------|--------------:|-------------:|--------------:|-------------:|:-----------------------------------------|
| 2013-08-16 |         -4.17 |        -5.91 |         -0.64 |        -1.39 | rupee sell-off, 2013                     |
| 2013-08-27 |         -3.51 |        -5.52 |         -0.92 |        -1.78 | rupee sell-off, 2013                     |
| 2013-09-03 |         -3.84 |        -5.34 |          0.43 |         0.89 | rupee sell-off, 2013                     |
| 2013-09-05 |          2.62 |         9.04 |          1.92 |         4.51 | RBI governor change (Rajan), banks rally |
| 2013-09-19 |          3.6  |         6.49 |          2.42 |         5.01 | not labelled                             |
| 2014-03-07 |          1.94 |         5.24 |          0.2  |         0.7  | not labelled                             |
| 2014-05-09 |          2.94 |         5.33 |         -0.09 |        -0.11 | not labelled                             |
| 2015-08-24 |         -6.1  |        -7.15 |         -2.98 |        -3.44 | global sell-off (China), 'Black Monday'  |
| 2019-09-20 |          5.18 |         7.98 |          0.39 |         0.45 | corporate tax cut announced              |
| 2019-09-23 |          2.85 |         5.32 |          2.35 |         3.59 | not labelled                             |
| 2020-03-09 |         -5.02 |        -4.94 |         -2.28 |        -2.81 | covid crash / lockdown period            |
| 2020-03-12 |         -8.67 |        -9.98 |         -4.08 |        -5.08 | covid crash / lockdown period            |
| 2020-03-16 |         -7.92 |        -8.56 |         -3.76 |        -4.49 | covid crash / lockdown period            |
| 2020-03-18 |         -5.72 |        -7.37 |          1.34 |         1.15 | covid crash / lockdown period            |
| 2020-03-20 |          5.67 |         1.16 |          0.25 |        -0.93 | covid crash / lockdown period            |
| 2020-03-23 |        -13.9  |       -18.31 |         -9.59 |       -10.4  | covid crash / lockdown period            |
| 2020-03-25 |          6.41 |         7.72 |         -0.85 |        -2.05 | covid crash / lockdown period            |
| 2020-03-26 |          3.82 |         5.95 |          1.59 |         1.61 | covid crash / lockdown period            |
| 2020-03-30 |         -4.48 |        -6.13 |         -3.22 |        -3.64 | covid crash / lockdown period            |
| 2020-04-01 |         -4.08 |        -5.01 |         -0.16 |        -0.11 | covid crash / lockdown period            |
| 2020-04-03 |         -2.08 |        -5.41 |          1.24 |         0.64 | covid crash / lockdown period            |
| 2020-04-07 |          8.4  |        10    |          4.39 |         6.75 | covid crash / lockdown period            |
| 2020-04-17 |          3    |         6.4  |          3.61 |         5    | covid crash / lockdown period            |
| 2020-04-21 |         -3.07 |        -5.58 |         -2.68 |        -3.52 | covid crash / lockdown period            |
| 2020-05-04 |         -5.92 |        -8.68 |         -3.37 |        -4.85 | covid crash / lockdown period            |
| 2020-05-18 |         -3.49 |        -6.93 |          0.23 |        -0.21 | covid crash / lockdown period            |
| 2020-05-27 |          3.12 |         7.03 |          0.59 |         0.93 | covid crash / lockdown period            |
| 2021-02-01 |          4.63 |         7.93 |          0.91 |         1.34 | union budget day                         |
| 2021-04-12 |         -3.6  |        -5.24 |         -1.29 |        -2.53 | second covid wave in India               |

On every one of these days Nifty and Bank Nifty moved in the same direction, which is what a real market event looks like
and not what a bad print looks like. I can name the cause for some of the days (see last column) but not all of them.
**I did not remove or winsorise them.** Removing the crash days would make risk look much smaller than it really is,
and fat tails are one of the things the brief asks about. Where an outlier could drive a test, I show the result with and without 2020.

Nifty closed at exactly the same level as the previous day on 3 days (2014-05-14, 2016-10-27, 2017-03-31).
Their ranges and volumes look normal. With a 0.05 tick and daily moves of ~60 points I'd expect about one such coincidence in 10 years,
so three is a bit high but not alarming. I left them in (they are real bars, just with an unchanged close).

## 6. Check against NSE's official holiday lists

The file data/reference/nse_trading_holidays_2012_2021.csv has every weekday trading holiday of 2012-2021 with its source on each row.
2012, 2015 and 2016 come from NSE's own website (archived pages), 2017-2021 from NSE's yearly circulars, and 2013 and 2014 from Zerodha's copy of the exchange list
(NSE's archived pages for those two years load their tables with scripts, so I could not read them). Closures announced later are included with a note:
the Muharram move in 2013, the two 2014 and two 2019 election days, and 11-Nov-2015 (Diwali, Muhurat session only). Section 7 checks the lists again, 2013 and 2014 included, against NSE's own index files.

|   year |   official weekday holidays |   expected sessions |   nifty rows |   bank rows |   open days missing from Nifty |   open days missing from Bank Nifty |   rows on official holidays |
|-------:|----------------------------:|--------------------:|-------------:|------------:|-------------------------------:|------------------------------------:|----------------------------:|
|   2012 |                          15 |                 246 |          242 |         245 |                              4 |                                   1 |                           0 |
|   2013 |                          13 |                 248 |          247 |         248 |                              1 |                                   0 |                           0 |
|   2014 |                          19 |                 242 |          240 |         242 |                              2 |                                   0 |                           0 |
|   2015 |                          15 |                 246 |          244 |         246 |                              2 |                                   0 |                           0 |
|   2016 |                          15 |                 246 |          244 |         246 |                              2 |                                   0 |                           0 |
|   2017 |                          13 |                 247 |          248 |         248 |                              0 |                                   0 |                           1 |
|   2018 |                          16 |                 245 |          245 |         246 |                              1 |                                   0 |                           1 |
|   2019 |                          17 |                 244 |          241 |         242 |                              3 |                                   2 |                           0 |
|   2020 |                          12 |                 250 |          250 |         250 |                              0 |                                   0 |                           0 |
|   2021 |                          14 |                 247 |          248 |         248 |                              0 |                                   0 |                           1 |

**Open days missing from Nifty only (12):** 2012-01-02, 2012-05-21, 2012-08-28, 2013-01-01, 2014-01-01, 2014-02-17, 2015-01-01, 2015-04-15, 2016-01-01, 2016-08-12, 2018-01-01, 2019-01-01.
These are exactly the 12 dates found in section 2. None is an NSE holiday, so Yahoo's Nifty series is missing 12 real trading days and Bank Nifty has them.

**Open days missing from both series (3):** 2012-10-26, 2019-02-13, 2019-03-29.
The exchange was open on all three (news reports give the Nifty close as 5,664.30 on 26-Oct-2012, 10,793.65 on 13-Feb-2019 and 11,623.90 on 29-Mar-2019),
so these are gaps in Yahoo's data and not holidays. My earlier reading of every 'missing in both' day as a holiday was wrong for these three.

**Rows dated on an official holiday (3):** 2017-10-19, 2018-11-07, 2021-11-04.
All of these are Diwali Laxmi Pujan days with an evening Muhurat session, which section 4 already drops.

Of the 149 weekdays missing from both series, 146 are official holidays and 3 are real trading days (listed above).

Also worth noting:
- In 2013 the exchanges moved the Muharram holiday from 14 Nov to 15 Nov (announced on 13 Nov 2013). Yahoo has 14 Nov and not 15 Nov, which matches the revised list.
- I also tried two python calendar libraries (exchange_calendars and holidays). They disagree with each other on 6 dates and both still have the old 2013 Muharram date, so I used the official lists.
- This section covers the research period only. The locked 2022-2025 dates were compared with NSE's calendar after the out-of-sample run (post_hoc_locked_data_check.pdf).

## 7. Check against NSE's own index files

NSE puts one file per trading day on its archive site with the open, high, low and close of all its indices (nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv).
The file data/reference/nse_index_ohlc_2012_2021.csv has the Nifty 50 and Bank Nifty rows of those files (built by 02c_build_nse_index_reference.py, the saved files are in data/reference/sources/nse_index_files/).
Yahoo stays the data source of the study; this section is a check on it and not a replacement.

| index      |   Yahoo bars |   compared with NSE |   open identical |   high identical |   low identical |   close identical |
|:-----------|-------------:|--------------------:|-----------------:|-----------------:|----------------:|------------------:|
| Nifty 50   |         2449 |                2404 |             2404 |             2402 |            2402 |              2404 |
| Bank Nifty |         2461 |                2415 |             2414 |             2414 |            2413 |              2414 |

**What could not be checked.** NSE's files start on 2012-02-21, so 33 Nifty bars before that date have no official file to compare with. NSE's archive also lacks 12 later days on which Yahoo has a bar: 2013-10-09, 2014-03-19, 2014-12-15, 2015-02-02, 2015-03-12, 2015-03-13, 2015-05-19, 2015-07-08, 2015-09-04, 2015-10-16, 2015-12-01, 2016-06-20. These bars stay unchecked. The locked 2022-2025 period is covered separately, after the out-of-sample run, in post_hoc_locked_data_check.pdf.

**Result.** The Nifty open and close are identical to NSE's on all 2404 compared days. The open is the price the strategy trades at, so this is the number that matters most. Bank Nifty differs on 1 of 2415 opens and 1 of 2415 closes.

Every price that differs (9 in all):

| index      | date       | price   | Yahoo     | NSE       | in the study?       |
|:-----------|:-----------|:--------|:----------|:----------|:--------------------|
| Nifty 50   | 2012-05-31 | High    | 4,924.25  | 4,949.25  | kept                |
| Nifty 50   | 2015-03-30 | High    | 8,492.30  | 8,504.55  | kept                |
| Nifty 50   | 2012-05-31 | Low     | 4,894.45  | 4,883.55  | kept                |
| Nifty 50   | 2021-02-24 | Low     | 14,504.50 | 14,723.05 | kept                |
| Bank Nifty | 2016-11-10 | Open    | 20,200.25 | 19,827.50 | removed by cleaning |
| Bank Nifty | 2016-11-10 | High    | 20,200.25 | 20,283.15 | removed by cleaning |
| Bank Nifty | 2016-11-10 | Low     | 20,200.25 | 19,787.45 | removed by cleaning |
| Bank Nifty | 2018-11-07 | Low     | 25,747.60 | 25,698.10 | removed by cleaning |
| Bank Nifty | 2018-11-07 | Close   | 25,769.70 | 25,737.50 | removed by cleaning |

The Bank Nifty bar of 10-Nov-2016 is the placeholder from section 4 (Yahoo has 20,200.25 in all four prices), and 7-Nov-2018 is a Diwali Muhurat session; the cleaning rules remove both. The rows marked 'kept' differ only in highs and lows. The strategy trades on opens and closes, so none of them touches a signal or a return. I did not try to find out which source has the right high or low.

**The holiday lists, checked the other way round.** NSE only publishes a file for a day it traded. From 2012-02-21 on, 147 holidays of my list fall inside NSE's coverage and only 6 of them have a file, all Diwali Muhurat evenings (2012-11-13, 2014-10-23, 2015-11-11, 2017-10-19, 2018-11-07, 2021-11-04). Every other weekday without an NSE file is on the holiday list, except 12 days (2013-10-09, 2014-03-19, 2014-12-15, 2015-02-02, 2015-03-12, 2015-03-13, 2015-05-19, 2015-07-08, 2015-09-04, 2015-10-16, 2015-12-01, 2016-06-20); Yahoo has a bar for both indices on 12 of them, so they look like holes in NSE's archive and not closures. No holiday on my list is contradicted, including the 2013 and 2014 ones that came from a broker's copy. The Muharram move of 2013 shows too: NSE has a file for 2013-11-14 and none for 2013-11-15.

**Days NSE has and Yahoo lacks.** NSE's files contain 14 of the real trading days that Yahoo's Nifty lacks (2012-05-21, 2012-08-28, 2012-10-26, 2013-01-01, 2014-01-01, 2014-02-17, 2015-01-01, 2015-04-15, 2016-01-01, 2016-08-12, 2018-01-01, 2019-01-01, 2019-02-13, 2019-03-29) and the 3 that Bank Nifty lacks. The three days missing from both series (section 6) are among them, and NSE's own Nifty closes for them are 5,664.30, 10,793.65, 11,623.90, equal to the news figures quoted in section 6. One of the 12 Nifty-only dates from section 6, 2012-01-02, is before NSE's files begin, so it stays missing.

**Does it matter?** I put those days back and reran the frozen rule on the research period (Nifty, threshold 0.5, 60-day window, hold 2 days, 0.05% per side):

| data                         |   days |   net Sharpe |   gross Sharpe |   CAGR % |   max drawdown % |   trades |
|:-----------------------------|-------:|-------------:|---------------:|---------:|-----------------:|---------:|
| Yahoo only (as in the study) |   2445 |        1.246 |          1.678 |    20.19 |           -16.74 |      661 |
| Yahoo plus the NSE days      |   2459 |        1.227 |          1.66  |    19.77 |           -15.62 |      663 |

The result moves by 0.02 of Sharpe, so the missing days do not carry the finding. I kept the Yahoo-only series in the study on purpose: the frozen rules and the locked 2022-2025 file are built on it, and mixing two sources across the research and out-of-sample periods would be worse than losing 14 days. This table is only a side check; every other number in the study stays as it was. I also reran the 98-test scan, the grid and the reality check on the filled data (nse_filled_side_check.pdf): the same tests survive the correction and the same rule is chosen.

## 8. Known limitations
- Saturday special sessions (budget days 28-Feb-2015 and 1-Feb-2020) are not in the Yahoo data, so their moves sit inside the following Monday's return.
- Open prices are the index value at 9:15. They can't be traded exactly (index futures or ETFs open slightly differently), which is one reason for costs.
- The first return after a holiday covers more than one calendar day. I don't scale it; vol is slightly overstated on Mondays and post-holiday days.

