#!/usr/bin/env python3
"""논문 2 v2 — Stage 2b: 커밋 표 → 저장소 신호 v2 (교정 정의 + 민감도 변형)
입력: data/v2/commits.csv.gz, data/v2/repo_arcs.csv, data/v2/sample_flags.csv, data/signal7_msg.csv
출력: data/v2/signals_v2.csv, data/v2/thresholds_v2.csv
교정 결정(E-series, 결과 관측 전 확정):
 E1 large-insert 임계 = pre-era × 언어군 P95 **고정**(주 표본 pre 커밋 기준; 코호트<100커밋은 pre 전체 P95) + 절대 임계 200/500
 E2 sig8(AI-paste 동시발생)은 합성에서 제거(trailer 라벨과 순환)
 E3 모든 신호는 원척도로 보고; 표준화는 풀링(공통 기준) z만 보조
 E5 org 제외 플래그: GitHub 자체 테스트/데모 org(이름에 test|demo|sandbox|sample|playground|staging|production) → org_test=1, 주 분석 제외(민감도로 포함 재추정)
 E6 large-insert 주 임계 = 절대 200줄(보조 500줄); 언어군 P95는 벤더링·생성파일로 20만 줄까지 치솟아 임계로 부적합(thresholds_v2.csv 기록)
 E4 신호명 재명명: large_insert_share, samefile_rerun_rate, burst_share, test_touch_share, time_dispersion, edit_size_log
"""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
c = pd.read_csv(os.path.join(V2, "commits.csv.gz"), dtype={"ai_tool": str, "sha": str}, low_memory=False)
STUDENT_ONLY = os.environ.get("STUDENT_ONLY", "0") == "1"      # v3: 상속 이력·교수자형 저자 커밋 제외 (17_history_flags.py)
FLAGS_FILE = os.environ.get("FLAGS_FILE", "")                    # v4 (2026-10-30): 23_flags_v4.py 의 규칙별 파일 (repo, sha, student)
ARCS_FILE = os.environ.get("ARCS_FILE", "")
OUT_NAME = os.environ.get("OUT_NAME", "signals_v3.csv" if STUDENT_ONLY else "signals_v2.csv")
if FLAGS_FILE:
    hf = pd.read_csv(FLAGS_FILE, dtype={"sha": str}).drop_duplicates(["repo", "sha"])
    c = c.merge(hf, on=["repo", "sha"], how="left")
    c = c[(c.is_bot == 1) | (c.student == 1)].drop(columns=["student"])
elif STUDENT_ONLY:
    hf = pd.read_csv(os.path.join(V2, "commit_history_flags.csv.gz"), dtype={"sha": str})
    c = c.merge(hf[["repo", "sha", "ts", "student"]], on=["repo", "sha", "ts"], how="left")
    c = c[(c.is_bot == 1) | (c.student == 1)].drop(columns=["student"])   # 봇은 n_bot 집계용으로 유지, 사람 커밋은 학생 커밋만
