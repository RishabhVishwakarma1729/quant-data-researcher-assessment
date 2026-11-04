# 05_freeze_rules.py
# the "no more changes" moment. writes down the final parameters and a fingerprint (sha256) of every file that matters,
# so 06_run_oos.py can refuse to run if anything was edited afterwards.
# reading the locked csv files here is only to hash their raw bytes, nothing in them gets parsed or looked at

import os                                                   # paths
import sys                                                  # to quit with a message
import json                                                 # output file
import hashlib                                              # fingerprints
import datetime as dt                                       # timestamp

from common import HERE, OUT_DIR, TAB_DIR                   # folder paths

FROZEN_FILE = os.path.join(OUT_DIR, "frozen_rules.json")
LOCK_FILE = os.path.join(OUT_DIR, "oos_run.lock")

if os.path.exists(LOCK_FILE):                               # too late, the locked data has been used
    sys.exit("oos_run.lock already exists, the freeze must happen before the out-of-sample run")


def sha(path):
    # sha256 of the raw bytes of a file
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# parameters picked by 04_strategy_research.py using the research period only
params = json.load(open(os.path.join(TAB_DIR, "selected_params.json")))

frozen = {
    "frozen_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "what_this_means": "rules and code below were fixed BEFORE the locked 2022-2025 data was opened",
    "params": params,
    # every code file that defines the strategy or the final run
    "code_hashes": {name: sha(os.path.join(HERE, name)) for name in ["strategy.py", "common.py", "06_run_oos.py"]},
    # the raw locked data files, so i can show they are the same files i downloaded before doing any research
    "locked_data_hashes": {name: sha(os.path.join(HERE, "..", "data", "locked_oos", name))
                           for name in ["nifty50_locked.csv", "banknifty_locked.csv"]},
    # the research results the parameters came from
    "research_result_hashes": {name: sha(os.path.join(TAB_DIR, name)) for name in ["grid_research.csv", "selected_params.json"]},
}

with open(FROZEN_FILE, "w") as f:
    json.dump(frozen, f, indent=2)
print("frozen at", frozen["frozen_at"])
print(json.dumps(frozen["params"], indent=2))
