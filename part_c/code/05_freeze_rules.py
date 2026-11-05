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

FROZEN_FILE = os.path.join(OUT_DIR, "frozen_rules.json")    # where the freeze record is written
LOCK_FILE = os.path.join(OUT_DIR, "oos_run.lock")           # this file appears once the single out-of-sample run has started

if os.path.exists(LOCK_FILE):                               # too late, the locked data has been used
    sys.exit("oos_run.lock already exists, the freeze must happen before the out-of-sample run")   # stop here and say why


def sha(path):                                              # fingerprint of one file
    # sha256 of the raw bytes of a file
    with open(path, "rb") as f:                             # open it as raw bytes, nothing is interpreted
        return hashlib.sha256(f.read()).hexdigest()         # same bytes always give the same 64 character code, any edit changes it


# parameters picked by 04_strategy_research.py using the research period only
params = json.load(open(os.path.join(TAB_DIR, "selected_params.json")))   # read the chosen rule settings

frozen = {                                                  # everything that gets written into the freeze record
    "frozen_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),   # the time of the freeze
    "what_this_means": "rules and code below were fixed BEFORE the locked 2022-2025 data was opened",   # a plain sentence for whoever reads the file
    "params": params,                                       # the rule settings that were chosen
    # every code file that defines the strategy or the final run
    "code_hashes": {name: sha(os.path.join(HERE, name)) for name in ["strategy.py", "common.py", "06_run_oos.py"]},
    # the raw locked data files, so i can show they are the same files i downloaded before doing any research
    "locked_data_hashes": {name: sha(os.path.join(HERE, "..", "data", "locked_oos", name))
                           for name in ["nifty50_locked.csv", "banknifty_locked.csv"]},
    # the research results the parameters came from
    "research_result_hashes": {name: sha(os.path.join(TAB_DIR, name)) for name in ["grid_research.csv", "selected_params.json"]},
}

with open(FROZEN_FILE, "w") as f:                           # write the freeze record
    json.dump(frozen, f, indent=2)                          # as readable json
print("frozen at", frozen["frozen_at"])                     # show the time of the freeze
print(json.dumps(frozen["params"], indent=2))               # and the settings that were frozen
