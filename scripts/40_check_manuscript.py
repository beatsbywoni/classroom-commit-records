#!/usr/bin/env python3
"""Check the numbers typed into the manuscript source against the result files and derived tables.

Most numbers in the manuscript are not typed: the tables in tables5/ are written by 35_tables_v5.py and the
numbers in the text by 38_text_numbers.py (macros \\R{...}). This script covers the rest. It reads the
manuscript source, finds every number outside generated tables, macros, labels, citations, and equations, and
assigns each one to exactly one of three classes:

  checked   the number appears in a phrase whose expected text is computed here from the result files
            (results_*.json, registration/*.json) or the derived tables, and the phrase is found verbatim;
  constant  a date, year, version, design parameter (caps, thresholds, interval levels, numbers of draws or
            replicates, sample sizes of the review design), or label, listed below with the phrase it occurs in;
  recorded  a number reported from a step that this package cannot re-run and whose output is not distributed
            as a result file (listed below with its source).

It fails (exit status 1) if an expected phrase is not found (a mismatch) or if any number is in no class
(unclassified), and writes a JSON report.

Usage: python 40_check_manuscript.py --tex manuscript/main_v6.tex --results DIR --derived DIR
                                     --registration registration/ --report out.json
(--results and --derived are the data/v2 folder that 00_reproduce_from_package.py builds.)
"""
import argparse, json, math, os, re, sys
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--tex", required=True); ap.add_argument("--results", required=True); ap.add_argument("--derived", required=True)
ap.add_argument("--registration", required=True); ap.add_argument("--report", required=True)
a = ap.parse_args()
R = lambda n: json.load(open(os.path.join(a.results, n)))
REG = lambda n: json.load(open(os.path.join(a.registration, n)))
tex = open(a.tex, encoding="utf-8").read()

# ---------- formatting helpers ----------
def i(n): return f"{int(n):,}"
def pc(x, k=0): return f"{100 * x:.{k}f}\\%"
def pct_num(x, k=0): return f"{100 * x:.{k}f}"
def r(x, k=2): return f"{x:.{k}f}"
def pval(p, k=2): return f"{p:.{k}f}".lstrip("0") if p < 1 else "1"
WORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}

# ---------- inputs ----------
RG = R("results_record_generation.json"); DS = R("results_v4_descriptives.json"); AV = R("results_activity_validation.json")
AR = R("results_activity_review_v4.json"); CC = R("results_copy_check.json"); RV = R("results_reml_validation.json")
TR = R("results_trailer_v4.json"); EX2 = R("results_v2_extra_v3.json"); SDR = R("results_v5_sdref.json")
ERA4, AG4 = R("results_v4_era.json")["era"], R("results_v4_agent.json")["agent"]
ERA5, AG5 = R("results_v5_era.json")["era"], R("results_v5_agent.json")["agent"]
NOS4 = R("results_v4_agent_nostarter.json")["agent_nostarter"]
REGIME = R("results_v4_era_regime.json")["era_regime"]
ST = R("results_v5_stability.json")["stability"]; ST4 = R("results_v4_stability.json")["stability"]
SAMP = {k: R(f"results_v5_samples_{k}.json")["samples"][k] for k in ("ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3")}
RULES = {k: R(f"results_v5_rule_{k}_rules.json") for k in ("v3", "v4_d0", "v4_shared", "v4_staff3", "v4_staff10", "v4_nostaff", "v4_strict")}
H = REG("registered_results_core.json"); H5 = REG("registered_results_h5.json")
sig = pd.read_csv(os.path.join(a.derived, "signals_v4.csv"), low_memory=False, dtype={"ai_tool_main": str})
starter = pd.read_csv(os.path.join(a.derived, "repo_starter.csv"))
record = pd.read_csv(os.path.join(a.derived, "flags_v4", "repo_record.csv"))
SIG6 = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion"]

# ---------- values computed from the derived tables ----------
base = sig[(sig.ghc_verified == 1) & (sig.n_commits_human >= 3) & (sig.org_test == 0)]
prim = base[base.assignment_copy == 0]; cop = base[base.assignment_copy == 1]
cop_orgs = cop.org.nunique(); cop_alone = int((~cop.org.isin(set(prim.org))).sum())
cr = pd.to_datetime(prim.created_ts, unit="s")
st_ = prim[["repo"]].assign(cr=cr.values).merge(starter, on="repo", how="left")
st_["starter"] = (st_.root_bot == 1) & (st_.root_bot_add >= 20)
before_jul20 = st_[st_.cr < "2020-07-01"]; h2_20 = st_[(st_.cr >= "2020-07-01") & (st_.cr < "2021-01-01")]
hy = {r_["half"]: r_ for r_ in RG["by_half_year"]}
late_hy = [hy[h] for h in ("2024H2", "2025H1", "2025H2", "2026H1")]; early_hy = [hy[h] for h in ("2021H1", "2021H2", "2022H1", "2022H2", "2023H1", "2023H2", "2024H1")]
nby = RG["noncopy_by_year"]
v4s = AR["variants_vs_v4"]; v4n = AR["v4_student"]
var_change = [abs(v4s[k]["student"] - v4n) / v4n for k in ("v3", "v4_d0", "v4_shared", "v4_staff3", "v4_staff10", "v4_nostaff")]
strict_drop = 1 - RULES["v4_strict"]["era"]["n"] / ERA5["n"] if "n" in RULES["v4_strict"].get("era", {}) else None
copies_orgs_added = SAMP["copies_kept"]["era"]["orgs"] - ERA5["orgs"]
d2 = EX2["diag_registered"]
raw_reg = [x["raw_d"] for x in d2]; z_reg = [x["registered_z_diff"] for x in d2]
sdr = SDR["sd_ref"]
w_ratio = []
for fam, b in (("era", ERA4), ("agent", AG4)):
    for c in SIG6:
        w_ratio.append(b["within"][c]["d"] and (ERA5 if fam == "era" else AG5)["within"][c]["d"] / b["within"][c]["d"])