fl = pd.read_csv(os.path.join(V2, "sample_flags.csv"))
arcs = pd.read_csv(os.path.join(V2, "repo_arcs.csv"))
s7 = pd.read_csv(os.path.join(D, "signal7_msg.csv"))
print("commits", len(c), "repos", c.repo.nunique())
hc = c[c.is_bot == 0].sort_values(["repo", "ts"], kind="stable").copy()
# --- 저장소 기본
g = hc.groupby("repo")
rep = pd.DataFrame({
    "n_commits_human": g.size(), "n_merge": g.is_merge.sum(), "n_authors_human": g.author_hash.nunique(),
    "first_ts": g.ts.min(), "last_ts": g.ts.max(), "n_trailer_commits": g.ai_trailer.sum(), "n_signedoff": g.signedoff.sum(), "n_coauthor_human": g.coauthor_human.sum(),
    "n_bot_commits": c[c.is_bot == 1].groupby("repo").size(),
}).reset_index()
rep["n_bot_commits"] = rep.n_bot_commits.fillna(0).astype(int)
rep["first_date"] = pd.to_datetime(rep.first_ts, unit="s", utc=True).dt.strftime("%Y-%m-%d")
rep["first_month"] = pd.to_datetime(rep.first_ts, unit="s", utc=True).dt.to_period("M").astype(str)
rep["first_year"] = pd.to_datetime(rep.first_ts, unit="s", utc=True).dt.year
rep["month_index"] = (pd.to_datetime(rep.first_ts, unit="s", utc=True).dt.year - 2015) * 12 + pd.to_datetime(rep.first_ts, unit="s", utc=True).dt.month - 1  # 2015-01 = 0
rep["era"] = np.where(rep.first_ts < 1669852800, "pre", np.where(rep.first_ts >= 1672531200, "post", "buffer"))
rep["trailer"] = (rep.n_trailer_commits > 0).astype(int)
rep["signedoff"] = (rep.n_signedoff > 0).astype(int)
rep["coauthor_human"] = ((rep.n_coauthor_human > 0) & (rep.n_trailer_commits == 0)).astype(int)   # 사람 Co-authored-by만 있는 저장소 (placebo)
tool = hc[hc.ai_trailer == 1].groupby("repo").ai_tool.agg(lambda s: s.value_counts().index[0]).rename("ai_tool_main")
rep = rep.merge(tool, on="repo", how="left")
main = g.author_hash.agg(lambda s: s.value_counts().index[0]).rename("student_hash")
rep = rep.merge(main, on="repo", how="left")
# --- 플래그 병합
rep = rep.merge(fl[["repo","org","lang_family","owner_type","ghc_verified","name_coursework","stars","fork"]], on="repo", how="left")
rep["lang_family"] = rep.lang_family.fillna("other")
org_n = rep.groupby("org").size().rename("org_n_all"); rep = rep.merge(org_n, on="org", how="left")
rep["org_test"] = rep.org.fillna("").str.contains(r"(test|demo|sandbox|sample|playground|staging|production)", case=False, regex=True).astype(int)
rep["tier"] = np.where(rep.ghc_verified.fillna(False), "A_ghc",
              np.where((rep.owner_type == "Organization") & (rep.org_n_all >= 5) & rep.name_coursework.fillna(False), "B_likely", "C_other"))
# --- 신호: 편집 크기, 버스트, 분산, 테스트, 메시지 길이
nm = hc[hc.is_merge == 0].copy(); nm["churn"] = nm["add"] + nm["del"]
gn = nm.groupby("repo")
rep = rep.merge(gn.churn.median().rename("median_churn"), on="repo", how="left")
rep["edit_size_log"] = np.log1p(rep.median_churn)
rep = rep.merge(np.log1p(gn["add"].max()).rename("max_insert_log"), on="repo", how="left")
hc["gap"] = hc.groupby("repo").ts.diff()
for mins in (15, 30, 60):
    rep = rep.merge((hc.gap < mins * 60).groupby(hc.repo).sum().rename(f"n_burst{mins}"), on="repo", how="left")
    rep[f"burst_share_{mins}"] = np.where(rep.n_commits_human >= 2, rep[f"n_burst{mins}"] / (rep.n_commits_human - 1), np.nan)
rep["test_touch_share"] = (hc.n_test_files > 0).groupby(hc.repo).mean().reindex(rep.repo).to_numpy()
def disp(ts):
    if len(ts) < 4 or ts.max() == ts.min(): return np.nan
    q = np.quantile(ts, [0.25, 0.75]); return (q[1] - q[0]) / (ts.max() - ts.min())
rep["time_dispersion"] = g.ts.apply(lambda s: disp(s.to_numpy())).reindex(rep.repo).to_numpy()
rep["span_days"] = (rep.last_ts - rep.first_ts) / 86400
rep["msg_len_median"] = g.msg_len.median().reindex(rep.repo).to_numpy()
rep["msg_len_log"] = np.log1p(rep.msg_len_median)
rep = rep.merge(arcs[["repo","arcs2","arcs3","arcs4"]], on="repo", how="left")
if ARCS_FILE:
    arcs_s = pd.read_csv(ARCS_FILE).set_index("repo")
    for k in (2, 3, 4): rep[f"arcs{k}"] = rep.repo.map(arcs_s[f"arcs{k}"])
