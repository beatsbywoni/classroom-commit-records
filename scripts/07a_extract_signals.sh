#!/usr/bin/env bash
# ============================================================
# 논문 2 — 07a 신호 추출 (등록 동결 정의 그대로: 신호 1~6, 8 + 라벨·공변량)
# ※ OSF 등록(2026-08-06, Accepted) 이후 첫 outcome 계산 스크립트
#
# 사용법:  bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/07a_extract_signals.sh
# 입력:   data/logs/*.log.gz, data/repos_enumerated.jsonl, data/.salt
# 산출:   data/signals_repo.csv  (저장소 1행: 신호 7종 + era/trailer/공변량)
#         data/cohort_p95.csv    (era×언어군 코호트별 large-paste 임계)
# 소요:   ~10–20분
#
# 구현 결정(공개 기록 — DEVIATIONS_IMPLEMENTATION_NOTES.md 참조):
#  - 신호는 '사람 저자' 커밋에서만 계산(봇 정규식은 등록문 §2와 동일)
#  - merge 커밋(부모≥2)은 add/del 기반 신호(1·2·8)에서 제외, 시간 신호(3·6)에는 포함
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
PY="${SCRIPT_DIR}/.extract_signals_runner.py"

cat > "$PY" <<'PYEOF'
import csv, gzip, hashlib, json, math, os, re, statistics, sys
from multiprocessing import Pool
from datetime import datetime, timezone
from collections import defaultdict

DATA = sys.argv[1]
LOGS = os.path.join(DATA, "logs")
JSONL = os.path.join(DATA, "repos_enumerated.jsonl")
SALT_F = os.path.join(DATA, ".salt")
OUT = os.path.join(DATA, "signals_repo.csv")
OUT_P95 = os.path.join(DATA, "cohort_p95.csv")

SALT = open(SALT_F).read().strip() if os.path.exists(SALT_F) else ""
BOT_RE = re.compile(r'(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)', re.I)
AI_RE  = re.compile(r'co-?authored-by:\s*.*?(copilot|claude|anthropic|cursor|devin|aider|codex|openai|gemini|chatgpt)', re.I)
TESTDIR_RE  = re.compile(r'(^|/)(tests?|spec)(/|$)', re.I)
TESTFILE_RE = re.compile(r'(^test_|_test\.|Test\.|\.spec\.)')
NOREPLY = re.compile(r'^(\d+\+)?([^@]+)@users\.noreply\.github\.com$', re.I)
PRE_CUT  = 1669852800   # 2022-12-01
POST_CUT = 1672531200   # 2023-01-01

def canon(ae, an):
    ae = ae.strip().lower()
    m = NOREPLY.match(ae)
    if m: return "gh:" + m.group(2)
    return ae if ae else "name:" + an.strip().lower()

def h(x): return hashlib.sha256((SALT + x).encode()).hexdigest()[:16]

def lang_family(lang):
    if not lang: return "other"
    l = lang.lower()
    if l == "python": return "python"
    if l in ("java", "kotlin"): return "java_kotlin"
    if l in ("c", "c++"): return "c_cpp"
    if l in ("javascript", "typescript"): return "js_ts"
    if l == "c#": return "csharp"
    if l in ("html", "css", "scss"): return "web_markup"
    if l == "jupyter notebook": return "notebook"
    return "other"

def parse_one(fname):
    repo = fname[:-7].replace("__", "/", 1)
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    commits = []   # (ts, is_merge, add, del, files, is_trailer)
    n_bot = 0
    authors = defaultdict(int)
    for rec in text.split("\x1e"):
        parts = rec.split("\x1f")
        if len(parts) < 7: continue
        an, ae, at, parents, body = parts[1], parts[2], parts[3], parts[5], parts[6]
        tail = parts[7] if len(parts) > 7 else ""
        if BOT_RE.search((an + "|" + ae).lower()):
            n_bot += 1; continue
        try: ts = int(at)
        except ValueError: continue
        is_merge = parents.strip().count(" ") >= 1
        add = dele = 0; files = []
        for line in tail.splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                a, d, p = cols
                if a.isdigit(): add += int(a)
                if d.isdigit(): dele += int(d)
                files.append(p)
        commits.append((ts, is_merge, add, dele, files, bool(AI_RE.search(body))))
        authors[h(canon(ae, an))] += 1
    if not commits:
        return (repo, repo.split("/")[0], "", 0, 0, n_bot, 0, 0,
                None, None, None, None, None, [], [], 0)
    commits.sort(key=lambda c: c[0])
    ts_all   = [c[0] for c in commits]
    nonmerge = [c for c in commits if not c[1]]
    n_h, n_merge = len(commits), len(commits) - len(nonmerge)
    n_trailer = sum(1 for c in commits if c[5])
    # 신호 1: median (add+del) over non-merge commits, log1p
    sig1 = round(math.log1p(statistics.median([c[2] + c[3] for c in nonmerge])), 6) if nonmerge else None
    # 신호 3: share of commits within <30min of previous
    gaps = [1 for i in range(1, len(ts_all)) if ts_all[i] - ts_all[i-1] < 1800]
    sig3 = round(len(gaps) / (n_h - 1), 6) if n_h >= 2 else None
    # 신호 4: same-file >=3 consecutive-commit arcs / n_commits
    arcs = 0; run = {}
    prev_files = set()
    for c in commits:
        fs = set(c[4])
        new_run = {}
        for fpath in fs:
            r = run.get(fpath, 0) + 1 if fpath in prev_files else 1
            new_run[fpath] = r
            if r == 3: arcs += 1
        run = new_run; prev_files = fs
    sig4 = round(arcs / n_h, 6)
    # 신호 5: share of commits touching test paths
    t_n = sum(1 for c in commits if any(TESTDIR_RE.search(p) or TESTFILE_RE.search(p.rsplit("/",1)[-1]) for p in c[4]))
    sig5 = round(t_n / n_h, 6)
    # 신호 6: IQR(ts)/span
    span = ts_all[-1] - ts_all[0]
    if span > 0 and n_h >= 4:
        q = statistics.quantiles(ts_all, n=4)
        sig6 = round((q[2] - q[0]) / span, 6)
    else:
        sig6 = None
    main = max(authors.items(), key=lambda kv: kv[1])[0] if authors else ""
    adds_nm    = [c[2] for c in nonmerge]
    trailer_nm = [c[5] for c in nonmerge]
    return (repo, repo.split("/")[0], main, n_h, n_merge, n_bot, len(authors), n_trailer,
            sig1, sig3, sig4, sig5, sig6, adds_nm, trailer_nm, ts_all[0])

