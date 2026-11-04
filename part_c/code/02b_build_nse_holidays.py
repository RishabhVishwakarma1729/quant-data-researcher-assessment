# 02b_build_nse_holidays.py
# builds data/reference/nse_trading_holidays_2012_2021.csv (every weekday trading holiday of NSE) from the saved sources
# in data/reference/sources. it only reads those files, nothing is downloaded here. 02_clean_data.py uses the csv in its calendar check
# with --locked it builds nse_trading_holidays_2022_2025.csv instead (only for the post-hoc check, see 07_post_hoc_locked_check.py)

import os                                               # paths
import re                                               # to pull the dates out of the text
import sys                                              # to stop early in post-hoc mode
import csv                                              # writing the csv
import argparse                                         # command line option
import datetime as dt                                   # dates

ap = argparse.ArgumentParser()
ap.add_argument("--locked", action="store_true", help="2022-2025 holiday list (post-hoc check) instead of 2012-2021")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))       # folder of this script
REF = os.path.normpath(os.path.join(HERE, "..", "data", "reference"))   # reference folder
SRC = os.path.join(REF, "sources")                      # the saved official documents

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]   # first three letters of each month


def month_no(name):
    # "January" / "Jan" -> 1
    return MONTHS.index(name.lower()[:3]) + 1


def read(name):
    # text of one saved source file
    with open(os.path.join(SRC, name), encoding="utf-8", errors="ignore") as f:
        return f.read()


def cut(text, markers):
    # keep the text before the first marker that shows up, so only the first table (the trading holidays) is read
    end = len(text)
    for m in markers:
        k = text.find(m)
        if k != -1:
            end = min(end, k)
    return text[:end]


def dates_dmy(text, year):
    # 26-Jan-2012 style (NSE website)
    return [dt.date(int(y), month_no(m), int(d)) for d, m, y in re.findall(r"(\d{2})-([A-Za-z]{3})-(\d{4})", text) if int(y) == year]


def dates_long(text, year):
    # January 26, 2018 style (NSE circulars) and Jan 26, 2013 style (zerodha 2013)
    out = []
    for m, d, y in re.findall(r"([A-Za-z]{3,9})\.? (\d{1,2}), ?(\d{4})", text):
        if m.lower()[:3] in MONTHS and int(y) == year:
            out.append(dt.date(int(y), month_no(m), int(d)))
    return out


def dates_ordinal(text, year):
    # February 27th style (zerodha 2014, the year is not written in each row)
    return [dt.date(year, month_no(m), int(d)) for m, d in re.findall(r"([A-Za-z]{3,9}) (\d{1,2})(?:st|nd|rd|th)", text) if m.lower()[:3] in MONTHS]