if STUDENT_ONLY and not FLAGS_FILE:
    au = pd.read_csv(os.path.join(V2, "repo_history_audit_all.csv")).rename(columns={"n_human": "n_human_all"})
    rep = rep.merge(au[["repo", "n_human_all", "n_inherited", "n_staff", "n_student"]], on="repo", how="left")
    # 동일 파일 재수정 run 을 학생 커밋만으로 재계산한 값(18_arcs_student.py)으로 대체
    arcs_s = pd.read_csv(os.path.join(V2, "repo_arcs_student.csv")).set_index("repo")
    for k in (2, 3, 4): rep[f"arcs{k}"] = rep.repo.map(arcs_s[f"arcs{k}"])
for k in (2, 3, 4): rep[f"samefile_rerun_rate_k{k}"] = rep[f"arcs{k}"] / rep.n_commits_human
rep = rep.merge(s7[["repo","n_msgs","sig7_msg_informativeness"]].rename(columns={"sig7_msg_informativeness": "msg_informativeness"}), on="repo", how="left")
RECORD_FILE = os.environ.get("RECORD_FILE", "")   # v4: 저장소 기록 특성(과제 사본 여부, 전체 비봇 커밋 수, 생성 시각)
if RECORD_FILE:
    rr = pd.read_csv(RECORD_FILE)[["repo", "assignment_copy", "n_nonbot", "created_ts"]]
    rep = rep.merge(rr, on="repo", how="left")
# --- E1 large-insert 임계: 주 표본(A_ghc ∧ 사람커밋≥3) pre-era 비-merge 사람 커밋 기준, 언어군별 P95 고정
prim_pre = rep[(rep.tier == "A_ghc") & (rep.n_commits_human >= 3) & (rep.era == "pre")][["repo","lang_family"]]
pp = nm.merge(prim_pre, on="repo")
thr_rows = []; thr = {}
fallback = float(np.percentile(pp["add"], 95))
for fam, s in pp.groupby("lang_family"):
    v = float(np.percentile(s["add"], 95)) if len(s) >= 100 else fallback
    thr[fam] = v; thr_rows.append((fam, len(s), v, len(s) >= 100))
thr_rows.append(("__fallback_pre_all__", len(pp), fallback, True))
pd.DataFrame(thr_rows, columns=["lang_family","n_pre_commits_primary","p95_add_fixed","own_cohort"]).to_csv(os.path.join(V2, "thresholds_v2.csv" if not FLAGS_FILE else "thresholds_" + OUT_NAME.replace("signals_", "")), index=False)
nm = nm.merge(rep[["repo","lang_family"]], on="repo", how="left")
nm["thr"] = nm.lang_family.map(thr).fillna(fallback)
nm["li_fixed"] = (nm["add"] >= nm.thr).astype(int); nm["li_200"] = (nm["add"] >= 200).astype(int); nm["li_500"] = (nm["add"] >= 500).astype(int)
gn2 = nm.groupby("repo")
for col in ("li_fixed", "li_200", "li_500"):
    rep = rep.merge(gn2[col].mean().rename("large_insert_share_" + col.split("_")[1]), on="repo", how="left")
# 등록 정의 재현용(era×언어 P95, 전체 코퍼스 기준)은 analysis_table(sig2)로 대체 — 여기서는 생략
# --- 정의 신호 수 (주 신호 6종: edit_size_log, large_insert_share_fixed, burst_share_30, samefile_rerun_rate_k3, test_touch_share, time_dispersion, msg_informativeness → 7)
oa = rep[(rep.tier == "A_ghc") & (rep.n_commits_human >= 3)].groupby("org").agg(org_n_primary=("repo","size"), org_authors_primary=("student_hash","nunique"))
rep = rep.merge(oa, on="org", how="left")
MAIN = ["edit_size_log","large_insert_share_200","burst_share_30","samefile_rerun_rate_k3","test_touch_share","time_dispersion","msg_informativeness"]
rep["n_main_defined"] = rep[MAIN].notna().sum(axis=1)
rep = rep[rep.n_authors_human >= 1]
rep.to_csv(os.path.join(V2, OUT_NAME), index=False)
print("saved", len(rep), "repos;", "tier:", rep.tier.value_counts().to_dict())
print(pd.read_csv(os.path.join(V2, "thresholds_v2.csv" if not FLAGS_FILE else "thresholds_" + OUT_NAME.replace("signals_", ""))).to_string())
