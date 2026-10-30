#!/usr/bin/env python3
"""논문 2 v4 — 플랫폼이 복사한 시작 코드(starter code) 표시 (2026-10-30, 독립 감사 반영).
정의: 저장소의 루트 커밋(부모 없음) 가운데 GitHub Classroom 봇(작성자 github-classroom[bot])이 만든 커밋이 있으면 root_bot = 1,
그 커밋들이 추가한 줄 수를 root_bot_add로 기록. 분석에서는 root_bot_add >= 20 을 '시작 코드가 있는 저장소'로 쓴다.
(이전 표 repo_bot_starter.csv의 bot_add는 봇 패턴에 맞는 모든 커밋의 추가 줄 수 합이어서 dependabot·github-actions 커밋까지 포함했다.)
출력: data/v2/repo_starter.csv (repo, root_bot, root_bot_add)"""
import os, gzip
from multiprocessing import Pool
import pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2"); LOGS = os.path.join(D, "logs")
CLASSROOM_BOT = "github-classroom[bot]"

def parse(fname):
    repo = fname[:-7].replace("__", "/", 1)
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f: text = f.read()
    except Exception:
        return (repo, 0, 0)
    root_bot, add = 0, 0
    for rec in text.split("\x1e"):
        p = rec.split("\x1f")
        if len(p) < 7 or p[5].strip(): continue          # keep root commits only (no parents)
        if p[1].strip().lower() != CLASSROOM_BOT: continue
        root_bot = 1
        for l in (p[7] if len(p) > 7 else "").splitlines():
            q = l.split("\t")
            if len(q) == 3 and q[0].isdigit(): add += int(q[0])
    return (repo, root_bot, add)

if __name__ == "__main__":
    files = sorted(f for f in os.listdir(LOGS) if f.endswith(".log.gz"))
    with Pool(2) as pool: rows = pool.map(parse, files, chunksize=200)
    out = pd.DataFrame(rows, columns=["repo", "root_bot", "root_bot_add"]); out.to_csv(os.path.join(V2, "repo_starter.csv"), index=False)
    print(len(out), "repositories;", int(out.root_bot.sum()), "with a Classroom-bot root commit;", int((out.root_bot_add >= 20).sum()), "with >= 20 lines")
