# 02c_build_nse_index_reference.py
# builds data/reference/nse_index_ohlc_2012_2021.csv: open, high, low, close of Nifty 50 and Bank Nifty as published by NSE itself
# NSE puts one file per trading day on its archive site (ind_close_all_DDMMYYYY.csv, all indices in one file)
# files that are already saved in data/reference/sources/nse_index_files are not downloaded again, so this runs offline too.
# the repository does not include those raw files, so a fresh run downloads them first (about 2,400 files for 2012-2021, one request at a time, a few minutes)
#   python 02c_build_nse_index_reference.py            -> research period 2012-2021 (used by 02_clean_data.py, section 7)
#   python 02c_build_nse_index_reference.py --locked   -> 2022-2025, ONLY for the post-hoc check after the single out-of-sample run
#                                                         (used by 07_post_hoc_locked_check.py, it is not part of the research)
# this script never opens the locked price files, it only downloads NSE's public files

import os                                               # paths
import csv                                              # writing the csv
import time                                             # small pause between requests
import argparse                                         # command line option
import datetime as dt                                   # dates
import urllib.request                                   # download
import urllib.error                                     # to catch the 404s

ap = argparse.ArgumentParser()                          # reads the options typed after the script name
ap.add_argument("--locked", action="store_true", help="2022-2025 (post-hoc check) instead of 2012-2021")   # the only option: switch to the locked period
args = ap.parse_args()                                  # args.locked is True if --locked was given

HERE = os.path.dirname(os.path.abspath(__file__))       # folder of this script
REF = os.path.normpath(os.path.join(HERE, "..", "data", "reference"))   # the reference data folder, one level up

if args.locked:                                         # post-hoc mode: the 2022-2025 period
    FIRST, LAST = dt.date(2022, 1, 1), dt.date(2025, 12, 31)     # the period that was locked
    FOLDER, OUT_NAME = "nse_index_files_2022_2025", "nse_index_ohlc_2022_2025.csv"   # where the daily files live, and the csv to write
    LAST_WEEKDAY = 6                                    # monday to saturday: special saturday sessions (budget days) happen in this period
    EXTRA_DAYS = {dt.date(2023, 11, 12)}                # Diwali muhurat session on a sunday
else:                                                   # normal mode: the research period
    FIRST, LAST = dt.date(2012, 1, 1), dt.date(2021, 12, 31)     # research period only
    FOLDER, OUT_NAME = "nse_index_files", "nse_index_ohlc_2012_2021.csv"   # where the daily files live, and the csv to write
    LAST_WEEKDAY = 5                                    # monday to friday
    EXTRA_DAYS = set()                                  # no weekend sessions are looked at in this period

RAW = os.path.join(REF, "sources", FOLDER)              # the saved daily files
os.makedirs(RAW, exist_ok=True)                         # create that folder if it does not exist yet

URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_%s.csv"   # the address of one day's file, %s is the date as DDMMYYYY

NIFTY = {"S&P CNX Nifty", "CNX Nifty", "Nifty 50"}      # NSE renamed the index twice in this period
BANK = {"CNX Bank", "Nifty Bank"}                       # and the bank index once

# dates NSE answered "not found" for (holidays, and a few days its archive simply does not have)
nf_path = os.path.join(RAW, "not_found_404.txt")        # the saved list of those dates
not_found = set(open(nf_path).read().split()) if os.path.exists(nf_path) else set()   # read it if it exists, else start empty

