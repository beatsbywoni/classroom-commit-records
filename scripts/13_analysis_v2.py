#!/usr/bin/env python3
"""논문 2 v2 — Stage 3: 교정 분석 (신호별 원척도 era 대비 · 연속 시간 · trailer 대비+placebo · 민감도)
입력: data/v2/signals_v2.csv   출력: data/v2/results_v2.json, data/v2/results_v2.md, data/v2/fig_*.png, data/v2/timebins.csv
"""
import json, math, os, warnings, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
rng = np.random.default_rng(20261030)
SIG = {"edit_size_log": -1, "large_insert_share_200": -1, "burst_share_30": +1, "samefile_rerun_rate_k3": +1,
       "test_touch_share": +1, "time_dispersion": +1, "msg_informativeness": +1}
LABEL = {"edit_size_log": "Edit size (log median churn)", "large_insert_share_200": "Large-insert share (>=200 added lines)",
         "burst_share_30": "Burst share (<30 min gap)", "samefile_rerun_rate_k3": "Same-file rerun rate (>=3 consecutive)",
         "test_touch_share": "Test-path touch share", "time_dispersion": "Time dispersion (IQR/span)", "msg_informativeness": "Message informativeness"}
SIG_FILE = os.environ.get("SIG_FILE", "signals_v2.csv"); SUF = os.environ.get("SUF", "")
r = pd.read_csv(os.path.join(V2, SIG_FILE), dtype={"ai_tool_main": str}, low_memory=False)
r["log_commits"] = np.log1p(r.n_commits_human); r["post"] = (r.era == "post").astype(int)
r["first_dt"] = pd.to_datetime(r.first_date)
r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
def primary(d): return d[(d.tier == "A_ghc") & (d.n_commits_human >= 3) & (d.org_test == 0)]
SAMPLES = {"primary": primary(r),
           "primary_ge5": r[(r.tier == "A_ghc") & (r.n_commits_human >= 5) & (r.org_test == 0)],
           "primary_incl_testorgs": r[(r.tier == "A_ghc") & (r.n_commits_human >= 3)],
           "tierAB": r[r.tier.isin(["A_ghc", "B_likely"]) & (r.n_commits_human >= 3) & (r.org_test == 0)],
           "all_tiers_ge5": r[(r.n_commits_human >= 5) & (r.org_test == 0)]}
R = {"samples": {k: {"n": int(len(v)), "pre": int((v.era == "pre").sum()), "post": int((v.era == "post").sum()), "trailer": int(v.trailer.sum()), "orgs": int(v.org.nunique())} for k, v in SAMPLES.items()}}

def cohens_d(y, x):
    a, b = y[x == 1], y[x == 0]
    sp = math.sqrt(((len(a)-1)*a.var(ddof=1) + (len(b)-1)*b.var(ddof=1)) / (len(a)+len(b)-2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else float("nan")
def mixed(d, y, label, extra="", vc=False):
    NA = {"beta": float("nan"), "se": float("nan"), "p": float("nan"), "d_std": float("nan"), "ci90_d": [float("nan")]*2, "ci95_d": [float("nan")]*2, "tost_equiv_010": False, "cohens_d_raw": float("nan"), "mean0": float("nan"), "mean1": float("nan")}
    d = d.dropna(subset=[y, label, "log_commits", "n_authors_human", "lang_family", "org"]).copy()
    if d[label].nunique() < 2 or len(d) < 20: return dict(NA, n=int(len(d)), model="insufficient")
    terms = [label, "log_commits"] + (["n_authors_human"] if d.n_authors_human.nunique() > 1 else []) + (["C(lang_family)"] if d.lang_family.nunique() > 1 else [])
    f = f"{y} ~ " + " + ".join(terms) + extra
    m = None
    try:
        m = smf.mixedlm(f, d, groups=d["org"]).fit(reml=True, method="lbfgs"); note = "org RI"
        if not np.isfinite(m.bse[label]): raise RuntimeError("SE nan")
    except Exception:
        try: m = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["org"]}); note = "OLS org-cluster"
        except Exception:
            try: m = smf.ols(f, d).fit(cov_type="HC1"); note = "OLS HC1"
            except Exception: return dict(NA, n=int(len(d)), model="failed")
    b, se, p = float(m.params[label]), float(m.bse[label]), float(m.pvalues[label]); sd = float(d[y].std(ddof=1))
    return {"n": int(len(d)), "beta": b, "se": se, "p": p, "d_std": b/sd, "ci90_d": [(b-1.645*se)/sd, (b+1.645*se)/sd],
            "ci95_d": [(b-1.96*se)/sd, (b+1.96*se)/sd], "tost_equiv_010": bool((b-1.645*se)/sd > -0.10 and (b+1.645*se)/sd < 0.10),
            "cohens_d_raw": cohens_d(d[y].to_numpy(), d[label].to_numpy()), "mean0": float(d.loc[d[label]==0, y].mean()), "mean1": float(d.loc[d[label]==1, y].mean()), "model": note}
