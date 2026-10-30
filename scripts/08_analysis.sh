#!/usr/bin/env bash
# ============================================================
# 논문 2 — 08 확증 분석 (사전등록 판정 기준 그대로)
#
# 사용법:  bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/08_analysis.sh
#          ROBUST=1 bash .../08_analysis.sh   ← robustness 스위트까지 (추가 시간 소요)
#
# 입력:  data/signals_repo.csv, data/signal7_msg.csv, data/logs/(P2용 1회 스캔·캐시)
# 산출:  data/results/results_core.md  ← **최종 판정 보고서**
#        data/results/results_core.json, data/analysis_table.csv.gz
# 판정(등록 §Inference Criteria):
#   지지 = Holm p<.05(방향 일치) ∧ permutation p<.05 ∧ placebo 비유의(|d|<0.05)
#   등가 = TOST 90% CI ⊂ ±0.10
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
VENV="${DATA}/.venv07"
PY="${SCRIPT_DIR}/.analysis_runner.py"
mkdir -p "${DATA}/results"

"${VENV}/bin/pip" -q install pandas statsmodels scipy 2>/dev/null

cat > "$PY" <<'PYEOF'
import gzip, json, math, os, re, sys, warnings
DATA = sys.argv[1]
LOGS = os.path.join(DATA, "logs")
SO_RE = re.compile(r'^\s*signed-off-by\s*:', re.I | re.M)

