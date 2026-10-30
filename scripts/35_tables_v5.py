#!/usr/bin/env python3
"""논문 2 — 7차 작업지시서 판(v5) 원고 표 생성. 결과 JSON에서 직접 읽는다(숫자를 옮겨 적지 않음).
본문: tab_main (두 대비의 핵심 비교, 여섯 신호). 부록: 상세 비교표, 생성 방식 제한 비교, 원단위, 임계값, 표본, 규칙, 안정성,
메시지 차별성(보충), 트레일러(보충).
메시지 차별성은 분류된 커밋이 아니라 모든 비봇 커밋 메시지로 계산된 값이라 본문 비교에서 빼고 보충 결과로만 보고한다.
출력: <toce_v2>/tables5/*.tex"""
import os, json, math
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
_H = os.path.dirname(os.path.abspath(__file__)); _T = next((p for p in (os.path.join(_H, "..", "toce_v2"), os.path.join(_H, "..", "..", "toce_v2")) if os.path.isdir(p)), os.path.join(_H, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "tables5")); os.makedirs(OUT, exist_ok=True)
SIG6 = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion"]
MSG = "msg_informativeness"
NAME = {"edit_size_log": "Edit size", "large_insert_share_200": "Large-insert share", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns",
        "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", MSG: "Message distinctiveness",
        "burst_share_15": "Burst share, 15-minute window", "burst_share_60": "Burst share, 60-minute window", "samefile_rerun_rate_k2": "Same-file reruns, run length 2",
        "samefile_rerun_rate_k4": "Same-file reruns, run length 4", "large_insert_share_500": "Large-insert share, $\\geq 500$ lines", "max_insert_log": "Log of largest single insertion",
        "msg_len_log": "Log median message length"}
def J(n): return json.load(open(os.path.join(V2, n)))
def f(x, k=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)): return "--"
    t = f"{x:+.{k}f}"
    if float(t) == 0: t = f"{0:.{k}f}"
    return "$" + t + "$"
def _end(x, k):
    """Interval endpoint; an endpoint that rounds to zero is printed with one more decimal so that its side of zero is visible."""
    t = f"{x:+.{k}f}"
    return f"{x:+.{k + 1}f}" if float(t) == 0 else t
def ci(a, k=2): return f"$[{_end(a[0], k)}, {_end(a[1], k)}]$"
def pv(p):
    if p < 0.001: return "$<$.001"
    return f"{p:.3f}".lstrip("0") if p < 0.995 else ".99"
def write(name, lines): open(os.path.join(OUT, name + ".tex"), "w").write("\n".join(lines) + "\n")

def within_cell(b, ww, c):
    """Within-organization estimate with its 90% interval; if the test inversion found no bound, the searched range is given."""
    w = b["within"][c]
    if not w["ci_grid_edge"]: return f"{f(w['d'])} {ci(w['ci90_d'])}"
    g = ww[c]["grid_d"]
    if ww[c]["ci_grid_edge"]: return f"{f(w['d'])}, none in $[{g[0]:+.1f}, {g[1]:+.1f}]$"
    return f"{f(w['d'])} {ci(ww[c]['ci90_d'])}"