def perm(d, y, label, n_iter=2000):
    d = d.dropna(subset=[y, label, "log_commits", "org"]).sort_values("org", kind="stable")
    X = np.column_stack([np.ones(len(d)), d.log_commits.to_numpy()]); yy = d[y].to_numpy()
    res = yy - X @ np.linalg.lstsq(X, yy, rcond=None)[0]; lab = d[label].to_numpy().astype(float)
    oid = pd.factorize(d.org, sort=False)[0].astype(float); obs = res[lab==1].mean() - res[lab==0].mean(); cnt = 0
    for _ in range(n_iter):
        idx = np.argsort(oid + rng.random(len(d))*0.5, kind="stable"); pl = lab[idx]
        if pl.sum() == 0 or pl.sum() == len(pl): continue
        if abs(res[pl==1].mean() - res[pl==0].mean()) >= abs(obs): cnt += 1
    return float((cnt+1)/(n_iter+1))
def holm(ps):
    keys = sorted(ps, key=lambda k: ps[k]); out = {}; prev = 0
    for i, k in enumerate(keys):
        v = min(1.0, ps[k]*(len(keys)-i)); prev = max(prev, v); out[k] = prev
    return out
def composite(d, cols=SIG, ref=None):
    ref = d if ref is None else ref
    Z = np.column_stack([SIG[c]*(d[c]-ref[c].mean())/ref[c].std(ddof=1) for c in cols])
    return np.where(np.isfinite(Z).sum(1) >= 5, np.nanmean(Z, 1), np.nan)

# ---------- A. 신호별 era 대비 (주 표본 + 민감도)
R["era"] = {}
for sname, d in SAMPLES.items():
    d = d[d.era.isin(["pre", "post"])].copy(); d["shortcut_pooled"] = -composite(d); out = {}
    for c in list(SIG) + ["shortcut_pooled"]:
        out[c] = mixed(d, c, "post")
        if sname == "primary": out[c]["p_perm"] = perm(d, c, "post")
    hp = holm({c: out[c]["p"] for c in SIG})
    for c in SIG: out[c]["p_holm"] = hp[c]
    R["era"][sname] = out
# A2. 양 era에 걸친 org 내 비교(org 고정효과)
d = SAMPLES["primary"]; d = d[d.era.isin(["pre","post"])]
both = d.groupby("org").era.agg(lambda s: {"pre","post"} <= set(s)); d2 = d[d.org.isin(both[both].index)].copy()
R["era_within_org"] = {"n": int(len(d2)), "orgs": int(d2.org.nunique())}
for c in SIG:
    dd = d2.dropna(subset=[c]); m = smf.ols(f"{c} ~ post + log_commits + n_authors_human + C(org)", dd).fit(cov_type="cluster", cov_kwds={"groups": dd["org"]})
    sd = float(dd[c].std(ddof=1)); b, se = float(m.params["post"]), float(m.bse["post"])
    R["era_within_org"][c] = {"beta": b, "se": se, "p": float(m.pvalues["post"]), "d_std": b/sd, "ci95_d": [(b-1.96*se)/sd, (b+1.96*se)/sd]}

