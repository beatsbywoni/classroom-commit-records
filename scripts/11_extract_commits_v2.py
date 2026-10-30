#!/usr/bin/env python3
"""논문 2 v2 — Stage 2a: 로그 1회 통과 → 커밋 단위 표 (data/v2/commits.csv.gz)
07a와 동일 파싱 규칙(봇 정규식, AI trailer 정규식, 테스트 경로, salt 해시) 유지. 신호 계산은 12_signals_v2.py에서.
사용: nohup python3 scripts/11_extract_commits_v2.py > data/v2/extract.log 2>&1 &
"""
import csv, gzip, hashlib, os, re, sys, time
from multiprocessing import Pool
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
LOGS = os.path.join(D, "logs"); V2 = os.path.join(D, "v2"); os.makedirs(V2, exist_ok=True)
SALT = open(os.path.join(D, ".salt")).read().strip()
BOT_RE = re.compile(r'(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)', re.I)
AI_RE  = re.compile(r'co-?authored-by:\s*.*?(copilot|claude|anthropic|cursor|devin|aider|codex|openai|gemini|chatgpt)', re.I)
SO_RE  = re.compile(r'^\s*signed-off-by\s*:', re.I | re.M)
CO_RE  = re.compile(r'^\s*co-?authored-by\s*:', re.I | re.M)   # 모든 Co-authored-by (사람 포함) → 사람 공저자 trailer = CO ∧ ¬AI
TRAILER_LINE = re.compile(r'^\s*[A-Za-z][A-Za-z-]+:\s+\S', re.M)   # 'Key: value' 꼴 줄 (trailer)
TESTDIR_RE  = re.compile(r'(^|/)(tests?|spec)(/|$)', re.I)
TESTFILE_RE = re.compile(r'(^test_|_test\.|Test\.|\.spec\.)')
NOREPLY = re.compile(r'^(\d+\+)?([^@]+)@users\.noreply\.github\.com$', re.I)
def canon(ae, an):
    ae = ae.strip().lower(); m = NOREPLY.match(ae)
    return "gh:" + m.group(2) if m else (ae if ae else "name:" + an.strip().lower())
def h(x): return hashlib.sha256((SALT + x).encode()).hexdigest()[:16]
def parse_one(fname):
    repo = fname[:-7].replace("__", "/", 1)
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f: text = f.read()
    except Exception: return [], (repo, 0, 0, 0, 0)
    out = []; filesets = []
    for rec in text.split("\x1e"):
        parts = rec.split("\x1f")
        if len(parts) < 7: continue
        sha, an, ae, at, parents, body = parts[0].strip()[:12], parts[1], parts[2], parts[3], parts[5], parts[6]
        tail = parts[7] if len(parts) > 7 else ""
        try: ts = int(at)
        except ValueError: continue
        is_bot = 1 if BOT_RE.search((an + "|" + ae).lower()) else 0
        is_merge = 1 if parents.strip().count(" ") >= 1 else 0
        add = dele = nf = nt = 0; fs = []
        for line in tail.splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d, p = cols; nf += 1; fs.append(p)
                if a.isdigit(): add += int(a)
                if d.isdigit(): dele += int(d)
                if TESTDIR_RE.search(p) or TESTFILE_RE.search(p.rsplit("/", 1)[-1]): nt += 1
        m = AI_RE.search(body)
        tool = m.group(1).lower() if m else ""
        so = 1 if SO_RE.search(body) else 0
        co_h = 1 if (CO_RE.search(body) and not m) else 0
        # trailer 줄 제거 후 메시지 길이 (학생 언어만)
        msg = "\n".join(l for l in body.splitlines() if not TRAILER_LINE.match(l)).strip()
        out.append((repo, sha, ts, is_bot, is_merge, h(canon(ae, an)), add, dele, nf, nt, 1 if m else 0, tool, so, co_h, len(msg), msg.count("\n") + 1 if msg else 0))
        if not is_bot: filesets.append((ts, set(fs)))
    # 동일 파일 연속 재수정 run (사람 커밋, 시간순; 07a 규칙) — k=2,3,4 변형
    filesets.sort(key=lambda x: x[0]); arcs = {2: 0, 3: 0, 4: 0}; run = {}; prev = set()
    for _, fs in filesets:
        new = {}
        for fp in fs:
            r = run.get(fp, 0) + 1 if fp in prev else 1
            new[fp] = r
            if r in arcs: arcs[r] += 1
        run = new; prev = fs
    return out, (repo, len(filesets), arcs[2], arcs[3], arcs[4])
if __name__ == "__main__":
    files = sorted(os.listdir(LOGS)); t0 = time.time()
    print(f"== 11 커밋 추출: {len(files):,} 로그 ==", flush=True)
    n = 0
    fa = open(os.path.join(V2, "repo_arcs.csv"), "w", newline=""); wa = csv.writer(fa); wa.writerow(["repo","n_human","arcs2","arcs3","arcs4"])
    with gzip.open(os.path.join(V2, "commits.csv.gz"), "wt", newline="") as f, Pool(4) as pool:
        w = csv.writer(f)
        w.writerow(["repo","sha","ts","is_bot","is_merge","author_hash","add","del","n_files","n_test_files","ai_trailer","ai_tool","signedoff","coauthor_human","msg_len","msg_lines"])
        for i, (rows, arc) in enumerate(pool.imap(parse_one, files, chunksize=100)):
            w.writerows(rows); n += len(rows); wa.writerow(arc)
            if (i + 1) % 2000 == 0: print(f"  …{i+1:,}/{len(files):,} 로그, {n:,} 커밋, {time.time()-t0:.0f}s", flush=True)
    fa.close()
    print(f"== 완료: {n:,} 커밋, {time.time()-t0:.0f}s ==", flush=True)
