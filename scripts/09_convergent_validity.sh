#!/usr/bin/env bash
# ============================================================
# 논문 2 — 09 H5 수렴타당도 + 최종 Holm(4검정)
#
# 사용법:  bash ~/Desktop/GitHub_AI코딩_마이닝/논문2_작업/scripts/09_convergent_validity.sh
# 입력:   data/codeworkout/F19_Release_All_05_23_22.zip, S19_All_Release_2_10_22.zip
#         data/results/results_core.json (08 산출)
# 산출:   data/results/results_final.md / results_h5.json
#
# H5(등록): 커밋형 struggle 지표(외부 ProgSnap2 세션 로그에서 계산) vs
#           고유 struggle 지표(오류/재제출 기반)의 학생 수준 상관 r ≥ 0.30 (95% CI 하한 > 0.15)
# ============================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${SCRIPT_DIR}/../data"
VENV="${DATA}/.venv07"
PY="${SCRIPT_DIR}/.h5_runner.py"

cat > "$PY" <<'PYEOF'
import io, json, math, os, sys, zipfile, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats

DATA = sys.argv[1]
CW = os.path.join(DATA, "codeworkout")
RES = os.path.join(DATA, "results")

def load_semester(zpath, prefix):
    z = zipfile.ZipFile(zpath)
    def p(name):
        for n in z.namelist():
            if n.endswith(name): return n
        raise FileNotFoundError(name)
    mt = pd.read_csv(z.open(p("MainTable.csv")))
    # CodeStateID → 코드 길이 (편집 크기 아날로그용)
    cs = pd.read_csv(z.open(p("CodeStates/CodeStates.csv")))
    code_col = [c for c in cs.columns if c.lower() == "code"][0]
    id_col = [c for c in cs.columns if "codestateid" in c.lower()][0]
    cs["clen"] = cs[code_col].astype(str).str.len()
    lens = dict(zip(cs[id_col], cs["clen"]))
    mt["semester"] = prefix
    return mt, lens

def student_measures(mt, lens):
    """학생별: 커밋형 아날로그 4신호 + 고유 struggle 2지표"""
    cols = {c.lower(): c for c in mt.columns}
    sid, ts = cols["subjectid"], cols["servertimestamp"]
    pid = cols.get("problemid", cols.get("assignmentid"))
    ev  = cols.get("eventtype")
    sc  = cols.get("score")
    csid = cols.get("codestateid")
    if ev is not None and (mt[ev] == "Submit").any():
        mt = mt[mt[ev] == "Submit"].copy()
    mt["t"] = pd.to_datetime(mt[ts], errors="coerce", format="mixed")
    mt = mt.dropna(subset=["t"]).sort_values([sid, "t"])
    out = []
    for s, g in mt.groupby(sid):
        n = len(g)
        if n < 10: continue
        t = g["t"].to_numpy()
        gaps = np.diff(t).astype("timedelta64[s]").astype(float)
        burst = float((gaps < 1800).mean()) if len(gaps) else np.nan
        span = (t[-1] - t[0]) / np.timedelta64(1, "s")
        if span > 0 and n >= 4:
            q = np.percentile(t.astype("datetime64[s]").astype(float), [25, 75])
            disp = float((q[1] - q[0]) / span)
        else:
            disp = np.nan
        # 편집 크기 아날로그: 같은 문제 연속 제출 간 코드 길이 변화 중앙값 (log1p)
        dl = []
        if csid is not None and pid is not None:
            for _, gg in g.groupby(pid):
                L = [lens.get(x) for x in gg[csid]]
                L = [x for x in L if x is not None]
                dl += [abs(b - a) for a, b in zip(L, L[1:])]
        edit = float(np.log1p(np.median(dl))) if dl else np.nan
        # 복구 아크 아날로그: 같은 문제 ≥3 연속 제출 run 수 / 제출 수
        arcs = 0
        if pid is not None:
            pr = g[pid].to_numpy(); run = 1
            for a, b in zip(pr, pr[1:]):
                if a == b: run += 1
                else:
                    if run >= 3: arcs += 1
                    run = 1
            if run >= 3: arcs += 1
        arc = arcs / n
        # 고유 struggle: 문제당 시도 수(재제출) + 비만점 제출률(오류)
        att = float(g.groupby(pid).size().mean()) if pid is not None else np.nan
        if sc is not None:
            scv = pd.to_numeric(g[sc], errors="coerce")
            err = float((scv < scv.max()).mean()) if np.isfinite(scv.max()) else np.nan
        else:
            err = np.nan
        out.append((s, n, edit, burst, arc, disp, att, err))
    return pd.DataFrame(out, columns=["sid", "n_events", "edit", "burst", "arc", "disp", "att", "err"])

