#!/usr/bin/env bash
# ============================================================
# 논문 2 본 크롤 1단계 — Classroom-패턴 공개 저장소 전수 열거
#
# 사용법 (터미널에서 한 줄, 토큰 강력 권장 — 없으면 3배 느림):
#   GITHUB_TOKEN=ghp_xxx bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/02_enumerate_repos.sh
#
# 특징:
#  - 검색 API의 쿼리당 1,000건 캡을 "생성일 적응 슬라이싱"으로 우회
#  - 중단해도 안전: 재실행하면 완료된 슬라이스는 건너뜀 (state 파일)
#  - 산출: 논문2_작업/data/repos_enumerated.jsonl (저장소당 1줄 JSON)
#  - 예상 소요: 토큰 있음 ~40–60분 / 없음 3시간+
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data"
mkdir -p "$DATA_DIR"

python3 - "$DATA_DIR" <<'PYEOF'
import json, os, sys, time, datetime, urllib.request, urllib.error, urllib.parse

DATA_DIR = sys.argv[1]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SLEEP = 2.2 if TOKEN else 6.5          # 검색 API: 인증 30/min, 비인증 10/min
OUT_F   = os.path.join(DATA_DIR, "repos_enumerated.jsonl")
STATE_F = os.path.join(DATA_DIR, "enum_state.json")

QUERIES = ["classroom in:name", "github-classroom in:name", "topic:github-classroom"]
D0 = datetime.date(2008, 1, 1)
D1 = datetime.date.today()

state = {"done": []}
if os.path.exists(STATE_F):
    state = json.load(open(STATE_F))
done = set(state["done"])

seen = set()
if os.path.exists(OUT_F):
    for line in open(OUT_F):
        try: seen.add(json.loads(line)["full_name"])
        except Exception: pass
out = open(OUT_F, "a")

def api(url, tries=6):
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "struggle-signature-pilot",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                wait = int(e.headers.get("Retry-After") or 0)
                if not wait:
                    reset = e.headers.get("X-RateLimit-Reset")
                    wait = max(5, int(reset) - int(time.time()) + 2) if reset else 60
                wait = min(wait, 300)
                print(f"    …rate limit, {wait}s 대기 (시도 {i+1}/{tries})", flush=True)
                time.sleep(wait)
            elif e.code == 422:   # 슬라이스 결과 빈 페이지 등
                return {"items": [], "total_count": 0}
            else:
                print(f"    HTTP {e.code}: {url[:120]}", flush=True)
                time.sleep(10)
        except Exception as ex:
            print(f"    오류 {ex}; 15s 후 재시도", flush=True)
            time.sleep(15)
    return None

def search_url(q, lo, hi, page=1, per=100):
    qq = urllib.parse.quote(f"{q} created:{lo}..{hi}")
    return f"https://api.github.com/search/repositories?q={qq}&per_page={per}&page={page}"

def total(q, lo, hi):
    d = api(search_url(q, lo, hi, per=1)); time.sleep(SLEEP)
    return None if d is None else d.get("total_count", 0)

def keep(item):
    o = item.get("owner") or {}
    return {
        "full_name": item["full_name"], "owner": o.get("login"), "owner_type": o.get("type"),
        "created_at": item.get("created_at"), "pushed_at": item.get("pushed_at"),
        "size_kb": item.get("size"), "fork": item.get("fork"), "archived": item.get("archived"),
        "language": item.get("language"), "default_branch": item.get("default_branch"),
        "stars": item.get("stargazers_count"),
        "desc": (item.get("description") or "")[:120]}

def harvest(q, lo, hi):
    """total<=1000이 보장된 슬라이스를 페이지네이션 수집"""
    n_new = 0
    for page in range(1, 11):
        d = api(search_url(q, lo, hi, page=page)); time.sleep(SLEEP)
        if d is None: return False
        items = d.get("items", [])
        for it in items:
            fn = it["full_name"]
            if fn not in seen:
                seen.add(fn); out.write(json.dumps(keep(it), ensure_ascii=False) + "\n"); n_new += 1
        if len(items) < 100: break
    out.flush()
    print(f"  [OK] {q} | {lo}..{hi} → 신규 {n_new} (누적 {len(seen)})", flush=True)
    return True

def size_slices():
    return ["0..0","1..5","6..20","21..60","61..200","201..1000","1001..10000",">10000"]

def process(q, lo, hi):
    key = f"{q}|{lo}|{hi}"
    if key in done: return
    t = total(q, lo, hi)
    if t is None:
        print(f"  [건너뜀-오류] {key}", flush=True); return
    if t == 0:
        done.add(key); return
    if t <= 1000:
        if harvest(q, lo, hi): done.add(key)
        return
    lo_d = datetime.date.fromisoformat(lo); hi_d = datetime.date.fromisoformat(hi)
    if lo_d < hi_d:                       # 날짜 반분할
        mid = lo_d + (hi_d - lo_d) // 2
        process(q, lo, str(mid)); process(q, str(mid + datetime.timedelta(days=1)), hi)
        done.add(key)
    else:                                 # 단일 날짜 >1000 → size로 재분할
        print(f"  [단일일자 {t}건] {key} → size 분할", flush=True)
        for s in size_slices():
            k2 = f"{q}|{lo}|{hi}|size:{s}"
            if k2 in done: continue
            qq = urllib.parse.quote(f"{q} created:{lo}..{hi} size:{s}")
            base = f"https://api.github.com/search/repositories?q={qq}&per_page=100&page="
            got_all = True
            for page in range(1, 11):
                d = api(base + str(page)); time.sleep(SLEEP)
                if d is None: got_all = False; break
                items = d.get("items", [])
                for it in items:
                    fn = it["full_name"]
                    if fn not in seen:
                        seen.add(fn); out.write(json.dumps(keep(it), ensure_ascii=False) + "\n")
                if len(items) < 100: break
            if got_all: done.add(k2)
            out.flush()
        done.add(key)

def save_state():
    json.dump({"done": sorted(done)}, open(STATE_F, "w"))

print(f"== 열거 시작 {datetime.datetime.now():%Y-%m-%d %H:%M} | 토큰: {'있음' if TOKEN else '없음(느림!)'} ==", flush=True)
try:
    for q in QUERIES:
        print(f"\n### 쿼리: {q}", flush=True)
        # 연 단위 1차 분할(파일럿 실측상 연 1.5만 이하 → 대부분 월/주 분할로 수렴)
        for y in range(2008, D1.year + 1):
            lo = f"{y}-01-01"; hi = f"{y}-12-31" if y < D1.year else str(D1)
            process(q, lo, hi)
            save_state()
finally:
    save_state(); out.close()

print(f"\n== 완료. 총 {len(seen)}개 저장소 → {OUT_F} ==")
print("   다음: 03_clone_extract.sh 로 클론·로그 추출")
PYEOF
