#!/usr/bin/env python3
"""논문 2 v2 — Stage 3c: 원고용 그림·민감도 표
출력: data/v2/fig_yearfe.(png|pdf), fig_contrasts.(png|pdf), fig_registered_vs_raw.(png|pdf), sensitivity_thresholds.md, attrition.md, results_v2_extra.json
"""
import json, os, warnings, numpy as np, pandas as pd, statsmodels.formula.api as smf
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
SIG_FILE = os.environ.get("SIG_FILE", "signals_v2.csv"); SUF = os.environ.get("SUF", "")
r = pd.read_csv(os.path.join(V2, SIG_FILE), dtype={"ai_tool_main": str}, low_memory=False); r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date)
r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
p = r[(r.tier == "A_ghc") & (r.n_commits_human >= 3) & (r.org_test == 0)].copy()
SIG = ["edit_size_log","large_insert_share_200","burst_share_30","samefile_rerun_rate_k3","test_touch_share","time_dispersion","msg_informativeness"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large inserts", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns", "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", "msg_informativeness": "Message distinctiveness"}
X = {}

FITLOG = {"bfgs": 0, "powell": 0, "nm": 0, "all_failed": 0}
def mfit(formula, data):
    """REML random-intercept fit with a validity check (added 2026-10-30). statsmodels' L-BFGS optimizer was found to return
    degenerate fits on these data (infinite log-likelihood, fixed effects equal to the organization fixed-effects solution).
    BFGS is used, with Powell and Nelder-Mead as fallbacks; a fit is accepted only if it converged with a finite
    log-likelihood and finite standard errors. If all three fail, the caller's OLS fallback is used and counted."""
    for meth in ("bfgs", "powell", "nm"):
        try:
            m = smf.mixedlm(formula, data, groups=data["org"]).fit(reml=True, method=meth, maxiter=3000)
            if m.converged and np.isfinite(m.llf) and np.all(np.isfinite(np.asarray(m.bse_fe))):
                FITLOG[meth] += 1; return m
        except Exception:
            pass
    FITLOG["all_failed"] += 1
    raise RuntimeError("mixed model failed with bfgs, powell and nm")
