# 01_download_data.py
# pulls nifty 50 and bank nifty daily data from yahoo finance (free, no key needed)
# the two periods are downloaded separately and saved in separate folders,
# so the 2022-2025 locked set never gets mixed in with the research data

import os                       # for paths and making folders
import datetime as dt           # to stamp the log file
import pandas as pd             # tables
import yfinance as yf           # yahoo downloader

# folder where this script lives, everything else is relative to it
HERE = os.path.dirname(os.path.abspath(__file__))
# data folders one level up
RESEARCH_DIR = os.path.join(HERE, "..", "data", "research")
LOCKED_DIR = os.path.join(HERE, "..", "data", "locked_oos")

# yahoo tickers for the two indices, and the short names i use in file names
TICKERS = {"^NSEI": "nifty50", "^NSEBANK": "banknifty"}

# yahoo's "end" date is exclusive, so these give 2012-01-01..2021-12-31 and 2022-01-01..2025-12-31
RESEARCH_START, RESEARCH_END = "2012-01-01", "2022-01-01"
LOCKED_START, LOCKED_END = "2022-01-01", "2026-01-01"


def grab(ticker, start, end):
    # download raw (not adjusted) daily bars, indices have no splits/dividends anyway
    df = yf.download(ticker, start=start, end=end, interval="1d",
                     auto_adjust=False, progress=False)
    # newer yfinance versions return two-level columns, flatten them to just the field name
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # keep only the columns i care about, in a fixed order
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    # make the index a plain date (no timezone) and give it a name
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "date"
    return df


def main():
    # make sure the folders exist
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    os.makedirs(LOCKED_DIR, exist_ok=True)

    # lines for the log file, i'll write them at the end
    log = ["download run at " + dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "source: yahoo finance via the yfinance python package"]

    for ticker, name in TICKERS.items():
        # ---- research period: fine to look at ----
        res = grab(ticker, RESEARCH_START, RESEARCH_END)
        res.to_csv(os.path.join(RESEARCH_DIR, name + "_research.csv"))
        # it is ok to print this one
        line = "%s research: %d rows, %s to %s" % (name, len(res), res.index.min().date(), res.index.max().date())
        print(line)
        log.append(line)

        # ---- locked period: save it and do NOT look at it ----
        locked = grab(ticker, LOCKED_START, LOCKED_END)
        # only check that something came back, nothing else about it gets printed
        assert len(locked) > 0, "locked download came back empty for " + ticker
        locked.to_csv(os.path.join(LOCKED_DIR, name + "_locked.csv"))
        line = "%s locked: saved, not inspected" % name
        print(line)
        log.append(line)

    # write the log next to the data
    with open(os.path.join(HERE, "..", "data", "download_log.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