stab_d = max(abs(ST[f][c]["d_M1000"] - (ERA5 if f == "era" else AG5)["cap"]["50"][c]["d"]) for f in ("era", "agent") for c in SIG6) if "d_M1000" in ST["era"][SIG6[0]] else None
T5, TP = TR["full_frame_ge5"], TR["primary"]
org_one = float((prim.groupby("org").size() == 1).mean())
msg_share = {e: float((prim[prim.era == e].n_commits_human == prim[prim.era == e].n_nonbot).mean()) for e in ("pre", "post")}
raw5, ri5, cov5 = ERA5["raw"], {c: ERA5["ri"][c]["d"] for c in SIG6}, {c: ERA5["raw_cov"][c]["d"] for c in SIG6}
three = ["edit_size_log", "large_insert_share_200", "test_touch_share"]
others_small = all(abs(raw5[c]) < 0.1 for c in SIG6 if c not in three)
cov_change = max(abs(cov5[c] - raw5[c]) for c in three)
def wide_contains(b):
    return sum(1 for c in SIG6 if not b["within"][c]["ci_grid_edge"] and b["within"][c]["ci90_d"][0] <= 0 <= b["within"][c]["ci90_d"][1] and (b["within"][c]["ci90_d"][0] <= -0.3 or b["within"][c]["ci90_d"][1] >= 0.3))
n_wide = wide_contains(ERA5)
stab_e = []; stab_ci = []
for f_, B_ in (("era", ERA5), ("agent", AG5)):
    for c in ST[f_]:
        x = ST[f_][c]; d_ = B_["cap"]["50"][c]["d"]
        stab_e += [abs(x["d_M1000"] - d_), abs(x["d_rep2"] - d_)]; stab_ci += [abs(x["ci90_rep2"][k] - B_["cap"]["50"][c]["ci90"][k]) for k in (0, 1)]
se_ratio = sorted(row["nm_se"] / row["own_se"] for row in RV["rows"])
ceil3 = lambda x: math.ceil(x * 1000) / 1000
tools = T5["tools"]; nai = T5["ai"]

