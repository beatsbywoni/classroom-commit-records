#!/usr/bin/env python3
"""논문 2 v4 — 주 분석 (2026-10-30, 6차 작업지시서 반영).

변경점 (v3 대비):
  - 학생 활동 분류 규칙 v4 (23_flags_v4.py), Classroom 과제 사본 저장소 제외.
  - 혼합모형은 독립 구현 reml_ri.py (statsmodels와 계수·분산성분·로그우도 대조: 26_validate_reml.py).
  - 조직 기여 제한(cap) 추정: 같은 적합에서 원단위(beta)와 표준화(d = beta / SD) 모두 산출, 점추정은 M회 추출 평균,
    구간은 조직 단위 군집 부트스트랩(B회; 각 반복은 조직을 복원추출해 새 조직으로 취급한 뒤 m회 cap 추출 평균).
    Rubin식 결합 구간은 비교용으로만 함께 기록.
  - 모든 cap 분석(주 대비, 연도, 저커밋, 표본·규칙 민감도)에 같은 M, B, m 사용.
출력: data/v2/results_v4{SUF}.json, results_v4{SUF}.md
"""
import os, sys, json, time, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reml_ri as RR

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
SIG_FILE = os.environ.get("SIG_FILE", "signals_v4.csv"); SUF = os.environ.get("SUF", "")
M = int(os.environ.get("M_DRAWS", 200)); B = int(os.environ.get("B_BOOT", 1000)); MB = int(os.environ.get("M_PER_BOOT", 5)); BY = int(os.environ.get("B_YEAR", 500))
QUICK = os.environ.get("QUICK", "0") == "1"
SIG = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion", "msg_informativeness"]
LOWSIG = ["edit_size_log", "large_insert_share_200", "max_insert_log", "test_touch_share"]
EXTRA = ["burst_share_15", "burst_share_60", "samefile_rerun_rate_k2", "samefile_rerun_rate_k4", "large_insert_share_500", "max_insert_log", "msg_len_log"]
rng = np.random.default_rng(20261030)

def load(fn):
    r = pd.read_csv(os.path.join(V2, fn), dtype={"ai_tool_main": str}, low_memory=False)
    r["log_commits"] = np.log1p(r.n_commits_human); r["first_dt"] = pd.to_datetime(r.first_date); r["org"] = r.org.fillna(r.repo.str.split("/").str[0])
    r["lang_family"] = r.lang_family.fillna("other").astype(str)
    if "assignment_copy" not in r: r["assignment_copy"] = 0
    r["assignment_copy"] = r.assignment_copy.fillna(0).astype(int)
    bs = pd.read_csv(os.path.join(V2, "repo_starter.csv")); r = r.merge(bs, on="repo", how="left").fillna({"root_bot": 0, "root_bot_add": 0})
    r["starter"] = (r.root_bot_add >= 20).astype(int)   # root commit by the Classroom bot adding >= 20 lines: starter code copied by the platform (33_starter_code.py)
    return r

def primary(r, min_c=3, test=False, tiers=("A_ghc",), copies=False):
    m = r.tier.isin(tiers) & (r.n_commits_human >= min_c)
    if not test: m &= (r.org_test == 0)
    if not copies: m &= (r.assignment_copy == 0)
    return r[m].copy()

def contrasts(p, extra=False):
    d = p[p.era.isin(["pre", "post"])].copy(); d["post"] = (d.era == "post").astype(int)
    da = p[p.first_dt >= "2023-01-01"].copy(); da["agent"] = (da.first_dt >= "2025-02-01").astype(int)
    out = {"era": (d, "post"), "agent": (da, "agent")}
    if extra:
        # same record-generation regime: post era limited to first commits before July 2024 (template-copy model throughout)
        out["era_regime"] = (d[(d.post == 0) | (d.first_dt < "2024-07-01")].copy(), "post")
        # the same restriction defined by repository creation time, at which the platform's creation method applies:
        # before the general release of fork-based creation (July 2024) and before its beta (January 2024)
        cr = pd.to_datetime(d.created_ts, unit="s")
        out["era_preswitch"] = (d[(d.post == 0) | (cr < "2024-07-01")].copy(), "post")
        out["era_prebeta"] = (d[(d.post == 0) | (cr < "2024-01-01")].copy(), "post")
        # agentic contrast limited to repositories without platform-copied starter code in both periods
        out["agent_nostarter"] = (da[da.starter == 0].copy(), "agent")
    return out

