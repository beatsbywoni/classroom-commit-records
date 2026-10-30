#!/usr/bin/env python3
"""논문 2 v2 — Stage 3d: 구성(composition)·지배 클러스터 점검과 최종 추정
 (1) 세 추정량 비교: raw / org RI / org-capped(강의 동등가중, cap=50, 40회 재표집 평균·분위)
 (2) leave-one-organization-out (상위 10 org) 및 상위 5 제외
 (3) within-org 고정효과 + wild cluster bootstrap(Rademacher, 1999회)
 (4) 양 era에 걸친 org의 org 단위 짝지은 차이
 (5) 에이전트기 대비 동일 절차
 (6) AI trailer vs 사람 co-author 차이 검정(동일 모형 내 두 지표, Wald)
 (7) 신호별 등가 판정(캡 추정의 90% 구간 vs ±0.10)
출력: data/v2/results_composition.json, results_composition.md, fig_composition.pdf/png
"""
import json, os, warnings, numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
SIG_FILE = os.environ.get("SIG_FILE", "signals_v2.csv"); SUF = os.environ.get("SUF", "")
r = pd.read_csv(os.path.join(V2, SIG_FILE), dtype={"ai_tool_main": str}, low_memory=False)
r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date); r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
p = r[(r.tier == "A_ghc") & (r.n_commits_human >= 3) & (r.org_test == 0)].copy()
SIG = ["edit_size_log","large_insert_share_200","burst_share_30","samefile_rerun_rate_k3","test_touch_share","time_dispersion","msg_informativeness"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large inserts", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns", "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", "msg_informativeness": "Message distinctiveness"}
rng = np.random.default_rng(20261030); R = {}

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
def cap_sample(d, cap, seed):
    """org별 최대 cap개 무작위 추출 (pandas 버전 무관)"""
    sh = d.sample(frac=1.0, random_state=int(seed)); return sh[sh.groupby("org").cumcount() < cap]

def ri(d, c, label):
    x = d.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    try: m = mfit(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x)
    except Exception: m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    b, se = float(m.params[label]), float(m.bse[label]); return {"d": b/sd, "se_d": se/sd, "p": float(m.pvalues[label]), "n": int(len(x))}
def raw_d(d, c, label):
    a, b = d.loc[d[label]==1, c].dropna(), d.loc[d[label]==0, c].dropna(); sp = np.sqrt(((len(a)-1)*a.var()+(len(b)-1)*b.var())/(len(a)+len(b)-2)); return float((a.mean()-b.mean())/sp)
def capped(d, label, cap=50, reps=40):
    out = {c: [] for c in SIG}; ns = []
    for _ in range(reps):
        s = cap_sample(d, cap, rng.integers(1e9)); ns.append(len(s))
        for c in SIG:
            x = ri(s, c, label); out[c].append((x["d"], x["se_d"]))
    res = {}
    for c in SIG:
        ds = np.array([v[0] for v in out[c]]); ses = np.array([v[1] for v in out[c]])
        # Rubin-style 결합: 평균 d, 총분산 = 평균 SE² + (1+1/m)·재표집 분산
        tv = ses.mean()**2 + (1 + 1/reps) * ds.var(ddof=1); se = float(np.sqrt(tv))
        res[c] = {"d": float(ds.mean()), "se_d": se, "ci90": [float(ds.mean()-1.645*se), float(ds.mean()+1.645*se)], "ci95": [float(ds.mean()-1.96*se), float(ds.mean()+1.96*se)],
                  "p": float(2*(1-stats.norm.cdf(abs(ds.mean()/se)))), "equiv_010": bool(ds.mean()-1.645*se > -0.10 and ds.mean()+1.645*se < 0.10)}
    return res, int(np.mean(ns))