CHECKS = [  # (expected phrase, source)
    # abstract, introduction, collection
    (f"examines all three for {i(len(starter))} public repositories", "repo_starter rows"),
    (f"; {i(len(record))} were verified as created by Classroom, and {i(DS['n'])} of these, in {DS['orgs']} organizations", "repo_record rows; descriptives"),
    (f"three checks for {i(len(starter))} public repositories", "repo_starter rows"),
    (f"and yielded {i(RG['enumerated_n'])} repositories", "record_generation.enumerated_n"),
    (f"{i(len(starter))} yielded a parsable log", "repo_starter rows"),
    (f"which the platform writes ({i(len(record))} repositories)", "repo_record rows"),
    (f"{i(RG['verified_nontest'])} verified repositories remain", "record_generation.verified_nontest"),
    (f"The primary sample comprises {i(DS['n'])} verified repositories with at least three classified commits in {DS['orgs']} organizations", "descriptives"),
    (f"{i(DS['era']['pre'])} pre-ChatGPT, {i(DS['era']['post'])} post-ChatGPT, and {DS['era']['buffer']} in the buffer month", "descriptives.era"),
    (f"the median repository spans {WORD[round(DS['median_span_days'])]} days and {WORD[round(DS['median_commits'])]} classified commits, and {pct_num(DS['single_author'])}\\% have a single author", "descriptives"),
    (f"The median organization contributes one repository and {'three fifths' if abs(org_one - 0.6) < 0.05 else 'MISMATCH'} contribute only one; the ten largest contribute {i(DS['top10'])}, {'more than half' if DS['top10'] > DS['n'] / 2 else 'MISMATCH'}; the largest alone contributes {i(DS['largest'])} ({pc(DS['largest_share'])})", "descriptives; derived organization sizes"),
    (f"Only {DS['spanning_orgs']} organizations have repositories on both sides of the ChatGPT boundary ({i(DS['spanning_repos'])} repositories, of which {i(DS['spanning_sizes'][0])} belong to the largest and {i(DS['spanning_sizes'][1])} to the next), and only {DS['agent_spanning_orgs']} span the February 2025 boundary ({i(DS['agent_spanning_repos'])} repositories, {i(DS['agent_spanning_sizes'][0])} from the largest)", "descriptives"),
    (f"finds {DS['students_both']} authors with repositories in both eras", "descriptives.students_both"),
    # Table 1
    (f"August 5, 2026 & {i(RG['enumerated_n'])} \\\\", "record_generation.enumerated_n"),
    (f"non-empty, cloned, and log parsed & {i(len(starter))} \\\\", "repo_starter rows"),
    (f"(description or name fingerprint) & {i(len(record))} \\\\", "repo_record rows"),
    (f"with at least one classified commit & {i(DS['ver_ge1'])} \\\\", "descriptives.ver_ge1"),
    (f"with at least three classified commits & {i(DS['ver_ge3'])} \\\\", "descriptives.ver_ge3"),
    (f"excluding test, demo, and sandbox organizations & {i(DS['ver_ge3_nontest'])} \\\\", "descriptives.ver_ge3_nontest"),
    (f"(primary sample) & {i(DS['n'])} \\\\", "descriptives.n"),
    (f"December 2022 buffer & {i(DS['era']['pre'])} / {i(DS['era']['post'])} / {DS['era']['buffer']} \\\\", "descriptives.era"),
    (f"pre or post era & {i(DS['low_n'])} \\\\", "descriptives.low_n"),
    (f"full frame & {i(min(v['era']['n'] for v in SAMP.values()))} to {i(max(v['era']['n'] for v in SAMP.values()))} \\\\", "samples era n"),
    # record generation (Section 4.1)
    (f"apart from {RG['copies_by_year'].get('2019', 0) + RG['copies_by_year'].get('2023', 0)} isolated cases", "record_generation.copies_by_year before 2024"),
    (f"2026, {pct_num(min(h['copy_share'] for h in late_hy))}\\% to {pct_num(max(h['copy_share'] for h in late_hy))}\\% of the verified repositories", "record_generation.by_half_year"),
    (f"and {pct_num(hy['2026H2']['copy_share'])}\\% of the {hy['2026H2']['n']} created in the five weeks before collection), {i(RG['assignment_copies'])} of {i(RG['verified_nontest'])} in all", "record_generation"),
    (f"Of these, {len(cop)} have three or more classified commits", "derived: verified copies with three or more classified commits"),
    (f"from {cop_orgs} organizations, {cop_alone} of them from organizations with no other repository", "derived"),
    (f"{CC['groups']['copy_after_2024_07']['with_forks']} of {CC['groups']['copy_after_2024_07']['sampled']} sampled copies had forks (median {CC['groups']['copy_after_2024_07']['median_forks']})", "copy_check"),
    (f"against {CC['groups']['noncopy_after_2024_07']['with_forks']} of {CC['groups']['noncopy_after_2024_07']['sampled']} other verified repositories created in the same period (median {CC['groups']['noncopy_after_2024_07']['median_forks']}) and {CC['groups']['noncopy_before_2024']['with_forks']} of {CC['groups']['noncopy_before_2024']['sampled']} created before 2024", "copy_check"),
    (f"and {CC['groups']['copy_after_2024_07']['generated_from_template']} of the {CC['groups']['copy_after_2024_07']['sampled']} copies were generated from a template", "copy_check"),
    (f"falls from between {pct_num(min(h['primary_starter_share'] for h in early_hy))}\\% and {pct_num(max(h['primary_starter_share'] for h in early_hy))}\\% in each half-year from 2021 to mid-2024 to between {pct_num(min(h['primary_starter_share'] for h in late_hy))}\\% and {pct_num(max(h['primary_starter_share'] for h in late_hy))}\\% after it", "record_generation.by_half_year"),
    (f"({'The bot authored no root commit in this sample before July 2020' if before_jul20.starter.sum() == 0 else 'MISMATCH'} and about {pct_num(round(h2_20.starter.mean(), 1))}\\% in the second half of 2020", "derived: primary sample, starter flag by creation date"),
    (f"{pct_num(min(nby[y]['zero'] for y in ('2017', '2018', '2019', '2020', '2021')))}\\% to {pct_num(max(nby[y]['zero'] for y in ('2017', '2018', '2019', '2020', '2021')))}\\% for repositories created in 2017 to 2021, {pct_num(nby['2022']['zero'])}\\% in 2022, {pct_num(nby['2023']['zero'])}\\% in 2023, {pct_num(nby['2024']['zero'])}\\% in 2024, {pct_num(nby['2025']['zero'])}\\% in 2025, and {pct_num(nby['2026']['zero'])}\\% in 2026", "record_generation.noncopy_by_year"),
    (f"observed for a year or more ({pct_num(RG['obs_window_2025']['ge_1y'])}\\%) than among those observed for less ({pct_num(RG['obs_window_2025']['lt_1y'])}\\%)", "record_generation.obs_window_2025"),
    (f"while {i(REGIME['n_post'])} of the {i(AG4['n_pre'])} early-post repositories", "era_regime.n_post; agent.n_pre"),
    # activity attribution (Section 4.2)
    (f"Of the {i(AV['transitions']['n_nonbot'])} non-bot commits in verified repositories outside test organizations", "activity_validation"),
    (f"were mostly committed before the repository existed ({pct_num(AV['v3_categories']['inherited (shared SHA)']['pre_creation_0'])}\\%), but the {pct_num(1 - AV['v3_categories']['inherited (shared SHA)']['pre_creation_0'])}\\% committed afterward", "activity_validation"),
    (f"({AV['manual_review']['rows'][0]['student']} of {AV['manual_review']['rows'][0]['student'] + AV['manual_review']['rows'][0]['instructor_or_history'] + AV['manual_review']['rows'][0]['undeterminable']} in a review)", "activity_validation.manual_review"),
    (f"Of the commits it treated as staff-like, {pct_num(AV['v3_categories']['staff-like']['name_match'])}\\% were by authors who match the repository name", "activity_validation"),
    (f"pre-existing history: {pct_num(AV['v3_categories']['student']['pre_creation_1d'], 1)}\\% of them, {pct_num(next(x['pre_creation_1d'] for x in AV['v3_categories_by_era'] if x['v3cls'] == 'student' and x['era'] == 'pre'), 1)}\\% in the pre-ChatGPT era", "activity_validation"),
    (f"Under the adopted rule, {i(AV['v4_exclusion_reasons']['pre_existing_history'])} of the {i(AV['transitions']['n_nonbot'])} commits are excluded as pre-existing history, {AV['v4_exclusion_reasons']['instructor_push_shared_ge5']} as pushes to many repositories, and {i(AV['v4_exclusion_reasons']['staff_like_unmatched'])} as staff-like; {i(AV['transitions']['v3_student_to_v4_excluded'])} commits that the previous rule kept are excluded and {i(AV['transitions']['v3_excluded_to_v4_student'])} that it excluded are kept", "activity_validation"),
    (f"Among classified commits, {pct_num(AV['v4_kept_name_match_share'])}\\% have an owner match ({pct_num(AV['v4_kept_name_match_by_era']['pre'])}\\% in the pre era, {pct_num(AV['v4_kept_name_match_by_era']['post'])}\\% in the post era)", "activity_validation"),
    (f"All {AR['by_category']['kept_match']['n']} owner-matched classified commits reviewed were judged student work", "activity_review"),
    (f"Of {AR['by_category']['kept_nomatch']['n']} classified commits without an owner match, {AR['by_category']['kept_nomatch']['S']} were judged student work", "activity_review"),
    (f"), {AR['by_category']['kept_nomatch']['I']} were not (", "activity_review"),
    (f"and {AR['by_category']['kept_nomatch']['U']} were undeterminable; weighting", "activity_review"),
    (f"The {AR['by_category']['excl_push']['pop']} commits excluded as pushes", "activity_review"),
    (f"by {pct_num(min(var_change), 1)}\\% to {pct_num(max(var_change), 1)}\\%", "activity_review.variants_vs_v4"),
    (f"drops most team repositories and {pct_num(1 - RULES['v4_strict']['era']['n'] / ERA5['n']) if 'n' in RULES['v4_strict']['era'] else 'MISSING'}\\% of the sample", "rule v4_strict era n"),
    (f"Retaining the {len(cop)} assignment copies would add {copies_orgs_added} organizations", "derived copies; samples_copies_kept orgs"),
    # comparisons (Section 5)
    (f"In the {DS['spanning_orgs']} organizations observed in both eras", "descriptives"),
    (f"rested on {DS['spanning_orgs']} organizations for the ChatGPT boundary and {DS['agent_spanning_orgs']} for the agentic one", "descriptives"),
    (f"rests on {DS['spanning_orgs']} and {DS['agent_spanning_orgs']} organizations dominated by one or two", "descriptives"),
    (f"({DS['agent_spanning_orgs']} organizations, one with {DS['agent_spanning_sizes'][0]} of {DS['agent_spanning_repos']} repositories)", "descriptives"),
    (f"are about plus {round(raw5['edit_size_log'], 1):.1f} for all repositories and minus {abs(ri5['edit_size_log']):.2f} and minus {abs(ri5['large_insert_share_200']):.2f} under random intercepts" if round(raw5['edit_size_log'], 1) == round(raw5['large_insert_share_200'], 1) else "MISMATCH figure description", "era raw and RI (figure description)"),
    ("the other differences are smaller than 0.1 in absolute value" if others_small else "MISMATCH others", "era raw"),
    (f"changes none of these three by more than {0.02 if cov_change <= 0.02 else cov_change:.2f}", "era raw vs covariates"),
    (f"differences of 0.3 SD or more for {WORD[n_wide]} of the six signals", "era within intervals"),
    ("its intervals contained both no change and changes of 0.3 SD or more" if n_wide >= 1 else "MISMATCH", "era within intervals"),
    (f"(5.8\\% of commits kept by the previous rule, 14.8\\% in" if (pct_num(AV['v3_categories']['student']['pre_creation_1d'], 1), pct_num(next(x['pre_creation_1d'] for x in AV['v3_categories_by_era'] if x['v3cls'] == 'student' and x['era'] == 'pre'), 1)) == ("5.8", "14.8") else "MISMATCH 5.8/14.8", "activity_validation"),
    (f"excluded as templates ({pct_num(1 - AV['v3_categories']['inherited (shared SHA)']['pre_creation_0'])}\\% of the previous rule's inherited commits", "activity_validation"),
    (f"(starter share from {pct_num(min(h['primary_starter_share'] for h in early_hy))}--{pct_num(max(h['primary_starter_share'] for h in early_hy))}\\% per half-year in 2021 to mid-2024 to {pct_num(min(h['primary_starter_share'] for h in late_hy))}--{pct_num(max(h['primary_starter_share'] for h in late_hy))}\\%", "record_generation"),
    (f"a different sample ({pct_num(msg_share['pre'])}\\% of pre-era and {pct_num(msg_share['post'])}\\% of post-era repositories)", "derived: repositories whose non-bot commits are all classified"),
    (f"have SDs between {min(w_ratio):.2f} and {max(w_ratio):.2f} times those of the primary samples", "v4 and v5 within estimates (ratio of denominators)"),
    (f"instead of ${ERA4['within']['edit_size_log']['d']:.2f}$)", "results_v4_era within (own-sample SD)"),
    (f"instead of ${NOS4['raw']['edit_size_log']:+.2f}$ for all repositories)", "results_v4_agent_nostarter raw (own-sample SD)"),
    (f"The estimates differ by at most {ceil3(max(stab_e)):.3f} SD and the interval endpoints by at most {ceil3(max(stab_ci)):.3f}", "stability"),
    (f"The weights are Rademacher for {ERA5['within']['edit_size_log']['orgs']} clusters and Webb's six-point distribution for {AG5['within']['edit_size_log']['orgs']}, because Rademacher weights on {AG5['within']['edit_size_log']['orgs']} clusters", "within orgs"),
    (f"are up to {pct_num(se_ratio[-2] - 1)}\\% larger in {len(se_ratio) - 1} models and {pct_num(se_ratio[-1] - 1)}\\% larger in one model", "reml_validation rows"),
    # Appendix A (registered analysis)
    (f"of which {i(H['n_analysis'])} had at least five defined signals ({i(H['n_pre'])} pre, {i(H['n_post'])} post, {H['n_trailer']} with AI trailers)", "registered_results_core"),
    (f"& $d = {H['H1']['d_std']:.3f}$ & 90\\% CI $[{H['H1']['tost_ci90_d'][0]:.3f}, {H['H1']['tost_ci90_d'][1]:.3f}]$; $p_{{\\text{{Holm}}}} = {pval(H5['holm_final_4tests']['H1'])}$; perm $p = {pval(H['H1']['p_perm'])}$", "registered_results_core; h5 Holm"),
    (f"P1 passed ($d = {H['P1']['d_std']:.3f}$, $p = {pval(H['P1']['p'])}$)", "registered_results_core"),
    (f"& $d = {H['H2a']['d_std']:.3f}$ & $p_{{\\text{{Holm}}}} = {H5['holm_final_4tests']['H2a'] * 1e4:.1f} \\times 10^{{-4}}$; perm $p = {pval(H['H2a']['p_perm'], 3)}$; $n = {i(H['H2a']['n']).replace(',', '{,}')}$", "registered_results_core; h5 Holm"),
    (f"P2 failed ($d = {H['P2']['d_std']:.3f}$, $p = {pval(H['P2']['p'], 3)}$; $n = {i(H['P2']['n']).replace(',', '{,}')}$)", "registered_results_core"),
    (f"& $\\beta = {H['H3']['baseline:post01']['beta']:.3f}$ & $p = {pval(H['H3']['baseline:post01']['p'])}$; {i(H['H3']['n_students'])} students, {i(H['H3']['n_obs'])} later repositories; baseline $\\times$ trailer $\\beta = +{H['H3']['baseline:trailer']['beta']:.2f}$, $p = {pval(H['H3']['baseline:trailer']['p'])}$", "registered_results_core"),
    (f"& $r = {H5['pooled']['pearson_r']:.2f}$ & 95\\% CI $[{H5['pooled']['ci95'][0]:.2f}, {H5['pooled']['ci95'][1]:.2f}]$; Spearman $\\rho = {H5['pooled']['spearman_rho']:.2f}$; $n = {H5['pooled']['n']}$ CodeWorkout students", "registered_results_h5"),
    (f"; 916 students)", "registered_results_h5.pooled.n") if H5["pooled"]["n"] == 916 else ("MISMATCH 916", "h5"),
    (f"The pooled correlation was $r = {H5['pooled']['pearson_r']:.2f}$ (F19: ${H5['F19']['pearson_r']:.2f}$; S19: ${H5['S19']['pearson_r']:.2f}$; timing-only variant ${H5['pooled']['timing_only_r']:.2f}$)", "registered_results_h5"),
    (f"was positive at $p = {pval(H['H3']['baseline:trailer']['p'])}$ uncorrected", "registered_results_core"),
    (f"only {DS['students_both']} students have repositories in both eras", "descriptives.students_both"),
    (f"on the raw scale the same signals in the same sample differed between eras by up to ${max(abs(x) for x in raw_reg):.2f}$ standard deviations", "results_v2_extra_v3.diag_registered"),
    (f"ranging from about minus {abs(min(raw_reg)):.2f} to plus {max(raw_reg):.2f}; gray bars show registered-standardization differences all within plus or minus {math.ceil(max(abs(x) for x in z_reg) * 100) / 100:.2f}", "results_v2_extra_v3.diag_registered"),
    (f"For the eight registered signals in the registered sample ({i(H['n_analysis'])} repositories", "registered_results_core"),
    # Appendix C (estimation)
    (f"matched the stored ones in all {SDR['checks']} checks", "sdref.checks"),
    (f"For the {RV['summary']['n_models']} random-intercept models", "reml_validation"),
    (f"the coefficients agree to within ${RV['summary_vs_nm']['max_abs_diff_beta_own_vs_nm'] * 1e5:.0f} \\times 10^{{-5}}$, the restricted log-likelihoods to within ${math.ceil(RV['summary_vs_nm']['max_abs_diff_llf_own_vs_nm'] * 1e6) / 10:.1f} \\times 10^{{-5}}$, and the organization variances to within ${math.ceil(RV['summary_vs_nm']['max_abs_diff_s2u_own_vs_nm'] * 1e5) / 10:.1f} \\times 10^{{-4}}$", "reml_validation.summary_vs_nm"),
    (f"BFGS failed to converge on {RV['summary_vs_nm']['bfgs_not_converged']} of the {RV['summary']['n_models']}", "reml_validation"),
    (f"With statsmodels' default L-BFGS optimizer, {RV['summary']['lbfgs_degenerate']} of the same {RV['summary']['n_models']} models", "reml_validation"),
    (f"and {RV['summary']['lbfgs_equals_fe']} returned fixed-effect coefficients identical", "reml_validation"),
    # Appendix F (trailers)
    (f"{TR['prevalence']['2023'] * 100:.2f}\\% carried an AI trailer in 2023, {TR['prevalence']['2024'] * 100:.2f}\\% in 2024, {TR['prevalence']['2025'] * 100:.1f}\\% in 2025, and {TR['prevalence']['2026'] * 100:.1f}\\% in the first seven months of 2026", "trailer.prevalence"),
    (f"Of the {nai} AI-trailer repositories in the model sample below", "trailer"),
    (f"{pct_num(tools['claude'] / nai)}\\% name Claude, {pct_num(tools['copilot'] / nai)}\\% Copilot, and {pct_num(tools['cursor'] / nai)}\\% Cursor, and {pct_num(T5['year_mix_ai']['2026'] / nai)}\\% began in 2026", "trailer.tools, year_mix_ai"),
    (f"In the full frame ({i(T5['n'])} repositories in {T5['orgs']} organizations; {T5['ai']} with AI trailers, {T5['human']} with human co-author trailers only)", "trailer"),
    (f"AI-trailer repositories are burstier (${T5['burst_share_30']['ai_d']:+.2f}$), have more distinctive messages (${T5['msg_informativeness']['ai_d']:+.2f}$), and are more concentrated in time (${T5['time_dispersion']['ai_d']:+.2f}$, $p = {pval(T5['time_dispersion']['ai_p'], 3)}$)", "trailer"),
    (f"human-co-author repositories are also burstier (${T5['burst_share_30']['human_d']:+.2f}$) and more distinctive (${T5['msg_informativeness']['human_d']:+.2f}$), but less concentrated in time (${T5['time_dispersion']['human_d']:+.2f}$)", "trailer"),
    (f"($p = {pval(T5['burst_share_30']['human_p'], 3)}$, ${pval(T5['msg_informativeness']['human_p'], 3)}$, and ${pval(T5['time_dispersion']['human_p'], 3)}$)", "trailer"),
    (f"for time dispersion only (${T5['time_dispersion']['diff_d']:.2f} \\pm {1.96 * T5['time_dispersion']['diff_se_d']:.2f}$; Holm $p = {pval(T5['time_dispersion']['diff_p_holm'], 3)}$), and larger in the primary sample (${TP['time_dispersion']['diff_d']:.2f} \\pm {1.96 * TP['time_dispersion']['diff_se_d']:.2f}$; {TP['n']} repositories, {TP['orgs']} organizations)", "trailer"),
    (f"the difference keeps its sign (${T5['time_dispersion']['fe_diff_d']:.2f}$ and ${TP['time_dispersion']['fe_diff_d']:.2f}$) but rests on {T5['orgs_ai_and_human']} and {TP['orgs_ai_and_human']} organizations", "trailer"),
    (f"its wild-bootstrap $p$-values are ${T5['time_dispersion']['fe_p_wild']:.2f}$".replace("$0.", "$.") + f" and ${TP['time_dispersion']['fe_p_wild']:.2f}$".replace("$0.", "$."), "trailer"),
]

