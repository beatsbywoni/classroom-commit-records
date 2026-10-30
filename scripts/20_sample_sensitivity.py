#!/usr/bin/env python3
"""논문 2 v3 — 표본·임계 민감도를 캡 추정량(org cap 50, 20회)으로: 주 표본 / 사람커밋≥5 / 테스트 org 포함 / tier B 포함 / 전체 프레임(≥3),
및 임계 변형(버스트 15/60, 재실행 k=2/4, 대형삽입 500, 최대삽입, 메시지 길이) → data/v2/results_sample_sensitivity_v3.json / .md"""
import os, json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings("ignore")
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
r = pd.read_csv(os.path.join(V2, "signals_v3.csv"), dtype={"ai_tool_main": str}, low_memory=False)
r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date); r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
SIG = ["edit_size_log","large_insert_share_200","burst_share_30","samefile_rerun_rate_k3","test_touch_share","time_dispersion","msg_informativeness"]
ALT = ["burst_share_15","burst_share_60","samefile_rerun_rate_k2","samefile_rerun_rate_k4","large_insert_share_500","max_insert_log","msg_len_log"]
rng = np.random.default_rng(20261030)

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
    sh = d.sample(frac=1.0, random_state=int(seed)); return sh[sh.groupby("org").cumcount() < cap]
def ri(d, c, label):
    x = d.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    try: m = mfit(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x)
    except Exception: m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    return float(m.params[label]/sd), float(m.bse[label]/sd)
def capped(d, label, sigs, cap=50, reps=20):
    out = {c: [] for c in sigs}
    for _ in range(reps):
        s = cap_sample(d, cap, rng.integers(1e9))
        for c in sigs:
            if c in s.columns and s[c].notna().sum() > 50: out[c].append(ri(s, c, label))
    res = {}
    for c in sigs:
        if not out[c]: continue
        ds = np.array([v[0] for v in out[c]]); ses = np.array([v[1] for v in out[c]]); se = float(np.sqrt(ses.mean()**2 + (1+1/reps)*ds.var(ddof=1)))
        res[c] = {"d": float(ds.mean()), "se_d": se, "ci90": [float(ds.mean()-1.645*se), float(ds.mean()+1.645*se)]}
    return res
if "msg_len_log" not in r.columns and "msg_len_median" in r.columns: r["msg_len_log"] = np.log1p(r.msg_len_median)
samples = {
 "primary": r[(r.tier == "A_ghc") & (r.n_commits_human >= 3) & (r.org_test == 0)],
 "ge5": r[(r.tier == "A_ghc") & (r.n_commits_human >= 5) & (r.org_test == 0)],
 "test_orgs_kept": r[(r.tier == "A_ghc") & (r.n_commits_human >= 3)],
 "tierAB": r[r.tier.isin(["A_ghc", "B_likely"]) & (r.n_commits_human >= 3) & (r.org_test == 0)],
 "full_frame_ge3": r[(r.n_commits_human >= 3) & (r.org_test == 0)],
}
R = {}
for nm, base in samples.items():
    d = base[base.era.isin(["pre", "post"])].copy(); d["post"] = (d.era == "post").astype(int)
    da = base[base.first_dt >= "2023-01-01"].copy(); da["agent"] = (da.first_dt >= "2025-02-01").astype(int)
    sigs = SIG + (ALT if nm == "primary" else [])
    R[nm] = {"n_era": int(len(d)), "orgs_era": int(d.org.nunique()), "n_agent": int(len(da)), "era": capped(d, "post", sigs), "agent": capped(da, "agent", sigs)}
    print(nm, R[nm]["n_era"], flush=True)
R["fit_log"] = dict(FITLOG)
json.dump(R, open(os.path.join(V2, "results_sample_sensitivity_v3.json"), "w"), indent=1)
L = ["# 표본·임계 민감도 (org cap 50, 20회; d [90% CI])", ""]
for nm in [k for k in R if k != "fit_log"]:
    L.append(f"## {nm}: era n={R[nm]['n_era']} orgs={R[nm]['orgs_era']}; agent n={R[nm]['n_agent']}"); L.append("| 신호 | post−pre | agent−early |"); L.append("|---|---|---|")
    for c in R[nm]["era"]:
        e = R[nm]["era"][c]; a = R[nm]["agent"].get(c, {"d": float("nan"), "ci90": [float("nan")]*2})
        L.append(f"| {c} | {e['d']:+.2f} [{e['ci90'][0]:+.2f}, {e['ci90'][1]:+.2f}] | {a['d']:+.2f} [{a['ci90'][0]:+.2f}, {a['ci90'][1]:+.2f}] |")
    L.append("")
open(os.path.join(V2, "results_sample_sensitivity_v3.md"), "w").write("\n".join(L)); print("\n".join(L))