def wild(d, label, c, B=1999):
    x = d.dropna(subset=[c]).copy(); sd = float(x[c].std(ddof=1))
    m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family) + C(org)", x).fit(); b = float(m.params[label])
    m0 = smf.ols(f"{c} ~ log_commits + n_authors_human + C(lang_family) + C(org)", x).fit(); res = m0.resid.to_numpy(); fit0 = m0.fittedvalues.to_numpy()
    g = pd.factorize(x.org)[0]; G = g.max()+1; X = m.model.exog; XtXi = np.linalg.pinv(X.T @ X); j = list(m.params.index).index(label); cnt = 0
    for _ in range(B):
        w = rng.choice([-1, 1], size=G)[g]; bb = (XtXi @ X.T @ (fit0 + res*w))[j]
        if abs(bb) >= abs(b): cnt += 1
    return {"d": b/sd, "p_wild": (cnt+1)/(B+1), "n": int(len(x)), "orgs": int(G)}
def org_paired(d, label):
    both = d.groupby("org")[label].agg(lambda s: s.nunique() == 2); sp = d[d.org.isin(both[both].index)]
    om = sp.groupby(["org", label])[SIG].mean().unstack(label); out = {"orgs": int(sp.org.nunique()), "n": int(len(sp)), "org_sizes": sp.groupby("org").size().sort_values(ascending=False).tolist()}
    for c in SIG:
        diff = (om[(c, 1)] - om[(c, 0)]).dropna(); sd = float(d[c].std(ddof=1))
        out[c] = {"median_d": float(diff.median()/sd), "mean_d": float(diff.mean()/sd), "n_positive": int((diff > 0).sum()), "n_orgs": int(len(diff)), "sign_test_p": float(stats.binomtest(int((diff > 0).sum()), len(diff)).pvalue)}
    return out
def block(d, label, name):
    out = {"n": int(len(d)), "n1": int(d[label].sum()), "orgs": int(d.org.nunique())}
    out["raw"] = {c: raw_d(d, c, label) for c in SIG}; out["org_ri"] = {c: ri(d, c, label) for c in SIG}
    out["capped"], out["capped_n"] = capped(d, label)
    top = d.groupby("org").size().sort_values(ascending=False).head(10); out["top_orgs_sizes"] = top.tolist()
    out["loo"] = {c: [ri(d[d.org != o], c, label)["d"] for o in top.index] for c in SIG}
    out["drop_top5"] = {c: ri(d[~d.org.isin(top.index[:5])], c, label)["d"] for c in SIG}
    both = d.groupby("org")[label].agg(lambda s: s.nunique() == 2); dw = d[d.org.isin(both[both].index)]
    out["within"] = {c: wild(dw, label, c) for c in SIG}; out["within_org_sizes"] = dw.groupby("org").size().sort_values(ascending=False).tolist()
    out["paired"] = org_paired(d, label); R[name] = out
