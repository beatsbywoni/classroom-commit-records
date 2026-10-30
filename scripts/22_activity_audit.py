#!/usr/bin/env python3
"""논문 2 v3 — 학생 활동 분류 규칙 검증용 커밋 특성 추출 (2026-10-30, 6차 작업지시서).
검증 Classroom 저장소(테스트 org 포함 전부)의 비봇 커밋마다: 작성 시각이 저장소 생성 이전인지, 작성자 식별자(noreply 로그인·이메일 로컬파트·이름)가
저장소 이름 끝의 로그인과 일치하는지 계산. 이름·이메일은 저장하지 않고 일치 여부(불리언)만 저장. 커밋 제목(subject)은 수동 검토용으로만 저장하며 공개 패키지에는 넣지 않음.
출력: data/v2/activity_audit/part_{k}.csv (repo, sha, author_ts, pre_creation, name_match, noreply)
사용: python3 22_activity_audit.py K N  (전체를 N 조각으로 나눠 K번째 처리)"""
import os, sys, gzip, json, re
import pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2")
OUT = os.path.join(V2, "activity_audit"); os.makedirs(OUT, exist_ok=True)
k, n = int(sys.argv[1]), int(sys.argv[2])
fl = pd.read_csv(os.path.join(V2, "sample_flags.csv"), usecols=["repo", "ghc_verified"], low_memory=False)
repos = sorted(fl[fl.ghc_verified == 1].repo)
created = {}
for line in open(os.path.join(D, "repos_enumerated.jsonl")):
    r = json.loads(line); created[r["full_name"]] = pd.Timestamp(r["created_at"]).timestamp()
NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$", re.I)
def cands(name, email):
    c = set(); email = (email or "").strip(); name = (name or "").strip()
    m = NOREPLY.match(email)
    if m: c.add(m.group(1).lower())
    if "@" in email: c.add(email.split("@")[0].lower())
    if name:
        c.add(re.sub(r"[^a-z0-9]", "", name.lower())); c.add(re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))
    return {x for x in c if len(x) >= 3}, bool(m)
def matches(repo_name, cs):
    nl = repo_name.lower(); nn = re.sub(r"[^a-z0-9]", "", nl)
    for x in cs:
        if nl.endswith("-" + x) or nl == x or ("-" + x + "-") in nl or (len(x) >= 5 and nn.endswith(re.sub(r"[^a-z0-9]", "", x))):
            return True
    return False
rows = []
for i, repo in enumerate(repos):
    if i % n != k: continue
    fn = os.path.join(D, "logs", repo.replace("/", "__") + ".log.gz")
    if not os.path.exists(fn): continue
    try: txt = gzip.open(fn, "rt", errors="replace").read()
    except Exception: continue
    rname = repo.split("/")[1]; ct = created.get(repo)
    for rec in txt.split("\x1e")[1:]:
        f = rec.split("\x1f")
        if len(f) < 7: continue
        sha, an, ae, at, cmt = f[0][:12], f[1], f[2], f[3], f[4]
        if "[bot]" in an or "[bot]" in ae or an.lower() in ("github classroom", "github-classroom"): continue
        cs, nr = cands(an, ae)
        try: at = int(at); cmt = int(cmt)
        except Exception: at = cmt = None
        subj = (f[6].strip().splitlines() or [""])[0][:120] if len(f) > 6 else ""
        rows.append((repo, sha, at, cmt, int(at is not None and ct is not None and at < ct - 60), int(cmt is not None and ct is not None and cmt < ct - 60), int(matches(rname, cs)), int(nr), subj))
pd.DataFrame(rows, columns=["repo", "sha", "author_ts", "committer_ts", "pre_creation", "pre_creation_committer", "name_match", "noreply", "subject"]).to_csv(os.path.join(OUT, f"part_{k}.csv"), index=False)
print("part", k, "rows", len(rows))