# Numbers that are not results: dates, years, versions, design parameters, labels. Each is listed with the phrase it occurs in.
CONSTANT_PHRASES = [
    "retired Classroom in 2026", "From mid-2024 Classroom", "retired Classroom in August 2026", "It documents a 2024 change",
    "on August 5, 2026", "API's 1,000-result window", "on August 6, 2026", "on August 28, 2026", "the snapshot of August 2026",
    "before December 1, 2022", "from January 1, 2023", "(December 2022 is a buffer)", "(January 2023 to January 2025)", "(February 2025 onward)",
    "August 5, 2026 &", "December 2022 buffer", "a 60-second tolerance", "(before December 2022 or from January 2023)", "144 commits from 18 non-empty strata",
    "from late 2023 on", "from mid-2024, carry", "random samples of 40 identified copies, 40 other verified repositories created in the same period, and 20 verified repositories created before 2024",
    "adds 20 or more lines", "The 200-line threshold", "the 95th percentile", "classified 5\\% of commits as large",
    "$\\geq 200$ added lines", "less than 30 minutes", "($k = 25$, 50, 100)", "averaged over 200 draws",
    "(July 1, 2024)", "(January 1, 2024)", "from January 2024;", "Classroom-bot root commit of 20 or more lines",
    "preregistered in August 2026", "(E1 to E15)", "By late 2023,", "since 2019", "from 2021 on", "In January 2024 GitHub",
    "in July 2024, Classroom", "created before 2024 has", "second half of 2024 to the first half of 2026", "were created before July 2024",
    "in 50 or more repositories", "in 5 to 49 repositories", "the six cell-by-breadth groups",
    "(shaded band: $\\pm 0.10$)", "at 25 (down triangle), 50 (diamond, with 90\\%", "at caps of 25, 50, and 100", "at the cap of 50",
    "begun in 2022, falls in 2023 (capped 2023-versus-2022", "in July 2024 (", "of January 2024 (", "capped at 50",
    "(15 or 60 minutes)", "(500 lines, or the largest single insertion)", "of 500 lines in the agentic era", "the cap of 50 (", "more than 50, and a cap of 50",
    "after mid-2024", "across 2024", "in 2024 was announced", "a 2024 change in how", "Claude Fable 5.1 and Claude Opus 5.5 for the October 2026", "for the August 2026 collection",
    "August 6, 2026, secondary-data", "SHA-256 manifest", "era-by-language 95th percentile", "(10,000)", "on 77 students",
    "margin $d = \\pm 0.10$", "(fake boundary at June 1, 2021)", "D1 to D10", "E1 to E15", "D1, D2, D4, D5, and D6",
    "(E1, E2, E3, E5, E11, E15)", "(E4, E9, E10, E14)", "(E7, E8, E12, E13, E14)", "(E6, E14, E15)", "caps of 25, 50, and 100",
    "(95th percentile of added lines", "(August 2026) concluded", "(October 2026) analyzed", "Classroom's 2024 change",
    "over 200 independent draws", "in each of 1,000 replicates", "the 90\\% and 95\\% intervals", "estimates from 1,000 draws",
    "(1,999 replicates)", "give only $2^6 = 64$ possible", "within $10^{-8}$", "relative to 2019", "in 2021 and 2022, lower in 2023, and higher again from 2024; test-path touches dip in 2023",
    "(for large-insert share under the cap, about as high in 2024 and 2026), falls in 2023", "is $1$ minus", "in August 2026 from all", "begun in 2021 and 2022",
    "in 2020,", "in 2021,", "in 2022, and", "in 2023; the 2023-versus-2022", "begun from 2024", "first commits 2024 onward",
    "at the 5\\% level", "Spring and Fall 2019", "dataset 3458", "$\\log(1 + {}$median", "(95\\%", "90\\% CI", "95\\% CI", "90\\%", "95\\%",
]
# Numbers reported from steps whose outputs are not result files in this package.
RECORDED = [
    ("The 58,526 non-empty repositories", "collection log of 02_enumerate/03_clone_extract (raw logs not distributed)"),
    ("concentrated in 169 repositories", "22_activity_audit.py console output on the raw logs"),
    ("non-bot author (25,743)", "registered analysis (07b_extract), table not distributed with repository names"),
    ("C/C++ 256,181; C\\# 40,880; other 17,325; web markup 9,287; notebooks 2,397; JavaScript/TypeScript 2,252; Java/Kotlin 358; Python 214; all languages 28,622", "computed from commit-level added lines (commits_v2), registered definition"),
    ("(29\\% of the sample), within organization-by-era cohort otherwise (71\\%)", "registered analysis (08_analysis.sh) output"),
    ("standardized 71\\% of its sample", "registered analysis (08_analysis.sh) output"),
    ("(22,071 repositories, 71\\%", "registered analysis (08_analysis.sh) output"),
    ("43 robustness specifications in $[-0.056, 0.013]$", "registration/registered_results_core.json robustness (count and range)"),
]