d = p[p.era.isin(["pre", "post"])].copy(); d["post"] = (d.era == "post").astype(int); block(d, "post", "era")
da = p[p.first_dt >= "2023-01-01"].copy(); da["agent"] = (da.first_dt >= "2025-02-01").astype(int); block(da, "agent", "agent")
# (6) trailer: AI vs human co-author within one model, 2024+, full frame ≥5 and primary
R["trailer"] = {}
for name, base in [("all_tiers_ge5", r[(r.n_commits_human >= 5) & (r.org_test == 0)]), ("primary", p)]:
    w = base[base.first_dt >= "2024-01-01"].copy(); orgs = set(w[w.trailer == 1].org) | set(w[w.coauthor_human == 1].org); w = w[w.org.isin(orgs)]
    out = {"n": int(len(w)), "ai": int(w.trailer.sum()), "human": int(w.coauthor_human.sum()), "orgs": int(w.org.nunique()), "tools": w.loc[w.trailer == 1, "ai_tool_main"].value_counts().to_dict()}
    for c in SIG:
        x = w.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        try:
            m = mfit(f"{c} ~ trailer + coauthor_human + log_commits + n_authors_human + C(lang_family)", x)
            names = list(m.fe_params.index); V = np.asarray(m.cov_params())[:len(names), :len(names)]; pa = m.fe_params
        except Exception:
            m = smf.ols(f"{c} ~ trailer + coauthor_human + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
            names = list(m.params.index); V = np.asarray(m.cov_params()); pa = m.params
        i, j = names.index("trailer"), names.index("coauthor_human"); diff = float(pa["trailer"] - pa["coauthor_human"]); se = float(np.sqrt(V[i, i] + V[j, j] - 2*V[i, j]))
        out[c] = {"ai_d": float(pa["trailer"]/sd), "ai_se": float(np.sqrt(V[i, i])/sd), "ai_p": float(m.pvalues["trailer"]), "human_d": float(pa["coauthor_human"]/sd), "human_se": float(np.sqrt(V[j, j])/sd), "human_p": float(m.pvalues["coauthor_human"]),
                  "diff_d": diff/sd, "diff_se": se/sd, "diff_p": float(2*(1-stats.norm.cdf(abs(diff/se)))), "n": int(len(x))}
    # Holm on diff p
    ps = {c: out[c]["diff_p"] for c in SIG}; keys = sorted(ps, key=lambda k: ps[k]); prev = 0
    for k, c in enumerate(keys): v = min(1.0, ps[c]*(len(keys)-k)); prev = max(prev, v); out[c]["diff_p_holm"] = prev
    R["trailer"][name] = out
R["fit_log"] = dict(FITLOG)
json.dump(R, open(os.path.join(V2, "results_composition" + SUF + ".json"), "w"), indent=1, default=str)
# ---- 보고서
L = ["# 구성·지배 클러스터 점검 결과 (Stage 3d)", ""]
for name, title in [("era", "post vs pre"), ("agent", "agentic (2025-02+) vs early post")]:
    b = R[name]; L.append(f"## {title}: n={b['n']}, label1={b['n1']}, orgs={b['orgs']}; capped n≈{b['capped_n']}; top-10 org sizes {b['top_orgs_sizes']}")
    L.append("| 신호 | raw d | org-RI d (p) | capped d [90% CI] equiv | LOO min..max (top10) | drop top5 | within-org d (wild p; orgs) | paired: median d, +/n (sign p) |"); L.append("|---|---|---|---|---|---|---|---|")
    for c in SIG:
        cp = b["capped"][c]; w = b["within"][c]; pr = b["paired"][c]
        L.append(f"| {SHORT[c]} | {b['raw'][c]:+.2f} | {b['org_ri'][c]['d']:+.2f} ({b['org_ri'][c]['p']:.2g}) | {cp['d']:+.2f} [{cp['ci90'][0]:+.2f}, {cp['ci90'][1]:+.2f}] {'EQ' if cp['equiv_010'] else '-'} | {min(b['loo'][c]):+.2f}..{max(b['loo'][c]):+.2f} | {b['drop_top5'][c]:+.2f} | {w['d']:+.2f} ({w['p_wild']:.2f}; {w['orgs']}) | {pr['median_d']:+.2f}, {pr['n_positive']}/{pr['n_orgs']} ({pr['sign_test_p']:.2f}) |")
    L.append(f"within-org sizes: {b['within_org_sizes']}"); L.append("")
for name in R["trailer"]:
    t = R["trailer"][name]; L.append(f"## trailer ({name}): n={t['n']}, AI={t['ai']}, human-only={t['human']}, orgs={t['orgs']}, tools={t['tools']}")
    L.append("| 신호 | AI d (p) | human d (p) | AI−human d (p, Holm) |"); L.append("|---|---|---|---|")
    for c in SIG: x = t[c]; L.append(f"| {SHORT[c]} | {x['ai_d']:+.2f} ({x['ai_p']:.3f}) | {x['human_d']:+.2f} ({x['human_p']:.3f}) | {x['diff_d']:+.2f} ± {1.96*x['diff_se']:.2f} ({x['diff_p']:.3f}, {x['diff_p_holm']:.3f}) |")
    L.append("")
open(os.path.join(V2, "results_composition" + SUF + ".md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
# ---- 그림: 세 추정량 (raw / org-RI / capped) × 두 대비 (fig_composition) ; trailer 차이 (fig_trailer)
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.6))
for k, (name, title) in enumerate([("era", "A. Post-ChatGPT vs. pre"), ("agent", "B. Agentic era vs. early post")]):
    ax = axes[k]; b = R[name]; y = np.arange(len(SIG))
    ax.scatter([b["raw"][c] for c in SIG], y-0.22, marker="s", color="#aaaaaa", label="Raw (no adjustment)", zorder=3)
    ax.errorbar([b["org_ri"][c]["d"] for c in SIG], y, xerr=[1.96*b["org_ri"][c]["se_d"] for c in SIG], fmt="o", color="#555555", capsize=2, label="Organization random intercepts", zorder=3)
    ax.errorbar([b["capped"][c]["d"] for c in SIG], y+0.22, xerr=[1.96*b["capped"][c]["se_d"] for c in SIG], fmt="D", color="black", capsize=2, label="Organizations capped at 50", zorder=3)
    ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0); ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG], fontsize=9); ax.invert_yaxis(); ax.set_title(title, fontsize=11); ax.set_xlabel("Standardized difference (SD units), 95% CI", fontsize=9); ax.tick_params(labelsize=9); ax.set_xlim(-0.75, 0.75)
    if k == 1: ax.legend(fontsize=8, loc="lower right", framealpha=0.95)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_composition" + SUF + ".pdf")); fig.savefig(os.path.join(V2, "fig_composition" + SUF + ".png"), dpi=200)
