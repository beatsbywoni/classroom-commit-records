#!/usr/bin/env python3
"""v3: 동일 파일 연속 재수정 run(k=2,3,4)을 학생 커밋(비봇·비상속·비교수자)만으로 재계산 → data/v2/repo_arcs_student.csv"""
import csv, gzip, os, re, sys, time
from multiprocessing import Pool
import pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); LOGS = os.path.join(D, "logs"); V2 = os.path.join(D, "v2")
hf = pd.read_csv(os.path.join(V2, "commit_history_flags.csv.gz"), dtype={"sha": str})
STUDENT = {}
for repo, sha, st in zip(hf.repo, hf.sha, hf.student):
    if st == 1: STUDENT.setdefault(repo, set()).add(sha)
def parse_one(fname):
    repo = fname[:-7].replace("__", "/", 1); keep = STUDENT.get(repo, set())
    if not keep: return (repo, 0, 0, 0, 0)
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f: text = f.read()
    except Exception: return (repo, 0, 0, 0, 0)
    fs_list = []
    for rec in text.split("\x1e"):
        parts = rec.split("\x1f")
        if len(parts) < 7: continue
        sha = parts[0].strip()[:12]
        if sha not in keep: continue
        try: ts = int(parts[3])
        except ValueError: continue
        tail = parts[7] if len(parts) > 7 else ""
        fs = [l.split("\t")[2] for l in tail.splitlines() if len(l.split("\t")) == 3]
        fs_list.append((ts, set(fs)))
    fs_list.sort(key=lambda x: x[0]); arcs = {2: 0, 3: 0, 4: 0}; run = {}; prev = set()
    for _, fs in fs_list:
        new = {}
        for fp in fs:
            r = run.get(fp, 0) + 1 if fp in prev else 1; new[fp] = r
            if r in arcs: arcs[r] += 1
        run = new; prev = fs
    return (repo, len(fs_list), arcs[2], arcs[3], arcs[4])
if __name__ == "__main__":
    files = sorted(os.listdir(LOGS)); t0 = time.time()
    with open(os.path.join(V2, "repo_arcs_student.csv"), "w", newline="") as f, Pool(4) as pool:
        w = csv.writer(f); w.writerow(["repo", "n_student", "arcs2", "arcs3", "arcs4"])
        for row in pool.imap_unordered(parse_one, files, chunksize=200): w.writerow(row)
    print("done", time.time() - t0)