def so_one(fname):
    """P2 placebo: Signed-off-by trailer 존재 여부 (워커에서 실행 — 모듈 최상위 유지)"""
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f:
            t = f.read()
    except Exception:
        return None
    return (fname[:-7].replace("__", "/", 1), 1 if SO_RE.search(t) else 0)

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    import numpy as np, pandas as pd
    import statsmodels.formula.api as smf

    ROBUST = os.environ.get("ROBUST", "0") == "1"
    RES = os.path.join(DATA, "results")
    SIGNS = {"sig1_edit_granularity": -1, "sig2_large_paste": -1, "sig3_iteration_burst": 1,
             "sig4_error_recovery": 1, "sig5_test_engagement": 1, "sig6_dispersion": 1,
             "sig7_msg_informativeness": 1, "sig8_ai_paste_cooccur": -1}
    SIGCOLS = list(SIGNS.keys())
    rng = np.random.default_rng(20260806)   # 재현성 시드 = 등록일

    # ---------- 0. P2 스캔 (1회, 캐시) ----------
    P2 = os.path.join(DATA, "p2_signedoff.csv")
    if not os.path.exists(P2):
        print("== P2용 Signed-off-by 스캔 (1회, ~10분) ==", flush=True)
        from multiprocessing import Pool
        with Pool(8) as pool:
            res = [r for r in pool.imap_unordered(so_one, sorted(os.listdir(LOGS)), chunksize=400) if r]
        pd.DataFrame(res, columns=["repo", "signedoff"]).to_csv(P2, index=False)

    # ---------- 1. 병합·포함기준·표준화 ----------
    print("== 1. 데이터 구성 ==", flush=True)
    df = pd.read_csv(os.path.join(DATA, "signals_repo.csv"))
    s7 = pd.read_csv(os.path.join(DATA, "signal7_msg.csv"))
    p2 = pd.read_csv(P2)
    df = df.merge(s7[["repo", "sig7_msg_informativeness"]], on="repo", how="left") \
           .merge(p2, on="repo", how="left")
    df["signedoff"] = df["signedoff"].fillna(0).astype(int)
    df = df[(df.n_commits_human >= 5) & (df.n_authors_human >= 1)].copy()
    df["log_commits"] = np.log1p(df.n_commits_human)
    df["first_year"] = pd.to_datetime(df.first_date, errors="coerce").dt.year
    df["student_hash"] = df["student_hash"].fillna("")
    cnt = df.groupby("student_hash")["repo"].transform("count")
    df["multi_student"] = (cnt >= 2) & (df.student_hash != "")

    def zscore_group(d, keys, min_n):
        g = d.groupby(keys)
        for c in SIGCOLS:
            m, s, n = g[c].transform("mean"), g[c].transform("std"), g[c].transform("count")
            z = (d[c] - m) / s
            z[(n < min_n) | (s == 0) | s.isna()] = np.nan
            d[c + "_z"] = z
        return d

    zc = [c + "_z" for c in SIGCOLS]
    # 등록 정의: within-student(≥2 repo) / 그 외 org×era 코호트 (코호트<5는 era 전체 — 구현결정 D7)
    dfA = zscore_group(df[df.multi_student].copy(), ["student_hash"], 2)
    dfB = zscore_group(df[~df.multi_student].copy(), ["org", "era"], 5)
    fb  = zscore_group(df[~df.multi_student].copy(), ["era"], 30)
    for c in zc: dfB[c] = dfB[c].fillna(fb[c])
    df = pd.concat([dfA, dfB]).sort_index()

    za = np.column_stack([SIGNS[c] * df[c + "_z"].to_numpy() for c in SIGCOLS])
    ndef = np.isfinite(za).sum(axis=1)
    df["struggle"] = np.where(ndef >= 5, np.nanmean(za, axis=1), np.nan)
    df["shortcut"] = -df["struggle"]
    # Shortcut 축(등록 Indices): 신호 2·8의 원방향 z 평균 (높을수록 shortcut)
    df["shortcut_axis"] = np.nanmean(np.column_stack(
        [df["sig2_large_paste_z"].to_numpy(), df["sig8_ai_paste_cooccur_z"].to_numpy()]), axis=1)
    df["n_signals_defined"] = ndef
    ana = df[np.isfinite(df.struggle)].copy()

    # H3 전용 코호트-z (구현결정 D8: 학생내 z는 학생 간 기저 분산을 소거 → H3만 org×era-z)
    dfc = zscore_group(df.copy(), ["org", "era"], 5)
    fbc = zscore_group(df.copy(), ["era"], 30)
    for c in zc: dfc[c] = dfc[c].fillna(fbc[c])
    zac = np.column_stack([SIGNS[c] * dfc[c + "_z"].to_numpy() for c in SIGCOLS])
    dfc["struggle_c"] = np.where(np.isfinite(zac).sum(axis=1) >= 5, np.nanmean(zac, axis=1), np.nan)

    ana.to_csv(os.path.join(DATA, "analysis_table.csv.gz"), index=False, compression="gzip")
    R = {"n_analysis": int(len(ana)), "n_pre": int((ana.era == "pre").sum()),
         "n_post": int((ana.era == "post").sum()), "n_trailer": int(ana.trailer.sum())}
    print(f"   분석표본 {R['n_analysis']:,} (pre {R['n_pre']:,} / post {R['n_post']:,} / trailer {R['n_trailer']:,})", flush=True)

    # ---------- 2. 공통 함수 ----------
    def cohens_d(y, x01):
        a, b = y[x01 == 1], y[x01 == 0]
        if len(a) < 2 or len(b) < 2: return float("nan")
        sp = math.sqrt(((len(a)-1)*a.std(ddof=1)**2 + (len(b)-1)*b.std(ddof=1)**2) / (len(a)+len(b)-2))
        return float((a.mean() - b.mean()) / sp) if sp > 0 else float("nan")

    def mixed(d, label, outcome="shortcut", year_vc=True):
        d = d.dropna(subset=[outcome, label, "log_commits", "n_authors_human", "lang_family", "org"]).copy()
        terms = [label, "log_commits"]                       # 상수 공변량 자동 제외(특이행렬 방지)
        if d["n_authors_human"].nunique() > 1: terms.append("n_authors_human")
        if d["lang_family"].nunique() > 1: terms.append("C(lang_family)")
        f = f"{outcome} ~ " + " + ".join(terms)
        m = None
        try:
            if not year_vc:
                raise RuntimeError("year VC excluded by design (D9: treatment nested in year)")
            m = smf.mixedlm(f, d, groups=d["org"],
                            vc_formula={"yr": "0 + C(first_year)"}).fit(reml=True, method="lbfgs")
            note = "org RI + year VC"
        except Exception:
            try:
                m = smf.mixedlm(f, d, groups=d["org"]).fit(reml=True, method="lbfgs")
                note = "org RI" + ("" if not year_vc else " (year VC dropped — preregistered fallback)")
            except Exception:
                m = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["org"]})
                note = "OLS + org-cluster robust SE (MixedLM 수렴 실패 fallback)"
        b, se, p = float(m.params[label]), float(m.bse[label]), float(m.pvalues[label])
        sd = float(d[outcome].std(ddof=1))
        return {"n": int(len(d)), "beta": b, "se": se, "p": p, "d_std": b / sd,
                "ci95": [b - 1.96*se, b + 1.96*se],
                "tost_ci90_d": [(b - 1.645*se)/sd, (b + 1.645*se)/sd],
                "cohens_d_raw": cohens_d(d[outcome].to_numpy(), d[label].to_numpy()), "model": note}

    def perm_test(d, label, outcome="shortcut", n_iter=10000):
        """org 내 라벨 재배치. 통계량 = 공변량 잔차화 후 라벨 평균차 (org-정렬 좌표계로 통일)"""
        d = d.dropna(subset=[outcome, label, "log_commits", "n_authors_human", "org"]).copy()
        d = d.sort_values("org", kind="stable")
        X = np.column_stack([np.ones(len(d)), d.log_commits.to_numpy(), d.n_authors_human.to_numpy()])
        y = d[outcome].to_numpy()
        resid = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
        lab = d[label].to_numpy().astype(float)
        org_id = pd.factorize(d.org, sort=False)[0].astype(float)   # 이미 org 정렬됨
        obs = resid[lab == 1].mean() - resid[lab == 0].mean()
        cnt = 0
        for _ in range(n_iter):
            idx = np.argsort(org_id + rng.random(len(d)) * 0.5, kind="stable")  # org 블록 보존, 블록 내 셔플
            pl = lab[idx]
            st = resid[pl == 1].mean() - resid[pl == 0].mean()
            if abs(st) >= abs(obs): cnt += 1
        return {"obs_diff": float(obs), "p_perm": float((cnt + 1) / (n_iter + 1))}

    def tost_ok(ci): return bool(ci[0] > -0.10 and ci[1] < 0.10)

    # ---------- 3. 확증 검정 ----------
    print("== 2. H1 (era) ==", flush=True)
    d1 = ana[ana.era.isin(["pre", "post"])].copy(); d1["era01"] = (d1.era == "post").astype(int)
    R["H1"] = mixed(d1, "era01", year_vc=False); R["H1"].update(perm_test(d1, "era01"))
    R["H1"]["tost_equiv"] = tost_ok(R["H1"]["tost_ci90_d"])

    print("== 3. P1 placebo (pre 내부 가짜 경계 2021-06-01) ==", flush=True)
    dp = ana[ana.era == "pre"].copy()
    dp["fake"] = (pd.to_datetime(dp.first_date) >= "2021-06-01").astype(int)
    R["P1"] = mixed(dp, "fake", year_vc=False)
    R["P1"]["pass"] = bool(R["P1"]["p"] > .05 and abs(R["P1"]["d_std"]) < .05)

    print("== 4. H2a (trailer, org×era 매칭) ==", flush=True)
    tr_orgs = ana[ana.trailer == 1][["org", "era"]].drop_duplicates()
    d2 = ana.merge(tr_orgs, on=["org", "era"])
    R["H2a"] = mixed(d2, "trailer"); R["H2a"].update(perm_test(d2, "trailer"))
    R["H2a"]["tost_equiv"] = tost_ok(R["H2a"]["tost_ci90_d"])
    R["H2a"]["n_orgs_matched"] = int(tr_orgs.org.nunique())

    print("== 5. P2 placebo (Signed-off-by 가짜 trailer) ==", flush=True)
    so_orgs = ana[ana.signedoff == 1][["org", "era"]].drop_duplicates()
    dso = ana.merge(so_orgs, on=["org", "era"])
    R["P2"] = mixed(dso, "signedoff")
    R["P2"]["pass"] = bool(R["P2"]["p"] > .05 and abs(R["P2"]["d_std"]) < .05)

    print("== 6. H3 (widening gap, 코호트-z) ==", flush=True)
    h3 = dfc[np.isfinite(dfc.struggle_c) & dfc.multi_student & (dfc.student_hash != "")].copy()
    h3 = h3.sort_values(["student_hash", "first_date"], kind="stable")
    firsts = h3.drop_duplicates("student_hash")[["student_hash", "struggle_c"]] \
               .rename(columns={"struggle_c": "baseline"})
    later = h3[h3.duplicated("student_hash")].merge(firsts, on="student_hash")
    later["post01"] = (later.era == "post").astype(int)
    later = later.dropna(subset=["struggle_c", "baseline", "log_commits", "org"])
    f3 = "struggle_c ~ baseline*post01 + baseline*trailer + log_commits"
    try:
        m3 = smf.mixedlm(f3, later, groups=later["student_hash"]).fit(reml=True, method="lbfgs")
        note3 = "student RI"
        if not np.isfinite(m3.bse.get("baseline:post01", np.nan)): raise RuntimeError("SE 미정의")
    except Exception:
        try:
            m3 = smf.ols(f3, later).fit(cov_type="cluster", cov_kwds={"groups": later["org"]})
            note3 = "OLS + org-cluster SE (student RI 특이 — 후속관측 1개/학생 다수)"
        except Exception as e:
            m3 = None; note3 = f"모형 실패: {e}"
    R["H3"] = {"n_obs": int(len(later)), "n_students": int(later.student_hash.nunique()), "model": note3}
    if m3 is not None:
        for t in ["baseline:post01", "baseline:trailer"]:
            if t in m3.params.index:
                R["H3"][t] = {"beta": float(m3.params[t]), "se": float(m3.bse[t]), "p": float(m3.pvalues[t])}

    # ---------- 4. Holm (잠정 3검정; H5는 09에서 합류) ----------
    import numpy as _np
    ps = {"H1": R["H1"]["p"], "H2a": R["H2a"]["p"],
          "H3": R["H3"].get("baseline:post01", {}).get("p", float("nan"))}
    order = sorted([k for k in ps if _np.isfinite(ps[k])], key=lambda k: ps[k])
    holm = {}
    for i, k in enumerate(order):
        holm[k] = min(1.0, ps[k] * (len(order) - i))
    for i in range(1, len(order)):
        holm[order[i]] = max(holm[order[i]], holm[order[i-1]])
    R["holm_provisional_3tests"] = holm
    R["note_H5"] = "H5(수렴타당도)는 DataShop/iSnap 확보 후 09에서 — 최종 Holm은 4검정으로 재계산"

    # ---------- 5. 판정·보고서 ----------
    def verdict(h, beta_dir=+1):
        r = R[h]
        dir_ok = (r["beta"] * beta_dir) > 0
        sig = holm.get(h, 1) < .05 and r.get("p_perm", 1) < .05 and dir_ok
        pl = R["P1"]["pass"] if h == "H1" else (R["P2"]["pass"] if h == "H2a" else True)
        if sig and pl: return "SUPPORTED"
        if r.get("tost_equiv"): return "EQUIVALENT (TOST)"
        if sig and not pl: return "CONFOUNDED (placebo fail)"
        return "NOT SUPPORTED"
    R["verdict"] = {"H1": verdict("H1"), "H2a": verdict("H2a")}
    b3 = R["H3"].get("baseline:post01", {})
    R["verdict"]["H3"] = "SUPPORTED" if (b3.get("p", 1) < .05 and b3.get("beta", 0) < 0
                                          and holm.get("H3", 1) < .05) else "NOT SUPPORTED"

    prof = [(c, SIGNS[c], round(float(ana.loc[ana.era == "pre", c + "_z"].mean()), 4),
             round(float(ana.loc[ana.era == "post", c + "_z"].mean()), 4)) for c in SIGCOLS]

    if ROBUST:
        print("== ROBUST 스위트 ==", flush=True)
        rb = {}
        top20 = ana.org.value_counts().head(20).index
        rb["leave_one_org_out_d"] = {o: round(mixed(d1[d1.org != o], "era01", year_vc=False)["d_std"], 4) for o in top20}
        rb["leave_one_year_out_d"] = {int(y): round(mixed(d1[d1.first_year != y], "era01", year_vc=False)["d_std"], 4)
                                      for y in sorted(d1.first_year.dropna().unique())
                                      if (d1.first_year == y).sum() > 100}
        for cut, name in [("2022-06-01", "boundary_2022_06_d"), ("2023-06-01", "boundary_2023_06_d")]:
            dd = ana.copy()
            dd["era01"] = (pd.to_datetime(dd.first_date) >= cut).astype(int)
            rb[name] = round(mixed(dd, "era01", year_vc=False)["d_std"], 4)
        loso = {}
        for drop in SIGCOLS:
            cols2 = [c for c in SIGCOLS if c != drop]
            za2 = np.column_stack([SIGNS[c] * ana[c + "_z"].to_numpy() for c in cols2])
            tmp = ana.copy()
            tmp["shortcut"] = -np.where(np.isfinite(za2).sum(1) >= 5, np.nanmean(za2, 1), np.nan)
            t2 = tmp[tmp.era.isin(["pre", "post"])].dropna(subset=["shortcut"]).copy()
            t2["era01"] = (t2.era == "post").astype(int)
            loso[drop] = round(mixed(t2, "era01", year_vc=False)["d_std"], 4)
        rb["leave_one_signal_out_d"] = loso
        rb["solo_only_d"] = round(mixed(d1[d1.n_authors_human == 1], "era01", year_vc=False)["d_std"], 4)
        R["robustness"] = rb

    json.dump(R, open(os.path.join(RES, "results_core.json"), "w"), indent=1, default=str)

    L = ["# 08 확증 분석 결과 (등록: osf.io/zshu4, Accepted 2026-08-06)", ""]
    L.append(f"분석표본: {R['n_analysis']:,} repos (pre {R['n_pre']:,} / post {R['n_post']:,} / trailer {R['n_trailer']:,})")
    L.append("")
    for h, dr in [("H1", "post > pre"), ("H2a", "trailer > non-trailer")]:
        r = R[h]
        L.append(f"## {h} ({dr}) → **{R['verdict'][h]}**")
        L.append(f"- β={r['beta']:.4f} (SE {r['se']:.4f}) | 표준화 d={r['d_std']:.3f} | 95% CI [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]")
        L.append(f"- p={r['p']:.2e} | Holm p={holm.get(h, float('nan')):.2e} | permutation p={r['p_perm']:.4f} | n={r['n']:,} ({r['model']})")
        L.append(f"- TOST 90% CI(d) [{r['tost_ci90_d'][0]:.3f}, {r['tost_ci90_d'][1]:.3f}] → 등가={r['tost_equiv']}")
        L.append("")
    L.append(f"Placebo P1(가짜 경계): d={R['P1']['d_std']:.3f}, p={R['P1']['p']:.3f} → pass={R['P1']['pass']}")
    L.append(f"Placebo P2(Signed-off-by): d={R['P2']['d_std']:.3f}, p={R['P2']['p']:.3f} → pass={R['P2']['pass']} (n={R['P2']['n']:,})")
    L.append("")
    L.append(f"## H3 (widening gap) → **{R['verdict']['H3']}** (학생 {R['H3']['n_students']:,}명 / 관측 {R['H3']['n_obs']:,} / {R['H3']['model']})")
    for t in ["baseline:post01", "baseline:trailer"]:
        if t in R["H3"]:
            x = R["H3"][t]; L.append(f"- {t}: β={x['beta']:.4f} (SE {x['se']:.4f}), p={x['p']:.2e}")
    L.append("")
    L.append("## 신호별 z 프로파일 (탐색; 신호, σ, pre 평균, post 평균)")
    for row in prof: L.append(f"- {row}")
    L.append("")
    L.append(f"주: {R['note_H5']}")
    if ROBUST: L.append("Robustness 수치: results_core.json 'robustness' 필드")
    open(os.path.join(RES, "results_core.md"), "w").write("\n".join(L) + "\n")
    print("\n" + "\n".join(L))
    print(f"\n== 저장: {RES}/results_core.md / .json ==")
PYEOF

"${VENV}/bin/python3" "$PY" "$DATA"