def reml_beta(x, c, label, levels, extra_labels=(), factors=("lang_family",)):
    X, names = RR.design(x, [label] + list(extra_labels), factors=factors, levels=levels)
    f = RR.fit(x[c].to_numpy(), X, x.org.to_numpy())
    i = names.index(label); return f, names, i

def cap_draw(x, cap, gen):
    perm = gen.permutation(len(x)); sh = x.iloc[perm]
    return sh[sh.groupby("org").cumcount().to_numpy() < cap]

def _cap_rows(codes, cap, gen):
    """Indices of a random draw that keeps at most `cap` rows per group (array version of cap_draw)."""
    perm = gen.permutation(len(codes)); oc = codes[perm]
    order = np.argsort(oc, kind="stable"); s_oc = oc[order]
    starts = np.r_[0, np.flatnonzero(np.diff(s_oc)) + 1]; pos = np.arange(len(s_oc)) - np.repeat(starts, np.diff(np.r_[starts, len(s_oc)]))
    return perm[order[pos < cap]]

def _fit_rows(y, X, codes, rows, j):
    Xs = X[rows]; keep = np.ones(X.shape[1], bool)
    for k in range(1, X.shape[1]):
        col = Xs[:, k]
        if k != j and (col.min() == col.max()): keep[k] = False
    jj = int(keep[:j].sum()); f = RR.fit(y[rows], Xs[:, keep], codes[rows]); return f["beta"][jj], f["se"][jj]

def capped(x, c, label, cap, levels, M=M, B=B, MB=MB, boot=True, factors=("lang_family",), extra_labels=(), target=None):
    """Point estimate: mean over M cap draws. Interval: organization cluster bootstrap (B replicates; in each, organizations
    are resampled with replacement and treated as distinct, and the estimate is the mean over MB cap draws).
    Natural (beta) and standardized (d = beta / SD of the signal in the contrast sample) units come from the same fits.
    If `target` is a list of two column names, the estimate is the difference of their coefficients (used for year contrasts)."""
    x = x.dropna(subset=[c, "log_commits", "n_authors_human", "lang_family", "org"] + ([label] if label else []))
    sd = float(x[c].std(ddof=1)); y = x[c].to_numpy(float)
    X, names = RR.design(x, ([label] if label else []) + list(extra_labels), factors=factors, levels=levels)
    codes = pd.factorize(x.org)[0]
    if target is None:
        j = names.index(label)
        def est(rows): return _fit_rows(y, X, codes, rows, j)
    else:
        j1, j0 = names.index(target[0]), names.index(target[1])
        def est(rows):
            b1, _ = _fit_rows(y, X, codes, rows, j1); b0, _ = _fit_rows(y, X, codes, rows, j0); return b1 - b0, np.nan
    bs, ses = [], []
    for _ in range(M):
        b_, s_ = est(_cap_rows(codes, cap, rng)); bs.append(b_); ses.append(s_)
    bs, ses = np.array(bs), np.array(ses); e = float(bs.mean())
    out = {"beta": e, "d": e / sd, "sd": sd, "draw_sd_beta": float(bs.std(ddof=1))}
    if target is None:
        se_r = float(np.sqrt(np.nanmean(ses) ** 2 + (1 + 1 / M) * bs.var(ddof=1)))
        out.update({"rubin_se_beta": se_r, "rubin_ci90": [(e - 1.645 * se_r) / sd, (e + 1.645 * se_r) / sd]})
    if boot:
        G = codes.max() + 1; idx = [np.flatnonzero(codes == g) for g in range(G)]; bb = []
        for _ in range(B):
            pick = rng.integers(0, G, size=G)
            rows = np.concatenate([idx[g] for g in pick]); newc = np.concatenate([np.full(len(idx[g]), k) for k, g in enumerate(pick)])
            yb, Xb = y[rows], X[rows]
            vals = []
            for _ in range(MB):
                rr_ = _cap_rows(newc, cap, rng)
                try:
                    if target is None: vals.append(_fit_rows(yb, Xb, newc, rr_, j)[0])
                    else: vals.append(_fit_rows(yb, Xb, newc, rr_, j1)[0] - _fit_rows(yb, Xb, newc, rr_, j0)[0])
                except Exception: pass
            if vals: bb.append(np.mean(vals))
        bb = np.array(bb)
        out.update({"boot_n": int(len(bb)), "boot_se_beta": float(bb.std(ddof=1)),
                    "ci90_beta": [float(np.quantile(bb, .05)), float(np.quantile(bb, .95))], "ci95_beta": [float(np.quantile(bb, .025)), float(np.quantile(bb, .975))]})
        out["ci90"] = [v / sd for v in out["ci90_beta"]]; out["ci95"] = [v / sd for v in out["ci95_beta"]]
        out["p_boot"] = float(min(1.0, 2 * min((bb <= 0).mean(), (bb >= 0).mean())))
    return out

