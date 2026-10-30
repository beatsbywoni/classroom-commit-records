#!/usr/bin/env bash
# ============================================================
# 논문 2 — 코퍼스 분포 분석 (사전등록 ⟦TBD⟧ 확정용) — v2 (macOS spawn 수정)
#
# 사용법 (터미널 한 줄):
#   bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/05_corpus_stats.sh
#
# 입력:  data/logs/*.log.gz
# 산출:  data/repo_summary.csv   저장소별 1행 요약
#        data/corpus_stats.txt   전체 분포 헤드라인
# 소요:  약 5–15분 (병렬 8, 진행률 표시)
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
PY="${SCRIPT_DIR}/.corpus_stats_runner.py"

cat > "$PY" <<'PYEOF'
import csv, gzip, os, re, sys
from multiprocessing import Pool
from datetime import datetime, timezone
from collections import Counter

DATA = sys.argv[1]
LOGS = os.path.join(DATA, "logs")
OUT_CSV = os.path.join(DATA, "repo_summary.csv")
OUT_TXT = os.path.join(DATA, "corpus_stats.txt")

AI_RE  = re.compile(r'co-?authored-by:\s*.*?(copilot|claude|anthropic|cursor|devin|aider|codex|openai|gemini|chatgpt)', re.I)
BOT_RE = re.compile(r'(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)', re.I)
CHATGPT_CUT = 1669852800   # 2022-12-01 UTC
POST_CUT    = 1672531200   # 2023-01-01 UTC

def parse_one(fname):
    path = os.path.join(LOGS, fname)
    repo = fname[:-7].replace("__", "/", 1)
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    recs = text.split("\x1e")
    n_c = n_merge = n_bot = ai_n = 0
    tot_add = tot_del = 0
    max_ins = 0
    ts_list = []
    humans, bots, agents = set(), set(), set()
    for rec in recs:
        if not rec.strip():
            continue
        parts = rec.split("\x1f")
        if len(parts) < 7:
            continue
        an, ae, at, parents, body = parts[1], parts[2], parts[3], parts[5], parts[6]
        tail = parts[7] if len(parts) > 7 else ""
        n_c += 1
        if parents.strip().count(" ") >= 1:
            n_merge += 1
        try:
            ts_list.append(int(at))
        except ValueError:
            pass
        ident = (an + "|" + ae).lower()
        if BOT_RE.search(ident):
            n_bot += 1; bots.add(ident)
        else:
            humans.add(ident)
        m = AI_RE.search(body)
        if m:
            ai_n += 1; agents.add(m.group(1).lower())
        add_c = 0
        for line in tail.splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d = cols[0], cols[1]
                if a.isdigit():
                    tot_add += int(a); add_c += int(a)
                if d.isdigit():
                    tot_del += int(d)
        if add_c > max_ins:
            max_ins = add_c
    if n_c == 0:
        return (repo, 0, 0, 0, 0, "", "", 0, 0, 0, 0, "", 0)
    first_ts = min(ts_list) if ts_list else 0
    last_ts  = max(ts_list) if ts_list else 0
    iso = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d") if t else ""
    return (repo, n_c, n_merge, len(humans), len(bots), iso(first_ts), iso(last_ts),
            tot_add, tot_del, max_ins, ai_n, ";".join(sorted(agents)), first_ts)

def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs)-1, int(p/100*len(xs)))] if xs else 0

if __name__ == "__main__":
    files = sorted(os.listdir(LOGS))
    print(f"== 스캔 시작: {len(files)}개 로그 ==", flush=True)
    rows = []
    with Pool(8) as pool:
        for i, r in enumerate(pool.imap_unordered(parse_one, files, chunksize=200)):
            if r: rows.append(r)
            if (i + 1) % 5000 == 0:
                print(f"  …{i+1}/{len(files)}", flush=True)

    hdr = ["repo","n_commits","n_merge","n_authors_human","n_authors_bot","first_date","last_date",
           "total_add","total_del","max_single_insert","ai_trailer_commits","ai_agents"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f); w.writerow(hdr)
        for r in rows: w.writerow(r[:12])

    nc       = [r[1] for r in rows if r[1] > 0]
    n_ge5    = sum(1 for r in rows if r[1] >= 5 and r[3] >= 1)
    solo     = sum(1 for r in rows if r[3] == 1 and r[1] >= 5)
    ai_repos = sum(1 for r in rows if r[10] > 0)
    ai_ge5   = sum(1 for r in rows if r[10] > 0 and r[1] >= 5 and r[3] >= 1)
    pre      = sum(1 for r in rows if r[1] >= 5 and r[3] >= 1 and r[12] and r[12] < CHATGPT_CUT)
    post     = sum(1 for r in rows if r[1] >= 5 and r[3] >= 1 and r[12] and r[12] >= POST_CUT)
    agent_cnt = Counter()
    for r in rows:
        for a in (r[11].split(";") if r[11] else []):
            if a: agent_cnt[a] += 1

    L = []
    L.append(f"코퍼스 스캔 {datetime.now():%Y-%m-%d %H:%M}")
    L.append(f"총 저장소(로그 파싱 성공): {len(rows)}")
    L.append(f"총 커밋: {sum(nc):,}")
    L.append(f"커밋 수 분포: p25={pct(nc,25)} p50={pct(nc,50)} p75={pct(nc,75)} p90={pct(nc,90)} p99={pct(nc,99)}")
    L.append(f"포함기준(커밋≥5 & 사람저자≥1) 충족: {n_ge5:,}  (그중 1인 저장소 {solo:,})")
    L.append(f"pre-ChatGPT(첫 커밋<2022-12): {pre:,} | post(≥2023-01): {post:,}  [포함기준 충족분 기준]")
    L.append(f"AI-trailer 저장소: {ai_repos:,} (포함기준 충족+trailer: {ai_ge5:,})")
    L.append(f"AI agent 분포: " + ", ".join(f"{k}:{v}" for k, v in agent_cnt.most_common()))
    txt = "\n".join(L)
    open(OUT_TXT, "w").write(txt + "\n")
    print("\n" + txt)
    print(f"\n== 저장: {OUT_CSV} / {OUT_TXT} ==")
PYEOF

python3 "$PY" "$DATA"
