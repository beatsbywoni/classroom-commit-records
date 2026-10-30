#!/usr/bin/env python3
"""논문 2 v4 — 원고 표(LaTeX) 생성: 결과 JSON에서 직접 읽어 숫자를 옮겨 적지 않는다.
입력: data/v2/results_v4_*.json, results_trailer_v4.json, results_record_generation.json, results_activity_review_v4.json
출력: <OUT>/tab_*.tex  (OUT 기본값: ../../toce_v2/tables), 그리고 본문 서술용 요약 data/v2/results_v4_summary.json"""
import os, json, math
import numpy as np
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
_H = os.path.dirname(os.path.abspath(__file__)); _T = next((p for p in (os.path.join(_H, "..", "toce_v2"), os.path.join(_H, "..", "..", "toce_v2")) if os.path.isdir(p)), os.path.join(_H, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "tables")); os.makedirs(OUT, exist_ok=True)
SIG = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion", "msg_informativeness"]
NAME = {"edit_size_log": "Edit size", "large_insert_share_200": "Large-insert share", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns",
        "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", "msg_informativeness": "Message distinctiveness",
        "burst_share_15": "Burst share, 15-minute window", "burst_share_60": "Burst share, 60-minute window", "samefile_rerun_rate_k2": "Same-file reruns, run length 2",
        "samefile_rerun_rate_k4": "Same-file reruns, run length 4", "large_insert_share_500": "Large-insert share, $\\geq 500$ lines", "max_insert_log": "Log of largest single insertion",
        "msg_len_log": "Log median message length"}
def J(n): return json.load(open(os.path.join(V2, n)))
def f(x, k=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)): return "--"
    s = f"{x:+.{k}f}"; return "$" + s.replace("-", "-") + "$"
def ci(a, k=2): return f"$[{a[0]:+.{k}f}, {a[1]:+.{k}f}]$"
def pv(p):
    if p < 0.001: return "$<$.001"
    return f"{p:.3f}".lstrip("0") if p < 0.995 else ".99"

def describe(b, c):
    """Robust to weighting / same sign, imprecise / sensitive to weighting (Section 5.4)."""
    vals = [b["raw"][c], b["raw_cov"][c]["d"], b["cap"]["25"][c]["d"], b["cap"]["50"][c]["d"], b["cap"]["100"][c]["d"], b["ri"][c]["d"]]
    sg = set(np.sign(np.round(vals, 3)))
    if len(sg) == 1 and 0 not in sg:
        excl = all((b["cap"][k][c]["ci90"][0] > 0) or (b["cap"][k][c]["ci90"][1] < 0) for k in ("25", "50", "100"))
        if excl:
            marg = any(((b["cap"][k][c]["ci95"][0] <= 0 <= b["cap"][k][c]["ci95"][1]) or min(abs(b["cap"][k][c]["ci90"][0]), abs(b["cap"][k][c]["ci90"][1])) < 0.02) for k in ("25", "50", "100"))
            return "robust (marginal)" if marg else "robust"
        return "same sign, imprecise"
    return "sensitive"

def within_cell(w):
    if w["ci_grid_edge"]: return f"{f(w['d'])} unbounded ({pv(w['p_wild'])})"
    return f"{f(w['d'])} {ci(w['ci90_d'])} ({pv(w['p_wild'])})"

def upper_rows(b):
    """Two rows per signal: estimates, then the 90% bootstrap intervals of the capped estimates."""
    out = []
    for c in SIG:
        cp = b["cap"]
        out.append(f"{NAME[c]} & {f(b['raw'][c])} & {f(b['raw_cov'][c]['d'])} & {f(cp['25'][c]['d'])} & {f(cp['50'][c]['d'])} & {f(cp['100'][c]['d'])} & {f(b['ri'][c]['d'])} & \\multirow{{2}}{{=}}{{{describe(b, c)}}} \\\\")
        out.append(f" & & & {{{ci(cp['25'][c]['ci90'])}}} & {{{ci(cp['50'][c]['ci90'])}}} & {{{ci(cp['100'][c]['ci90'])}}} & ({pv(b['ri'][c]['p'])}) & \\\\[2pt]")
    return out

