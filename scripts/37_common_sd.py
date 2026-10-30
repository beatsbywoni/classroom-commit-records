#!/usr/bin/env python3
"""Paper 2, 8th work order: one standardization denominator per contrast and signal.

In results_v4_*.json each comparison was standardized by the standard deviation of the signal in the sample that
comparison was fitted on: the within-organization comparison by the SD among the spanning organizations, the
leave-one-out and drop-five comparisons by the SD without those organizations, the restricted, sample-variant and
rule-variant comparisons by the SD of their own samples, and the year effects by the SD of the year sample. Differences
between comparisons therefore mixed changes in the coefficient with changes in the denominator.

This script re-expresses every standardized estimate of the two era contrasts in one unit per contrast and signal:
the SD of the signal in the primary analysis sample of that contrast (post-ChatGPT vs pre: 4,941 repositories;
agentic vs early post: 2,875; per signal, the repositories on which the signal is defined). The conversion is exact:
each stored d was computed as beta / s_old, so d_new = d_old * s_old / s_ref, and intervals are rescaled in the same way.
Where the old denominator was not stored, it is recomputed from the same sample construction as in 25_analysis_v4.py,
and the deterministic coefficients (raw differences, random-intercept, leave-one-out, drop-five and within-organization
point estimates) are recomputed and checked against the stored values before conversion. No bootstrap is re-run:
bootstrap and test-inversion intervals are rescaled from the stored values.

Kept in their own units, and labelled as such in the paper: threshold variants of a signal (a different measure, its SD
in the same primary sample), the low-commit analysis (a different population of repositories and signals computed from
one or two commits), and the trailer analysis (a different population).

Input: data/v2/results_v4_*.json and the derived tables used by 25_analysis_v4.py. Output: data/v2/results_v5_*.json
(same structure, standardized values replaced, plus "sd_ref" and "sd_old" fields) and data/v2/results_v5_sdref.json.
"""
import os, sys, json, copy, glob, importlib.util
import numpy as np, pandas as pd, statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("A", os.path.join(HERE, "25_analysis_v4.py")); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
V2 = A.V2
COV = ["log_commits", "n_authors_human", "lang_family", "org"]
FAM = {"era": "era", "era_regime": "era", "era_preswitch": "era", "era_prebeta": "era", "agent": "agent", "agent_nostarter": "agent"}
CHECK = []          # (what, old_beta, recomputed_beta)

def J(n): return json.load(open(os.path.join(V2, n)))
def W(n, obj): json.dump(obj, open(os.path.join(V2, n), "w"), indent=1, default=float)
def sd_cov(x, c, lab): return float(x.dropna(subset=[c, lab] + COV)[c].std(ddof=1))
def sd_raw(x, c): return float(x.dropna(subset=[c])[c].std(ddof=1))
def spanning(x, lab):
    both = x.groupby("org")[lab].agg(lambda s: s.nunique() == 2); return x[x.org.isin(both[both].index)]

r = A.load(A.SIG_FILE); p = A.primary(r); CON = A.contrasts(p, extra=True)
REF = {f: {c: sd_cov(CON[f][0], c, CON[f][1]) for c in A.SIG} for f in ("era", "agent")}
# per-signal analysis N in the primary samples (repositories on which the signal is defined)
NSIG = {f: {c: int(CON[f][0].dropna(subset=[c, CON[f][1]] + COV).shape[0]) for c in A.SIG} for f in ("era", "agent")}

def conv_ci(v, k): return [None if (a is None or not np.isfinite(a)) else a * k for a in v]