# ---------- extract numbers outside generated content ----------
body_start = tex.index("\\begin{abstract}"); body_end = tex.index("\\bibliography")
masked = list(tex)
def mask(pattern, flags=re.S):
    for m in re.finditer(pattern, tex, flags):
        if m.start() < body_start: continue
        for k in range(m.start(), m.end()): masked[k] = " "
for pat in (r"\\begin\{CCSXML\}.*?\\end\{CCSXML\}", r"\\ccsdesc(\[[^\]]*\])?\{[^}]*\}", r"\\R\{[^}]*\}", r"\\begin\{equation\}.*?\\end\{equation\}",
            r"\\(ref|label|cite\w*|input|eqref|url|includegraphics|bibliography\w*|hspace|vspace)(\[[^\]]*\])?\{[^}]*\}", r"\\setlength\{[^}]*\}\{[^}]*\}", r"[_^]\{?-?\d+\}?",
            r"\\begin\{tabular\}\{[^\n]*", r"p\{[\d.]+cm\}", r"%[^\n]*", r"\\(begin|end)\{[^}]*\}(\[[^\]]*\])?", r"width=[\d.]+\\linewidth", r"\\texttt\{[^}]*\}",
            r"\\section\*?\{[^}]*\}|\\subsection\*?\{[^}]*\}", r"\\\\\[\d+pt\]", r"\\multicolumn\{\d+\}"):
    mask(pat)