if __name__ == "__main__":
    era = J("results_v4_era.json")["era"]; ag = J("results_v4_agent.json")["agent"]; d = J("results_v4_descriptives.json")
    WW = J("results_v4_within_wide.json")["within_wide"]
    # ---- main table: both contrasts, six signals ----
    L = [r"\begin{table}", r"\caption{Era comparisons on the six signals computed from classified commits, in standardized units ($d$). All repositories: raw difference in means. Capped: random-intercept model fitted with each organization limited to 25, 50, and 100 repositories (mean of 200 draws), with the organization-bootstrap 90\% interval at 50. RI: organization random intercepts on all repositories, and in parentheses the same estimate without the largest organization. Within: organization fixed effects on the organizations observed in both periods, with the 90\% interval from inverting a wild cluster bootstrap test; where the inversion found no bound, the searched range is given. Full results in Appendix~\ref{app:sens}.}",
         r"\label{tab:main}", r"\scriptsize", r"\setlength{\tabcolsep}{2pt}", r"\begin{tabular}{@{}l r c c r l@{}}", r"\toprule",
         r"Signal & All & Capped & Cap 50, & RI & Within \\", r" & repos. & 25 / 50 / 100 & 90\% CI & (w/o largest) & [90\% CI] \\"]
    S = {}
    for k, b, title in (("era", era, f"A. Post-ChatGPT minus pre ({era['n']:,} repositories, {era['orgs']} organizations; within: {d['spanning_orgs']} organizations)"),
                        ("agent", ag, f"B. Agentic era minus early post ({ag['n']:,} repositories, {ag['orgs']} organizations; within: {d['agent_spanning_orgs']} organizations)")):
        L += [r"\midrule", r"\multicolumn{6}{@{}l}{" + title + r"} \\", r"\midrule"]
        for c in SIG6:
            cp = b["cap"]
            L.append(f"{NAME[c]} & {f(b['raw'][c])} & {f(cp['25'][c]['d'])} / {f(cp['50'][c]['d'])} / {f(cp['100'][c]['d'])} & {ci(cp['50'][c]['ci90'])} & {f(b['ri'][c]['d'])} ({f(b['loo'][c][0])}) & {within_cell(b, WW[k], c)} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_main", L)
    # ---- appendix: full comparison tables ----
    def full_table(name, b, ww, caption, label, spanning, sigs):
        L = [r"\begin{table}[h]", r"\caption{" + caption + "}", r"\label{" + label + "}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}",
             r"\begin{tabular}{@{}l r r c c c r@{}}", r"\toprule", r"Signal & Raw & Cov. & Cap 25 & Cap 50 & Cap 100 & RI ($p$) \\", r"\midrule"]
        for c in sigs:
            cp = b["cap"]
            L.append(f"{NAME[c]} & {f(b['raw'][c])} & {f(b['raw_cov'][c]['d'])} & {f(cp['25'][c]['d'])} & {f(cp['50'][c]['d'])} & {f(cp['100'][c]['d'])} & {f(b['ri'][c]['d'])} ({pv(b['ri'][c]['p'])}) \\\\")
            L.append(f" & & & {ci(cp['25'][c]['ci90'])} & {ci(cp['50'][c]['ci90'])} & {ci(cp['100'][c]['ci90'])} & \\\\[2pt]")
        L += [r"\bottomrule", r"\end{tabular}", "", r"\medskip", "", r"\begin{tabular}{@{}l l r l r l@{}}", r"\toprule",
              r"Signal & LOO min/max & Drop 5 & Within [90\% CI] & $p_{\text{wild}}$ & Paired median, $+/" + str(spanning) + r"$ \\", r"\midrule"]
        for c in sigs:
            lo = b["loo"][c]; pr = b["paired"][c]
            L.append(f"{NAME[c]} & {f(min(lo))}/{f(max(lo))} & {f(b['drop_top5'][c])} & {within_cell(b, ww, c)} & {pv(b['within'][c]['p_wild'])} & {f(pr['median_d'])}, {pr['n_positive']}" + (f" of {pr['n_orgs']}" if pr["n_orgs"] != spanning else "") + r" \\")
        L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write(name, L)
    full_table("tab_era_full", era, WW["era"], f"Post-ChatGPT minus pre-ChatGPT, full results ({era['n']:,} repositories, {era['orgs']} organizations; {era['n_pre']:,} pre, {era['n_post']:,} post). Cov.: all repositories with the covariates and no organization term. RI ($p$): organization random intercepts with the uncorrected $p$-value (the text reports Holm-corrected values where significance is claimed). Capped estimates with their 90\\% organization-bootstrap intervals (1,000 replicates) on the second line. Lower part: random-intercept estimates leaving out each of the ten largest organizations (minimum and maximum) and the five largest together; within-organization comparison on the {d['spanning_orgs']} organizations observed in both eras with its wild-bootstrap $p$; organization-level paired median and the number of organizations in which the post mean is higher.", "tab:era", d["spanning_orgs"], SIG6)
    full_table("tab_agent_full", ag, WW["agent"], f"Agentic era (February 2025 onward) minus early post (January 2023 to January 2025), full results ({ag['n']:,} repositories, {ag['orgs']} organizations; {ag['n_pre']:,} early post, {ag['n_post']:,} agentic). Columns as in Table~\\ref{{tab:era}}; within-organization and paired comparisons on the {d['agent_spanning_orgs']} organizations observed in both periods ({d['agent_spanning_repos']} repositories, {d['agent_spanning_sizes'][0]} in one organization); the test inversion found no bound within the searched range (50 bootstrap standard errors on each side of the estimate).", "tab:agent", d["agent_spanning_orgs"], SIG6)
    # ---- appendix: restricted comparisons ----
    L = [r"\begin{table}[h]", r"\caption{Comparisons restricted with respect to the platform change (Section~\ref{sec:restricted}). A and B: post-ChatGPT minus pre-ChatGPT, keeping post-era repositories created before the general release of fork-based creation (July 1, 2024) or before its beta (January 1, 2024). C: agentic era minus early post, keeping repositories without a Classroom-bot root commit that adds 20 or more lines. Capped estimates with 90\% organization-bootstrap intervals (1,000 replicates).}",
         r"\label{tab:regime}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}", r"\begin{tabular}{@{}l r r c c c r@{}}", r"\toprule", r"Signal & Raw & Cov. & Cap 25 & Cap 50 & Cap 100 & RI \\"]
    S["regime"] = {}
    for part, title in (("era_preswitch", "A. Post era created before July 2024"), ("era_prebeta", "B. Post era created before January 2024"), ("agent_nostarter", "C. Agentic era, no Classroom-bot starter commit")):
        b = J(f"results_v4_{part}.json")[part]
        L += [r"\midrule", r"\multicolumn{7}{@{}l}{" + title + f" ({b['n']:,} repositories, {b['orgs']} organizations; {b['n_pre']:,} and {b['n_post']:,})" + r"} \\", r"\midrule"]
        for c in SIG6:
            cp = b["cap"]
            L.append(f"{NAME[c]} & {f(b['raw'][c])} & {f(b['raw_cov'][c]['d'])} & {f(cp['25'][c]['d'])} & {f(cp['50'][c]['d'])} & {f(cp['100'][c]['d'])} & {f(b['ri'][c]['d'])} \\\\")
            L.append(f" & & & {ci(cp['25'][c]['ci90'])} & {ci(cp['50'][c]['ci90'])} & {ci(cp['100'][c]['ci90'])} & \\\\[2pt]")
        S["regime"][part] = {"n": b["n"], "orgs": b["orgs"], "n_pre": b["n_pre"], "n_post": b["n_post"]}
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_regime", L)
    # ---- appendix: natural units ----
    def natural(b, c):
        cp = b["cap"]["50"][c]; be, lo, hi = cp["beta"], cp["ci90_beta"][0], cp["ci90_beta"][1]; m = b["means"][c]
        if c == "edit_size_log": return (f"{100*(math.exp(be)-1):+.0f}\\%", f"$[{100*(math.exp(lo)-1):+.0f}, {100*(math.exp(hi)-1):+.0f}]$", f"{math.expm1(m['pre']):.0f} / {math.expm1(m['post']):.0f} lines")
        if c in ("large_insert_share_200", "burst_share_30", "test_touch_share"): return (f"{100*be:+.1f} pp", f"$[{100*lo:+.1f}, {100*hi:+.1f}]$", f"{100*m['pre']:.1f}\\% / {100*m['post']:.1f}\\%")
        return (f"{be:+.3f}", f"$[{lo:+.3f}, {hi:+.3f}]$", f"{m['pre']:.3f} / {m['post']:.3f}")
    L = [r"\begin{table}[h]", r"\caption{Capped estimates (cap 50) in natural units, from the same fits and bootstrap replicates as the standardized estimates, with unadjusted means of the two periods. Edit size: percent change in the median lines per commit; means are geometric means of the per-repository median.}", r"\label{tab:natural}",
         r"\scriptsize", r"\setlength{\tabcolsep}{3pt}", r"\begin{tabular}{@{}l l l l l l l@{}}", r"\toprule", r" & \multicolumn{3}{l}{Post $-$ pre} & \multicolumn{3}{l}{Agentic $-$ early post} \\", r"Signal & Cap 50 & [90\% CI] & Means & Cap 50 & [90\% CI] & Means \\", r"\midrule"]
    for c in SIG6:
        a = natural(era, c); g = natural(ag, c); L.append(f"{NAME[c]} & {a[0]} & {a[1]} & {a[2]} & {g[0]} & {g[1]} & {g[2]} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_natural", L)
    # ---- appendix: thresholds ----
    E = J("results_v4_extra.json")["extra"]
    L = [r"\begin{table}[h]", r"\caption{Threshold and measure variants: organization random intercepts (RI, $d \pm$ 95\% half-width) and capped estimates at 50 (200 draws; 90\% organization-bootstrap interval, 500 replicates, 1,000 for the main rows).}", r"\label{tab:sens}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{@{}l l l l l@{}}", r"\toprule", r" & \multicolumn{2}{l}{Post $-$ pre} & \multicolumn{2}{l}{Agentic $-$ early post} \\", r"Variant & RI & Cap 50 [90\% CI] & RI & Cap 50 [90\% CI] \\", r"\midrule"]
    for c in ["burst_share_15", "burst_share_30", "burst_share_60", "samefile_rerun_rate_k2", "samefile_rerun_rate_k3", "samefile_rerun_rate_k4", "large_insert_share_200", "large_insert_share_500", "max_insert_log", "edit_size_log"]:
        cells = []
        for k, b in (("era", era), ("agent", ag)):
            ri, cp = (E[k][c]["ri"], E[k][c]["cap50"]) if c in E[k] else (b["ri"][c], b["cap"]["50"][c])
            cells.append(f"{f(ri['d'])} $\\pm$ {1.96*ri['se_d']:.2f} & {f(cp['d'])} {ci(cp['ci90'])}")
        L.append(f"{NAME[c]}{' (main)' if c in SIG6 else ''} & {cells[0]} & {cells[1]} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_sens", L)
    # ---- appendix: samples ----
    samp = {}
    for nm in ("ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3"): samp[nm] = J(f"results_v4_samples_{nm}.json")["samples"][nm]
    cols = ["primary", "ge5", "test_orgs_kept", "copies_kept", "tierAB", "full_frame_ge3"]
    HD = {"primary": "Primary", "ge5": "$\\geq 5$ commits", "test_orgs_kept": "Test orgs kept", "copies_kept": "Copies kept", "tierAB": "Tier A+B", "full_frame_ge3": "Full frame"}
    L = [r"\begin{table}[h]", r"\caption{Sample variants of the capped estimate (cap 50; 200 draws; 500 organization-bootstrap replicates, 1,000 for the primary sample), $d$; $^{*}$: 90\% interval excludes zero.}", r"\label{tab:sampsens}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}", r"\begin{tabular}{@{}l " + "r " * len(cols) + r"@{}}", r"\toprule"]
    for k, title, b0 in (("era", "Post-ChatGPT $-$ pre", era), ("agent", "Agentic era $-$ early post", ag)):
        L += [r"\multicolumn{" + str(len(cols) + 1) + r"}{@{}l}{" + title + r"} \\", "Signal & " + " & ".join(HD[x] for x in cols) + r" \\", r"\midrule"]
        for c in SIG6:
            row = []
            for x in cols:
                cp = b0["cap"]["50"][c] if x == "primary" else samp[x][k]["cap50"][c]
                row.append(f"{f(cp['d'])}{'$^{*}$' if (cp['ci90'][0] > 0 or cp['ci90'][1] < 0) else ''}")
            L.append(NAME[c] + " & " + " & ".join(row) + r" \\")
        ns = [(b0["n"], b0["orgs"]) if x == "primary" else (samp[x][k]["n"], samp[x][k]["orgs"]) for x in cols]
        L += [r"\midrule", "Repositories / orgs & " + " & ".join(f"{a:,} / {o:,}" for a, o in ns) + r" \\", r"\midrule"]
    L[-1] = r"\bottomrule"; L += [r"\end{tabular}", r"\end{table}"]; write("tab_sampsens", L)
    # ---- appendix: rules ----
    RV = [("rule_v3", "Prev."), ("rule_v4_d0", "No margin"), ("rule_v4_shared", "Shared"), ("rule_v4_staff3", "Staff 3"), ("rule_v4_staff10", "Staff 10"), ("rule_v4_nostaff", "No staff"), ("rule_v4_strict", "Strict")]
    R = {k: J(f"results_v4_{k}_rules.json") for k, _ in RV}
    L = [r"\begin{table}[h]", r"\caption{Activity-rule variants: capped estimates (cap 50; 200 draws; 500 bootstrap replicates, 1,000 for the adopted rule), $d$; $^{*}$: 90\% interval excludes zero. Prev.: the previous rule. No margin: history defined as any commit before creation. Shared: every shared SHA excluded. Staff 3 and Staff 10: staff-like threshold of three and ten repositories. No staff: no staff-like rule. Strict: owner-matched commits only.}", r"\label{tab:rules}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}", r"\begin{tabular}{@{}l " + "r " * (len(RV) + 1) + r"@{}}", r"\toprule"]
    for k2, title, b0 in (("era", "Post-ChatGPT $-$ pre", era), ("agent", "Agentic era $-$ early post", ag)):
        L += [r"\multicolumn{" + str(len(RV) + 2) + r"}{@{}l}{" + title + r"} \\", "Signal & Adopted & " + " & ".join(t for _, t in RV) + r" \\", r"\midrule"]
        for c in SIG6:
            cells = [f"{f(cp['d'])}{'$^{*}$' if (cp['ci90'][0] > 0 or cp['ci90'][1] < 0) else ''}" for cp in [b0["cap"]["50"][c]] + [R[k][k2]["cap50"][c] for k, _ in RV]]
            L.append(NAME[c] + " & " + " & ".join(cells) + r" \\")
        L += [r"\midrule", "Repositories & " + f"{b0['n']:,} & " + " & ".join(f"{R[k][k2]['n']:,}" for k, _ in RV) + r" \\", r"\midrule"]
    L[-1] = r"\bottomrule"; L += [r"\end{tabular}", r"\end{table}"]; write("tab_rules", L)
    # ---- appendix: stability ----
    st = J("results_v4_stability.json")["stability"]
    L = [r"\begin{table}[h]", r"\caption{Stability of the capped estimate (cap 50): reported estimate (200 draws), estimate from 1,000 draws, and a repetition of the whole procedure with a new random stream; 90\% organization-bootstrap intervals as reported and in the repetition; for comparison only, the interval from the multiple-imputation combining rule; and the between-draw standard deviation relative to the bootstrap standard error.}", r"\label{tab:stability}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}",
         r"\begin{tabular}{@{}l r r r l l l r@{}}", r"\toprule", r"Signal & $d$ & $d_{1000}$ & Rep. & Bootstrap & Bootstrap, rep. & Rubin & $s_{\text{draw}}/s_{\text{boot}}$ \\"]
    for k, title, b0 in (("era", "Post-ChatGPT $-$ pre", era), ("agent", "Agentic era $-$ early post", ag)):
        L += [r"\midrule", r"\multicolumn{8}{@{}l}{" + title + r"} \\", r"\midrule"]
        for c in SIG6:
            m = b0["cap"]["50"][c]; s = st[k][c]
            L.append(f"{NAME[c]} & {f(m['d'])} & {f(s['d_M1000'])} & {f(s['d_rep2'])} & {ci(m['ci90'])} & {ci(s['ci90_rep2'])} & {ci(m['rubin_ci90'])} & {m['draw_sd_beta']/m['boot_se_beta']:.2f} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_stability", L)
    # ---- supplementary: message distinctiveness ----
    lm = J("results_v4_low_msg.json")["msg_subset"]
    L = [r"\begin{table}[h]", r"\caption{Supplementary: message distinctiveness, computed on all non-bot commit messages (not only classified commits), $d$, with 90\% intervals (organization bootstrap for the capped estimates; test inversion for the within-organization estimates, ``none'' where no bound was found). Subset: the repositories in which every non-bot commit is classified, so that the messages coincide with the classified commits' messages; this restriction also changes the sample.}", r"\label{tab:msg}", r"\scriptsize", r"\setlength{\tabcolsep}{2.5pt}",
         r"\begin{tabular}{@{}p{2.6cm} r c c c r c@{}}", r"\toprule", r"Contrast and sample & Raw & Cap 25 & Cap 50 & Cap 100 & RI & Within \\", r"\midrule"]
    for k, b, t in (("era", era, "Post $-$ pre, primary"), ("agent", ag, "Agentic $-$ early post, primary")):
        cp = b["cap"]; w = b["within"][MSG]
        wtxt = ci(w["ci90_d"]) if not w["ci_grid_edge"] else "none"
        L.append(f"{t} & {f(b['raw'][MSG])} & {f(cp['25'][MSG]['d'])} & {f(cp['50'][MSG]['d'])} & {f(cp['100'][MSG]['d'])} & {f(b['ri'][MSG]['d'])} & {f(w['d'])} \\\\")
        L.append(f" & & {ci(cp['25'][MSG]['ci90'])} & {ci(cp['50'][MSG]['ci90'])} & {ci(cp['100'][MSG]['ci90'])} & & {wtxt} \\\\[2pt]")
    for k, t in (("era", "Post $-$ pre, subset"), ("agent", "Agentic $-$ early post, subset")):
        v = lm[k]
        L.append(f"{t} ({v['n']:,}) & {f(v['raw'])} & & {f(v['cap50']['d'])} & & {f(v['ri']['d'])} & \\\\")
        L.append(f" & & & {ci(v['cap50']['ci90'])} & & & \\\\[2pt]")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]; write("tab_msg", L)
    # ---- supplementary: trailers ----
    T = J("results_trailer_v4.json"); SIG7 = SIG6 + [MSG]
    L = [r"\begin{table}[h]", r"\caption{Supplementary: AI-trailer and human-co-author-trailer repositories versus other repositories, first commits 2024 onward, from Equation~\ref{eq:trailer} with organization random intercepts and year fixed effects; full frame: repositories with five or more classified commits; primary sample: three or more. Difference: $\beta_{\mathrm{AI}} - \beta_{\mathrm{H}}$ in SD units with 95\% half-width; $p$ uncorrected and Holm-corrected over the signals. FE: the same difference with organization fixed effects and its wild-cluster-bootstrap $p$ (1,999 replicates).}", r"\label{tab:trailer}", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}"]
    for kk, title in (("full_frame_ge5", "Full frame"), ("primary", "Primary sample")):
        t = T[kk]
        L += [r"\begin{tabular}{@{}l l l l l l@{}}", r"\toprule", r"\multicolumn{6}{@{}l}{" + f"{title} ({t['n']:,} repositories, {t['orgs']} organizations; {t['ai']} with AI trailers, {t['human']} with human co-author trailers only)" + r"} \\",
              r"Signal & AI $d$ ($p$) & Human $d$ ($p$) & Difference & $p$ (Holm) & FE diff.\ ($p_{\text{wild}}$) \\", r"\midrule"]
        for c in SIG7:
            v = t[c]
            L.append(f"{NAME[c]} & {f(v['ai_d'])} ({pv(v['ai_p'])}) & {f(v['human_d'])} ({pv(v['human_p'])}) & {f(v['diff_d'])} $\\pm$ {1.96*v['diff_se_d']:.2f} & {pv(v['diff_p'])} ({pv(v['diff_p_holm']) if v['diff_p_holm'] < 0.995 else '1'}) & {f(v['fe_diff_d'])} ({pv(v['fe_p_wild'])}) \\\\")
        L += [r"\bottomrule", r"\end{tabular}", "", r"\medskip", ""]
    L = L[:-3] + [r"\end{table}"]; write("tab_trailer", L)
    print("tables written to", OUT)
