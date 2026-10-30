#!/usr/bin/env python3
"""Paper 2, 8th work order: numbers cited in the text, generated from the final result files.

Writes <toce_v2>/tables5/results_macros.tex, which defines one LaTeX macro per cited result:
    \\R{era.ri.edit}   ->  the random-intercept estimate for edit size in the post-ChatGPT contrast, e.g. -0.33
Keys: <part>.<estimate>.<signal>, with
    part      era, agent (primary contrasts); preswitch, prebeta (post era restricted by creation date); nostarter
              (agentic contrast without platform-copied starter code); low (one or two classified commits);
              msgsub (message subset); year; samp-<sample>; rule-<rule>; ff (full frame, era contrast)
    estimate  raw, cov, cap25, cap50, cap100, cap50ci, cap50ciHalf95, cap100ci95, ri, rip, riholm, loo (without the
              largest organization), loomin, loomax, drop5, w, wci, wp, wrange, nat, natci, mean0, mean1
    signal    edit, large, burst, rerun, test, time, msg, maxins
A missing key stops compilation with an error, so the text cannot silently cite a number that no longer exists.
Standardized values come from the common-SD result files (results_v5_*.json, 37_common_sd.py).
"""
import os, sys, json, math, importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); V2 = os.path.join(HERE, "..", "data", "v2")
_T = next((p for p in (os.path.join(HERE, "..", "toce_v2"), os.path.join(HERE, "..", "..", "toce_v2"), os.path.join(HERE, "..", "manuscript")) if os.path.isdir(p)), os.path.join(HERE, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "tables5")); os.makedirs(OUT, exist_ok=True)
SHORT = {"edit_size_log": "edit", "large_insert_share_200": "large", "burst_share_30": "burst", "samefile_rerun_rate_k3": "rerun",
         "test_touch_share": "test", "time_dispersion": "time", "msg_informativeness": "msg", "max_insert_log": "maxins"}
SIG6 = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion"]
SIG7 = SIG6 + ["msg_informativeness"]
M = {}

def J(n):
    n5 = n.replace("results_v4_", "results_v5_")
    return json.load(open(os.path.join(V2, n5 if os.path.exists(os.path.join(V2, n5)) else n)))
def num(x, k=2):
    t = f"{x:+.{k}f}"
    return f"{0:.{k}f}" if float(t) == 0 else t
def end(x, k=2):
    t = f"{x:+.{k}f}"
    return f"{x:+.{k + 1}f}" if float(t) == 0 else t
def D(x, k=2): return r"\ensuremath{" + num(x, k).replace("-", "-") + "}"
def CI(a, k=2): return r"\ensuremath{[" + end(a[0], k) + ", " + end(a[1], k) + "]}"
def P(p):
    """p-values in the text: three decimals below .10, two above (tables print three)."""
    if p < 0.001: return r"\ensuremath{<}.001"
    if p < 0.1: return f"{p:.3f}".lstrip("0")
    return f"{p:.2f}".lstrip("0") if p < 0.995 else ".99"
def put(k, v):
    assert k not in M, k; M[k] = v
def holm(ps):
    order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0.0
    for i, j in enumerate(order): run = max(run, min(1.0, (m - i) * ps[j])); adj[j] = run
    return adj