fig, ax = plt.subplots(figsize=(6.2, 4.2)); t = R["trailer"]["all_tiers_ge5"]; y = np.arange(len(SIG))
ax.errorbar([t[c]["ai_d"] for c in SIG], y-0.18, xerr=[1.96*t[c]["ai_se"] for c in SIG], fmt="o", color="black", capsize=2, label="AI trailer vs. peers")
ax.errorbar([t[c]["human_d"] for c in SIG], y+0.18, xerr=[1.96*t[c]["human_se"] for c in SIG], fmt="o", color="#aaaaaa", capsize=2, label="Human co-author trailer vs. peers")
ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0); ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG], fontsize=9); ax.invert_yaxis(); ax.set_xlabel("Standardized difference (SD units), 95% CI", fontsize=9); ax.tick_params(labelsize=9); ax.set_xlim(-0.75, 0.75)
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18), ncol=2, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_trailer" + SUF + ".pdf"), bbox_inches="tight"); fig.savefig(os.path.join(V2, "fig_trailer" + SUF + ".png"), dpi=200, bbox_inches="tight"); print("figs saved")

# ====================== v3 추가 (작업지시서 2026-10-30 반영) ======================
# (A) 원단위 효과: 캡 추정 β (로그/비율 원척도) → 비율 신호는 퍼센트포인트, 로그 신호는 배수
def ri_raw(d, c, label):
    x = d.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"])
    try: m = mfit(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x)
    except Exception: m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    return float(m.params[label]), float(m.bse[label])
def capped_raw(d, label, cap=50, reps=40):
    out = {c: [] for c in SIG}
    for _ in range(reps):
        s = cap_sample(d, cap, rng.integers(1e9))
        for c in SIG: out[c].append(ri_raw(s, c, label))
    res = {}
    for c in SIG:
        bs = np.array([v[0] for v in out[c]]); ses = np.array([v[1] for v in out[c]]); se = float(np.sqrt(ses.mean()**2 + (1+1/reps)*bs.var(ddof=1)))
        res[c] = {"beta": float(bs.mean()), "se": se, "ci90": [float(bs.mean()-1.645*se), float(bs.mean()+1.645*se)], "pre_mean": float(d.loc[d[label]==0, c].mean()), "post_mean": float(d.loc[d[label]==1, c].mean())}
    return res
