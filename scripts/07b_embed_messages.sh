#!/usr/bin/env bash
# ============================================================
# 논문 2 — 07b 신호 7 (msg_informativeness) — multilingual-e5-small 임베딩
#
# 사용법:  bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/07b_embed_messages.sh
# 첫 실행 시 전용 가상환경에 sentence-transformers 자동 설치(~2GB, 수 분).
# 이후 58,516개 저장소의 사람 커밋 메시지(~120만 건)를 임베딩.
# Apple Silicon(MPS) 가속 자동 사용. 예상 1~3시간. **중단해도 재실행하면 이어짐.**
#
# 산출: data/signal7_msg.csv  (repo, n_msgs, sig7_msg_informativeness)
# 정의(등록 동결): 1 − 저장소 내 메시지 임베딩 평균 쌍별 코사인 (n≥2에서만 정의)
# 구현 노트: trailer 줄(Co-authored-by 등)은 메시지 본문에서 제거 후 임베딩
#            (템플릿 서명이 유사도를 인위적으로 올리는 것 방지 — NOTES 문서 기록)
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
VENV="${DATA}/.venv07"
PY="${SCRIPT_DIR}/.embed_messages_runner.py"

if [ ! -x "${VENV}/bin/python3" ]; then
  echo "== 가상환경 생성 + sentence-transformers 설치 (최초 1회) =="
  python3 -m venv "$VENV" && "${VENV}/bin/pip" -q install --upgrade pip \
    && "${VENV}/bin/pip" -q install sentence-transformers || { echo "설치 실패"; exit 1; }
fi

cat > "$PY" <<'PYEOF'
import csv, gzip, os, re, sys
import numpy as np

DATA = sys.argv[1]
LOGS = os.path.join(DATA, "logs")
OUT  = os.path.join(DATA, "signal7_msg.csv")

BOT_RE = re.compile(r'(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)', re.I)
TRAILER_LINE = re.compile(r'^\s*(co-?authored-by|signed-off-by|reviewed-by|change-id)\s*:', re.I)

done = set()
if os.path.exists(OUT):
    with open(OUT) as f:
        for row in csv.reader(f):
            if row and row[0] != "repo": done.add(row[0])
    print(f"== 재개: {len(done)}개 완료분 건너뜀 ==", flush=True)

def messages_of(fname):
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return []
    msgs = []
    for rec in text.split("\x1e"):
        parts = rec.split("\x1f")
        if len(parts) < 7: continue
        an, ae, body = parts[1], parts[2], parts[6]
        if BOT_RE.search((an + "|" + ae).lower()): continue
        lines = [l for l in body.splitlines() if not TRAILER_LINE.match(l)]
        m = "\n".join(lines).strip()
        if m: msgs.append(m[:256])
    return msgs

from sentence_transformers import SentenceTransformer
import torch
dev = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"== 모델 로드: intfloat/multilingual-e5-small (device={dev}) ==", flush=True)
model = SentenceTransformer("intfloat/multilingual-e5-small", device=dev)

files = [f for f in sorted(os.listdir(LOGS)) if f[:-7].replace("__", "/", 1) not in done]
print(f"== 대상 {len(files)}개 저장소 ==", flush=True)

out = open(OUT, "a", newline="")
w = csv.writer(out)
if not done:
    w.writerow(["repo", "n_msgs", "sig7_msg_informativeness"])

BATCH_REPOS = 200
for i in range(0, len(files), BATCH_REPOS):
    chunk = files[i:i+BATCH_REPOS]
    texts, spans, metas = [], [], []
    for fname in chunk:
        repo = fname[:-7].replace("__", "/", 1)
        msgs = messages_of(fname)
        spans.append((repo, len(msgs), len(texts)))
        texts.extend("query: " + m for m in msgs)
    if texts:
        emb = model.encode(texts, batch_size=256, normalize_embeddings=True,
                           show_progress_bar=False, convert_to_numpy=True)
    else:
        emb = np.zeros((0, 384), dtype=np.float32)
    for repo, n, start in spans:
        if n >= 2:
            v = emb[start:start+n]
            s = v.sum(axis=0)
            mean_cos = (float(s @ s) - n) / (n * (n - 1))   # 평균 쌍별 코사인 (정규화 벡터)
            sig7 = round(1.0 - mean_cos, 6)
            w.writerow([repo, n, sig7])
        else:
            w.writerow([repo, n, ""])
    out.flush()
    print(f"  …{min(i+BATCH_REPOS, len(files))}/{len(files)} (메시지 {len(texts)}건 배치)", flush=True)

out.close()
print(f"== 완료 → {OUT} ==")
PYEOF

"${VENV}/bin/python3" "$PY" "$DATA"