def pctl(xs, p):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * p
    f = math.floor(k); c = math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)

if __name__ == "__main__":
    lang = {}
    with open(JSONL) as f:
        for line in f:
            try:
                r = json.loads(line); lang[r["full_name"]] = lang_family(r.get("language"))
            except Exception: pass

    files = sorted(os.listdir(LOGS))
    print(f"== 07a 신호 추출: {len(files)}개 로그 (pass 1) ==", flush=True)
    rows = []
    with Pool(8) as pool:
        for i, r in enumerate(pool.imap_unordered(parse_one, files, chunksize=200)):
            if r: rows.append(r)
            if (i + 1) % 5000 == 0: print(f"  …{i+1}/{len(files)}", flush=True)

    print("== pass 2: 코호트(era×언어군) P95 임계 → 신호 2·8 ==", flush=True)
    def era_of(first_ts):
        if not first_ts: return ""
        if first_ts < PRE_CUT: return "pre"
        if first_ts >= POST_CUT: return "post"
        return "buffer"
    cohort_adds = defaultdict(list)
    for r in rows:
        fam = lang.get(r[0], "other"); e = era_of(r[15])
        if e in ("pre", "post"):
            cohort_adds[(e, fam)].extend(r[13])
    p95 = {k: pctl(v, 0.95) for k, v in cohort_adds.items() if len(v) >= 100}
    fallback = pctl([a for v in cohort_adds.values() for a in v], 0.95)
    with open(OUT_P95, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["era", "lang_family", "n_commits", "p95_add"])
        for (e, fam), v in sorted(cohort_adds.items()):
            w.writerow([e, fam, len(v), p95.get((e, fam), fallback)])

    iso = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d") if t else ""
    hdr = ["repo","org","student_hash","lang_family","first_date","era","pre2015",
           "n_commits_human","n_merge","n_bot_commits","n_authors_human","n_trailer_commits","trailer",
           "sig1_edit_granularity","sig2_large_paste","sig3_iteration_burst","sig4_error_recovery",
           "sig5_test_engagement","sig6_dispersion","sig8_ai_paste_cooccur","p95_used"]
    n_inc = 0
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(hdr)
        for r in rows:
            (repo, org, main, n_h, n_merge, n_bot, n_auth, n_tr,
             s1, s3, s4, s5, s6, adds, trailers, first_ts) = r
            fam = lang.get(repo, "other"); e = era_of(first_ts)
            thr = p95.get((e, fam), fallback)
            if adds and thr is not None:
                s2 = round(sum(1 for a in adds if a >= thr) / len(adds), 6)
                s8 = round(sum(1 for a, t in zip(adds, trailers) if t and a >= thr) / len(adds), 6)
            else:
                s2 = s8 = None
            if n_h >= 5 and n_auth >= 1: n_inc += 1
            na = lambda x: "" if x is None else x
            w.writerow([repo, org, main, fam, iso(first_ts), e,
                        1 if (first_ts and first_ts < 1420070400) else 0,
                        n_h, n_merge, n_bot, n_auth, n_tr, 1 if n_tr > 0 else 0,
                        na(s1), na(s2), na(s3), na(s4), na(s5), na(s6), na(s8), na(thr)])
    print(f"\n== 완료: {len(rows)}행 (포함기준 충족 {n_inc:,}) → {OUT} ==")
    print(f"   코호트 임계표: {OUT_P95}")
    print("   다음: 07b_embed_messages.sh (신호 7) → 08 분석")
PYEOF

python3 "$PY" "$DATA"