def contrast(part, b, ww=None):
    put(f"{part}.n", f"{b['n']:,}"); put(f"{part}.orgs", f"{b['orgs']:,}")
    if "n_pre" in b: put(f"{part}.npre", f"{b['n_pre']:,}"); put(f"{part}.npost", f"{b['n_post']:,}")
    sigs = [c for c in SIG7 if c in b["raw"]]
    sz = [b["cap"][k][c]["d"] for k in ("25", "50", "100") for c in ("edit_size_log", "large_insert_share_200")]
    put(f"{part}.capmin.size", D(min(sz))); put(f"{part}.capmax.size", D(max(sz)))
    if "within" in b: put(f"{part}.wpmin", P(min(b["within"][c]["p_wild"] for c in SIG6))); put(f"{part}.wpmax", P(max(b["within"][c]["p_wild"] for c in SIG6)))
    hol = dict(zip(SIG6, holm(np.array([b["ri"][c]["p"] for c in SIG6]))))
    for c in sigs:
        s = SHORT[c]
        put(f"{part}.raw.{s}", D(b["raw"][c]))
        if "raw_cov" in b: put(f"{part}.cov.{s}", D(b["raw_cov"][c]["d"]))
        for cap in ("25", "50", "100"):
            e = b["cap"][cap][c]; put(f"{part}.cap{cap}.{s}", D(e["d"])); put(f"{part}.cap{cap}ci.{s}", CI(e["ci90"])); put(f"{part}.cap{cap}ci95.{s}", CI(e["ci95"]))
        cv = [b["cap"][k][c]["d"] for k in ("25", "50", "100")]; put(f"{part}.capmin.{s}", D(min(cv))); put(f"{part}.capmax.{s}", D(max(cv)))
        put(f"{part}.ri.{s}", D(b["ri"][c]["d"])); put(f"{part}.rip.{s}", P(b["ri"][c]["p"]))
        if c in hol: put(f"{part}.riholm.{s}", P(hol[c]))
        if "loo" in b:
            put(f"{part}.loo.{s}", D(b["loo"][c][0])); put(f"{part}.loomin.{s}", D(min(b["loo"][c]))); put(f"{part}.loomax.{s}", D(max(b["loo"][c])))
            put(f"{part}.drop5.{s}", D(b["drop_top5"][c]))
        if "within" in b:
            w = b["within"][c]; put(f"{part}.w.{s}", D(w["d"])); put(f"{part}.wp.{s}", P(w["p_wild"]))
            if not w["ci_grid_edge"]: put(f"{part}.wci.{s}", CI(w["ci90_d"]))
            if ww is not None:
                g = ww[c]
                if g["ci_grid_edge"]: put(f"{part}.wrange.{s}", r"\ensuremath{[" + f"{g['grid_d'][0]:+.1f}, {g['grid_d'][1]:+.1f}" + "]}")
        if "means" in b and c in b["means"]:
            m = b["means"][c]; cp = b["cap"]["50"][c]; be, lo, hi = cp["beta"], cp["ci90_beta"][0], cp["ci90_beta"][1]
            if c == "edit_size_log":
                put(f"{part}.nat.{s}", f"{100 * (math.exp(be) - 1):+.0f}\\%"); put(f"{part}.natlo.{s}", f"{100 * (math.exp(lo) - 1):+.0f}\\%"); put(f"{part}.nathi.{s}", f"{100 * (math.exp(hi) - 1):+.0f}\\%")
                put(f"{part}.natabs.{s}", f"{abs(100 * (math.exp(be) - 1)):.0f}\\%"); put(f"{part}.natloabs.{s}", f"{abs(100 * (math.exp(lo) - 1)):.0f}\\%"); put(f"{part}.nathiabs.{s}", f"{abs(100 * (math.exp(hi) - 1)):.0f}\\%")
            elif c in ("large_insert_share_200", "burst_share_30", "test_touch_share"):
                put(f"{part}.nat.{s}", r"\ensuremath{" + f"{100 * be:+.1f}" + "}"); put(f"{part}.natabs.{s}", f"{abs(100 * be):.1f}")
                put(f"{part}.natci.{s}", r"\ensuremath{[" + f"{100 * lo:+.1f}, {100 * hi:+.1f}" + "]}")
                put(f"{part}.mean0.{s}", f"{100 * m['pre']:.1f}\\%"); put(f"{part}.mean1.{s}", f"{100 * m['post']:.1f}\\%")

