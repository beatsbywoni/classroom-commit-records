#!/usr/bin/env python3
"""논문 2 v3 — 포함 분포(작업지시서): 검증 Classroom 저장소 전체(테스트 org 제외)에서 학생 커밋 0/1/2/3+ 분포를
(a) 저장소 생성 연도 기준 era, (b) 첫 비봇 커밋 기준 era 로 보고. 학생 커밋이 0개인 저장소는 signals_v3에 없으므로
sample_flags + repo_history_audit_all 로 계산 → data/v2/results_inclusion_all_v3.json / .md"""
import os, json, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
fl = pd.read_csv(os.path.join(V2, "sample_flags.csv"), low_memory=False)
s2 = pd.read_csv(os.path.join(V2, "signals_v2.csv"), low_memory=False)[["repo", "org_test", "era"]].rename(columns={"era": "era_nonbot"})
a = pd.read_csv(os.path.join(V2, "repo_history_audit_all.csv"))[["repo", "n_human", "n_inherited", "n_staff", "n_student"]]
v = fl[fl.ghc_verified == 1].merge(s2, on="repo", how="left").merge(a, on="repo", how="left")
v["org_test"] = v.org_test.fillna(0); v = v[v.org_test == 0].copy()
for c in ("n_human", "n_inherited", "n_staff", "n_student"): v[c] = v[c].fillna(0)
v["cat"] = pd.cut(v.n_student, [-1, 0, 1, 2, 1e9], labels=["0", "1", "2", "3+"])
v["era_created"] = np.where(v.created_year <= 2022, "pre", "post")
v["has_bot"] = (v.n_commits - v.n_commits_human.fillna(0)) > 0
R = {"n_verified_nontest": int(len(v)), "n_no_nonbot_commits": int((v.n_human == 0).sum()), "n_zero_student_with_nonbot": int(((v.n_human > 0) & (v.n_student == 0)).sum()),
     "zero_student_inherited_only": int(((v.n_human > 0) & (v.n_student == 0) & (v.n_inherited == v.n_human)).sum()),
     "by_created_era_counts": pd.crosstab(v.era_created, v.cat).to_dict("index"), "by_created_era_share": pd.crosstab(v.era_created, v.cat, normalize="index").round(4).to_dict("index"),
     "by_created_year_share": pd.crosstab(v.created_year, v.cat, normalize="index").round(3).to_dict("index"), "by_created_year_n": v.created_year.value_counts().sort_index().to_dict(),
     "share_with_bot_commits_by_created_year": v.groupby("created_year").has_bot.mean().round(3).to_dict()}
e = v[v.n_human > 0]
R["by_first_nonbot_era_counts"] = pd.crosstab(e.era_nonbot, e.cat).to_dict("index"); R["by_first_nonbot_era_share"] = pd.crosstab(e.era_nonbot, e.cat, normalize="index").round(4).to_dict("index")
json.dump(R, open(os.path.join(V2, "results_inclusion_all_v3.json"), "w"), indent=1, default=str)
L = ["# 포함 분포: 검증 Classroom 저장소 전체 (테스트 org 제외)", f"n={R['n_verified_nontest']}; 비봇 커밋 없음 {R['n_no_nonbot_commits']}; 비봇 있으나 학생 커밋 0 {R['n_zero_student_with_nonbot']} (상속만 {R['zero_student_inherited_only']})",
     "## 생성 연도 기준 era × 학생 커밋 수 (행 비율)", str(pd.crosstab(v.era_created, v.cat, normalize='index').round(3)), str(pd.crosstab(v.era_created, v.cat)),
     "## 생성 연도별", str(pd.crosstab(v.created_year, v.cat, normalize='index').round(2)), "## 첫 비봇 커밋 기준 era (비봇 커밋 ≥1)", str(pd.crosstab(e.era_nonbot, e.cat, normalize='index').round(3)), str(pd.crosstab(e.era_nonbot, e.cat))]
open(os.path.join(V2, "results_inclusion_all_v3.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
