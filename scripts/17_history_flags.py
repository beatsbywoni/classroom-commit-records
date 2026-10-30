#!/usr/bin/env python3
"""논문 2 v3 — 작업 이력 검증: 전체 코퍼스 커밋에 (a) 상속 이력 플래그(같은 org 내 ≥2 저장소에 등장하는 SHA),
(b) 교수자형 저자 플래그(org 내 ≥5 저장소에 커밋하되 그중 절반 미만에서만 최다 저자) 부여 → data/v2/commit_history_flags.csv.gz
학생 커밋 = 비봇 ∧ 비상속 ∧ 비교수자형. 저장소별 요약 → data/v2/repo_history_audit_all.csv
"""
import os, numpy as np, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2")
c = pd.read_csv(os.path.join(V2, "commits.csv.gz"), dtype={"ai_tool": str, "sha": str}, low_memory=False)
c["org"] = c.repo.str.split("/").str[0]
h = c[c.is_bot == 0].copy()
sha_cnt = h.groupby(["org", "sha"]).repo.nunique().rename("n_repos_with_sha").reset_index()
h = h.merge(sha_cnt, on=["org", "sha"], how="left"); h["inherited"] = (h.n_repos_with_sha >= 2).astype(int)
ns = h[h.inherited == 0]
top = ns.groupby(["repo", "author_hash"]).size().reset_index(name="n").sort_values(["repo", "n"], ascending=[True, False]).drop_duplicates("repo")
top["org"] = top.repo.str.split("/").str[0]
ar = ns.groupby(["org", "author_hash"]).repo.nunique().rename("n_repos").reset_index()
tp = top.groupby(["org", "author_hash"]).size().rename("n_top").reset_index()
ar = ar.merge(tp, on=["org", "author_hash"], how="left").fillna({"n_top": 0})
ar["staff_like"] = ((ar.n_repos >= 5) & (ar.n_top < 0.5 * ar.n_repos)).astype(int)
h = h.merge(ar[["org", "author_hash", "staff_like"]], on=["org", "author_hash"], how="left").fillna({"staff_like": 0})
h["staff_like"] = h.staff_like.astype(int); h["student"] = ((h.inherited == 0) & (h.staff_like == 0)).astype(int)
h[["repo", "sha", "ts", "inherited", "staff_like", "student"]].to_csv(os.path.join(V2, "commit_history_flags.csv.gz"), index=False, compression="gzip")
rs = h.groupby("repo").agg(n_human=("sha", "size"), n_inherited=("inherited", "sum"), n_staff=("staff_like", lambda s: int(((s == 1) & (h.loc[s.index, "inherited"] == 0)).sum())), n_student=("student", "sum"))
rs.to_csv(os.path.join(V2, "repo_history_audit_all.csv"))
print("human commits", len(h), "inherited", int(h.inherited.sum()), "staff(non-inherited)", int(((h.staff_like == 1) & (h.inherited == 0)).sum()), "student", int(h.student.sum()))
