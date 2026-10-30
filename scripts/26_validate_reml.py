#!/usr/bin/env python3
"""논문 2 v4 — 혼합모형 교차 검증: 독립 구현(reml_ri.py) vs statsmodels MixedLM (BFGS, Nelder-Mead) vs L-BFGS.
대상: 주 대비 두 개 × 7개 신호(조직 랜덤절편), 연도 효과 모형 7개, 저커밋 4개.
기록: 계수, 표준오차, 조직 분산, 잔차 분산, REML 로그우도, 그리고 L-BFGS 결과가 퇴화했는지(llf 무한, 분산 0, 고정효과 해와 같은 계수).
출력: data/v2/results_reml_validation.json, .md"""
import os, sys, json, numpy as np, pandas as pd, statsmodels.formula.api as smf, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reml_ri as RR
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
SIG = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion", "msg_informativeness"]
r = pd.read_csv(os.path.join(V2, "signals_v4.csv"), dtype={"ai_tool_main": str}, low_memory=False)
r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date); r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
r["lang_family"] = r.lang_family.fillna("other").astype(str); r["assignment_copy"] = r.assignment_copy.fillna(0).astype(int)
p = r[(r.tier == "A_ghc") & (r.n_commits_human >= 3) & (r.org_test == 0) & (r.assignment_copy == 0)]
d = p[p.era.isin(["pre", "post"])].copy(); d["post"] = (d.era == "post").astype(int)
da = p[p.first_dt >= "2023-01-01"].copy(); da["agent"] = (da.first_dt >= "2025-02-01").astype(int)
low = r[(r.tier == "A_ghc") & (r.org_test == 0) & (r.assignment_copy == 0) & r.n_commits_human.between(1, 2) & r.era.isin(["pre", "post"])].copy(); low["post"] = (low.era == "post").astype(int)
rows = []
def compare(x, c, label, model):
    x = x.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"])
    lv = {"lang_family": sorted(x.lang_family.unique())}
    X, names = RR.design(x, [label], levels=lv); f = RR.fit(x[c].to_numpy(), X, x.org.to_numpy()); i = names.index(label)
    form = f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)"
    row = {"model": model, "signal": c, "n": len(x), "orgs": x.org.nunique(), "own_beta": f["beta"][i], "own_se": f["se"][i], "own_s2u": f["sigma2_u"], "own_s2": f["sigma2"], "own_llf": f["llf"]}
    fe = smf.ols(form + " + C(org)", x).fit().params[label]; row["fe_beta"] = float(fe)
    for meth in ("bfgs", "nm", "lbfgs"):
        try:
            m = smf.mixedlm(form, x, groups=x["org"]).fit(reml=True, method=meth, maxiter=5000)
            row[f"{meth}_beta"] = float(m.fe_params[label]); row[f"{meth}_se"] = float(m.bse_fe[label]); row[f"{meth}_s2u"] = float(m.cov_re.iloc[0, 0])
            row[f"{meth}_s2"] = float(m.scale); row[f"{meth}_llf"] = float(m.llf); row[f"{meth}_conv"] = bool(m.converged)
        except Exception as e:
            row[f"{meth}_err"] = type(e).__name__
    row["lbfgs_degenerate"] = bool(("lbfgs_llf" in row) and (not np.isfinite(row["lbfgs_llf"])))
    row["lbfgs_equals_fe"] = bool(("lbfgs_beta" in row) and abs(row["lbfgs_beta"] - row["fe_beta"]) < 1e-8 * max(1, abs(row["fe_beta"])))
    rows.append(row); print(model, c, {k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items() if k.endswith(("beta", "llf", "s2u")) or k.startswith("lbfgs_")}, flush=True)
for c in SIG: compare(d, c, "post", "era")
for c in SIG: compare(da, c, "agent", "agent")
for c in ["edit_size_log", "large_insert_share_200", "max_insert_log", "test_touch_share"]: compare(low, c, "post", "low_commit")
T = pd.DataFrame(rows)
def rel(a, b): return float(np.nanmax(np.abs(a - b) / np.maximum(np.abs(b), 1e-12)))
S = {"n_models": len(T),
     "max_abs_diff_beta_own_vs_bfgs_sd_units": float(np.nanmax(np.abs(T.own_beta - T.bfgs_beta) / np.array([d[c].std() if m in ("era",) else (da[c].std() if m == "agent" else low[c].std()) for m, c in zip(T.model, T.signal)]))),
     "max_rel_diff_s2u_own_vs_bfgs": rel(T.own_s2u, T.bfgs_s2u), "max_rel_diff_s2_own_vs_bfgs": rel(T.own_s2, T.bfgs_s2),
     "max_abs_diff_llf_own_vs_bfgs": float(np.nanmax(np.abs(T.own_llf - T.bfgs_llf))), "se_ratio_own_over_bfgs_range": [float((T.own_se / T.bfgs_se).min()), float((T.own_se / T.bfgs_se).max())],
     "max_abs_diff_beta_bfgs_vs_nm": float(np.nanmax(np.abs(T.bfgs_beta - T.nm_beta))) if "nm_beta" in T else None,
     "lbfgs_degenerate": int(T.lbfgs_degenerate.sum()), "lbfgs_equals_fe": int(T.lbfgs_equals_fe.sum())}
json.dump({"summary": S, "rows": rows}, open(os.path.join(V2, "results_reml_validation.json"), "w"), indent=1, default=float)
print(json.dumps(S, indent=1))
