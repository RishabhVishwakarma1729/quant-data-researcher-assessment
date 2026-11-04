# 02c_build_nse_index_reference.py
# builds data/reference/nse_index_ohlc_2012_2021.csv: open, high, low, close of Nifty 50 and Bank Nifty as published by NSE itself
# NSE puts one file per trading day on its archive site (ind_close_all_DDMMYYYY.csv, all indices in one file)
# files that are already saved in data/reference/sources/nse_index_files are not downloaded again, so this runs offline too
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

ap = argparse.ArgumentParser()
ap.add_argument("--locked", action="store_true", help="2022-2025 (post-hoc check) instead of 2012-2021")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))       # folder of this script
REF = os.path.normpath(os.path.join(HERE, "..", "data", "reference"))

if args.locked:
    FIRST, LAST = dt.date(2022, 1, 1), dt.date(2025, 12, 31)     # the period that was locked
    FOLDER, OUT_NAME = "nse_index_files_2022_2025", "nse_index_ohlc_2022_2025.csv"
    LAST_WEEKDAY = 6                                    # monday to saturday: special saturday sessions (budget days) happen in this period
    EXTRA_DAYS = {dt.date(2023, 11, 12)}                # Diwali muhurat session on a sunday
else:
    FIRST, LAST = dt.date(2012, 1, 1), dt.date(2021, 12, 31)     # research period only
    FOLDER, OUT_NAME = "nse_index_files", "nse_index_ohlc_2012_2021.csv"
    LAST_WEEKDAY = 5                                    # monday to friday
    EXTRA_DAYS = set()

RAW = os.path.join(REF, "sources", FOLDER)              # the saved daily files
os.makedirs(RAW, exist_ok=True)

URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_%s.csv"

NIFTY = {"S&P CNX Nifty", "CNX Nifty", "Nifty 50"}      # NSE renamed the index twice in this period
BANK = {"CNX Bank", "Nifty Bank"}                       # and the bank index once

# dates NSE answered "not found" for (holidays, and a few days its archive simply does not have)
nf_path = os.path.join(RAW, "not_found_404.txt")
not_found = set(open(nf_path).read().split()) if os.path.exists(nf_path) else set()

# ---------------------------------------------------------------- 1. download whatever is not saved yet
d = FIRST
fresh = 0                                               # how many files were really downloaded in this run
while d <= LAST:
    tag = d.strftime("%d%m%Y")
    path = os.path.join(RAW, "ind_close_all_%s.csv" % tag)
    wanted = d.weekday() < LAST_WEEKDAY or d in EXTRA_DAYS
    if wanted and not os.path.exists(path) and d.isoformat() not in not_found:     # a day we know nothing about yet
        try:
            req = urllib.request.Request(URL % tag, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            if body.startswith(b"Index Name"):          # a real csv (the site answers errors with an html page)
                with open(path, "wb") as f:
                    f.write(body)
            else:
                not_found.add(d.isoformat())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                not_found.add(d.isoformat())            # holiday or missing in NSE's archive
            else:
                raise
        fresh += 1
        time.sleep(0.2)                                 # one request at a time, no hammering of the server
    d += dt.timedelta(days=1)
with open(nf_path, "w") as f:
    f.write("\n".join(sorted(not_found)) + "\n")

# ---------------------------------------------------------------- 2. pick the two indices out of every saved file
rows = []
quirks = []                                             # files where the date written inside differs from the date in the file name
for name in sorted(os.listdir(RAW)):
    if not name.startswith("ind_close_all_"):
        continue
    file_date = dt.datetime.strptime(name[len("ind_close_all_"):-len(".csv")], "%d%m%Y").date()   # the date NSE put in the file name
    with open(os.path.join(RAW, name), encoding="utf-8", errors="ignore") as f:
        for r in csv.DictReader(f):
            idx = r["Index Name"].strip()
            if idx in NIFTY:
                label = "Nifty 50"
            elif idx in BANK:
                label = "Bank Nifty"
            else:
                continue                                # all the other indices are not needed
            day = r["Index Date"].strip().replace("/", "-")          # dd-mm-yyyy in most years, dd/mm/yyyy in some
            inner = dt.datetime.strptime(day, "%d-%m-%Y").date()
            if inner != file_date:
                # a few NSE files (6, 10 and 11 April 2023) write the date inside as mm-dd-yyyy, so 10 April shows up as "04-10-2023".
                # the file name is the date i trust, but only if the inner date is the same day with day and month swapped
                swapped = dt.datetime.strptime(day, "%m-%d-%Y").date()
                if swapped != file_date:
                    raise ValueError("%s: date inside the file (%s) does not match the file name" % (name, day))
                quirks.append((name, day))
            rows.append((file_date.isoformat(), label, float(r["Open Index Value"]), float(r["High Index Value"]),
                         float(r["Low Index Value"]), float(r["Closing Index Value"])))
rows.sort()
if quirks:
    print("files with the date written month-first inside (used the file name):", sorted(set(q[0] for q in quirks)))

# ---------------------------------------------------------------- 3. write the csv
out = os.path.join(REF, OUT_NAME)
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "index", "open", "high", "low", "close"])
    w.writerows(rows)
print("downloaded %d new files, wrote %d rows to %s" % (fresh, len(rows), out))
for label in ["Nifty 50", "Bank Nifty"]:
    mine = [r for r in rows if r[1] == label]
    print(label, len(mine), "days, first", mine[0][0], "last", mine[-1][0])
