#!/usr/bin/env bash
# ============================================================
# 논문 2 파일럿 — 공개 GitHub Classroom-패턴 저장소 카운트
#
# 사용법 (터미널에서 한 줄):
#   bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/01_pilot_count.sh
#
# (선택) GitHub 토큰이 있으면 3배 빠름:
#   GITHUB_TOKEN=ghp_xxx bash .../01_pilot_count.sh
#
# 결과: 콘솔 표 + 논문2_작업/pilot_count_YYYYMMDD_HHMM.csv 저장
# 요구: macOS 기본 curl·python3 만 사용 (추가 설치 불필요)
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="${SCRIPT_DIR}/../pilot_count_${STAMP}.csv"

# 비인증 검색 API는 10 req/min → 7초 간격. 토큰 있으면 30 req/min → 3초.
SLEEP=7
[ -n "${GITHUB_TOKEN:-}" ] && SLEEP=3

api() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    curl -s -H "Accept: application/vnd.github+json" \
         -H "Authorization: Bearer ${GITHUB_TOKEN}" "$1"
  else
    curl -s -H "Accept: application/vnd.github+json" "$1"
  fi
}

count() { # $1=라벨  $2=URL
  local n
  n=$(api "$2" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if "total_count" in d:
        print(d["total_count"])
    else:
        print("ERR:" + str(d.get("message", "unknown"))[:80])
except Exception:
    print("ERR:parse")')
  printf "  %-46s %s\n" "$1" "$n"
  echo "\"$1\",\"$2\",\"$n\"" >> "$OUT"
  sleep "$SLEEP"
}

echo "label,url,total_count" > "$OUT"
echo "== 공개 Classroom-패턴 저장소 파일럿 카운트 =="
echo "   시작: $(date '+%Y-%m-%d %H:%M')  (쿼리 간격 ${SLEEP}s, 총 ~16쿼리)"
echo ""

R="https://api.github.com/search/repositories?per_page=1&q="
U="https://api.github.com/search/users?per_page=1&q="

echo "[A] 저장소 이름/토픽 패턴"
count "repo명: github-classroom"          "${R}github-classroom+in:name"
count "repo명: classroom"                 "${R}classroom+in:name"
count "topic: github-classroom"           "${R}topic:github-classroom"
count "topic: classroom-assignment"       "${R}topic:classroom-assignment"
count "repo명: assignment"                "${R}assignment+in:name"
count "repo명: cs1"                       "${R}cs1+in:name"

echo ""
echo "[B] 'classroom in:name' 연도별 (pre/post-ChatGPT 구도)"
count "  생성 2021"                       "${R}classroom+in:name+created:2021-01-01..2021-12-31"
count "  생성 2022"                       "${R}classroom+in:name+created:2022-01-01..2022-12-31"
count "  생성 2023"                       "${R}classroom+in:name+created:2023-01-01..2023-12-31"
count "  생성 2024"                       "${R}classroom+in:name+created:2024-01-01..2024-12-31"
count "  생성 2025"                       "${R}classroom+in:name+created:2025-01-01..2025-12-31"
count "  생성 2026"                       "${R}classroom+in:name+created:2026-01-01..2026-12-31"

echo ""
echo "[C] 활동성 필터 (커밋이 실제로 있는 저장소 근사)"
count "classroom+size>50KB"               "${R}classroom+in:name+size:%3E50"
count "classroom+2024이후push"            "${R}classroom+in:name+pushed:%3E2024-01-01"

echo ""
echo "[D] 조직(org) 패턴"
count "org명: classroom"                  "${U}classroom+type:org"
count "org명: cs1"                        "${U}cs1+type:org"

echo ""
echo "== 완료. CSV 저장: $OUT =="
echo "   해석 메모: [A]는 상한 추정(중복·비교육용 포함), [B]의 연도 분포로"
echo "   pre/post cohort 실현 가능성 판단, [C]로 실질 표본 하한 추정."