# ---------- B. 연속 시간: 반기 구간 평균 + 연도 FE + piecewise
d = SAMPLES["primary"].copy(); d["half"] = d.first_dt.dt.year.astype(str) + np.where(d.first_dt.dt.month <= 6, "H1", "H2")
tb = d[d.first_dt >= "2017-01-01"].groupby("half").agg(n=("repo","size"), **{f"{c}_mean": (c, "mean") for c in SIG}, **{f"{c}_se": (c, lambda s: s.std(ddof=1)/np.sqrt(s.notna().sum())) for c in SIG}).reset_index()
tb.to_csv(os.path.join(V2, "timebins" + SUF + ".csv"), index=False)
R["time"] = {}
d["t"] = (d.first_dt - pd.Timestamp("2022-12-01")).dt.days / 365.25     # 0 = ChatGPT
d["t_post"] = np.clip(d.t, 0, None); d["t_agent"] = np.clip((d.first_dt - pd.Timestamp("2025-02-01")).dt.days/365.25, 0, None)
dd = d[d.first_dt >= "2017-01-01"]
for c in SIG:
    x = dd.dropna(subset=[c, "org"])
    try: m = smf.mixedlm(f"{c} ~ t + t_post + t_agent + log_commits + n_authors_human + C(lang_family)", x, groups=x["org"]).fit(reml=True, method="lbfgs")
    except Exception: m = smf.ols(f"{c} ~ t + t_post + t_agent + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    sd = float(x[c].std(ddof=1))
    R["time"][c] = {k: {"beta_per_year_sd": float(m.params[k])/sd, "p": float(m.pvalues[k])} for k in ("t", "t_post", "t_agent")}
    # 연도 FE (2019 기준) 표준화 계수
    try:
        my = smf.mixedlm(f"{c} ~ C(first_year, Treatment(reference=2019)) + log_commits + n_authors_human + C(lang_family)", x[x.first_year>=2017], groups=x[x.first_year>=2017]["org"]).fit(reml=True, method="lbfgs")
        R["time"][c]["year_fe_d"] = {int(float(k.split("T.")[1].rstrip("]"))): float(v)/sd for k, v in my.params.items() if "first_year" in k}
    except Exception as e: R["time"][c]["year_fe_d"] = str(e)[:80]

# ---------- C. trailer 대비 (2024–26, org×era 매칭) + Signed-off-by placebo; 전체 프레임과 주 표본
R["trailer"] = {}
for sname, d in [("all_tiers_ge5", SAMPLES["all_tiers_ge5"]), ("primary", SAMPLES["primary"])]:
    d = d[d.first_dt >= "2024-01-01"].copy(); d["shortcut_pooled"] = -composite(d); out = {"n_window": int(len(d)), "n_trailer": int(d.trailer.sum()), "n_signedoff": int(d.signedoff.sum()),
        "tools": d.loc[d.trailer==1, "ai_tool_main"].value_counts().to_dict()}
    tro = d[d.trailer == 1][["org"]].drop_duplicates(); dt = d.merge(tro, on="org")
    soo = d[d.signedoff == 1][["org"]].drop_duplicates(); ds = d.merge(soo, on="org")
    coo = d[d.coauthor_human == 1][["org"]].drop_duplicates(); dc = d[d.trailer == 0].merge(coo, on="org")
    out["n_coauthor_human"] = int(d.coauthor_human.sum())
    for c in list(SIG) + ["shortcut_pooled"]:
        out[c] = {"ai_trailer": mixed(dt, c, "trailer"), "placebo_signedoff": mixed(ds, c, "signedoff"), "placebo_coauthor_human": mixed(dc, c, "coauthor_human")}
        if sname == "all_tiers_ge5": out[c]["ai_trailer"]["p_perm"] = perm(dt, c, "trailer")
    hp = holm({c: out[c]["ai_trailer"]["p"] for c in SIG})
    for c in SIG: out[c]["ai_trailer"]["p_holm"] = hp[c]
    R["trailer"][sname] = out
# trailer 연도별 보급률(전체 코퍼스)
R["trailer_prevalence_by_year"] = r[r.n_commits_human>=3].groupby("first_year").trailer.agg(["mean","sum","size"]).loc[2021:].round(4).to_dict("index")

# ---------- D. 기술통계(원고용)
p = SAMPLES["primary"]
R["desc"] = {"year_n": p.groupby("first_year").size().to_dict(), "lang": p.lang_family.value_counts().to_dict(),
             "span_days_median": float(p.span_days.median()), "commits_median": float(p.n_commits_human.median()), "solo_share": float((p.n_authors_human==1).mean()),
             "students": int(p.student_hash.nunique()), "students_multi": int((p.groupby("student_hash").size()>=2).sum()),
             "org_n_median": float(p.groupby("org").size().median()), "org_top": p.groupby("org").size().sort_values(ascending=False).head(10).to_dict()}
R["desc"]["lang_by_era"] = pd.crosstab(p.lang_family, p.era, normalize="columns").round(3).to_dict()
json.dump(R, open(os.path.join(V2, "results_v2" + SUF + ".json"), "w"), indent=1, default=str)

# ---------- 보고서
L = ["# v2 교정 분석 결과 (Stage 3, 2026-10-30)", ""]
L.append("## 표본"); [L.append(f"- {k}: {v}") for k, v in R["samples"].items()]
L.append(""); L.append("## A. 신호별 era 대비 — 주 표본 (post − pre; 혼합모형 org RI, 공변량 log commits·저자수·언어군)")
L.append("| 신호 | pre 평균 | post 평균 | raw d | 모형 d | 90% CI | Holm p | perm p | TOST ±0.10 |"); L.append("|---|---|---|---|---|---|---|---|---|")
for c in list(SIG) + ["shortcut_pooled"]:
    x = R["era"]["primary"][c]
    L.append(f"| {LABEL.get(c, c)} | {x['mean0']:.3f} | {x['mean1']:.3f} | {x['cohens_d_raw']:+.3f} | {x['d_std']:+.3f} | [{x['ci90_d'][0]:+.3f}, {x['ci90_d'][1]:+.3f}] | {x.get('p_holm', x['p']):.2g} | {x.get('p_perm', float('nan')):.3f} | {'equiv' if x['tost_equiv_010'] else 'NOT equiv'} |")
L.append(""); L.append("### 민감도 (모형 d, post−pre)")
L.append("| 신호 | " + " | ".join(SAMPLES) + " | within-org(15 org) |"); L.append("|---|" + "---|"*(len(SAMPLES)+1))
for c in SIG:
    L.append(f"| {c} | " + " | ".join(f"{R['era'][s][c]['d_std']:+.3f}" for s in SAMPLES) + f" | {R['era_within_org'][c]['d_std']:+.3f} (p={R['era_within_org'][c]['p']:.2g}) |")
L.append(""); L.append("## B. 연속 시간 (주 표본, 2017+): 연간 기울기(SD/년) — t: 기본 추세, t_post: 2022-12 이후 추가, t_agent: 2025-02 이후 추가")
for c in SIG:
    t = R["time"][c]; L.append(f"- {c}: t {t['t']['beta_per_year_sd']:+.3f} (p={t['t']['p']:.2g}), +post {t['t_post']['beta_per_year_sd']:+.3f} (p={t['t_post']['p']:.2g}), +agent {t['t_agent']['beta_per_year_sd']:+.3f} (p={t['t_agent']['p']:.2g})")
L.append(""); L.append("### 연도 고정효과 d (2019 기준)")
yrs = sorted({y for c in SIG if isinstance(R["time"][c].get("year_fe_d"), dict) for y in R["time"][c]["year_fe_d"]})
L.append("| 신호 | " + " | ".join(str(y) for y in yrs) + " |"); L.append("|---|" + "---|"*len(yrs))
for c in SIG:
    fe = R["time"][c].get("year_fe_d", {})
    L.append(f"| {c} | " + " | ".join(f"{fe.get(y, float('nan')):+.2f}" if isinstance(fe, dict) else "err" for y in yrs) + " |")
L.append(""); L.append("## C. AI-trailer 대비 (2024-01 이후, org 매칭) vs Signed-off-by placebo")
for sname in R["trailer"]:
    t = R["trailer"][sname]; L.append(f"### {sname}: 창 n={t['n_window']}, trailer {t['n_trailer']}, signed-off {t['n_signedoff']}, 도구 {t['tools']}")
    L.append(f"(사람 Co-authored-by 전용 저장소 {t['n_coauthor_human']})")
    L.append("| 신호 | AI d (n) | Holm p | perm p | SO placebo d (n) | p | Human-coauthor placebo d (n) | p |"); L.append("|---|---|---|---|---|---|---|---|")
    for c in list(SIG) + ["shortcut_pooled"]:
        a, b, h = t[c]["ai_trailer"], t[c]["placebo_signedoff"], t[c]["placebo_coauthor_human"]
        L.append(f"| {c} | {a['d_std']:+.3f} ({a['n']}) | {a.get('p_holm', a['p']):.2g} | {a.get('p_perm', float('nan')):.3f} | {b['d_std']:+.3f} ({b['n']}) | {b['p']:.2g} | {h['d_std']:+.3f} ({h['n']}) | {h['p']:.2g} |")
L.append(""); L.append("## trailer 보급률(연도, 사람커밋≥3 전체): " + ", ".join(f"{int(y)}: {v['mean']:.1%} ({int(v['sum'])}/{int(v['size'])})" for y, v in R["trailer_prevalence_by_year"].items()))
L.append(""); L.append("## 기술통계(주 표본): " + json.dumps(R["desc"], ensure_ascii=False, default=str)[:1500])
open(os.path.join(V2, "results_v2" + SUF + ".md"), "w").write("\n".join(L) + "\n")
# ---------- E. 3시기 대비: 에이전트 도구기(2025-02+) vs 초기 post(2023-01..2025-01); 팬데믹 혼입 점검
def contrast_block(d, label):
    out = {"n": int(len(d)), "n1": int(d[label].sum()), "orgs": int(d.org.nunique())}
    for c in SIG: out[c] = mixed(d, c, label)
    hp = holm({c: out[c]["p"] for c in SIG}); [out[c].__setitem__("p_holm", hp[c]) for c in SIG]
    return out
def within_org_block(d, label):
    both = d.groupby("org")[label].agg(lambda s: s.nunique() == 2); d2 = d[d.org.isin(both[both].index)]
    out = {"n": int(len(d2)), "orgs": int(d2.org.nunique())}
    for c in SIG:
        x = d2.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        try:
            m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(org)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
            b, se = float(m.params[label]), float(m.bse[label]); out[c] = {"d_std": b/sd, "p": float(m.pvalues[label]), "ci95_d": [(b-1.96*se)/sd, (b+1.96*se)/sd]}
        except Exception as e: out[c] = {"d_std": float("nan"), "p": float("nan"), "err": str(e)[:60]}
    return out
pp = SAMPLES["primary"].copy()
d = pp[pp.first_dt >= "2023-01-01"].copy(); d["agent"] = (d.first_dt >= "2025-02-01").astype(int)
R["agent_vs_earlypost"] = {"org_RI": contrast_block(d, "agent"), "within_org": within_org_block(d, "agent")}
d = pp[(pp.first_dt >= "2017-01-01") & (pp.era == "pre")].copy(); d["pand"] = (d.first_dt >= "2020-03-01").astype(int)
R["pandemic_within_pre"] = contrast_block(d, "pand")
d = pp[pp.era.isin(["pre","post"]) & ((pp.first_dt < "2020-03-01") | (pp.era == "post")) & (pp.first_dt >= "2017-01-01")].copy()
R["post_vs_prepandemic"] = contrast_block(d, "post")
R["era_within_org_detail"] = within_org_block(pp[pp.era.isin(["pre","post"])].copy(), "post")
json.dump(R, open(os.path.join(V2, "results_v2" + SUF + ".json"), "w"), indent=1, default=str)
L.append(""); L.append("## E. 3시기 대비 (주 표본)")
for key, title in [("agent_vs_earlypost", "에이전트 도구기(2025-02+) vs 초기 post(2023-01..2025-01)")]:
    a, w = R[key]["org_RI"], R[key]["within_org"]
    L.append(f"### {title}: org RI n={a['n']} (label1 {a['n1']}, orgs {a['orgs']}); within-org n={w['n']}, orgs {w['orgs']}")
    L.append("| 신호 | org-RI d | Holm p | within-org d | p |"); L.append("|---|---|---|---|---|")
    for c in SIG: L.append(f"| {c} | {a[c]['d_std']:+.3f} | {a[c]['p_holm']:.2g} | {w[c]['d_std']:+.3f} | {w[c]['p']:.2g} |")
for key, title in [("pandemic_within_pre", "pre 내부: 팬데믹기(2020-03..2022-11) vs 그 이전(2017..2020-02)"), ("post_vs_prepandemic", "post vs 팬데믹 이전 pre(2017..2020-02)만")]:
    a = R[key]; L.append(f"### {title}: n={a['n']} (label1 {a['n1']}, orgs {a['orgs']})")
    L.append("| 신호 | org-RI d | Holm p |"); L.append("|---|---|---|")
    for c in SIG: L.append(f"| {c} | {a[c]['d_std']:+.3f} | {a[c]['p_holm']:.2g} |")
L.append(""); L.append("## 언어군 구성(주 표본, 열 비율): " + json.dumps(R["desc"]["lang_by_era"]))
open(os.path.join(V2, "results_v2" + SUF + ".md"), "w").write("\n".join(L) + "\n")


# ---------- 그림: 반기별 추세
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, axes = plt.subplots(4, 2, figsize=(11, 12)); axes = axes.ravel()
xs = np.arange(len(tb)); labels = tb.half.tolist()
for i, c in enumerate(SIG):
    ax = axes[i]; ax.errorbar(xs, tb[f"{c}_mean"], yerr=1.96*tb[f"{c}_se"], fmt="o-", ms=3, lw=1, capsize=2)
    for h, ls in [("2022H2", "--"), ("2025H1", ":")]:
        if h in labels: ax.axvline(labels.index(h), ls=ls, color="gray", lw=1)
    ax.set_title(LABEL[c], fontsize=9); ax.set_xticks(xs[::2]); ax.set_xticklabels(labels[::2], rotation=60, fontsize=7)
axes[7].bar(xs, tb.n); axes[7].set_title("Repositories per half-year", fontsize=9); axes[7].set_xticks(xs[::2]); axes[7].set_xticklabels(labels[::2], rotation=60, fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_timebins" + SUF + ".png"), dpi=150); print("fig saved")