def ri_full(x, c, label, levels):
    x = x.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    f, names, i = reml_beta(x, c, label, levels); b, se = f["beta"][i], f["se"][i]
    return {"beta": float(b), "se_beta": float(se), "d": float(b / sd), "se_d": float(se / sd), "p": float(2 * (1 - stats.norm.cdf(abs(b / se)))), "sigma2_u": f["sigma2_u"], "sigma2": f["sigma2"], "llf": f["llf"], "n": int(len(x)), "sd": sd}

def raw_d(x, c, label):
    x = x.dropna(subset=[c]); sd = float(x[c].std(ddof=1)); return float((x.loc[x[label] == 1, c].mean() - x.loc[x[label] == 0, c].mean()) / sd)

def raw_cov(x, c, label):
    x = x.dropna(subset=[c, label, "log_commits", "n_authors_human", "lang_family", "org"]); sd = float(x[c].std(ddof=1))
    m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family)", x).fit(cov_type="cluster", cov_kwds={"groups": x["org"]})
    return {"d": float(m.params[label] / sd), "se_d": float(m.bse[label] / sd), "p": float(m.pvalues[label])}

def within(x, c, label, Bw=1999, kmult=6, npts=161):
    """Organization fixed effects on organizations observed in both periods; wild cluster bootstrap (Rademacher):
    p-value under the null (restricted residuals) and a percentile interval from the unrestricted bootstrap."""
    both = x.groupby("org")[label].agg(lambda s: s.nunique() == 2); x = x[x.org.isin(both[both].index)].dropna(subset=[c]).copy()
    sd = float(x[c].std(ddof=1))
    m = smf.ols(f"{c} ~ {label} + log_commits + n_authors_human + C(lang_family) + C(org)", x).fit(); b = float(m.params[label])
    m0 = smf.ols(f"{c} ~ log_commits + n_authors_human + C(lang_family) + C(org)", x).fit()
    g = pd.factorize(x.org)[0]; G = g.max() + 1; X = m.model.exog; XtXi = np.linalg.pinv(X.T @ X); j = list(m.params.index).index(label)
    # Rademacher weights; Webb six-point weights when clusters are fewer than 12 (Webb 2014; Roodman et al. 2019)
    if G >= 12: W = rng.choice([-1.0, 1.0], size=(Bw, G))[:, g]
    else: W = rng.choice(np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)]), size=(Bw, G))[:, g]
    P = (XtXi @ X.T)[j]                                                # row that maps an outcome vector to the coefficient
    r0, f0 = m0.resid.to_numpy(), m0.fittedvalues.to_numpy()
    p0 = float(((np.abs((W * r0) @ P + f0 @ P) >= abs(b)).sum() + 1) / (Bw + 1))
    # 90% interval by inverting the restricted wild bootstrap test over a grid of null values (cf. Roodman et al. 2019)
    Z = x[[label]].to_numpy(float)[:, 0]
    Xr = m0.model.exog; Hr = Xr @ np.linalg.pinv(Xr.T @ Xr) @ Xr.T if len(x) <= 4000 else None
    def p_at(b0):
        yt = x[c].to_numpy(float) - b0 * Z
        if Hr is not None: fr = Hr @ yt
        else: fr = smf.ols(f"yt ~ log_commits + n_authors_human + C(lang_family) + C(org)", x.assign(yt=yt)).fit().fittedvalues.to_numpy()
        rr = yt - fr; base = (fr + b0 * Z) @ P
        bb = (W * rr) @ P + base
        return float(((np.abs(bb - b0) >= abs(b - b0)).sum() + 1) / (Bw + 1))
    se0 = float(np.std((W * m.resid.to_numpy()) @ P)) or 1.0
    K = max(kmult * se0, 2 * abs(b) + 4 * se0); grid = np.linspace(b - K, b + K, npts); ps = np.array([p_at(v) for v in grid]); keep = grid[ps >= 0.10]
    ci = [float(keep.min() / sd), float(keep.max() / sd)] if len(keep) else [float("nan"), float("nan")]
    return {"d": b / sd, "p_wild": p0, "ci90_d": ci, "weights": "rademacher" if G >= 12 else "webb6", "ci_grid_edge": bool(len(keep) and (keep.min() <= grid[0] or keep.max() >= grid[-1])), "edge_low": bool(len(keep) and keep.min() <= grid[0]), "edge_high": bool(len(keep) and keep.max() >= grid[-1]), "grid_d": [float(grid[0] / sd), float(grid[-1] / sd)], "n": int(len(x)), "orgs": int(G)}