if __name__ == "__main__":
    era = J("results_v4_era.json")["era"]; ag = J("results_v4_agent.json")["agent"]; WW = J("results_v4_within_wide.json")["within_wide"]
    contrast("era", era, WW["era"]); contrast("agent", ag, WW["agent"])
    for part, key in (("preswitch", "era_preswitch"), ("prebeta", "era_prebeta"), ("nostarter", "agent_nostarter")):
        contrast(part, J(f"results_v4_{key}.json")[key])
    # year contrasts (2023 vs 2022), effects by year
    Y = J("results_v4_year.json")["year"]
    for c in SIG7:
        s = SHORT[c]
        if c in Y["ri"]:
            put(f"year.ri.c2322.{s}", D(Y["ri"][c]["c2023_2022"]["d"])); put(f"year.ri.c2322p.{s}", P(Y["ri"][c]["c2023_2022"]["p"]))
            put(f"year.cap.c2322.{s}", D(Y["cap50"][c]["c2023_2022"]["d"])); put(f"year.cap.c2322ci.{s}", CI(Y["cap50"][c]["c2023_2022"]["ci90"]))
            for yy, v in Y["cap50"][c]["effects"].items(): put(f"year.cap.{yy}.{s}", D(v[0]))
            for yy, v in Y["ri"][c]["effects"].items(): put(f"year.ri.{yy}.{s}", D(v[0]))
    # low-commit repositories (own SD) and message subset (common SD)
    L = J("results_v4_low_msg.json"); lo = L["low"]
    for k in ("n", "pre", "post", "orgs"): put(f"low.{k}", f"{lo[k]:,}")
    for c in ("edit_size_log", "large_insert_share_200", "max_insert_log", "test_touch_share"):
        s = SHORT[c]; e = lo[c]
        put(f"low.raw.{s}", D(e["raw"])); put(f"low.ri.{s}", D(e["ri"]["d"])); put(f"low.cap50.{s}", D(e["cap50"]["d"])); put(f"low.cap50ci.{s}", CI(e["cap50"]["ci90"])); put(f"low.cap50ci95.{s}", CI(e["cap50"]["ci95"]))
        if c in ("large_insert_share_200", "test_touch_share"): put(f"low.mean0.{s}", f"{100 * e['pre_mean']:.0f}\\%"); put(f"low.mean1.{s}", f"{100 * e['post_mean']:.0f}\\%")
    ms = L["msg_subset"]
    for fam in ("era", "agent"):
        e = ms[fam]; put(f"msgsub.{fam}.raw", D(e["raw"])); put(f"msgsub.{fam}.ri", D(e["ri"]["d"])); put(f"msgsub.{fam}.cap50", D(e["cap50"]["d"]))
        put(f"msgsub.{fam}.cap50ci", CI(e["cap50"]["ci90"])); put(f"msgsub.{fam}.n", f"{e['n']:,}")
    # sample and rule variants (cap 50; common SD)
    for nm in ("ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3"):
        Sm = J(f"results_v4_samples_{nm}.json")["samples"][nm]
        for fam in ("era", "agent"):
            e = Sm[fam]; put(f"samp-{nm}.{fam}.n", f"{e['n']:,}"); put(f"samp-{nm}.{fam}.orgs", f"{e['orgs']:,}")
            for c in SIG7:
                s = SHORT[c]; put(f"samp-{nm}.{fam}.rip.{s}", P(e["ri"][c]["p"])); put(f"samp-{nm}.{fam}.cap50.{s}", D(e["cap50"][c]["d"])); put(f"samp-{nm}.{fam}.cap50ci.{s}", CI(e["cap50"][c]["ci90"])); put(f"samp-{nm}.{fam}.ri.{s}", D(e["ri"][c]["d"]))
    for rule in ("v3", "v4_d0", "v4_nostaff", "v4_shared", "v4_staff10", "v4_staff3", "v4_strict"):
        Rr = J(f"results_v4_rule_{rule}_rules.json")
        for fam in ("era", "agent"):
            e = Rr[fam]
            for c in SIG7:
                s = SHORT[c]; put(f"rule-{rule}.{fam}.cap50.{s}", D(e["cap50"][c]["d"])); put(f"rule-{rule}.{fam}.cap50ci.{s}", CI(e["cap50"][c]["ci90"]))
                put(f"rule-{rule}.{fam}.raw.{s}", D(e["raw"][c])); put(f"rule-{rule}.{fam}.ri.{s}", D(e["ri"][c]["d"]))
    # largest movement of the capped estimate across the structure-preserving rule variants (previous rule and five variants)
    mv = []
    for rule in ("v3", "v4_d0", "v4_shared", "v4_staff10", "v4_staff3", "v4_nostaff"):
        Rr = J(f"results_v4_rule_{rule}_rules.json")
        for fam, base in (("era", era), ("agent", ag)):
            for c in SIG6: mv.append(abs(Rr[fam]["cap50"][c]["d"] - base["cap"]["50"][c]["d"]))
    put("rule.maxmove", f"{max(mv):.2f}")
    # sign changes across those variants: largest |estimate| among pairs whose signs differ (both nonzero at two decimals)
    sg = []
    for rule in ("v3", "v4_d0", "v4_shared", "v4_staff10", "v4_staff3", "v4_nostaff"):
        Rr = J(f"results_v4_rule_{rule}_rules.json")
        for fam, base in (("era", era), ("agent", ag)):
            for c in SIG6:
                a0, a1 = base["cap"]["50"][c]["d"], Rr[fam]["cap50"][c]["d"]
                if round(a0, 2) != 0 and round(a1, 2) != 0 and (a0 > 0) != (a1 > 0): sg.append(max(abs(a0), abs(a1)))
    put("rule.signmax", f"{math.ceil(max(sg) * 100) / 100:.2f}" if sg else "0")
    # copies kept: movement of the agentic estimates
    ck = J("results_v4_samples_copies_kept.json")["samples"]["copies_kept"]["agent"]
    put("copies.maxmove.cap", f"{max(abs(ck['cap50'][c]['d'] - ag['cap']['50'][c]['d']) for c in SIG6):.2f}")
    put("copies.maxmove.ri", f"{max(abs(ck['ri'][c]['d'] - ag['ri'][c]['d']) for c in SIG6):.2f}")
    mm = max(max(abs(ck['ri'][c]['d'] - ag['ri'][c]['d']), abs(ck['cap50'][c]['d'] - ag['cap']['50'][c]['d'])) for c in SIG6)
    put("copies.maxmove.bound", f"{math.ceil(mm * 100) / 100:.2f}")
    # full frame, era contrast: how much a cap of 50 removes
    spec = importlib.util.spec_from_file_location("A", os.path.join(HERE, "25_analysis_v4.py")); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
    r = A.load(A.SIG_FILE); ff = r[(r.n_commits_human >= 3) & (r.org_test == 0)].copy(); x, lab = A.contrasts(ff)["era"]
    sz = x.groupby("org").size()
    put("ff.n", f"{len(x):,}"); put("ff.orgs", f"{x.org.nunique():,}"); put("ff.maxorg", f"{int(sz.max()):,}"); put("ff.orgsover50", f"{int((sz > 50).sum()):,}")
    put("ff.removed50", f"{int((sz - 50).clip(lower=0).sum()):,}"); put("ff.share1", f"{100 * (sz == 1).mean():.0f}\\%")
    # threshold and measure variants (each standardized by its own SD in the primary sample)
    EX = J("results_v4_extra.json")["extra"]
    for fam in ("era", "agent"):
        for v, e in EX[fam].items():
            put(f"extra.{fam}.{v}.cap50", D(e["cap50"]["d"])); put(f"extra.{fam}.{v}.cap50ci", CI(e["cap50"]["ci90"])); put(f"extra.{fam}.{v}.ri", D(e["ri"]["d"]))
    # review of the adopted rule (design-weighted) and the staff-like category (39_staff_review_estimates.py)
    AR = J("results_activity_review_v4.json")
    put("review.kept.notstudent", f"{100 * AR['weighted']['kept_not_student']:.0f}\\%"); put("review.kept.undet", f"{100 * AR['weighted']['kept_undeterminable']:.0f}\\%")
    put("review.hist.notstudent", f"{100 * AR['by_category']['excl_history']['w_I']:.0f}\\%")
    SR = J("results_staff_review.json")
    put("staff.design", f"{100 * SR['design_weighted_S']:.0f}\\%"); put("staff.post", f"{100 * SR['poststratified_S']:.0f}\\%")
    put("staff.pop", f"{SR['population']:,}"); put("staff.n", f"{SR['sampled']}"); put("staff.orgs", f"{SR['sample_orgs']}")
    for b_, k in (("50plus", "wide"), ("5to49", "narrow")):
        e = SR["by_breadth"][b_]
        put(f"staff.{k}.pop", f"{e['pop']:,}"); put(f"staff.{k}.share", f"{100 * e['pop'] / SR['population']:.0f}\\%"); put(f"staff.{k}.n", f"{e['n']}")
        put(f"staff.{k}.S", f"{e['S']}"); put(f"staff.{k}.orgs", f"{e['orgs_in_pop']}")
    small = sum(1 for r_ in SR["cells"] if 0 < r_["n"] <= 5); put("staff.smallgroups", {3: "three", 4: "four", 5: "five", 2: "two", 1: "one", 6: "six"}.get(small, str(small)))
    # per-signal analysis N
    SD = J("results_v5_sdref.json")
    for fam in ("era", "agent"):
        for c in SIG7: put(f"{fam}.N.{SHORT[c]}", f"{SD['n_signal'][fam][c]:,}")
    # the text words some macros by direction ("lower", "higher"); stop if a result file would contradict the wording
    _e = era["cap"]["50"]["edit_size_log"]; _t = era["cap"]["50"]["test_touch_share"]
    assert _e["beta"] < 0 and _e["ci90_beta"][0] < 0 < _e["ci90_beta"][1], "Section 5.1 words the capped edit-size effect as lower, from lower to higher"
    assert _t["beta"] < 0, "Section 5.1 words the capped test-path effect as lower"
    lines = ["% generated by 38_text_numbers.py from the final result files; do not edit",
             r"\makeatletter", r"\newcommand{\R}[1]{\ifcsname R@#1\endcsname\csname R@#1\endcsname\else\errmessage{Missing result #1}\fi}"]
    for k in sorted(M): lines.append(r"\expandafter\def\csname R@" + k + r"\endcsname{" + M[k] + "}")
    lines.append(r"\makeatother")
    open(os.path.join(OUT, "results_macros.tex"), "w").write("\n".join(lines) + "\n")
    print(len(M), "macros")
