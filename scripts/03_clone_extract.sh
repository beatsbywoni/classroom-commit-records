#!/usr/bin/env bash
# ============================================================
# 논문 2 본 크롤 2단계 — bare clone + git log(numstat) 추출
#
# 사용법 (02_enumerate_repos.sh 완료 후):
#   bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/03_clone_extract.sh
#
# 조절 변수(선택, 앞에 붙여서 실행):
#   PAR=6           병렬 클론 수 (기본 6)
#   MIN_KB=1        최소 저장소 크기 KB (기본 1 — 빈 저장소 제외)
#   MAX_REPOS=0     상한 (0=전체; 시험용으로 500 등 지정 가능)
#   KEEP_CLONES=0   1이면 클론 보관 (기본: 로그 추출 후 즉시 삭제)
#   예) PAR=8 MAX_REPOS=500 bash .../03_clone_extract.sh   ← 시험 실행 권장
#
# 산출:
#   data/logs/<owner>__<repo>.log.gz  커밋 헤더(\x1e 구분)+본문+numstat
#   data/clone_failed.txt             실패 목록(삭제·비공개 전환된 저장소)
# 재실행 시 이미 추출된 저장소는 자동 건너뜀 (중단 안전)
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data"
LOG_DIR="${DATA_DIR}/logs"
TMP_DIR="${DATA_DIR}/.clones"
LIST="${DATA_DIR}/repos_to_clone.txt"
JSONL="${DATA_DIR}/repos_enumerated.jsonl"
mkdir -p "$LOG_DIR" "$TMP_DIR"

PAR="${PAR:-6}"
MIN_KB="${MIN_KB:-1}"
MAX_REPOS="${MAX_REPOS:-0}"
KEEP_CLONES="${KEEP_CLONES:-0}"

if [ ! -f "$JSONL" ]; then
  echo "오류: $JSONL 없음 — 먼저 02_enumerate_repos.sh 실행" >&2; exit 1
fi

# 1) 필터링된 클론 목록 생성
python3 - "$JSONL" "$LIST" "$MIN_KB" "$MAX_REPOS" <<'PYEOF'
import json, sys
jsonl, out, min_kb, max_n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rows = []
for line in open(jsonl):
    try: r = json.loads(line)
    except Exception: continue
    if (r.get("size_kb") or 0) < min_kb: continue
    rows.append(r["full_name"])
rows = sorted(set(rows))
if max_n > 0: rows = rows[:max_n]
open(out, "w").write("\n".join(rows) + "\n")
print(f"클론 대상: {len(rows)}개 (size>={min_kb}KB) → {out}")
PYEOF

# 2) 클론+추출 워커
process_repo() {
  local fn="$1"
  local safe="${fn//\//__}"
  local dst="${LOG_DIR}/${safe}.log.gz"
  [ -s "$dst" ] && return 0                       # 이미 완료
  local dir="${TMP_DIR}/${safe}.git"
  rm -rf "$dir"
  local url="https://github.com/${fn}.git"
  [ -n "${GITHUB_TOKEN:-}" ] && url="https://x-access-token:${GITHUB_TOKEN}@github.com/${fn}.git"
  if ! git clone --bare --quiet --no-tags "$url" "$dir" 2>/dev/null; then
    echo "$fn" >> "${DATA_DIR}/clone_failed.txt"; rm -rf "$dir"; return 1
  fi
  # 커밋 레코드: \x1e 시작, \x1f 필드구분: hash/author/email/authored_ts/committed_ts/parents/전체메시지
  # 이어서 numstat 줄(추가TAB삭제TAB경로). 파싱은 분석 단계에서.
  git --git-dir="$dir" log --all --numstat \
      --pretty=format:'%x1e%H%x1f%an%x1f%ae%x1f%at%x1f%ct%x1f%P%x1f%B%x1f' 2>/dev/null \
    | gzip > "$dst" || { rm -f "$dst"; echo "$fn" >> "${DATA_DIR}/clone_failed.txt"; }
  [ "$KEEP_CLONES" = "1" ] || rm -rf "$dir"
  return 0
}
export -f process_repo
export LOG_DIR TMP_DIR DATA_DIR KEEP_CLONES GITHUB_TOKEN 2>/dev/null || true

TOTAL=$(wc -l < "$LIST" | tr -d ' ')
echo "== 클론·추출 시작: ${TOTAL}개, 병렬 ${PAR} (중단해도 재실행하면 이어짐) =="
echo "   진행 확인:  ls ${LOG_DIR} | wc -l"

# 3) 병렬 실행
xargs -n 1 -P "$PAR" -I {} bash -c 'process_repo "$@"' _ {} < "$LIST"

DONE=$(ls "$LOG_DIR" 2>/dev/null | wc -l | tr -d ' ')
FAIL=$( [ -f "${DATA_DIR}/clone_failed.txt" ] && sort -u "${DATA_DIR}/clone_failed.txt" | wc -l | tr -d ' ' || echo 0 )
echo ""
echo "== 완료: 추출 ${DONE} / 실패 ${FAIL} (실패 목록: data/clone_failed.txt) =="
echo "   실패는 대부분 삭제·비공개 전환된 저장소 — 그 자체가 '지금 수집해야 하는 이유'의 기록"