M = "".join(masked)
tokens = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"(?<![A-Za-z\\@\d])\d[\d,\.]*", M) if body_start <= m.start() < body_end]
covered = [None] * len(tex)
def cover(phrase, cls, note):
    found = [m.start() for m in re.finditer(re.escape(phrase), tex)]
    for s in found:
        for k in range(s, s + len(phrase)):
            if covered[k] is None: covered[k] = (cls, note)
    return len(found)
results = {"checked": [], "mismatches": [], "constant_phrases_missing": [], "recorded": [], "unclassified": []}
for phrase, src in CHECKS:
    n = cover(phrase, "checked", src)
    (results["checked"] if n else results["mismatches"]).append({"expected": phrase, "source": src, "found": n})
for phrase in CONSTANT_PHRASES:
    if not cover(phrase, "constant", "design parameter, date, or label"): results["constant_phrases_missing"].append(phrase)
for phrase, src in RECORDED:
    n = cover(phrase, "recorded", src)
    results["recorded"].append({"phrase": phrase, "source": src, "found": n})
    if not n: results["mismatches"].append({"expected": phrase, "source": "recorded value not found in text", "found": 0})
# automatic constants: years and day-of-month in dates, decision labels, figure-panel letters are not numbers
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
for s, e, t in tokens:
    if covered[s] is not None: continue
    ctx_before = tex[max(0, s - 12):s]; t0 = t.rstrip(".,")
    if re.fullmatch(r"(19|20)\d\d", t0) or re.search(rf"({MONTHS})\s*$", ctx_before) or re.search(r"[A-Z]$", ctx_before) or re.search(r"(Section|Table|Figure|Appendix)~?$", ctx_before):
        for k in range(s, e): covered[k] = ("constant", "date, year, or label")
