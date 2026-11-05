# 02d_build_nse_volume_reference.py
# builds data/reference/nse_volume_2012_2021.csv: traded volume (shares) and turnover (Rs crore) of Nifty 50 and Bank Nifty as published by NSE itself
# Yahoo's volume is empty or zero on many days (all of 2012 for Nifty), but NSE's own daily index files carry the number for every day they exist
# this script only reads the files that 02c_build_nse_index_reference.py saved in data/reference/sources, it downloads nothing
# (the repository does not include those raw files, so run 02c first if you want to rebuild; the csv files are already included)
#   python 02d_build_nse_volume_reference.py            -> research period 2012-2021 (used by 02_clean_data.py, section 3)
#   python 02d_build_nse_volume_reference.py --locked   -> 2022-2025, ONLY for the post-hoc check after the single out-of-sample run
#                                                          (used by 07_post_hoc_locked_check.py, it is not part of the research)
# it never opens the locked price files, volume of the locked period comes from NSE's public files only

import os                                               # paths
import sys                                              # to stop with a message
import csv                                              # reading and writing csv
import argparse                                         # command line option
import datetime as dt                                   # dates

ap = argparse.ArgumentParser()                          # reads the options typed after the script name
ap.add_argument("--locked", action="store_true", help="2022-2025 (post-hoc check) instead of 2012-2021")   # the only option: switch to the locked period
args = ap.parse_args()                                  # args.locked is True if --locked was given

HERE = os.path.dirname(os.path.abspath(__file__))       # folder of this script
REF = os.path.normpath(os.path.join(HERE, "..", "data", "reference"))   # the reference data folder, one level up

if args.locked:                                         # post-hoc mode: the 2022-2025 files
    FOLDER, OUT_NAME = "nse_index_files_2022_2025", "nse_volume_2022_2025.csv"   # read this folder, write this csv
else:                                                   # normal mode: the research period
    FOLDER, OUT_NAME = "nse_index_files", "nse_volume_2012_2021.csv"             # read this folder, write this csv
RAW = os.path.join(REF, "sources", FOLDER)              # the saved daily files
if not os.path.isdir(RAW):                              # the raw files are not in the repository
    sys.exit("%s not found: the raw NSE daily files are not part of this repository. Run 02c_build_nse_index_reference.py%s first, it downloads them." % (
        RAW, " --locked" if args.locked else ""))       # stop and tell the user what to do

NIFTY = {"S&P CNX Nifty", "CNX Nifty", "Nifty 50"}      # NSE renamed the index twice in this period
BANK = {"CNX Bank", "Nifty Bank"}                       # and the bank index once


def number(text):                                       # turns NSE's text into a number
    # NSE writes "-" where it has nothing; that becomes an empty cell here, never a zero
    text = text.strip()                                 # remove spaces around the text
    return "" if text in ("", "-") else float(text)     # empty stays empty, anything else becomes a number


rows = []                                               # one row per day and index, collected here
for name in sorted(os.listdir(RAW)):                    # go through the saved files, oldest date first in the name order
    if not name.startswith("ind_close_all_"):           # skip anything that is not a daily index file
        continue                                        # (for example the list of 404 dates)
    file_date = dt.datetime.strptime(name[len("ind_close_all_"):-len(".csv")], "%d%m%Y").date()   # the date trusted is the one in the file name (see 02c)
    with open(os.path.join(RAW, name), encoding="utf-8", errors="ignore") as f:   # open this day's file
        for r in csv.DictReader(f):                     # one dictionary per index in the file
            idx = r["Index Name"].strip()               # the index's name as NSE wrote it that year
            if idx in NIFTY:                            # it is the Nifty 50
                label = "Nifty 50"                      # use one fixed name for it
            elif idx in BANK:                           # it is the Bank Nifty
                label = "Bank Nifty"                    # use one fixed name for it
            else:                                       # any other index
                continue                                # the other indices are not needed
            vol = number(r["Volume"])                   # shares traded that day
            rows.append((file_date.isoformat(), label, "" if vol == "" else int(vol), number(r["Turnover (Rs. Cr.)"])))   # date, index, volume, turnover
rows.sort()                                             # order by date, then index name

out = os.path.join(REF, OUT_NAME)                       # where the csv will be written
with open(out, "w", newline="") as f:                   # open it for writing
    w = csv.writer(f)                                   # a csv writer for that file
    w.writerow(["date", "index", "volume_shares", "turnover_rs_crore"])   # the header row
    w.writerows(rows)                                   # all the data rows
print("wrote %d rows to %s" % (len(rows), out))         # say how much was written and where
for label in ["Nifty 50", "Bank Nifty"]:                # a short summary for each index
    mine = [r for r in rows if r[1] == label]           # this index's rows only
    empty = sum(1 for r in mine if r[2] == "")          # how many days have no volume
    print(label, len(mine), "days, first", mine[0][0], "last", mine[-1][0], "| days with no volume:", empty)   # the summary line