def paired(x, label):
    both = x.groupby("org")[label].agg(lambda s: s.nunique() == 2); sp = x[x.org.isin(both[both].index)]
    om = sp.groupby(["org", label])[SIG].mean().unstack(label); out = {"orgs": int(sp.org.nunique()), "n": int(len(sp))}
    for c in SIG:
        diff = (om[(c, 1)] - om[(c, 0)]).dropna(); sd = float(x[c].std(ddof=1))
        out[c] = {"median_d": float(diff.median() / sd), "n_positive": int((diff > 0).sum()), "n_orgs": int(len(diff)), "sign_test_p": float(stats.binomtest(int((diff > 0).sum()), len(diff)).pvalue)}
    return out

def contrast_block(x, label, sigs=SIG, full=True):
    levels = {"lang_family": sorted(x.lang_family.unique())}; out = {"n": int(len(x)), "n1": int(x[label].sum()), "orgs": int(x.org.nunique())}
    out["raw"] = {c: raw_d(x, c, label) for c in sigs}
    out["raw_cov"] = {c: raw_cov(x, c, label) for c in sigs}
    out["ri"] = {c: ri_full(x, c, label, levels) for c in sigs}
    out["cap"] = {}
    for cap in (25, 50, 100):
        out["cap"][str(cap)] = {c: capped(x, c, label, cap, levels) for c in sigs}; print("  cap", cap, "done", flush=True)
    if full:
        top = x.groupby("org").size().sort_values(ascending=False).head(10); out["top_orgs_sizes"] = top.tolist()
        out["loo"] = {c: [ri_full(x[x.org != o], c, label, levels)["d"] for o in top.index] for c in sigs}
        out["drop_top5"] = {c: ri_full(x[~x.org.isin(top.index[:5])], c, label, levels)["d"] for c in sigs}
        out["within"] = {c: within(x, c, label) for c in sigs}
        out["paired"] = paired(x, label)
    return out

PARTS = ["era", "agent", "era_regime", "agent_nostarter", "stability", "extra", "year", "low_msg",
         "samples_ge5", "samples_test_orgs_kept", "samples_copies_kept", "samples_tierAB", "samples_full_frame_ge3",
         "era_preswitch", "era_prebeta", "within_wide"]   # parts added later are appended so that earlier parts keep their random streams

