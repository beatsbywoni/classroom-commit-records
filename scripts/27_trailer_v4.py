#!/usr/bin/env python3
"""논문 2 v4 — AI 트레일러와 사람 공동저자 트레일러(위약 대조), 2024년 이후 첫 커밋, 연도 고정효과 포함.
RI: reml_ri (독립 구현; statsmodels와 대조는 26_validate_reml.py). 조직 고정효과 차이: OLS + 제한 wild 군집 부트스트랩
(조직 12개 미만이면 Webb 6점 가중), 90% 구간은 검정 역산. 출력: data/v2/results_trailer_v4.json"""
import os, sys, json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
from scipy import stats
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reml_ri as RR
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
SIG = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion", "msg_informativeness"]
rng = np.random.default_rng(20261030)
r = pd.read_csv(os.path.join(V2, "signals_v4.csv"), dtype={"ai_tool_main": str}, low_memory=False)
r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date); r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
r["lang_family"] = r.lang_family.fillna("other").astype(str); r["assignment_copy"] = r.assignment_copy.fillna(0).astype(int); r["year"] = r.first_dt.dt.year.astype(str)
def frame(base):
    w = base[base.first_dt >= "2024-01-01"].copy(); orgs = set(w[w.trailer == 1].org) | set(w[w.coauthor_human == 1].org); return w[w.org.isin(orgs)]
def holm(ps):
    keys = sorted(ps, key=lambda k: ps[k]); prev = 0; out = {}
    for k_, c in enumerate(keys): v = min(1.0, ps[c] * (len(keys) - k_)); prev = max(prev, v); out[c] = prev
    return out
def block(w, Bw=1999):
    lv = {"lang_family": sorted(w.lang_family.unique()), "year": sorted(w.year.unique())}
    bo = w.groupby("org").agg(ai=("trailer", "sum"), hu=("coauthor_human", "sum"), n=("repo", "size"))
    out = {"n": int(len(w)), "ai": int(w.trailer.sum()), "human": int(w.coauthor_human.sum()), "orgs": int(w.org.nunique()),
           "orgs_ai_and_peer": int(((bo.ai > 0) & (bo.n > bo.ai)).sum()), "orgs_ai_and_human": int(((bo.ai > 0) & (bo.hu > 0)).sum()),
           "tools": w.loc[w.trailer == 1, "ai_tool_main"].value_counts().to_dict(), "year_mix_ai": w.loc[w.trailer == 1, "year"].value_counts().to_dict()}
    for c in SIG:
        x = w.dropna(subset=[c]); sd = float(x[c].std(ddof=1))
        X, names = RR.design(x, ["trailer", "coauthor_human"], factors=("lang_family", "year"), levels=lv); f = RR.fit(x[c].to_numpy(), X, x.org.to_numpy())
        i, j = names.index("trailer"), names.index("coauthor_human"); V = f["cov"]; diff = f["beta"][i] - f["beta"][j]; se = np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j])
        o = {"ai_d": f["beta"][i] / sd, "ai_p": float(2 * (1 - stats.norm.cdf(abs(f["beta"][i] / np.sqrt(V[i, i]))))), "human_d": f["beta"][j] / sd,
             "human_p": float(2 * (1 - stats.norm.cdf(abs(f["beta"][j] / np.sqrt(V[j, j]))))), "diff_d": diff / sd, "diff_se_d": se / sd, "diff_p": float(2 * (1 - stats.norm.cdf(abs(diff / se)))), "n": int(len(x))}
        # organization fixed effects; coefficient on T in y ~ T + (T+H) is beta_AI - beta_H
        x2 = x.copy(); x2["t_plus_h"] = x2.trailer + x2.coauthor_human
        m = smf.ols(f"{c} ~ trailer + t_plus_h + log_commits + n_authors_human + C(lang_family) + C(year) + C(org)", x2).fit(); b = float(m.params["trailer"])
        m0 = smf.ols(f"{c} ~ t_plus_h + log_commits + n_authors_human + C(lang_family) + C(year) + C(org)", x2).fit()
        g = pd.factorize(x2.org)[0]; G = g.max() + 1; Xm = m.model.exog; P = (np.linalg.pinv(Xm.T @ Xm) @ Xm.T)[list(m.params.index).index("trailer")]
        W = rng.choice([-1.0, 1.0], size=(Bw, G))[:, g] if G >= 12 else rng.choice(np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)]), size=(Bw, G))[:, g]
        r0, f0 = m0.resid.to_numpy(), m0.fittedvalues.to_numpy()
        o["fe_diff_d"] = b / sd; o["fe_p_wild"] = float(((np.abs((W * r0) @ P + f0 @ P) >= abs(b)).sum() + 1) / (Bw + 1)); out[c] = o
    for key in ("diff_p", "fe_p_wild"):
        h = holm({c: out[c][key] for c in SIG})
        for c in SIG: out[c][key + "_holm"] = h[c]
    return out
R = {"full_frame_ge5": block(frame(r[(r.n_commits_human >= 5) & (r.org_test == 0)])),
     "primary": block(frame(r[(r.tier == "A_ghc") & (r.n_commits_human >= 3) & (r.org_test == 0) & (r.assignment_copy == 0)]))}
# trailer prevalence by year (repos with >=3 classified commits, full frame, test orgs excluded)
ff = r[(r.n_commits_human >= 3) & (r.org_test == 0)]
R["prevalence"] = ff.groupby(ff.first_dt.dt.year).trailer.mean().loc[2023:2026].round(4).to_dict()
json.dump(R, open(os.path.join(V2, "results_trailer_v4.json"), "w"), indent=1, default=float)
for k in ("full_frame_ge5", "primary"):
    t = R[k]; print(k, {kk: t[kk] for kk in ("n", "ai", "human", "orgs", "orgs_ai_and_peer", "orgs_ai_and_human")})
    for c in SIG: print("  ", c, {kk: round(v, 3) for kk, v in t[c].items() if isinstance(v, float)})
print("prevalence", R["prevalence"])