def convert_block(B, x, lab, fam, full):
    ref = REF[fam]; out = copy.deepcopy(B); out["sd_ref"] = ref; out["sd_old"] = {}
    for c in [c for c in A.SIG if c in B.get("raw", {})]:
        s_raw = sd_raw(x, c); beta = B["raw"][c] * s_raw
        xx = x.dropna(subset=[c]); CHECK.append((f"raw {fam} {c}", beta, xx.loc[xx[lab] == 1, c].mean() - xx.loc[xx[lab] == 0, c].mean()))
        out["raw"][c] = beta / ref[c]; out["sd_old"].setdefault(c, {})["raw"] = s_raw
    for c in [c for c in A.SIG if c in B.get("raw_cov", {})]:
        s = sd_cov(x, c, lab); k = s / ref[c]
        out["raw_cov"][c]["d"] = B["raw_cov"][c]["d"] * k; out["raw_cov"][c]["se_d"] = B["raw_cov"][c]["se_d"] * k; out["sd_old"][c]["raw_cov"] = s
    for c in [c for c in A.SIG if c in B.get("ri", {})]:
        e = B["ri"][c]; out["ri"][c]["d"] = e["beta"] / ref[c]; out["ri"][c]["se_d"] = e["se_beta"] / ref[c]; out["ri"][c]["sd"] = ref[c]; out["sd_old"][c]["ri"] = e["sd"]
    for cap, blk in B.get("cap", {}).items():
        for c, e in blk.items():
            k = e["sd"] / ref[c]; o = out["cap"][cap][c]
            o["d"] = e["beta"] / ref[c]; o["sd"] = ref[c]
            for key in ("ci90", "ci95", "rubin_ci90"):
                if key in e: o[key] = conv_ci(e[key], k)
    if full:
        lv = {"lang_family": sorted(x.lang_family.unique())}
        top = x.groupby("org").size().sort_values(ascending=False).head(10)
        out["loo"] = {}; out["drop_top5"] = {}
        for c in A.SIG:
            new = []
            for i, o in enumerate(top.index):
                f = A.ri_full(x[x.org != o], c, lab, lv); CHECK.append((f"loo {fam} {c} {i}", B["loo"][c][i] * f["sd"], f["beta"])); new.append(f["beta"] / ref[c])
            out["loo"][c] = new
            f = A.ri_full(x[~x.org.isin(top.index[:5])], c, lab, lv); CHECK.append((f"drop5 {fam} {c}", B["drop_top5"][c] * f["sd"], f["beta"])); out["drop_top5"][c] = f["beta"] / ref[c]
            out["within"][c] = convert_within(B["within"][c], x, c, lab, ref[c], f"within {fam} {c}")
        out["paired"] = copy.deepcopy(B["paired"])          # paired medians already used the SD of the full contrast sample
        for c in A.SIG:
            if c in B["paired"]:
                s_p = float(x[c].std(ddof=1)); out["paired"][c]["median_d"] = B["paired"][c]["median_d"] * s_p / ref[c]
    return out

def convert_within(e, x, c, lab, ref_c, tag):
    xs = spanning(x, lab).dropna(subset=[c]); s_w = float(xs[c].std(ddof=1))
    m = smf.ols(f"{c} ~ {lab} + log_commits + n_authors_human + C(lang_family) + C(org)", xs).fit()
    CHECK.append((tag, e["d"] * s_w, float(m.params[lab])))
    o = copy.deepcopy(e); k = s_w / ref_c
    o["d"] = float(m.params[lab]) / ref_c; o["ci90_d"] = conv_ci(e["ci90_d"], k)
    if "grid_d" in e: o["grid_d"] = conv_ci(e["grid_d"], k)
    o["sd_old"] = s_w; o["sd"] = ref_c
    return o