if __name__ == "__main__":
    t0 = time.time()
    PART = os.environ.get("PART", "era"); MODE = os.environ.get("MODE", "full")
    rng = np.random.default_rng([20261030, PARTS.index(PART) if PART in PARTS else 99])   # one reproducible stream per part
    globals()["rng"] = rng
    R = {"settings": {"M_draws": M, "B_boot": B, "B_boot_sensitivity": min(B, 500), "B_boot_year": BY, "draws_per_boot": MB, "sig_file": SIG_FILE, "part": PART}}
    r = load(SIG_FILE); p = primary(r)
    R["sample"] = {"primary_n": int(len(p)), "orgs": int(p.org.nunique()), "era_counts": p.era.value_counts().to_dict(),
                   "copies_excluded": int((primary(r, copies=True).assignment_copy == 1).sum())}
    def save(tag):
        json.dump(R, open(os.path.join(V2, f"results_v4{SUF}_{tag}.json"), "w"), indent=1, default=float); print("done", tag, round(time.time() - t0), flush=True)
    if MODE == "rules":   # classification-rule sensitivity: raw, RI, cap 50 for the two main contrasts
        for name, (x, lab) in contrasts(p).items():
            lv = {"lang_family": sorted(x.lang_family.unique())}
            R[name] = {"n": int(len(x)), "orgs": int(x.org.nunique()), "raw": {c: raw_d(x, c, lab) for c in SIG}, "ri": {c: ri_full(x, c, lab, lv) for c in SIG},
                       "cap50": {c: capped(x, c, lab, 50, lv, B=min(B, 500)) for c in SIG}}
        save("rules"); sys.exit(0)
    CON = contrasts(p, extra=True)
    if PART in CON:
        x, lab = CON[PART]; print("contrast", PART, flush=True)
        R[PART] = contrast_block(x, lab, full=PART in ("era", "agent"))
        R[PART]["means"] = {c: {"pre": float(x.loc[x[lab] == 0, c].mean()), "post": float(x.loc[x[lab] == 1, c].mean())} for c in SIG}
        R[PART]["n_pre"] = int((x[lab] == 0).sum()); R[PART]["n_post"] = int((x[lab] == 1).sum())
        save(PART); sys.exit(0)
    if PART == "within_wide":
        # the within-organization test inversion over a grid ten times wider (50 bootstrap standard errors on each side, 401 points)
        R["within_wide"] = {}
        for name in ("era", "agent"):
            x, lab = CON[name]; R["within_wide"][name] = {c: within(x, c, lab, kmult=50, npts=401) for c in SIG}; print("  within_wide", name, flush=True)
        save("within_wide"); sys.exit(0)
    if PART == "stability":
        R["stability"] = {}
        for name in ("era", "agent"):
            x, lab = CON[name]; lv = {"lang_family": sorted(x.lang_family.unique())}; R["stability"][name] = {}
            for c in SIG:
                big = capped(x, c, lab, 50, lv, M=1000, boot=False); rep2 = capped(x, c, lab, 50, lv)
                R["stability"][name][c] = {"d_M1000": big["d"], "d_rep2": rep2["d"], "ci90_rep2": rep2["ci90"], "rubin_ci90_rep2": rep2["rubin_ci90"]}
        save("stability"); sys.exit(0)
    CON = contrasts(p)
    if PART == "extra":
        R["extra"] = {}
        for name, (x, lab) in CON.items():
            lv = {"lang_family": sorted(x.lang_family.unique())}
            R["extra"][name] = {c: {"ri": ri_full(x, c, lab, lv), "cap50": capped(x, c, lab, 50, lv, B=min(B, 500))} for c in EXTRA}
        save("extra"); sys.exit(0)
    if PART == "year":
        # year effects (RI and cap 50), reference 2019, 2023-2022 contrast; capped effects and the contrast come from the same draws
        dy = p[p.first_dt >= "2017-01-01"].copy(); dy["year"] = dy.first_dt.dt.year.astype(str)
        lv = {"lang_family": sorted(dy.lang_family.unique()), "year": ["2019"] + [y for y in sorted(dy.year.unique()) if y != "2019"]}
        def fit_all(y, X, codes, rows, names):
            Xs = X[rows]; keep = np.ones(X.shape[1], bool)
            for k in range(1, X.shape[1]):
                if Xs[:, k].min() == Xs[:, k].max(): keep[k] = False
            f = RR.fit(y[rows], Xs[:, keep], codes[rows]); kn = [n for n, kk in zip(names, keep) if kk]
            return {n: b for n, b in zip(kn, f["beta"])}, f, kn
        R["year"] = {"ri": {}, "cap50": {}}
        for c in SIG:
            x = dy.dropna(subset=[c]); sd = float(x[c].std(ddof=1)); y = x[c].to_numpy(float)
            X, names = RR.design(x, [], factors=("year", "lang_family"), levels=lv); codes = pd.factorize(x.org)[0]
            allrows = np.arange(len(x)); bfull, f, kn = fit_all(y, X, codes, allrows, names)
            yrs = [n[5:-1] for n in kn if n.startswith("year[")]
            k23, k22 = kn.index("year[2023]"), kn.index("year[2022]"); V = f["cov"]
            con = bfull["year[2023]"] - bfull["year[2022]"]; vcon = V[k23, k23] + V[k22, k22] - 2 * V[k23, k22]
            R["year"]["ri"][c] = {"effects": {yy: [bfull[f"year[{yy}]"] / sd, 1.96 * np.sqrt(V[kn.index(f"year[{yy}]"), kn.index(f"year[{yy}]")]) / sd] for yy in yrs},
                                  "c2023_2022": {"d": con / sd, "p": float(2 * (1 - stats.norm.cdf(abs(con / np.sqrt(vcon)))))}}
            draws = []
            for _ in range(M):
                bd, _, _ = fit_all(y, X, codes, _cap_rows(codes, 50, rng), names); draws.append(bd)
            est = {yy: float(np.nanmean([d_.get(f"year[{yy}]", np.nan) for d_ in draws])) for yy in yrs}
            cest = float(np.nanmean([d_.get("year[2023]", np.nan) - d_.get("year[2022]", np.nan) for d_ in draws]))
            G = codes.max() + 1; idx = [np.flatnonzero(codes == g) for g in range(G)]; boot = []
            for _ in range(BY):
                pick = rng.integers(0, G, size=G); rows = np.concatenate([idx[g] for g in pick]); newc = np.concatenate([np.full(len(idx[g]), k) for k, g in enumerate(pick)])
                yb, Xb = y[rows], X[rows]; vals = []
                for _ in range(MB):
                    try: vals.append(fit_all(yb, Xb, newc, _cap_rows(newc, 50, rng), names)[0])
                    except Exception: pass
                if vals: boot.append({n: np.nanmean([v.get(n, np.nan) for v in vals]) for n in names if n.startswith("year[")})
            def q(vs, a): vs = np.array([v for v in vs if np.isfinite(v)]); return float(np.quantile(vs, a))
            eff = {yy: [est[yy] / sd, [q([b_.get(f"year[{yy}]", np.nan) for b_ in boot], .025) / sd, q([b_.get(f"year[{yy}]", np.nan) for b_ in boot], .975) / sd]] for yy in yrs}
            cb = np.array([b_.get("year[2023]", np.nan) - b_.get("year[2022]", np.nan) for b_ in boot]); cb = cb[np.isfinite(cb)]
            R["year"]["cap50"][c] = {"effects": eff, "c2023_2022": {"d": cest / sd, "ci90": [float(np.quantile(cb, .05)) / sd, float(np.quantile(cb, .95)) / sd], "p_boot": float(min(1, 2 * min((cb <= 0).mean(), (cb >= 0).mean())))}}
            print("  year", c, round(time.time() - t0), flush=True)

        save("year"); sys.exit(0)
    if PART == "low_msg":
        # low-commit repositories (1-2 classified commits)
        low = r[(r.tier == "A_ghc") & (r.org_test == 0) & (r.assignment_copy == 0) & (r.n_commits_human.between(1, 2)) & r.era.isin(["pre", "post"])].copy(); low["post"] = (low.era == "post").astype(int)
        lvl = {"lang_family": sorted(low.lang_family.unique())}
        R["low"] = {"n": int(len(low)), "pre": int((low.post == 0).sum()), "post": int(low.post.sum()), "orgs": int(low.org.nunique())}
        for c in LOWSIG:
            R["low"][c] = {"raw": raw_d(low, c, "post"), "ri": ri_full(low, c, "post", lvl), "cap50": capped(low, c, "post", 50, lvl), "pre_mean": float(low.loc[low.post == 0, c].mean()), "post_mean": float(low.loc[low.post == 1, c].mean())}
        print("low done", time.time() - t0, flush=True)
        # message-set check: repositories whose every non-bot commit is classified as student activity
        if "n_nonbot" in p:
            ps = p[p.n_nonbot == p.n_commits_human]; R["msg_subset"] = {"n": int(len(ps))}
            for name, (x, lab) in contrasts(ps).items():
                lv = {"lang_family": sorted(x.lang_family.unique())}
                R["msg_subset"][name] = {"raw": raw_d(x, "msg_informativeness", lab), "ri": ri_full(x, "msg_informativeness", lab, lv), "cap50": capped(x, "msg_informativeness", lab, 50, lv), "n": int(len(x))}

        save("low_msg"); sys.exit(0)
    if PART.startswith("samples_"):
        nm = PART[len("samples_"):]
        S = {"ge5": lambda: primary(r, min_c=5), "test_orgs_kept": lambda: primary(r, test=True), "copies_kept": lambda: primary(r, copies=True),
             "tierAB": lambda: primary(r, tiers=("A_ghc", "B_likely")), "full_frame_ge3": lambda: r[(r.n_commits_human >= 3) & (r.org_test == 0)].copy()}
        base = S[nm](); R["samples"] = {nm: {}}
        for name, (x, lab) in contrasts(base).items():
            lv = {"lang_family": sorted(x.lang_family.unique())}
            R["samples"][nm][name] = {"n": int(len(x)), "orgs": int(x.org.nunique()), "ri": {c: ri_full(x, c, lab, lv) for c in SIG}, "cap50": {c: capped(x, c, lab, 50, lv, B=min(B, 500)) for c in SIG}}
        save(PART); sys.exit(0)