counts = {"checked": 0, "constant": 0, "recorded": 0}
for s, e, t in tokens:
    c = covered[s]
    if c is None: results["unclassified"].append({"number": t, "line": tex[:s].count("\n") + 1, "context": tex[max(0, s - 70):e + 50].replace("\n", " ")})
    else: counts[c[0]] += 1
results["counts"] = dict(counts, unclassified=len(results["unclassified"]), numbers=len(tokens), checks=len(CHECKS), mismatches=len(results["mismatches"]))
json.dump(results, open(a.report, "w"), indent=1, ensure_ascii=False)
print(f"numbers outside generated content: {len(tokens)}; checked {counts['checked']}, constants {counts['constant']}, recorded {counts['recorded']}, unclassified {len(results['unclassified'])}")
print(f"expected phrases: {len(CHECKS)}; mismatches (expected phrase not found): {len(results['mismatches'])}")
for m in results["mismatches"]: print("  MISMATCH:", m["expected"][:160], "|", m["source"])
for u in results["unclassified"][:60]: print(f"  UNCLASSIFIED line {u['line']}: {u['number']} ... {u['context'][:140]}")
if results["constant_phrases_missing"]: print("  (constant phrases not found, not an error):", results["constant_phrases_missing"][:20])
sys.exit(1 if results["mismatches"] or results["unclassified"] else 0)