R["era"]["capped_raw"] = capped_raw(d, "post"); R["agent"]["capped_raw"] = capped_raw(da, "agent")
# (B) 연도 직접 대비: 2023 vs 2022 (공분산 반영 Wald), RI 및 캡(5회)
def year_contrast(dd, y1=2023, y0=2022):
    out = {}
    for c in SIG:
        x = dd.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        try:
            m = mfit(f"{c} ~ C(first_year, Treatment(reference=2019)) + log_commits + n_authors_human + C(lang_family)", x)
            names = list(m.fe_params.index); V = np.asarray(m.cov_params())[:len(names), :len(names)]; pa = m.fe_params
        except Exception:
            m = smf.ols(f"{c} ~ C(first_year, Treatment(reference=2019)) + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]}); names = list(m.params.index); V = np.asarray(m.cov_params()); pa = m.params
        k1 = [n for n in names if f"T.{y1}" in n][0]; k0 = [n for n in names if f"T.{y0}" in n][0]; i, j = names.index(k1), names.index(k0)
        diff = float(pa[k1] - pa[k0]); se = float(np.sqrt(V[i, i] + V[j, j] - 2*V[i, j])); out[c] = {"d": diff/sd, "se_d": se/sd, "p": float(2*(1-stats.norm.cdf(abs(diff/se))))}
    return out
dy = p[p.first_dt >= "2017-01-01"].copy()
R["year_contrast_2023_vs_2022"] = {"org_ri": year_contrast(dy)}
caps = []
for _ in range(5): caps.append(year_contrast(cap_sample(dy, 50, rng.integers(1e9))))
R["year_contrast_2023_vs_2022"]["capped"] = {c: {"d": float(np.mean([cc[c]["d"] for cc in caps])), "se_d": float(np.sqrt(np.mean([cc[c]["se_d"]**2 for cc in caps]) + 1.2*np.var([cc[c]["d"] for cc in caps], ddof=1)))} for c in SIG}
for c in SIG: v = R["year_contrast_2023_vs_2022"]["capped"][c]; v["p"] = float(2*(1-stats.norm.cdf(abs(v["d"]/v["se_d"]))))
# (C) trailer: 연도 고정효과 추가 + 주 표본 wild cluster bootstrap(AI−human 차이)
def trailer_block(base, name, year_fe=True):
    w = base[base.first_dt >= "2024-01-01"].copy(); orgs = set(w[w.trailer == 1].org) | set(w[w.coauthor_human == 1].org); w = w[w.org.isin(orgs)]
    both_in_org = w.groupby("org").agg(ai=("trailer", "sum"), hu=("coauthor_human", "sum"), n=("repo", "size"))
    out = {"n": int(len(w)), "ai": int(w.trailer.sum()), "human": int(w.coauthor_human.sum()), "orgs": int(w.org.nunique()),
           "orgs_with_ai_and_nontrailer_peer": int(((both_in_org.ai > 0) & (both_in_org.n > both_in_org.ai)).sum()), "orgs_with_both_ai_and_human": int(((both_in_org.ai > 0) & (both_in_org.hu > 0)).sum()),
           "year_mix_ai": w.loc[w.trailer == 1, "first_year"].value_counts().to_dict(), "year_mix_human": w.loc[w.coauthor_human == 1, "first_year"].value_counts().to_dict()}
    yfe = " + C(first_year)" if year_fe else ""
    for c in SIG:
        x = w.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        try:
            m = mfit(f"{c} ~ trailer + coauthor_human + log_commits + n_authors_human + C(lang_family){yfe}", x); names = list(m.fe_params.index); V = np.asarray(m.cov_params())[:len(names), :len(names)]; pa = m.fe_params
        except Exception:
            m = smf.ols(f"{c} ~ trailer + coauthor_human + log_commits + n_authors_human + C(lang_family){yfe}", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]}); names = list(m.params.index); V = np.asarray(m.cov_params()); pa = m.params
        i, j = names.index("trailer"), names.index("coauthor_human"); diff = float(pa["trailer"] - pa["coauthor_human"]); se = float(np.sqrt(V[i, i] + V[j, j] - 2*V[i, j]))
        out[c] = {"ai_d": float(pa["trailer"]/sd), "ai_se": float(np.sqrt(V[i, i])/sd), "ai_p": float(2*(1-stats.norm.cdf(abs(pa["trailer"]/np.sqrt(V[i, i]))))), "human_d": float(pa["coauthor_human"]/sd), "human_se": float(np.sqrt(V[j, j])/sd), "human_p": float(2*(1-stats.norm.cdf(abs(pa["coauthor_human"]/np.sqrt(V[j, j]))))), "diff_d": diff/sd, "diff_se": se/sd, "diff_p": float(2*(1-stats.norm.cdf(abs(diff/se)))), "n": int(len(x))}
        # wild cluster bootstrap on the difference (org FE OLS). Reparameterization: y ~ trailer + (trailer+coauthor_human): the coefficient on trailer is β_AI − β_H,
        # the coefficient on the sum is β_H. (An earlier version used y ~ (T−H) + T, whose first coefficient equals −β_H, not β_AI − β_H; corrected 2026-10-30.)
        x2 = x.copy(); x2["t_plus_h"] = x2.trailer + x2.coauthor_human
        m1 = smf.ols(f"{c} ~ trailer + t_plus_h + log_commits + n_authors_human + C(lang_family) + C(org){yfe}", x2).fit()
        b = float(m1.params["trailer"]); m0 = smf.ols(f"{c} ~ t_plus_h + log_commits + n_authors_human + C(lang_family) + C(org){yfe}", x2).fit(); res = m0.resid.to_numpy(); fit0 = m0.fittedvalues.to_numpy()
        g = pd.factorize(x2.org)[0]; G = g.max()+1; X = m1.model.exog; XtXi = np.linalg.pinv(X.T @ X); jj = list(m1.params.index).index("trailer"); cnt = 0
        for _ in range(999):
            ww = rng.choice([-1, 1], size=G)[g]; bb = (XtXi @ X.T @ (fit0 + res*ww))[jj]
            if abs(bb) >= abs(b): cnt += 1
        out[c]["diff_p_wild"] = (cnt+1)/1000; out[c]["diff_d_fe"] = b/sd
    ps = {c: out[c]["diff_p"] for c in SIG}; keys = sorted(ps, key=lambda k: ps[k]); prev = 0
    for k, c in enumerate(keys): v = min(1.0, ps[c]*(len(keys)-k)); prev = max(prev, v); out[c]["diff_p_holm"] = prev
    ps = {c: out[c]["diff_p_wild"] for c in SIG}; keys = sorted(ps, key=lambda k: ps[k]); prev = 0
    for k, c in enumerate(keys): v = min(1.0, ps[c]*(len(keys)-k)); prev = max(prev, v); out[c]["diff_p_wild_holm"] = prev
    return out