if __name__ == "__main__":
    # 1. contrast blocks
    for part, fam in FAM.items():
        R = J(f"results_v4_{part}.json"); x, lab = CON[part]
        R[part] = convert_block(R[part], x, lab, fam, full=part in ("era", "agent")); R["standardization"] = "d = beta / SD of the signal in the primary sample of the contrast (sd_ref)"
        W(f"results_v5_{part}.json", R); print("converted", part, flush=True)
    # 2. wide-grid test inversion
    R = J("results_v4_within_wide.json")
    for fam in ("era", "agent"):
        x, lab = CON[fam]
        for c in A.SIG: R["within_wide"][fam][c] = convert_within(R["within_wide"][fam][c], x, c, lab, REF[fam][c], f"within_wide {fam} {c}")
    W("results_v5_within_wide.json", R)
    # 3. stability (cap 50 on the primary samples: the old denominator is the reference one; checked)
    R = J("results_v4_stability.json")
    for fam in ("era", "agent"):
        x, lab = CON[fam]
        for c in A.SIG:
            k = sd_cov(x, c, lab) / REF[fam][c]; assert abs(k - 1) < 1e-12
    W("results_v5_stability.json", R)
    # 4. year effects: old denominator = SD in the year sample (first commits 2017 onward, all eras); new = era reference
    R = J("results_v4_year.json"); dy = p[p.first_dt >= "2017-01-01"]
    for est in ("ri", "cap50"):
        for c, e in R["year"][est].items():
            k = float(dy.dropna(subset=[c])[c].std(ddof=1)) / REF["era"][c]
            for yy, v in e["effects"].items():
                e["effects"][yy] = [v[0] * k, v[1] * k] if est == "ri" else [v[0] * k, conv_ci(v[1], k)]
            e["c2023_2022"]["d"] *= k
            if "ci90" in e["c2023_2022"]: e["c2023_2022"]["ci90"] = conv_ci(e["c2023_2022"]["ci90"], k)
            e["sd_old"] = k * REF["era"][c]; e["sd_ref"] = REF["era"][c]
    W("results_v5_year.json", R)
    # 5. message subset (supplementary): convert to the reference SD of message distinctiveness
    R = J("results_v4_low_msg.json"); ps = p[p.n_nonbot == p.n_commits_human]; CS = A.contrasts(ps); c = "msg_informativeness"
    for fam in ("era", "agent"):
        x, lab = CS[fam]; e = R["msg_subset"][fam]; ref = REF[fam][c]
        e["raw"] = e["raw"] * sd_raw(x, c) / ref
        e["ri"]["d"] = e["ri"]["beta"] / ref; e["ri"]["se_d"] = e["ri"]["se_beta"] / ref
        k = e["cap50"]["sd"] / ref; e["cap50"]["d"] = e["cap50"]["beta"] / ref
        for key in ("ci90", "ci95", "rubin_ci90"):
            if key in e["cap50"]: e["cap50"][key] = conv_ci(e["cap50"][key], k)
    R["low_note"] = "low-commit estimates are standardized by the SD in the low-commit sample (a different population)"
    W("results_v5_low_msg.json", R)
    # 6. sample variants
    for f in sorted(glob.glob(os.path.join(V2, "results_v4_samples_*.json"))):
        R = json.load(open(f))
        for nm, blk in R["samples"].items():
            for fam, e in blk.items():
                for c in A.SIG:
                    ref = REF[fam][c]
                    e["ri"][c]["d"] = e["ri"][c]["beta"] / ref; e["ri"][c]["se_d"] = e["ri"][c]["se_beta"] / ref
                    k = e["cap50"][c]["sd"] / ref; e["cap50"][c]["d"] = e["cap50"][c]["beta"] / ref
                    for key in ("ci90", "ci95", "rubin_ci90"):
                        if key in e["cap50"][c]: e["cap50"][c][key] = conv_ci(e["cap50"][c][key], k)
        W(os.path.basename(f).replace("results_v4_", "results_v5_"), R)
    # 7. rule variants (raw differences recomputed from each rule's signal table)
    for f in sorted(glob.glob(os.path.join(V2, "results_v4_rule_*_rules.json"))):
        R = json.load(open(f)); sigf = R["settings"]["sig_file"]
        rr = A.load(sigf); pr = A.primary(rr); CR = A.contrasts(pr)
        for fam in ("era", "agent"):
            e = R[fam]; x, lab = CR[fam]
            for c in A.SIG:
                ref = REF[fam][c]
                e["raw"][c] = e["raw"][c] * sd_raw(x, c) / ref
                e["ri"][c]["d"] = e["ri"][c]["beta"] / ref; e["ri"][c]["se_d"] = e["ri"][c]["se_beta"] / ref
                k = e["cap50"][c]["sd"] / ref; e["cap50"][c]["d"] = e["cap50"][c]["beta"] / ref
                for key in ("ci90", "ci95", "rubin_ci90"):
                    if key in e["cap50"][c]: e["cap50"][c][key] = conv_ci(e["cap50"][c][key], k)
        W(os.path.basename(f).replace("results_v4_", "results_v5_"), R); print("rules", sigf, flush=True)
    # 8. reference SDs, per-signal N, and the checks
    bad = [(w, a, b) for w, a, b in CHECK if abs(a - b) > 1e-6 * max(1, abs(b))]
    W("results_v5_sdref.json", {"sd_ref": REF, "n_signal": NSIG, "checks": len(CHECK), "check_failures": [[w, a, b] for w, a, b in bad],
                                 "rule": "every standardized estimate of a contrast uses the SD of the signal in the primary sample of that contrast"})
    print("checks", len(CHECK), "failures", len(bad))
    for w, a, b in bad[:20]: print("  FAIL", w, a, b)