# ---------------------------------------------------------------- 1. download whatever is not saved yet
d = FIRST                                               # start with the first day of the period
fresh = 0                                               # how many files were really downloaded in this run
while d <= LAST:                                        # one day at a time until the end of the period
    tag = d.strftime("%d%m%Y")                          # the date written the way NSE writes it in file names
    path = os.path.join(RAW, "ind_close_all_%s.csv" % tag)   # where this day's file is (or will be) saved
    wanted = d.weekday() < LAST_WEEKDAY or d in EXTRA_DAYS   # weekdays, plus the special days of this period
    if wanted and not os.path.exists(path) and d.isoformat() not in not_found:     # a day we know nothing about yet
        try:                                            # the download can fail, so it is wrapped
            req = urllib.request.Request(URL % tag, headers={"User-Agent": "Mozilla/5.0"})   # a normal browser-like request
            with urllib.request.urlopen(req, timeout=30) as r:   # ask NSE for the file, give up after 30 seconds
                body = r.read()                         # the file's bytes
            if body.startswith(b"Index Name"):          # a real csv (the site answers errors with an html page)
                with open(path, "wb") as f:             # save it exactly as received
                    f.write(body)                       # write the bytes
            else:                                       # NSE sent something that is not a csv
                not_found.add(d.isoformat())            # treat the day as "not available"
        except urllib.error.HTTPError as e:             # NSE answered with an error code
            if e.code == 404:                           # "not found": a holiday, or a day missing in NSE's archive
                not_found.add(d.isoformat())            # holiday or missing in NSE's archive
            else:                                       # any other error is a real problem
                raise                                   # stop and show it
        fresh += 1                                      # count this request
        time.sleep(0.2)                                 # one request at a time, no hammering of the server
    d += dt.timedelta(days=1)                           # move on to the next day
with open(nf_path, "w") as f:                           # save the list of "not found" dates for next time
    f.write("\n".join(sorted(not_found)) + "\n")        # one date per line

# ---------------------------------------------------------------- 2. pick the two indices out of every saved file
rows = []                                               # one row per day and index, collected here
quirks = []                                             # files where the date written inside differs from the date in the file name
for name in sorted(os.listdir(RAW)):                    # go through every saved file
    if not name.startswith("ind_close_all_"):           # skip anything that is not a daily index file
        continue                                        # (for example the list of 404 dates)
    file_date = dt.datetime.strptime(name[len("ind_close_all_"):-len(".csv")], "%d%m%Y").date()   # the date NSE put in the file name
    with open(os.path.join(RAW, name), encoding="utf-8", errors="ignore") as f:   # open this day's file
        for r in csv.DictReader(f):                     # one dictionary per index in the file
            idx = r["Index Name"].strip()               # the index's name as NSE wrote it that year
            if idx in NIFTY:                            # it is the Nifty 50
                label = "Nifty 50"                      # use one fixed name for it
            elif idx in BANK:                           # it is the Bank Nifty
                label = "Bank Nifty"                    # use one fixed name for it
            else:                                       # any other index
                continue                                # all the other indices are not needed
            day = r["Index Date"].strip().replace("/", "-")          # dd-mm-yyyy in most years, dd/mm/yyyy in some
            inner = dt.datetime.strptime(day, "%d-%m-%Y").date()     # the date written inside the file
            if inner != file_date:                      # it disagrees with the file name
                # a few NSE files (6, 10 and 11 April 2023) write the date inside as mm-dd-yyyy, so 10 April shows up as "04-10-2023".
                # the file name is the date i trust, but only if the inner date is the same day with day and month swapped
                swapped = dt.datetime.strptime(day, "%m-%d-%Y").date()   # read the inside date month-first instead
                if swapped != file_date:                # even swapped it does not match: something is really wrong
                    raise ValueError("%s: date inside the file (%s) does not match the file name" % (name, day))   # stop instead of guessing
                quirks.append((name, day))              # remember this file for the message at the end
            rows.append((file_date.isoformat(), label, float(r["Open Index Value"]), float(r["High Index Value"]),
                         float(r["Low Index Value"]), float(r["Closing Index Value"])))   # date, index, open, high, low, close
rows.sort()                                             # order by date, then index name
if quirks:                                              # only say something if there were odd files
    print("files with the date written month-first inside (used the file name):", sorted(set(q[0] for q in quirks)))   # list them

# ---------------------------------------------------------------- 3. write the csv
out = os.path.join(REF, OUT_NAME)                       # where the csv will be written
with open(out, "w", newline="") as f:                   # open it for writing
    w = csv.writer(f)                                   # a csv writer for that file
    w.writerow(["date", "index", "open", "high", "low", "close"])   # the header row
    w.writerows(rows)                                   # all the data rows
print("downloaded %d new files, wrote %d rows to %s" % (fresh, len(rows), out))   # say what was done
for label in ["Nifty 50", "Bank Nifty"]:                # a short summary for each index
    mine = [r for r in rows if r[1] == label]           # this index's rows only
    print(label, len(mine), "days, first", mine[0][0], "last", mine[-1][0])   # the summary line
