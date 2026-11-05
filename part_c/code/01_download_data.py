# 01_download_data.py
# pulls nifty 50 and bank nifty daily data from yahoo finance (free, no key needed)
# the two periods are downloaded separately and saved in separate folders,
# so the 2022-2025 locked set never gets mixed in with the research data

import os                       # for paths and making folders
import datetime as dt           # to stamp the log file
import pandas as pd             # tables
import yfinance as yf           # yahoo downloader

# folder where this script lives, everything else is relative to it
HERE = os.path.dirname(os.path.abspath(__file__))                   # full path of the folder this file is in
# data folders one level up
RESEARCH_DIR = os.path.join(HERE, "..", "data", "research")         # the 2012-2021 files go here
LOCKED_DIR = os.path.join(HERE, "..", "data", "locked_oos")         # the 2022-2025 files go here, kept apart on purpose

# yahoo tickers for the two indices, and the short names i use in file names
TICKERS = {"^NSEI": "nifty50", "^NSEBANK": "banknifty"}             # yahoo's name -> my file name

# yahoo's "end" date is exclusive, so these give 2012-01-01..2021-12-31 and 2022-01-01..2025-12-31
RESEARCH_START, RESEARCH_END = "2012-01-01", "2022-01-01"           # the research period
LOCKED_START, LOCKED_END = "2022-01-01", "2026-01-01"               # the locked out-of-sample period


def grab(ticker, start, end):                                       # downloads one index for one period
    # download raw (not adjusted) daily bars, indices have no splits/dividends anyway
    df = yf.download(ticker, start=start, end=end, interval="1d",
                     auto_adjust=False, progress=False)             # one row per trading day, no progress bar
    # newer yfinance versions return two-level columns, flatten them to just the field name
    if isinstance(df.columns, pd.MultiIndex):                       # only needed for the newer yfinance format
        df.columns = df.columns.get_level_values(0)                 # keep "Open", "High" ... and drop the ticker level
    # keep only the columns i care about, in a fixed order
    df = df[["Open", "High", "Low", "Close", "Volume"]]             # the five fields, always in this order
    # make the index a plain date (no timezone) and give it a name
    df.index = pd.to_datetime(df.index).tz_localize(None)           # dates without a timezone
    df.index.name = "date"                                          # the first column of the csv will be called "date"
    return df                                                       # hand the table back


def main():                                                         # the whole download, step by step
    # make sure the folders exist
    os.makedirs(RESEARCH_DIR, exist_ok=True)                        # create the research folder if it is missing
    os.makedirs(LOCKED_DIR, exist_ok=True)                          # same for the locked folder

    # lines for the log file, i'll write them at the end
    log = ["download run at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "source: yahoo finance via the yfinance python package"]   # when and where the data came from

    for ticker, name in TICKERS.items():                            # once for Nifty 50, once for Bank Nifty
        # ---- research period: fine to look at ----
        res = grab(ticker, RESEARCH_START, RESEARCH_END)            # download 2012-2021
        res.to_csv(os.path.join(RESEARCH_DIR, name + "_research.csv"))   # save it in the research folder
        # it is ok to print this one
        line = "%s research: %d rows, %s to %s" % (name, len(res), res.index.min().date(), res.index.max().date())   # a short summary line
        print(line)                                                 # show it on screen
        log.append(line)                                            # and keep it for the log file

        # ---- locked period: save it and do NOT look at it ----
        locked = grab(ticker, LOCKED_START, LOCKED_END)             # download 2022-2025
        # only check that something came back, nothing else about it gets printed
        assert len(locked) > 0, "locked download came back empty for " + ticker   # stop if the download failed
        locked.to_csv(os.path.join(LOCKED_DIR, name + "_locked.csv"))   # save it in the locked folder, unopened
        line = "%s locked: saved, not inspected" % name             # the log line says it was not looked at
        print(line)                                                 # show it on screen
        log.append(line)                                            # and keep it for the log file

    # write the log next to the data
    with open(os.path.join(HERE, "..", "data", "download_log.txt"), "w") as f:   # open the log file
        f.write("\n".join(log) + "\n")                              # one log line per row


if __name__ == "__main__":                                          # only run when started directly, not when imported
    main()                                                          # do the download