def fit(d, y, label, within=False):
    d = d.dropna(subset=[y, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(d[y].std(ddof=1))
    if within:
        m = smf.ols(f"{y} ~ {label} + log_commits + n_authors_human + C(org)", d).fit(cov_type="cluster", cov_kwds={"groups": d["org"]})
    else:
        try: m = mfit(f"{y} ~ {label} + log_commits + n_authors_human + C(lang_family)", d)
        except Exception: m = smf.ols(f"{y} ~ {label} + log_commits + n_authors_human + C(lang_family)", d).fit(cov_type="cluster", cov_kwds={"groups": d["org"]})
    b, se = float(m.params[label]), float(m.bse[label]); return b/sd, 1.96*se/sd, float(m.pvalues[label]), int(len(d))
# ---- 1. 연도 고정효과(2019 기준) + CI: org RI(전체) vs org 캡 50(강의 동등가중, 5회 재표집 평균)
def yfe_fit(dd):
    out = {}
    for c in SIG:
        x = dd.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        try: m = mfit(f"{c} ~ C(first_year, Treatment(reference=2019)) + log_commits + n_authors_human + C(lang_family)", x)
        except Exception: m = smf.ols(f"{c} ~ C(first_year, Treatment(reference=2019)) + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
        out[c] = {int(float(k.split("T.")[1].rstrip("]"))): (float(v)/sd, float(m.bse[k])/sd) for k, v in m.params.items() if "first_year" in k}; out[c][2019] = (0.0, 0.0)
    return out
d = p[(p.first_dt >= "2017-01-01")].copy(); yfe = yfe_fit(d)
rngy = np.random.default_rng(2026)
def cap_sample(d, cap, seed):
    """org별 최대 cap개 무작위 추출 (pandas 버전 무관)"""
    sh = d.sample(frac=1.0, random_state=int(seed)); return sh[sh.groupby("org").cumcount() < cap]
caps = []
for _ in range(5): caps.append(yfe_fit(cap_sample(d, 50, rngy.integers(1e9))))
yfe_cap = {c: {y: (float(np.mean([cc[c][y][0] for cc in caps if y in cc[c]])), float(np.sqrt(np.mean([cc[c][y][1]**2 for cc in caps if y in cc[c]]) + (1+1/5)*np.var([cc[c][y][0] for cc in caps if y in cc[c]], ddof=1 if sum(y in cc[c] for cc in caps) > 1 else 0)))) for y in yfe[c]} for c in SIG}
X["year_fe"] = {c: {y: (v[0], 1.96*v[1]) for y, v in yfe[c].items()} for c in SIG}; X["year_fe_capped"] = {c: {y: (v[0], 1.96*v[1]) for y, v in yfe_cap[c].items()} for c in SIG}
fig, axes = plt.subplots(4, 2, figsize=(8.5, 10)); axes = axes.ravel()
for i, c in enumerate(SIG):
    ax = axes[i]; ys = sorted(yfe[c])
    ax.axhline(0, color="gray", lw=0.8); ax.axvspan(2022.9, 2025.05, color="#f0f0f0"); ax.axvspan(2025.05, 2026.6, color="#dcdcdc")
    ax.errorbar([y-0.1 for y in ys], [yfe[c][y][0] for y in ys], yerr=[1.96*yfe[c][y][1] for y in ys], fmt="o-", ms=3, lw=1, capsize=2, color="#777777", label="Org. random intercepts")
    ax.errorbar([y+0.1 for y in ys], [yfe_cap[c][y][0] for y in ys], yerr=[1.96*yfe_cap[c][y][1] for y in ys], fmt="D-", ms=3, lw=1, capsize=2, color="black", label="Org. capped at 50")
    ax.set_title(SHORT[c], fontsize=10); ax.set_xticks(range(2017, 2027, 3)); ax.tick_params(labelsize=8)
    if i % 2 == 0: ax.set_ylabel("Effect vs. 2019 (SD units)", fontsize=8)
axes[7].axis("off"); axes[7].text(0, 0.9, "Year-of-first-commit effects relative to 2019,\ncovariates: log commits, authors, language family.\nGray: mixed model with organization random\nintercepts on all repositories. Black: the same\nmodel after capping each organization at 50\nrepositories (mean of 5 random draws).\nLight band: ChatGPT era (2023 to Jan 2025).\nDark band: agentic-tool era (Feb 2025 onward).\nBars: 95% CI.", fontsize=9, va="top")
axes[0].legend(fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_yearfe" + SUF + ".png"), dpi=200); fig.savefig(os.path.join(V2, "fig_yearfe" + SUF + ".pdf"))
# ---- 2. 대비 4종 dot plot: post vs pre (org RI / within-org), agent vs early post (org RI / within-org), AI trailer vs human co-author placebo (2024+, all tiers)
CONTR = {}
dpp = p[p.era.isin(["pre","post"])].copy(); dpp["post"] = (dpp.era == "post").astype(int)
both = dpp.groupby("org").post.agg(lambda s: s.nunique() == 2); dw = dpp[dpp.org.isin(both[both].index)]
da = p[p.first_dt >= "2023-01-01"].copy(); da["agent"] = (da.first_dt >= "2025-02-01").astype(int)
botha = da.groupby("org").agent.agg(lambda s: s.nunique() == 2); daw = da[da.org.isin(botha[botha].index)]
allt = r[(r.n_commits_human >= 5) & (r.org_test == 0) & (r.first_dt >= "2024-01-01")].copy()
tro = allt[allt.trailer == 1][["org"]].drop_duplicates(); dt = allt.merge(tro, on="org")
coo = allt[allt.coauthor_human == 1][["org"]].drop_duplicates(); dc = allt[allt.trailer == 0].merge(coo, on="org")
panels = [("A. Post-ChatGPT vs. pre (org RI)", dpp, "post", False), ("B. Post vs. pre, within 15 orgs", dw, "post", True),
          ("C. Agentic era vs. early post (org RI)", da, "agent", False), ("D. Agentic vs. early post, within 12 orgs", daw, "agent", True),
          ("E. AI trailer vs. org-matched peers (2024+)", dt, "trailer", False), ("F. Placebo: human co-author trailer (2024+)", dc, "coauthor_human", False)]
fig, axes = plt.subplots(3, 2, figsize=(9, 10.5)); axes = axes.ravel()
for i, (title, dd, lab, within) in enumerate(panels):
    ax = axes[i]; CONTR[title] = {}
    for j, c in enumerate(SIG):
        b, e, pv, n = fit(dd, c, lab, within); CONTR[title][c] = {"d": b, "ci95_half": e, "p": pv, "n": n}
        ax.errorbar(b, j, xerr=e, fmt="o", color="black" if pv < .05 else "gray", capsize=3, ms=4)
    ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f3f3f3"); ax.set_yticks(range(len(SIG))); ax.set_yticklabels([SHORT[c] for c in SIG], fontsize=8); ax.invert_yaxis()
    ax.set_title(title + f" (n={len(dd):,})", fontsize=9); ax.set_xlabel("Standardized difference (SD units)", fontsize=8); ax.tick_params(labelsize=8); ax.set_xlim(-0.9, 0.9)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_contrasts" + SUF + ".png"), dpi=200); fig.savefig(os.path.join(V2, "fig_contrasts" + SUF + ".pdf")); X["contrasts"] = CONTR
# ---- 3. 등록 표준화 vs 원척도 진단 (등록 분석표 analysis_table.csv.gz)
at = pd.read_csv(os.path.join(D, "analysis_table.csv.gz")); at = at[at.era.isin(["pre","post"])]
OLD = ["sig1_edit_granularity","sig2_large_paste","sig3_iteration_burst","sig4_error_recovery","sig5_test_engagement","sig6_dispersion","sig7_msg_informativeness","sig8_ai_paste_cooccur"]
OLDN = ["Edit granularity","Large-paste (era P95)","Iteration burst","Error-recovery arcs","Test engagement","Time dispersion","Message informativeness","AI-paste co-occurrence"]
diag = []
for c, nm in zip(OLD, OLDN):
    a, b = at.loc[at.era=="post", c].dropna(), at.loc[at.era=="pre", c].dropna(); sp = np.sqrt(((len(a)-1)*a.var()+(len(b)-1)*b.var())/(len(a)+len(b)-2)); draw = (a.mean()-b.mean())/sp
    za, zb = at.loc[at.era=="post", c+"_z"].dropna(), at.loc[at.era=="pre", c+"_z"].dropna(); dz = za.mean()-zb.mean()
    diag.append({"signal": nm, "raw_d": float(draw), "registered_z_diff": float(dz)})
X["diag_registered"] = diag; X["share_cohort_standardized"] = float((~at.multi_student).mean())
fig, ax = plt.subplots(figsize=(6.5, 3.6)); y = np.arange(len(diag))
ax.barh(y-0.18, [d_["raw_d"] for d_ in diag], height=0.36, color="black", label="Raw scale (Cohen's d)"); ax.barh(y+0.18, [d_["registered_z_diff"] for d_ in diag], height=0.36, color="#bbbbbb", label="Registered within-cohort z (mean difference)")
ax.set_yticks(y); ax.set_yticklabels(OLDN, fontsize=8); ax.invert_yaxis(); ax.axvline(0, color="gray", lw=0.8); ax.legend(fontsize=7, loc="lower right"); ax.set_xlabel("Post minus pre", fontsize=8); ax.tick_params(labelsize=8)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_registered_vs_raw" + SUF + ".png"), dpi=200); fig.savefig(os.path.join(V2, "fig_registered_vs_raw" + SUF + ".pdf"))
# ---- 4. 임계 민감도 (post vs pre, org RI; agent vs early post, org RI)
alts = {"burst_share_15": "Burst <15 min", "burst_share_30": "Burst <30 min (main)", "burst_share_60": "Burst <60 min", "samefile_rerun_rate_k2": "Same-file reruns k=2", "samefile_rerun_rate_k3": "Same-file reruns k=3 (main)", "samefile_rerun_rate_k4": "Same-file reruns k=4",
        "large_insert_share_200": "Large inserts >=200 (main)", "large_insert_share_500": "Large inserts >=500", "max_insert_log": "Log max single insert", "edit_size_log": "Edit size (main)", "msg_len_log": "Log median message length"}
S = []
for c, nm in alts.items():
    b1, e1, p1, n1 = fit(dpp, c, "post"); b2, e2, p2, n2 = fit(da, c, "agent"); S.append((nm, b1, e1, p1, b2, e2, p2))
X["sensitivity_thresholds"] = S
L = ["# 임계 민감도 (org RI; d ± 95% 반폭)", "", "| 변형 | post−pre d | p | agent−early d | p |", "|---|---|---|---|---|"] + [f"| {s[0]} | {s[1]:+.3f} ± {s[2]:.3f} | {s[3]:.2g} | {s[4]:+.3f} ± {s[5]:.3f} | {s[6]:.2g} |" for s in S]
# ---- 5. attrition
e = pd.read_csv(os.path.join(V2, "sample_flags.csv"))
L += ["", "# 표본 흐름", f"- 열거(2026-08-05): 70,495", f"- 클론·로그 파싱: {len(e):,}", f"- GHC 검증(desc/name): {int(e.ghc_verified.sum()):,}",
      f"- 사람 저자 ≥1 ∧ 사람 커밋 ≥3: {int(((r.tier=='A_ghc')&(r.n_commits_human>=3)).sum()):,}", f"- 테스트/데모 org 제외: {len(p):,} (pre {int((p.era=='pre').sum()):,} / post {int((p.era=='post').sum()):,} / buffer {int((p.era=='buffer').sum()):,})",
      f"- 주 신호 7종 중 ≥5 정의: {int((p.n_main_defined>=5).sum()):,}", f"- 비-GHC 'classroom' 명칭 저장소(사람 커밋 ≥5, 테스트 org 제외): {int(((r.tier!='A_ghc')&(r.n_commits_human>=5)&(r.org_test==0)).sum()):,} (보조 분석 전용)"]
open(os.path.join(V2, "sensitivity_thresholds" + SUF + ".md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
X["fit_log"] = dict(FITLOG)
json.dump(X, open(os.path.join(V2, "results_v2_extra" + SUF + ".json"), "w"), indent=1, default=str)
print("\ndiag:", json.dumps(diag, indent=0)); print("share cohort-standardized:", X["share_cohort_standardized"])
print("\ncontrasts:"); [print(" ", t, {SHORT[c]: round(v["d"], 2) for c, v in cc.items()}) for t, cc in CONTR.items()]
