#!/usr/bin/env python3
"""논문 2 v4 — 기록 생성 과정 점검 (2026-10-30). GitHub Classroom은 2024년 1월 공개 베타, 2024년 7월 일반 적용으로
스타터 코드가 있는 과제의 학생 저장소를 포크로 만들고, 과제마다 교사 조직에 템플릿 사본 저장소를 하나 만든다.
이 표집 틀은 GitHub 검색 API(포크 기본 제외)로 열거했으므로 포크인 학생 저장소는 틀에 없고 과제 사본은 틀에 들어온다.
생성 분기별로 검증 저장소 수, 과제 사본 비율, (사본 제외) 규칙상 학생 커밋 0/1/2/3+ 분포, 주 표본에서 플랫폼이 복사한
스타터 코드가 있는 비율, 관찰 기간을 계산한다. 출력: data/v2/results_record_generation.json"""
import os, json, numpy as np, pandas as pd
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
rr = pd.read_csv(os.path.join(V2, "flags_v4", "repo_record.csv"))
f4 = pd.read_csv(os.path.join(V2, "flags_v4", "v4.csv.gz")); ns = f4.groupby("repo").size()
en = pd.read_json(os.path.join(V2, "..", "repos_enumerated.jsonl"), lines=True)[["full_name", "fork"]]
bs = pd.read_csv(os.path.join(V2, "repo_starter.csv"))
rr["org_test"] = rr.org.fillna("").str.contains(r"(?:test|demo|sandbox|sample|playground|staging|production)", case=False, regex=True).astype(int)
rr = rr[rr.org_test == 0].copy()
rr["n_student"] = rr.repo.map(ns).fillna(0); rr = rr.merge(bs, on="repo", how="left").fillna({"root_bot": 0, "root_bot_add": 0})
rr["created"] = pd.to_datetime(rr.created_ts, unit="s"); rr["half"] = rr.created.dt.year.astype(str) + "H" + np.where(rr.created.dt.month <= 6, "1", "2")
rr["obs_days"] = (pd.Timestamp("2026-08-05") - rr.created).dt.days
rr["starter"] = (rr.root_bot_add >= 20).astype(int)
R = {"enumerated_forks": int(en.fork.fillna(False).sum()), "enumerated_n": int(len(en)),
     "verified_nontest": int(len(rr)), "assignment_copies": int(rr.assignment_copy.sum()),
     "copies_by_year": rr[rr.assignment_copy == 1].created.dt.year.value_counts().sort_index().to_dict()}
H = []
for h, g in rr[rr.created >= "2021-01-01"].groupby("half"):
    nc = g[g.assignment_copy == 0]; prim = nc[nc.n_student >= 3]
    H.append({"half": h, "n": int(len(g)), "copy_share": float(g.assignment_copy.mean()), "n_noncopy": int(len(nc)),
              "noncopy_zero": float((nc.n_student == 0).mean()), "noncopy_one_two": float(nc.n_student.between(1, 2).mean()), "noncopy_3plus": float((nc.n_student >= 3).mean()),
              "primary_n": int(len(prim)), "primary_starter_share": float(prim.starter.mean()) if len(prim) else None, "median_obs_days": float(g.obs_days.median())})
R["by_half_year"] = H
nc = rr[rr.assignment_copy == 0]
R["noncopy_by_year"] = {int(y): {"n": int(len(g)), "zero": float((g.n_student == 0).mean()), "one": float((g.n_student == 1).mean()), "two": float((g.n_student == 2).mean()), "three_plus": float((g.n_student >= 3).mean())} for y, g in nc.groupby(nc.created.dt.year) if y >= 2016}
x = nc[nc.created.dt.year.isin([2025])]
R["obs_window_2025"] = {w: float((g.n_student == 0).mean()) for w, g in x.groupby(np.where(x.obs_days >= 365, "ge_1y", "lt_1y"))}
json.dump(R, open(os.path.join(V2, "results_record_generation.json"), "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in R.items() if k != "by_half_year"}, indent=1, default=float))
print(pd.DataFrame(H).round(3).to_string(index=False))