def h5_corr(df):
    z = lambda x: (x - np.nanmean(x)) / np.nanstd(x)
    # 커밋형 composite: σ 정렬(우리 instrument와 동일 방향: edit −, burst +, arc +, disp +)
    commit_like = np.nanmean(np.column_stack([-z(df.edit), z(df.burst), z(df.arc), z(df.disp)]), axis=1)
    native = np.nanmean(np.column_stack([z(df.att), z(df.err)]), axis=1)
    m = np.isfinite(commit_like) & np.isfinite(native)
    r, p = stats.pearsonr(commit_like[m], native[m])
    rho, p_s = stats.spearmanr(commit_like[m], native[m])
    # 순환성 방어: 타이밍 전용(arc 제외 — arc는 재제출과 겹침)
    timing_only = np.nanmean(np.column_stack([-z(df.edit), z(df.burst), z(df.disp)]), axis=1)
    m2 = np.isfinite(timing_only) & np.isfinite(native)
    r2, p2 = stats.pearsonr(timing_only[m2], native[m2])
    nn = int(m.sum())
    zr = 0.5 * math.log((1 + r) / (1 - r)); se = 1 / math.sqrt(nn - 3)
    lo, hi = math.tanh(zr - 1.96 * se), math.tanh(zr + 1.96 * se)
    return {"n": nn, "pearson_r": round(float(r), 4), "p": float(p),
            "ci95": [round(lo, 4), round(hi, 4)], "spearman_rho": round(float(rho), 4),
            "timing_only_r": round(float(r2), 4), "timing_only_p": float(p2)}

print("== H5: CodeWorkout/CSEDM 로드 ==", flush=True)
res = {}
frames = []
for zf, tag in [("F19_Release_All_05_23_22.zip", "F19"), ("S19_All_Release_2_10_22.zip", "S19")]:
    mt, lens = load_semester(os.path.join(CW, zf), tag)
    sm = student_measures(mt, lens)
    res[tag] = h5_corr(sm)
    sm["semester"] = tag; frames.append(sm)
    print(f"  {tag}: 학생 {res[tag]['n']}명, r={res[tag]['pearson_r']}", flush=True)
pooled = pd.concat(frames)
res["pooled"] = h5_corr(pooled)
P = res["pooled"]
res["verdict_H5"] = "SUPPORTED" if (P["pearson_r"] >= 0.30 and P["ci95"][0] > 0.15) else "NOT SUPPORTED"

# ---------- 최종 Holm (4검정) ----------
core = json.load(open(os.path.join(RES, "results_core.json")))
ps = {"H1": core["H1"]["p"], "H2a": core["H2a"]["p"],
      "H3": core["H3"].get("baseline:post01", {}).get("p", float("nan")), "H5": P["p"]}
order = sorted([k for k in ps if np.isfinite(ps[k])], key=lambda k: ps[k])
holm = {}
for i, k in enumerate(order): holm[k] = min(1.0, ps[k] * (len(order) - i))
for i in range(1, len(order)): holm[order[i]] = max(holm[order[i]], holm[order[i-1]])
res["holm_final_4tests"] = {k: float(f"{v:.3e}") for k, v in holm.items()}

json.dump(res, open(os.path.join(RES, "results_h5.json"), "w"), indent=1)
L = ["# 최종 결과 — H5 수렴타당도 + Holm(4검정)", ""]
for tag in ["F19", "S19", "pooled"]:
    r = res[tag]
    L.append(f"## {tag}: r={r['pearson_r']} (95% CI {r['ci95']}), ρ={r['spearman_rho']}, n={r['n']}"
             f" | 타이밍전용 r={r['timing_only_r']}")
L.append("")
L.append(f"**H5 판정 (pooled, 임계 r≥0.30 ∧ CI하한>0.15): {res['verdict_H5']}**")
L.append("")
L.append("## 최종 Holm (4검정): " + ", ".join(f"{k}={v:.2e}" for k, v in holm.items()))
L.append("")
L.append("확증 최종 요약: H1 " + core["verdict"]["H1"] + " | H2a " + core["verdict"]["H2a"]
         + " | H3 " + core["verdict"]["H3"] + " | H5 " + res["verdict_H5"])
open(os.path.join(RES, "results_final.md"), "w").write("\n".join(L) + "\n")
print("\n" + "\n".join(L))
print(f"\n== 저장: {RES}/results_final.md / results_h5.json ==")
PYEOF

"${VENV}/bin/python3" "$PY" "$DATA"
