#!/usr/bin/env python3
"""논문 2 v2 — Stage 1: 표본 재정의 플래그 + 기술통계 (TOCE 리젝 후 교정 분석용, 2026-10-30)
입력: data/repos_enumerated.jsonl, data/repo_summary.csv, data/signals_repo.csv, data/student_repo_map.csv
출력: data/v2/sample_flags.csv, data/v2/descriptives_v2.md
"""
import json, os, re, sys
import pandas as pd, numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
V2 = os.path.join(D, "v2"); os.makedirs(V2, exist_ok=True)

rows = []
with open(os.path.join(D, "repos_enumerated.jsonl")) as f:
    for line in f:
        try: rows.append(json.loads(line))
        except Exception: pass
e = pd.DataFrame(rows)
e["desc"] = e["desc"].fillna("")
e["ghc_desc"] = e.desc.str.contains(r"created by GitHub Classroom", case=False, regex=True)
e["ghc_name"] = e.full_name.str.contains("github-classroom", case=False)
e["ghc_verified"] = e.ghc_desc | e.ghc_name
e["owner"] = e.full_name.str.split("/").str[0]
ASSIGN_RE = re.compile(r"(assignment|homework|\bhw\d|lab\d|lab-|exercise|project-?\d|starter|week-?\d|cs\d{2,3}|^[a-z0-9-]+-[a-z0-9]+-[a-z0-9]+$)", re.I)
e["name_coursework"] = e.full_name.str.split("/").str[1].apply(lambda s: bool(ASSIGN_RE.search(s)))
e["created_year"] = pd.to_datetime(e.created_at, errors="coerce").dt.year

rs = pd.read_csv(os.path.join(D, "repo_summary.csv"))
sg = pd.read_csv(os.path.join(D, "signals_repo.csv"), usecols=["repo","org","student_hash","lang_family","first_date","era","n_commits_human","n_authors_human","n_trailer_commits","trailer"])
m = sg.merge(e[["full_name","owner_type","ghc_desc","ghc_name","ghc_verified","name_coursework","fork","stars","created_year"]], left_on="repo", right_on="full_name", how="left").drop(columns=["full_name"])
m = m.merge(rs[["repo","n_commits","last_date"]], on="repo", how="left")
m["first_year"] = pd.to_datetime(m.first_date, errors="coerce").dt.year
m["span_days"] = (pd.to_datetime(m.last_date, errors="coerce") - pd.to_datetime(m.first_date, errors="coerce")).dt.days
m["inc5"] = (m.n_commits_human >= 5) & (m.n_authors_human >= 1)
m["inc3"] = (m.n_commits_human >= 3) & (m.n_authors_human >= 1)
# org 규모 (GHC 검증 표본 내)
oc = m[m.ghc_verified & m.inc3].groupby("org").size().rename("org_n_ghc_inc3")
m = m.merge(oc, left_on="org", right_index=True, how="left"); m["org_n_ghc_inc3"] = m.org_n_ghc_inc3.fillna(0).astype(int)
m.to_csv(os.path.join(V2, "sample_flags.csv"), index=False)

L = ["# v2 표본 기술통계 (Stage 1, 2026-10-30)", ""]
L.append(f"코퍼스 저장소(로그 파싱): {len(m):,} / 열거 {len(e):,}")
L.append(f"GHC 검증(desc 'created by GitHub Classroom' ∨ 이름 github-classroom): 코퍼스 {int(m.ghc_verified.sum()):,} (열거 {int(e.ghc_verified.sum()):,})")
L.append("")
L.append("## 포함기준별 표본 크기 (사람 저자 ≥1)")
for name, flag in [("GHC 검증", m.ghc_verified), ("비-GHC(classroom 명칭)", ~m.ghc_verified), ("전체", m.ghc_verified | ~m.ghc_verified)]:
    for k, inc in [("≥5", m.inc5), ("≥3", m.inc3)]:
        s = m[flag & inc]
        L.append(f"- {name} · 사람커밋{k}: n={len(s):,} (pre {int((s.era=='pre').sum()):,} / post {int((s.era=='post').sum()):,} / buffer {int((s.era=='buffer').sum()):,}; trailer {int(s.trailer.sum()):,}; Organization 소유 {s.owner_type.eq('Organization').mean():.1%})")
L.append("")
g = m[m.ghc_verified & m.inc3]
L.append("## GHC 검증 ∧ 사람커밋≥3 표본 (주 표본 후보)")
L.append(f"- n={len(g):,}; org 수 {g.org.nunique():,}; org당 저장소 중앙값 {g.groupby('org').size().median():.0f}, 최대 {g.groupby('org').size().max()}")
L.append(f"- org 규모 ≥5인 org: {(g.groupby('org').size()>=5).sum()} (저장소 {int((g.org_n_ghc_inc3>=5).sum()):,})")
both = g.groupby("org").era.agg(lambda s: set(s) >= {"pre","post"})
L.append(f"- 양 era에 걸친 org: {int(both.sum())} (저장소 {int(g.org.isin(both[both].index).sum()):,})")
L.append(f"- 연도별 n: " + ", ".join(f"{int(y)}:{n}" for y, n in g.groupby("first_year").size().items()))
L.append(f"- 언어군(상위): " + ", ".join(f"{k}:{v}" for k, v in g.lang_family.value_counts().head(8).items()))
L.append(f"- 저장소 기간(일) 중앙값 {g.span_days.median():.0f}, 사람 커밋 중앙값 {g.n_commits_human.median():.0f}, 단일저자 비율 {(g.n_authors_human==1).mean():.1%}")
# 학생
st = g[g.student_hash.notna() & (g.student_hash != "")]
sc = st.groupby("student_hash").agg(n=("repo","size"), eras=("era", lambda s: set(s)), first=("first_date","min"), last=("first_date","max"))
sc["span"] = (pd.to_datetime(sc["last"]) - pd.to_datetime(sc["first"])).dt.days
L.append("")
L.append("## 학생(주 저자 해시) — GHC 검증 ∧ ≥3")
L.append(f"- 고유 학생 {len(sc):,}; ≥2 저장소 {int((sc.n>=2).sum()):,}; ≥3 {int((sc.n>=3).sum()):,}")
L.append(f"- ≥2 저장소 학생의 활동기간(첫~마지막 저장소 시작, 일): 중앙값 {sc[sc.n>=2].span.median():.0f}, p75 {sc[sc.n>=2].span.quantile(.75):.0f}, p90 {sc[sc.n>=2].span.quantile(.9):.0f}")
L.append(f"- pre·post 양 era 모두에 저장소를 가진 학생: {int(sc.eras.apply(lambda s: {'pre','post'} <= s).sum()):,}")
L.append("")
L.append("## 비-GHC 저장소 표본 예시 (무작위 10)")
for r in m[~m.ghc_verified & m.inc5].sample(10, random_state=7).repo: L.append(f"- {r}")
open(os.path.join(V2, "descriptives_v2.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