R["trailer_yearfe"] = {"all_tiers_ge5": trailer_block(r[(r.n_commits_human >= 5) & (r.org_test == 0)], "all"), "primary": trailer_block(p, "primary")}
# (D) 저커밋 저장소(학생 커밋 1~2개, GHC 검증, 테스트 org 제외): 계산 가능한 신호의 era 대비
low = r[(r.tier == "A_ghc") & (r.org_test == 0) & (r.n_commits_human >= 1) & (r.n_commits_human <= 2) & r.era.isin(["pre", "post"])].copy(); low["post"] = (low.era == "post").astype(int)
LOWSIG = ["edit_size_log", "large_insert_share_200", "max_insert_log", "test_touch_share"]
out = {"n": int(len(low)), "pre": int((low.era == "pre").sum()), "post": int((low.era == "post").sum()), "orgs": int(low.org.nunique())}
for c in LOWSIG:
    x = low.dropna(subset=[c, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    try: m = mfit(f"{c} ~ post + log_commits + n_authors_human + C(lang_family)", x)
    except Exception: m = smf.ols(f"{c} ~ post + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    cp = []
    for _ in range(20):
        s_ = cap_sample(x, 50, rng.integers(1e9))
        try: mm = mfit(f"{c} ~ post + log_commits + n_authors_human + C(lang_family)", s_)
        except Exception: mm = smf.ols(f"{c} ~ post + log_commits + n_authors_human + C(lang_family)", s_).fit(cov_type="cluster", cov_kwds={"groups": s_["org"]})
        cp.append((float(mm.params["post"]), float(mm.bse["post"])))
    bs = np.array([v[0] for v in cp]); ses = np.array([v[1] for v in cp]); se = float(np.sqrt(ses.mean()**2 + 1.05*bs.var(ddof=1)))
    out[c] = {"raw_d": raw_d(x, c, "post"), "ri_d": float(m.params["post"]/sd), "ri_p": float(m.pvalues["post"]), "capped_d": float(bs.mean()/sd), "capped_ci90_d": [float((bs.mean()-1.645*se)/sd), float((bs.mean()+1.645*se)/sd)], "pre_mean": float(x.loc[x.post==0, c].mean()), "post_mean": float(x.loc[x.post==1, c].mean())}
R["low_commit_repos"] = out
# (E) 포함 확률: GHC 검증·테스트 org 제외 저장소의 학생 커밋 수 분포 by era
allg = r[(r.tier == "A_ghc") & (r.org_test == 0)]
R["inclusion_by_era"] = pd.crosstab(allg.era, pd.cut(allg.n_commits_human, [-1, 0, 1, 2, 1e9], labels=["0", "1", "2", "3+"]), normalize="index").round(4).to_dict("index")
R["inclusion_by_era_counts"] = pd.crosstab(allg.era, pd.cut(allg.n_commits_human, [-1, 0, 1, 2, 1e9], labels=["0", "1", "2", "3+"])).to_dict("index")

# (F) 캡 민감도(25, 100; 20회) 및 org 효과 없는 공변량 조정 추정(OLS, org 클러스터 SE): 조직 구성 vs 공변량 조정 분리
def raw_cov(d, c, label):
    x = d.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    return {"d": float(m.params[label]/sd), "se_d": float(m.bse[label]/sd), "p": float(m.pvalues[label])}
for name, dd, lab in (("era", d, "post"), ("agent", da, "agent")):
    R[name]["raw_cov"] = {c: raw_cov(dd, c, lab) for c in SIG}
    R[name]["cap_sensitivity"] = {}
    for cap in (25, 100):
        R[name]["cap_sensitivity"][str(cap)] = capped(dd, lab, cap=cap, reps=20)[0]
R["fit_log"] = dict(FITLOG)
json.dump(R, open(os.path.join(V2, "results_composition" + SUF + ".json"), "w"), indent=1, default=str)
L2 = ["", "## v3 추가 분석", "### 원단위(캡) 효과 post−pre: β [90% CI], pre/post 평균"]
for c in SIG: v = R["era"]["capped_raw"][c]; L2.append(f"- {c}: β={v['beta']:+.4f} [{v['ci90'][0]:+.4f}, {v['ci90'][1]:+.4f}] | pre {v['pre_mean']:.4f} post {v['post_mean']:.4f}")
L2.append("### 2023 vs 2022 직접 대비 (d, p): RI | capped")
for c in SIG: a = R["year_contrast_2023_vs_2022"]["org_ri"][c]; b = R["year_contrast_2023_vs_2022"]["capped"][c]; L2.append(f"- {c}: RI {a['d']:+.2f} (p={a['p']:.3f}) | capped {b['d']:+.2f} (p={b['p']:.3f})")
for nm in ("all_tiers_ge5", "primary"):
    t = R["trailer_yearfe"][nm]; L2.append(f"### trailer + year FE ({nm}): n={t['n']}, AI={t['ai']}, human={t['human']}, orgs={t['orgs']}, orgs with AI & non-trailer peer={t['orgs_with_ai_and_nontrailer_peer']}, orgs with both AI&human={t['orgs_with_both_ai_and_human']}; year mix AI {t['year_mix_ai']} human {t['year_mix_human']}")
    for c in SIG: v = t[c]; L2.append(f"- {c}: AI {v['ai_d']:+.2f} (p={v['ai_p']:.3f}) human {v['human_d']:+.2f} (p={v['human_p']:.3f}) diff {v['diff_d']:+.2f} ±{1.96*v['diff_se']:.2f} p={v['diff_p']:.3f} Holm={v['diff_p_holm']:.3f} | FE diff {v['diff_d_fe']:+.2f} wild p={v['diff_p_wild']:.3f} Holm={v['diff_p_wild_holm']:.3f} | n={v['n']}")
for name in ("era", "agent"):
    L2.append(f"### {name}: raw+covariates (no org) d (p) | cap 25 d [90%] | cap 100 d [90%]")
    for c in SIG: a = R[name]["raw_cov"][c]; b25 = R[name]["cap_sensitivity"]["25"][c]; b100 = R[name]["cap_sensitivity"]["100"][c]; L2.append(f"- {c}: {a['d']:+.2f} (p={a['p']:.3f}) | {b25['d']:+.2f} [{b25['ci90'][0]:+.2f}, {b25['ci90'][1]:+.2f}] | {b100['d']:+.2f} [{b100['ci90'][0]:+.2f}, {b100['ci90'][1]:+.2f}]")
lo = R["low_commit_repos"]; L2.append(f"### 저커밋(1–2 학생 커밋) 저장소: n={lo['n']} (pre {lo['pre']} / post {lo['post']}), orgs {lo['orgs']}")
for c in LOWSIG: v = lo[c]; L2.append(f"- {c}: raw {v['raw_d']:+.2f} | RI {v['ri_d']:+.2f} (p={v['ri_p']:.3f}) | capped {v['capped_d']:+.2f} [{v['capped_ci90_d'][0]:+.2f}, {v['capped_ci90_d'][1]:+.2f}] | pre {v['pre_mean']:.3f} post {v['post_mean']:.3f}")
L2.append(f"### 포함 확률(학생 커밋 수 분포, 행 비율): {json.dumps(R['inclusion_by_era'])}"); L2.append(f"counts: {json.dumps(R['inclusion_by_era_counts'])}")
open(os.path.join(V2, "results_composition" + SUF + ".md"), "a").write("\n".join(L2) + "\n"); print("\n".join(L2))

# 그림 2·3·1 은 21_figs_from_json.py 가 이 결과 JSON에서 다시 그린다(가중 경로 그림). 그림 4: 연도 고정효과 모형(본문 표 5와 동일)
fig, ax = plt.subplots(figsize=(6.2, 4.2)); t = R["trailer_yearfe"]["all_tiers_ge5"]; y = np.arange(len(SIG))
ax.errorbar([t[c]["ai_d"] for c in SIG], y-0.18, xerr=[1.96*t[c]["ai_se"] for c in SIG], fmt="o", color="black", capsize=2, label="AI trailer vs. peers")
ax.errorbar([t[c]["human_d"] for c in SIG], y+0.18, xerr=[1.96*t[c]["human_se"] for c in SIG], fmt="o", color="#aaaaaa", capsize=2, label="Human co-author trailer vs. peers")
ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0); ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG], fontsize=9); ax.invert_yaxis(); ax.set_xlabel("Standardized difference (SD units), 95% CI", fontsize=9); ax.tick_params(labelsize=9); ax.set_xlim(-0.75, 0.75)
ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18), ncol=2, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_trailer" + SUF + ".pdf"), bbox_inches="tight"); fig.savefig(os.path.join(V2, "fig_trailer" + SUF + ".png"), dpi=200, bbox_inches="tight"); print("fig_trailer regenerated from year-FE model")
