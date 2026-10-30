#!/usr/bin/env bash
# ============================================================
# CodeBench(UFAM) v1.81 데이터셋 다운로드 — 수렴타당도 보조 데이터
# 사용법 (터미널 한 줄):
#   bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/04_download_codebench.sh
# 산출: 논문2_작업/data/codebench/cb_dataset_*.tar.gz (18개 학기, 총 수 GB)
# 중단 후 재실행하면 이어받기(-C -) 됨.
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${SCRIPT_DIR}/../data/codebench"
mkdir -p "$DEST"
BASE="https://codebench.icomp.ufam.edu.br/dataset/files"

SEMS="2016_1 2016_2 2017_1 2017_2 2018_1 2018_2 2019_1 2019_2 2020_ERE 2020_1 2020_2 2021_1 2021_2 2022_1 2022_2 2023_1 2023_2 2024_1"

echo "== CodeBench v1.81 다운로드 (18개 학기) → $DEST =="
for s in $SEMS; do
  f="cb_dataset_${s}_v1.81.tar.gz"
  if [ -s "${DEST}/${f}" ] && ! [ -s "${DEST}/${f}.part" ]; then
    echo "  [있음] $f"; continue
  fi
  echo "  [받는 중] $f"
  if ! curl -L -C - --connect-timeout 15 --retry 1 -o "${DEST}/${f}" "${BASE}/${f}"; then
    echo "  [실패] $f — 서버 연결 불가면 아래 메모 참고 후 전체 중단(Ctrl+C) 권장"
    echo "  메모: 2026-08-05 현재 한국→UFAM 라우팅 문제로 접속 불가 사례 확인."
    echo "        서버 자체는 정상(해외 경유 시 접속됨). 하루 이틀 뒤 재시도 또는 VPN(미국) 사용."
    FAILS=$(( ${FAILS:-0} + 1 ))
    [ "$FAILS" -ge 2 ] && { echo "  연속 실패 — 중단합니다. 나중에 재실행하세요."; exit 1; }
  else
    FAILS=0
  fi
done
echo "== 완료. 압축은 풀지 말고 그대로 두세요(분석 단계에서 스트리밍 처리) =="