def contrast_table(name, b, caption, label, spanning):
    L = [r"\begin{table}", r"\caption{" + caption + "}", r"\label{" + label + "}", r"\scriptsize", r"\setlength{\tabcolsep}{2pt}",
         r"\begin{tabular}{@{}l r r c c c r p{1.38cm}@{}}", r"\toprule",
         r"Signal & Raw & Cov. & Cap 25 & Cap 50 & Cap 100 & RI ($p$) & Description \\", r"\midrule"]
    L += upper_rows(b)
    L += [r"\bottomrule", r"\end{tabular}", "", r"\medskip", "", r"\begin{tabular}{@{}l l r l l@{}}", r"\toprule",
          r"Signal & LOO min/max & Drop 5 & Within [90\% CI] ($p_{\text{wild}}$) & Paired median, $+/" + str(spanning) + r"$ \\", r"\midrule"]
    for c in SIG:
        lo = b["loo"][c]; pr = b["paired"][c]
        L.append(f"{NAME[c]} & {f(min(lo))}/{f(max(lo))} & {f(b['drop_top5'][c])} & {within_cell(b['within'][c])} & {f(pr['median_d'])}, {pr['n_positive']}" + (f" of {pr['n_orgs']}" if pr["n_orgs"] != spanning else "") + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    open(os.path.join(OUT, f"tab_{name}.tex"), "w").write("\n".join(L) + "\n")

def natural(b, c):
    cp = b["cap"]["50"][c]; be, lo, hi = cp["beta"], cp["ci90_beta"][0], cp["ci90_beta"][1]; m = b["means"][c]
    if c == "edit_size_log":
        return (f"{100*(math.exp(be)-1):+.0f}\\%", f"$[{100*(math.exp(lo)-1):+.0f}, {100*(math.exp(hi)-1):+.0f}]$", f"{math.expm1(m['pre']):.0f} / {math.expm1(m['post']):.0f} lines", "percent change in median lines per commit")
    if c in ("large_insert_share_200", "burst_share_30", "test_touch_share"):
        return (f"{100*be:+.1f} pp", f"$[{100*lo:+.1f}, {100*hi:+.1f}]$", f"{100*m['pre']:.1f}\\% / {100*m['post']:.1f}\\%", "percentage points")
    return (f"{be:+.3f}", f"$[{lo:+.3f}, {hi:+.3f}]$", f"{m['pre']:.3f} / {m['post']:.3f}", "signal units")

if __name__ == "__main__":
    S = {}
    era = J("results_v4_era.json")["era"]; ag = J("results_v4_agent.json")["agent"]
    d = J("results_v4_descriptives.json")
    contrast_table("era", era, f"Post-ChatGPT minus pre-ChatGPT on each signal, primary sample outside the buffer month ({era['n']:,} repositories, {era['orgs']} organizations; {era['n_pre']:,} pre, {era['n_post']:,} post). Upper part, comparisons among all organizations: raw standardized difference; difference adjusted for the covariates with no organization term (Cov.); contribution-capped estimates with each organization limited to 25, 50, and 100 repositories (mean of 200 draws; 90\\% interval from the organization bootstrap, 1,000 replicates, on the second line); organization random intercepts (RI) with uncorrected $p$; and the description of Section~\\ref{{sec:reading}}. Lower part: minimum and maximum of the RI estimate when each of the ten largest organizations is left out; RI with the five largest removed; within-organization fixed effects on the {d['spanning_orgs']} organizations observed in both eras ({d['spanning_repos']:,} repositories), with the 90\\% interval from test inversion and the wild-bootstrap $p$; organization-level paired median and the number of organizations in which the post mean is higher.", "tab:era", d["spanning_orgs"])
    contrast_table("agent", ag, f"Agentic era (first classified commit February 2025 onward) minus early post (January 2023 to January 2025), primary sample ({ag['n']:,} repositories, {ag['orgs']} organizations; {ag['n_pre']:,} early post, {ag['n_post']:,} agentic). Columns as in Table~\\ref{{tab:era}}; the within-organization and paired comparisons use the {d['agent_spanning_orgs']} organizations observed in both periods ({d['agent_spanning_repos']} repositories, {d['agent_spanning_sizes'][0]} in one organization). ``Unbounded'': the test does not reject any value within six bootstrap standard errors of the estimate.", "tab:agent", d["agent_spanning_orgs"])
    S["describe"] = {k: {c: describe(b, c) for c in SIG} for k, b in (("era", era), ("agent", ag))}
    # regime-restricted comparisons
    L = [r"\begin{table}", r"\caption{Comparisons within one record-generation regime (Section~\ref{sec:regime}). Upper: post-ChatGPT minus pre-ChatGPT, with the post era limited to first classified commits before July 1, 2024. Lower: agentic era minus early post, limited to repositories without platform-copied starter code. Columns as in the upper part of Table~\ref{tab:era}.}",
         r"\label{tab:regime}", r"\scriptsize", r"\setlength{\tabcolsep}{2pt}", r"\begin{tabular}{@{}l r r c c c r p{1.38cm}@{}}", r"\toprule",
         r"Signal & Raw & Cov. & Cap 25 & Cap 50 & Cap 100 & RI ($p$) & Description \\"]
    for part, title in (("era_regime", "Post-ChatGPT (first commit before July 2024) minus pre"), ("agent_nostarter", "Agentic era minus early post, no platform starter code")):
        b = J(f"results_v4_{part}.json")[part]
        L += [r"\midrule", r"\multicolumn{8}{@{}l}{" + title + f" ({b['n']:,} repositories, {b['orgs']} organizations; {b['n_pre']:,} and {b['n_post']:,})" + r"} \\", r"\midrule"]
        L += upper_rows(b)
        S["describe"][part] = {c: describe(b, c) for c in SIG}
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_regime.tex"), "w").write("\n".join(L) + "\n")
    # natural units (cap 50, same fits and replicates as the standardized estimates)
    L = [r"\begin{table}[h]", r"\caption{Contribution-capped estimates (cap 50) in natural units, from the same fits and bootstrap replicates as the standardized estimates of Tables~\ref{tab:era} and~\ref{tab:agent}, with unadjusted means of the two periods. Edit size: percent change in the median lines per commit (geometric means of the per-repository median shown as means).}", r"\label{tab:natural}",
         r"\scriptsize", r"\setlength{\tabcolsep}{3pt}", r"\begin{tabular}{@{}l l l l l l l@{}}", r"\toprule",
         r" & \multicolumn{3}{l}{Post $-$ pre} & \multicolumn{3}{l}{Agentic $-$ early post} \\", r"Signal & Cap 50 & [90\% CI] & Means & Cap 50 & [90\% CI] & Means \\", r"\midrule"]
    for c in SIG:
        a = natural(era, c); g = natural(ag, c)
        L.append(f"{NAME[c]} & {a[0]} & {a[1]} & {a[2]} & {g[0]} & {g[1]} & {g[2]} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_natural.tex"), "w").write("\n".join(L) + "\n")
    S["natural"] = {k: {c: natural(b, c)[:3] for c in SIG} for k, b in (("era", era), ("agent", ag))}
    # thresholds and measures
    E = J("results_v4_extra.json")["extra"]
    L = [r"\begin{table}[h]", r"\caption{Threshold and measure variants, primary sample: organization random intercepts (RI, $d \pm$ 95\% half-width) and contribution-capped estimates at 50 (200 draws; 90\% interval from 500 organization-bootstrap replicates, 1,000 for the main rows).}", r"\label{tab:sens}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{@{}l l l l l@{}}", r"\toprule", r" & \multicolumn{2}{l}{Post $-$ pre} & \multicolumn{2}{l}{Agentic $-$ early post} \\", r"Variant & RI & Cap 50 [90\% CI] & RI & Cap 50 [90\% CI] \\", r"\midrule"]
    main_rows = {"burst_share_30": "burst_share_15", "samefile_rerun_rate_k3": "samefile_rerun_rate_k2", "large_insert_share_200": "large_insert_share_500"}
    order = ["burst_share_15", "burst_share_30", "burst_share_60", "samefile_rerun_rate_k2", "samefile_rerun_rate_k3", "samefile_rerun_rate_k4", "large_insert_share_200", "large_insert_share_500", "max_insert_log", "edit_size_log", "msg_len_log"]
    for c in order:
        cells = []
        for k, b in (("era", era), ("agent", ag)):
            if c in E[k]: ri, cp = E[k][c]["ri"], E[k][c]["cap50"]
            else: ri, cp = b["ri"][c], b["cap"]["50"][c]   # main signals: main-analysis fits (1,000 replicates)
            cells.append(f"{f(ri['d'])} $\\pm$ {1.96*ri['se_d']:.2f} & {f(cp['d'])} {ci(cp['ci90'])}")
        lab = NAME[c] + (" (main)" if c in SIG else "")
        L.append(f"{lab} & {cells[0]} & {cells[1]} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_sens.tex"), "w").write("\n".join(L) + "\n")
    # samples
    samp = {"primary": None}
    for nm in ("ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3"):
        fn = os.path.join(V2, f"results_v4_samples_{nm}.json")
        if os.path.exists(fn): samp[nm] = J(f"results_v4_samples_{nm}.json")["samples"][nm]
    cols = [k for k in ("primary", "ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3") if k == "primary" or k in samp]
    HD = {"primary": "Primary", "ge5": "$\\geq 5$ commits", "test_orgs_kept": "Test orgs kept", "copies_kept": "Copies kept", "tierAB": "Tier A+B", "full_frame_ge3": "Full frame"}
    L = [r"\begin{table}[h]", r"\caption{Sample sensitivity of the contribution-capped estimate (cap 50; 200 draws; 500 organization-bootstrap replicates, 1,000 for the primary sample), $d$; $^{*}$: 90\% interval excludes zero. Repositories and organizations in each contrast are given under each panel.}", r"\label{tab:sampsens}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{@{}l " + "r " * len(cols) + r"@{}}", r"\toprule"]
    for k, title, b0 in (("era", "Post-ChatGPT $-$ pre", era), ("agent", "Agentic era $-$ early post", ag)):
        L += [r"\multicolumn{" + str(len(cols) + 1) + r"}{@{}l}{" + title + r"} \\", "Signal & " + " & ".join(HD[x] for x in cols) + r" \\", r"\midrule"]
        for c in SIG:
            row = []
            for x in cols:
                cp = b0["cap"]["50"][c] if x == "primary" else samp[x][k]["cap50"][c]
                star = "$^{*}$" if (cp["ci90"][0] > 0 or cp["ci90"][1] < 0) else ""
                row.append(f"{f(cp['d'])}{star}")
            L.append(NAME[c] + " & " + " & ".join(row) + r" \\")
        ns = [(b0["n"], b0["orgs"]) if x == "primary" else (samp[x][k]["n"], samp[x][k]["orgs"]) for x in cols]
        L += [r"\midrule", "Repositories / orgs & " + " & ".join(f"{a:,} / {o:,}" for a, o in ns) + r" \\", r"\midrule"]
    L[-1] = r"\bottomrule"; L += [r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_sampsens.tex"), "w").write("\n".join(L) + "\n")
    S["samples"] = {x: {k: {c: (samp[x][k]["cap50"][c]["d"], samp[x][k]["cap50"][c]["ci90"]) for c in SIG} for k in ("era", "agent")} for x in cols if x != "primary"}
    # classification-rule variants
    RV = [("rule_v3", "Prev."), ("rule_v4_d0", "No margin"), ("rule_v4_shared", "Shared"), ("rule_v4_staff3", "Staff 3"),
          ("rule_v4_staff10", "Staff 10"), ("rule_v4_nostaff", "No staff"), ("rule_v4_strict", "Strict")]
    have = [(k, t) for k, t in RV if os.path.exists(os.path.join(V2, f"results_v4_{k}_rules.json"))]
    if have:
        L = [r"\begin{table}[h]", r"\caption{Activity-rule variants: contribution-capped estimates (cap 50; 200 draws; 500 bootstrap replicates, 1,000 for the adopted rule), $d$; $^{*}$: 90\% interval excludes zero. Adopted: the rule of Section~\ref{sec:studentcommits} (Tables~\ref{tab:era} and~\ref{tab:agent}). Prev.: the previous rule. No margin: history defined as any commit before creation. Shared: every shared SHA excluded. Staff 3 and Staff 10: staff-like threshold of three and ten repositories. No staff: no staff-like rule. Strict: owner-matched commits only.}", r"\label{tab:rules}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}",
             r"\begin{tabular}{@{}l " + "r " * (len(have) + 1) + r"@{}}", r"\toprule"]
        R = {k: J(f"results_v4_{k}_rules.json") for k, _ in have}
        for k2, title, b0 in (("era", "Post-ChatGPT $-$ pre, cap 50", era), ("agent", "Agentic era $-$ early post, cap 50", ag)):
            L += [r"\multicolumn{" + str(len(have) + 2) + r"}{@{}l}{" + title + r"} \\", "Signal & Adopted & " + " & ".join(t for _, t in have) + r" \\", r"\midrule"]
            for c in SIG:
                cells = []
                for cp in [b0["cap"]["50"][c]] + [R[k][k2]["cap50"][c] for k, _ in have]:
                    star = "$^{*}$" if (cp["ci90"][0] > 0 or cp["ci90"][1] < 0) else ""; cells.append(f"{f(cp['d'])}{star}")
                L.append(NAME[c] + " & " + " & ".join(cells) + r" \\")
            L += [r"\midrule", "Repositories & " + f"{b0['n']:,} & " + " & ".join(f"{R[k][k2]['n']:,}" for k, _ in have) + r" \\", r"\midrule"]
        L[-1] = r"\bottomrule"; L += [r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_rules.tex"), "w").write("\n".join(L) + "\n")
        S["rules"] = {k: {k2: {c: [R[k][k2]["cap50"][c]["d"], R[k][k2]["cap50"][c]["ci90"], R[k][k2]["ri"][c]["d"]] for c in SIG} for k2 in ("era", "agent")} for k, _ in have}
        S["rules_n"] = {k: {k2: R[k][k2]["n"] for k2 in ("era", "agent")} for k, _ in have}
    # interval construction: bootstrap vs Rubin, stability
    st = J("results_v4_stability.json")["stability"]
    L = [r"\begin{table}[h]", r"\caption{Stability of the contribution-capped estimate (cap 50). $d$: reported estimate (200 draws); $d_{1000}$: 1,000 draws; Rep.: the full procedure repeated with a new random stream (200 draws, 1,000 bootstrap replicates). Bootstrap: 90\% organization-bootstrap interval as reported, and in the repetition. Rubin: interval from the multiple-imputation combining rule, shown for comparison only. $s_{\text{draw}}/s_{\text{boot}}$: between-draw standard deviation relative to the bootstrap standard error.}", r"\label{tab:stability}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}",
         r"\begin{tabular}{@{}l r r r l l l r@{}}", r"\toprule", r"Signal & $d$ & $d_{1000}$ & Rep. & Bootstrap & Bootstrap, rep. & Rubin & $s_{\text{draw}}/s_{\text{boot}}$ \\"]
    S["stability"] = {}
    for k, title, b0 in (("era", "Post-ChatGPT $-$ pre", era), ("agent", "Agentic era $-$ early post", ag)):
        L += [r"\midrule", r"\multicolumn{8}{@{}l}{" + title + r"} \\", r"\midrule"]
        for c in SIG:
            m = b0["cap"]["50"][c]; s = st[k][c]; r_ = m["draw_sd_beta"] / m["boot_se_beta"]
            L.append(f"{NAME[c]} & {f(m['d'])} & {f(s['d_M1000'])} & {f(s['d_rep2'])} & {ci(m['ci90'])} & {ci(s['ci90_rep2'])} & {ci(m['rubin_ci90'])} & {r_:.2f} \\\\")
            S["stability"].setdefault(k, {})[c] = {"d": m["d"], "d1000": s["d_M1000"], "rep2": s["d_rep2"], "ci": m["ci90"], "ci_rep2": s["ci90_rep2"], "rubin": m["rubin_ci90"], "ratio": r_,
                                                    "widen": 1 / math.sqrt(1 - r_ ** 2 * (1 / 5 - 1 / 200)) - 1 if r_ ** 2 * (1 / 5 - 1 / 200) < 1 else None}
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; open(os.path.join(OUT, "tab_stability.tex"), "w").write("\n".join(L) + "\n")
    # trailers
    T = J("results_trailer_v4.json")
    L = [r"\begin{table}", r"\caption{AI-trailer and human-co-author-trailer repositories versus other repositories, first commits 2024 onward, from Equation~\ref{eq:trailer} with organization random intercepts and year fixed effects. Difference is $\beta_{\mathrm{AI}} - \beta_{\mathrm{H}}$ in SD units with 95\% half-width; $p$ uncorrected and Holm-corrected over seven signals. FE: the same difference with organization fixed effects and its wild-cluster-bootstrap $p$ (1,999 replicates).}", r"\label{tab:trailer}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}"]
    for k, title in (("full_frame_ge5", "Full frame"), ("primary", "Primary sample")):
        t = T[k]
        L += [r"\begin{tabular}{@{}l l l l l l@{}}", r"\toprule", r"\multicolumn{6}{@{}l}{" + f"{title} ({t['n']:,} repositories, {t['orgs']} organizations; {t['ai']} with AI trailers, {t['human']} with human co-author trailers only)" + r"} \\",
              r"Signal & AI $d$ ($p$) & Human $d$ ($p$) & Difference & $p$ (Holm) & FE diff.\ ($p_{\text{wild}}$) \\", r"\midrule"]
        for c in SIG:
            v = t[c]; bold = v["diff_p_holm"] < 0.05
            pp = f"{pv(v['diff_p'])} ({pv(v['diff_p_holm']) if v['diff_p_holm'] < 0.995 else '1'})"
            if bold: pp = r"\textbf{" + pp + "}"
            L.append(f"{NAME[c]} & {f(v['ai_d'])} ({pv(v['ai_p'])}) & {f(v['human_d'])} ({pv(v['human_p'])}) & {f(v['diff_d'])} $\\pm$ {1.96*v['diff_se_d']:.2f} & {pp} & {f(v['fe_diff_d'])} ({pv(v['fe_p_wild'])}) \\\\")
        L += [r"\bottomrule", r"\end{tabular}", "", r"\medskip", ""]
    L = L[:-3] + [r"\end{table}"]; open(os.path.join(OUT, "tab_trailer.tex"), "w").write("\n".join(L) + "\n")
    # low-commit
    lo = J("results_v4_low_msg.json")
    S["low"] = lo["low"]; S["msg_subset"] = lo["msg_subset"]
    json.dump(S, open(os.path.join(V2, "results_v4_summary.json"), "w"), indent=1, default=float)
    print("tables written to", OUT); print(json.dumps(S["describe"], indent=0))