# ---------------------------------------------------------------- 0. post-hoc mode: the 2022-2025 holidays (python 02b_build_nse_holidays.py --locked)
# only used by 07_post_hoc_locked_check.py, after the single out-of-sample run. it reads NSE's four yearly circulars and nothing else
if args.locked:
    MUHURAT_LOCKED = "Laxmi Pujan; Muhurat Trading session (a star in the circular)"
    LOCKED_FILES = [(2022, "NSE_CMTR50560_holidays_2022.txt", "NSE circular NSE/CMTR/50560 dated 10-Dec-2021: nsearchives.nseindia.com/content/circulars/CMTR50560.pdf"),
                    (2023, "NSE_CMTR54757_holidays_2023.txt", "NSE circular NSE/CMTR/54757 dated 08-Dec-2022: nsearchives.nseindia.com/content/circulars/CMTR54757.pdf"),
                    (2024, "NSE_CMTR59722_holidays_2024.txt", "NSE circular NSE/CMTR/59722 dated 12-Dec-2023: nsearchives.nseindia.com/content/circulars/CMTR59722.pdf"),
                    (2025, "NSE_CMTR65587_holidays_2025.txt", "NSE circular NSE/CMTR/65587 dated 13-Dec-2024: nsearchives.nseindia.com/content/circulars/CMTR65587.pdf")]
    lrows = []
    for yr, fname, src in LOCKED_FILES:
        text = cut(read(fname), ["holidays falling on Saturday"])            # first table only (trading holidays on weekdays)
        days = sorted(set(dates_long(text, yr)))
        # in these four circulars every field of a row is on its own line: date / weekday / description
        names = {dt.date(int(y), month_no(m), int(d)): " ".join(n.split()) for m, d, y, n in      # (a description can run over two lines when the first ends with a slash)
                 re.findall(r"([A-Z][a-z]+) (\d{1,2}), ?(\d{4})\s*\n\s*\w+day\s*\n([^\n]+/\s*\n[^\n]+|[^\n]+)", text)}
        for d in days:
            note = MUHURAT_LOCKED if "*" in names.get(d, "") else ""
            lrows.append((d, names.get(d, "").replace("*", "").strip(), note, src))
    # changes announced after the yearly list (NSE circulars, also reported by the press; the data and NSE's own index files agree with each of them)
    lrows = [r for r in lrows if r[0] != dt.date(2023, 6, 28)]               # Bakri Id was moved, 28-Jun-2023 became a trading day
    lrows += [(dt.date(2023, 6, 29), "Bakri Id", "moved from 28-Jun-2023 to 29-Jun-2023 by NSE circular NSE/CMTR/57285 of 27-Jun-2023 (Maharashtra government decision)", "NSE circular NSE/CMTR/57285 of 27-Jun-2023"),
              (dt.date(2024, 1, 22), "Ram Mandir consecration (public holiday in Maharashtra)", "added by NSE circular of 19-Jan-2024 (partial modification of circular 59917); a normal Saturday session was held on 20-Jan-2024 instead", "NSE circular of 19-Jan-2024, trading holiday on 22-Jan-2024"),
              (dt.date(2024, 5, 20), "Parliamentary elections in Mumbai", "added by NSE circular of 08-Apr-2024 after the December 2023 list", "NSE circular of 08-Apr-2024, trading holiday on 20-May-2024"),
              (dt.date(2024, 11, 20), "Assembly elections in Maharashtra", "added by NSE circular of 08-Nov-2024 after the December 2023 list", "NSE circular of 08-Nov-2024, trading holiday on 20-Nov-2024")]
    lrows = sorted(set(r for r in lrows if r[0].weekday() < 5), key=lambda r: r[0])    # weekdays only
    out = os.path.join(REF, "nse_trading_holidays_2022_2025.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "description", "note", "source"])
        for d, name, note, src in lrows:
            w.writerow([d.isoformat(), name, note, src])
    print("wrote %d weekday holidays to %s" % (len(lrows), out))
    for yr in range(2022, 2026):
        print(yr, sum(1 for r in lrows if r[0].year == yr))
    sys.exit(0)

# ---------------------------------------------------------------- 1. the holiday dates of each year
holidays = {}                                           # year -> list of dates
for yr, fname in [(2012, "nse_website_holidays_2012_archived_2012-05-02.txt"),
                  (2015, "nse_website_holidays_2015_archived_2015-11-17.txt"),
                  (2016, "nse_website_holidays_2016_archived_2016-05-07.txt")]:
    text = read(fname)
    text = text[text.find("Sr. No."):]                  # start at the first table
    nxt = text.find("Sr. No.", 10)                      # the second table is the clearing holidays, not a market closure
    first = text[:nxt] if nxt != -1 else text           # so stop before it
    first = cut(first, ["holidays falling on Saturday"])
    holidays[yr] = sorted(set(dates_dmy(first, yr)))

# 2013 comes from zerodha's copy of the exchange list, and the exchanges moved muharram from 14 to 15 november (announced on 13 nov 2013)
text = cut(read("zerodha_exchange_holidays_2013.txt"), ["falling on Sunday", "MCX-2013"])
h13 = set(dates_long(text, 2013))
h13.discard(dt.date(2013, 11, 14))                      # this day became a normal trading day
h13.add(dt.date(2013, 11, 15))                          # and this one the holiday
holidays[2013] = sorted(h13)

# 2014 also comes from zerodha's copy (it includes the two election closures)
text = cut(read("zerodha_exchange_holidays_2014.txt"), ["Holidays falling on Sunday"])
holidays[2014] = sorted(set(dates_ordinal(text, 2014)))

# 2017 to 2021 are NSE's own yearly circulars
for yr, fname in [(2017, "NSE_FAOP33750_holidays_2017.txt"), (2018, "NSE_CMTR36475_holidays_2018.txt"), (2019, "NSE_CMTR39612_holidays_2019.txt"),
                  (2020, "NSE_CMTR42877_holidays_2020.txt"), (2021, "NSE_CMTR46623_holidays_2021.txt")]:
    text = cut(read(fname), ["holidays falling on Saturday"])
    holidays[yr] = sorted(set(dates_long(text, yr)))

# ---------------------------------------------------------------- 2. descriptions (where the source has the name on the same line)
desc = {}
for fname in ["nse_website_holidays_2012_archived_2012-05-02.txt", "nse_website_holidays_2015_archived_2015-11-17.txt",
              "nse_website_holidays_2016_archived_2016-05-07.txt"]:
    for d, m, y, wd, name in re.findall(r"(\d{2})-([A-Za-z]{3})-(\d{4}) \| (\w+) \| ([^|]+)\|", read(fname)):
        desc.setdefault(dt.date(int(y), month_no(m), int(d)), name.strip())
for fname in ["NSE_FAOP33750_holidays_2017.txt", "NSE_CMTR36475_holidays_2018.txt", "NSE_CMTR39612_holidays_2019.txt",
              "NSE_CMTR42877_holidays_2020.txt", "NSE_CMTR46623_holidays_2021.txt"]:
    for m, d, y, wd, name in re.findall(r"([A-Z][a-z]+) (\d{1,2}), ?(\d{4}) (\w+day) ([^\n]+)", read(fname)):
        desc.setdefault(dt.date(int(y), month_no(m), int(d)), name.strip())

# ---------------------------------------------------------------- 3. where each year came from, and notes on special days
SOURCE = {
    2012: "NSE website 'Holidays for the calendar year 2012' (archived 2012-05-02): web.archive.org/web/20120502180720/http://nseindia.com:80/products/content/derivatives/equities/mrkt_timing_holidays.htm",
    2013: "Zerodha reproduction of the exchange list (zerodha.com/z-connect/?p=60); Muharram date as revised by NSE/BSE on 13-Nov-2013 (Business Standard)",
    2014: "Zerodha reproduction of the exchange list (zerodha.com/z-connect/?p=2740)",
    2015: "NSE website 'Holidays for the calendar year 2015' (archived 2015-11-17): web.archive.org/web/20151117021549/http://nseindia.com/products/content/derivatives/equities/mrkt_timing_holidays.htm",
    2016: "NSE website 'Holidays for the calendar year 2016' (archived 2016-05-07): web.archive.org/web/20160507230314/https://www1.nseindia.com/products/content/derivatives/equities/mrkt_timing_holidays.htm",
    2017: "NSE circular NSE/FAOP/33750 dated 05-Dec-2016: nsearchives.nseindia.com/content/circulars/FAOP33750.pdf",
    2018: "NSE circular NSE/CMTR/36475 dated 12-Dec-2017: nsearchives.nseindia.com/content/circulars/CMTR36475.pdf",
    2019: "NSE circular NSE/CMTR/39612 dated 07-Dec-2018: nsearchives.nseindia.com/content/circulars/CMTR39612.pdf",
    2020: "NSE circular NSE/CMTR/42877 dated 11-Dec-2019: nsearchives.nseindia.com/content/circulars/CMTR42877.pdf",
    2021: "NSE circular NSE/CMTR/46623 dated 11-Dec-2020: archives.nseindia.com/content/circulars/CMTR46623.pdf",
}
MUHURAT = "Laxmi Pujan; Muhurat session in the evening"
NOTE = {
    dt.date(2013, 11, 15): "Muharram; moved from 14-Nov to 15-Nov by NSE/BSE on 13-Nov-2013 (14-Nov became a trading day)",
    dt.date(2012, 11, 13): "Laxmi Puja; Muhurat session in the evening",
    dt.date(2014, 10, 23): MUHURAT,
    dt.date(2017, 10, 19): MUHURAT,
    dt.date(2018, 11, 7): MUHURAT,
    dt.date(2021, 11, 4): MUHURAT,
    dt.date(2014, 4, 24): "special closure, parliamentary elections in Mumbai",
    dt.date(2014, 10, 15): "special closure, assembly elections in Maharashtra",
}

# ---------------------------------------------------------------- 4. put the rows together (weekdays only, weekend holidays do not matter here)
rows = []
for yr in range(2012, 2022):
    for d in holidays[yr]:
        if d.weekday() < 5:                             # monday to friday
            rows.append((d, desc.get(d, ""), NOTE.get(d, ""), SOURCE[yr]))

# closures that were announced after the yearly list (checked in news reports and NSE circulars)
rows += [
    (dt.date(2015, 11, 11), "Diwali Laxmi Pujan", "regular session closed, Muhurat session only (Business Standard, 11-Nov-2015); not in NSE's yearly trading-holiday table", "press report, see note"),
    (dt.date(2019, 4, 29), "Parliamentary elections in Mumbai", "added by NSE circular after the December 2018 list (Mar-2019)", "NSE circular, trading holiday on 29-Apr-2019"),
    (dt.date(2019, 10, 21), "Assembly elections in Maharashtra", "added by NSE circular 53/2019 (Oct-2019)", "NSE circular 53/2019, trading holiday on 21-Oct-2019"),
]
rows = sorted(set(rows), key=lambda r: r[0])            # in date order, no duplicates

# ---------------------------------------------------------------- 5. write the csv
out = os.path.join(REF, "nse_trading_holidays_2012_2021.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "note", "source"])
    for d, name, note, src in rows:
        w.writerow([d.isoformat(), name, note, src])
print("wrote %d weekday holidays to %s" % (len(rows), out))
for yr in range(2012, 2022):
    print(yr, sum(1 for r in rows if r[0].year == yr))
