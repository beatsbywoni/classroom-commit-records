#!/usr/bin/env bash
# Runs the v4 analysis parts two at a time, skipping parts whose result file already exists.
cd "$(dirname "$0")"
PARTS="era agent era_regime agent_nostarter stability extra year low_msg samples_ge5 samples_test_orgs_kept samples_copies_kept samples_tierAB samples_full_frame_ge3"
RULES="rule_v3 rule_v4_d0 rule_v4_shared rule_v4_staff3 rule_v4_staff10 rule_v4_nostaff rule_v4_strict"
run_part() { [ -f ../data/v2/results_v4_$1.json ] && return; PART=$1 python3 25_analysis_v4.py > ../data/v2/v4_$1.log 2>&1; echo "part $1 exit $?"; }
run_rule() { [ -f ../data/v2/results_v4_$1_rules.json ] && return; MODE=rules SIG_FILE=signals_$1.csv SUF=_$1 B_BOOT=500 python3 25_analysis_v4.py > ../data/v2/v4_$1.log 2>&1; echo "rule $1 exit $?"; }
for p in $PARTS; do run_part $p & if [ $(jobs -r | wc -l) -ge 2 ]; then wait -n; fi; done
for r in $RULES; do run_rule $r & if [ $(jobs -r | wc -l) -ge 2 ]; then wait -n; fi; done
wait; echo ALL_DONE
