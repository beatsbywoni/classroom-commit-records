#!/usr/bin/env bash
# ============================================================
# 논문 2 — 학생(저자) 연결 분석: within-student 설계 실현 가능성 판정
#
# 사용법:  bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/06_author_linkage.sh
#
# 하는 일: 포함기준(커밋≥5·사람저자≥1) 저장소만 재스캔 →
#   - 학생 식별자(이메일)를 salted SHA-256 해시로 익명화 (원문 비보존)
#   - 학생별 저장소 수 분포, ≥2개 저장소 학생 수 (within-student 표본)
#   - AI-trailer 저장소 저자 중 무-trailer 저장소도 가진 학생 수 (H2 표본)
# 산출:  data/author_linkage_stats.txt, data/student_repo_map.csv (해시 ID만)
# 소요:  5–15분
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
PY="${SCRIPT_DIR}/.author_linkage_runner.py"

cat > "$PY" <<'PYEOF'
import csv, gzip, hashlib, os, re, secrets, sys
from multiprocessing import Pool
from collections import defaultdict, Counter

DATA = sys.argv[1]
LOGS = os.path.join(DATA, "logs")
SUM  = os.path.join(DATA, "repo_summary.csv")
OUT_TXT = os.path.join(DATA, "author_linkage_stats.txt")
OUT_MAP = os.path.join(DATA, "student_repo_map.csv")
SALT_F  = os.path.join(DATA, ".salt")

if not os.path.exists(SALT_F):
    open(SALT_F, "w").write(secrets.token_hex(16))
SALT = open(SALT_F).read().strip()

BOT_RE = re.compile(r'(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)', re.I)
AI_RE  = re.compile(r'co-?authored-by:\s*.*?(copilot|claude|anthropic|cursor|devin|aider|codex|openai|gemini|chatgpt)', re.I)
NOREPLY = re.compile(r'^(\d+\+)?([^@]+)@users\.noreply\.github\.com$', re.I)

def canon(ae, an):
    """이메일 정규화: noreply는 username 기준, 그 외 소문자 이메일"""
    ae = ae.strip().lower()
    m = NOREPLY.match(ae)
    if m:
        return "gh:" + m.group(2)
    return ae if ae else "name:" + an.strip().lower()

def h(x):
    return hashlib.sha256((SALT + x).encode()).hexdigest()[:16]

# 포함기준 저장소 목록
included, trailer_repos = set(), set()
with open(SUM) as f:
    for row in csv.DictReader(f):
        if int(row["n_commits"]) >= 5 and int(row["n_authors_human"]) >= 1:
            included.add(row["repo"])
            if int(row["ai_trailer_commits"]) > 0:
                trailer_repos.add(row["repo"])

def parse_one(fname):
    repo = fname[:-7].replace("__", "/", 1)
    if repo not in included:
        return None
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    authors = Counter()
    ai_flag = repo in trailer_repos
    for rec in text.split("\x1e"):
        parts = rec.split("\x1f")
        if len(parts) < 7:
            continue
        an, ae = parts[1], parts[2]
        if BOT_RE.search((an + "|" + ae).lower()):
            continue
        authors[h(canon(ae, an))] += 1
    if not authors:
        return None
    # 주 저자(커밋 최다) + 전체 저자
    main = authors.most_common(1)[0][0]
    return (repo, main, list(authors.keys()), ai_flag)

if __name__ == "__main__":
    files = sorted(os.listdir(LOGS))
    print(f"== 포함기준 저장소 {len(included)}개 대상 저자 연결 스캔 ==", flush=True)
    results = []
    with Pool(8) as pool:
        for i, r in enumerate(pool.imap_unordered(parse_one, files, chunksize=200)):
            if r: results.append(r)
            if (i + 1) % 10000 == 0:
                print(f"  …{i+1}/{len(files)}", flush=True)

    stu_repos   = defaultdict(set)   # 주 저자 기준
    stu_ai      = defaultdict(set)   # 학생 → trailer 저장소들
    for repo, main, alls, ai in results:
        stu_repos[main].add(repo)
        if ai:
            stu_ai[main].add(repo)

    per = Counter(len(v) for v in stu_repos.values())
    multi = sum(1 for v in stu_repos.values() if len(v) >= 2)
    multi3 = sum(1 for v in stu_repos.values() if len(v) >= 3)
    # H2: trailer 저장소를 가진 학생 중, 무-trailer 포함 저장소도 가진 학생
    h2_students = sum(1 for s, ai_set in stu_ai.items() if len(stu_repos[s]) > len(ai_set))
    h2_pairs    = sum(min(len(ai_set), len(stu_repos[s]) - len(ai_set)) for s, ai_set in stu_ai.items() if len(stu_repos[s]) > len(ai_set))

    with open(OUT_MAP, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["student_hash", "n_repos", "n_ai_repos", "repos"])
        for s, rs in stu_repos.items():
            w.writerow([s, len(rs), len(stu_ai.get(s, ())), ";".join(sorted(rs))])

    L = []
    L.append(f"저자 연결 분석 (포함기준 저장소 {len(results)}개 파싱)")
    L.append(f"고유 학생(주 저자, 해시): {len(stu_repos):,}")
    L.append(f"저장소 수 분포: 1개={per.get(1,0):,}  2개={per.get(2,0):,}  3개+={sum(v for k,v in per.items() if k>=3):,}")
    L.append(f"within-student 설계 가능(≥2 저장소): {multi:,}명 (≥3: {multi3:,}명)")
    L.append(f"H2 표본: trailer 저장소 보유 학생 {len(stu_ai):,}명 중 무-trailer 저장소도 보유 = {h2_students:,}명 (매칭쌍 {h2_pairs:,})")
    txt = "\n".join(L)
    open(OUT_TXT, "w").write(txt + "\n")
    print("\n" + txt)
    print(f"\n== 저장: {OUT_MAP} / {OUT_TXT} ==")
PYEOF

python3 "$PY" "$DATA"
