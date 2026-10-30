#!/usr/bin/env python3
"""논문 2 v2 — Stage 5: 공개 재현 패키지 조립 (replication_v2/)
식별자 처리: repo·org 이름은 salted SHA-256(16자)로 치환(학생 GitHub 사용자명이 저장소명에 포함되므로). student_hash·author_hash는 이미 해시.
"""
import hashlib, os, shutil, json, gzip, csv
import pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2")
P = os.path.join(ROOT, "replication_v2"); os.makedirs(P, exist_ok=True)
for sub in ("scripts", "data_derived", "registration", "results", "figures", "manuscript"): os.makedirs(os.path.join(P, sub), exist_ok=True)
SALT = open(os.path.join(D, ".salt")).read().strip() + ":repo"
def h(x): return hashlib.sha256((SALT + str(x)).encode()).hexdigest()[:16]
# 1. 저장소 수준 신호표 (v2) — 이름 해시
r = pd.read_csv(os.path.join(V2, "signals_v2.csv"), dtype={"ai_tool_main": str}, low_memory=False)
r["repo_hash"] = r.repo.map(h); r["org_hash"] = r.org.fillna("").map(h)
keep = [c for c in r.columns if c not in ("repo", "org")]
r[["repo_hash", "org_hash"] + [c for c in keep if c not in ("repo_hash", "org_hash")]].to_csv(os.path.join(P, "data_derived", "signals_v2_hashed.csv"), index=False)
# 2. 커밋 수준 표 — 이름 해시 (메시지 본문 없음; 길이만)
with gzip.open(os.path.join(V2, "commits.csv.gz"), "rt") as f, gzip.open(os.path.join(P, "data_derived", "commits_v2_hashed.csv.gz"), "wt", newline="") as g:
    rd = csv.reader(f); w = csv.writer(g); hdr = next(rd); w.writerow(["repo_hash", "sha_hash"] + hdr[2:]); cache = {}
    for row in rd:
        rp = row[0]; hv = cache.get(rp)
        if hv is None: hv = cache[rp] = h(rp)
        w.writerow([hv, h(row[1])] + row[2:])
# 3. 등록 분석표(2026-08) — 이름 해시
a = pd.read_csv(os.path.join(D, "analysis_table.csv.gz"))
a["repo_hash"] = a.repo.map(h); a["org_hash"] = a.org.map(h)
a.drop(columns=["repo", "org"]).to_csv(os.path.join(P, "data_derived", "registered_analysis_table_hashed.csv.gz"), index=False, compression="gzip")
# 4. 표본 플래그 — 해시
fl = pd.read_csv(os.path.join(V2, "sample_flags.csv")); fl["repo_hash"] = fl.repo.map(h); fl["org_hash"] = fl.org.fillna("").map(h)
fl.drop(columns=["repo", "org"]).to_csv(os.path.join(P, "data_derived", "sample_flags_hashed.csv"), index=False)
# 5. 나머지 파일 복사
for src, dst in [("v2/thresholds_v2.csv", "data_derived/thresholds_v2.csv"), ("cohort_p95.csv", "data_derived/registered_cohort_p95.csv"),
                 ("v2/results_v2.json", "results/results_v2.json"), ("v2/results_v2.md", "results/results_v2.md"), ("v2/results_v2_extra.json", "results/results_v2_extra.json"),
                 ("v2/sensitivity_thresholds.md", "results/sensitivity_thresholds.md"), ("v2/descriptives_v2.md", "results/descriptives_v2.md"), ("v2/timebins.csv", "results/timebins.csv"),
                 ("results/results_core.json", "registration/registered_results_core.json"), ("results/results_core.md", "registration/registered_results_core.md"),
                 ("results/results_h5.json", "registration/registered_results_h5.json"), ("results/results_final.md", "registration/registered_results_final.md")]:
    shutil.copy(os.path.join(D, src), os.path.join(P, dst))
for f in ("04_OSF사전등록_v1.0_확정.md", "05_구현노트_DEVIATIONS.md", "SHA256_frozen_2026-08-06.txt"):
    shutil.copy(os.path.join(ROOT, f), os.path.join(P, "registration", f))
for f in os.listdir(os.path.join(ROOT, "scripts")):
    if f.endswith((".sh", ".py")) and not f.startswith("."): shutil.copy(os.path.join(ROOT, "scripts", f), os.path.join(P, "scripts", f))
for f in ("fig_yearfe.pdf", "fig_contrasts.pdf", "fig_registered_vs_raw.pdf", "fig_yearfe.png", "fig_contrasts.png", "fig_registered_vs_raw.png", "fig_timebins.png"):
    shutil.copy(os.path.join(V2, f), os.path.join(P, "figures", f))
print("package built at", P); os.system(f'du -sh "{P}"/*')
# 6. 결과 파일 내 org 이름 제거 (논문 윤리 진술과 일치: 강의·기관 비식별)
R = json.load(open(os.path.join(P, "results", "results_v2.json")))
if "desc" in R and "org_top" in R["desc"]:
    R["desc"]["org_top"] = {h(k): v for k, v in R["desc"]["org_top"].items()}
json.dump(R, open(os.path.join(P, "results", "results_v2.json"), "w"), indent=1, default=str)
for fn in ("results_v2.md", "descriptives_v2.md"):
    fp = os.path.join(P, "results", fn); txt = open(fp).read()
    if fn == "descriptives_v2.md" and "## 비-GHC 저장소 표본 예시" in txt: txt = txt.split("## 비-GHC 저장소 표본 예시")[0] + "## (example repository names removed from the public package)\n"
    if fn == "results_v2.md":
        import re as _re
        txt = _re.sub(r'"org_top": \{[^}]*\}', '"org_top": {redacted in public package}', txt)
    open(fp, "w").write(txt)
print("identifiers scrubbed from results")
# 7. 등록 결과 json 의 leave-one-org-out 키(org 이름) 해시
pr = os.path.join(P, "registration", "registered_results_core.json"); RR = json.load(open(pr))
if "robustness" in RR and "leave_one_org_out_d" in RR["robustness"]:
    RR["robustness"]["leave_one_org_out_d"] = {h(k): v for k, v in RR["robustness"]["leave_one_org_out_d"].items()}
json.dump(RR, open(pr, "w"), indent=1, default=str)
# 8. v2 결과 추가 복사
for f in ("results_composition.json", "results_composition.md"): shutil.copy(os.path.join(V2, f), os.path.join(P, "results", f))
for f in ("fig_composition.pdf", "fig_composition.png"): shutil.copy(os.path.join(V2, f), os.path.join(P, "figures", f))
print("registered LOO keys hashed; composition results copied")

# 9. v3 (student-commit) layer: history flags, student arcs, signals_v3, v3 results and figures (2026-10-30, E9-E11)
with gzip.open(os.path.join(V2, "commit_history_flags.csv.gz"), "rt") as f, gzip.open(os.path.join(P, "data_derived", "commit_history_flags_hashed.csv.gz"), "wt", newline="") as g:
    rd = csv.reader(f); w = csv.writer(g); hdr = next(rd); w.writerow(["repo_hash", "sha_hash"] + hdr[2:]); cache = {}
    for row in rd:
        rp = row[0]; hv = cache.get(rp)
        if hv is None: hv = cache[rp] = h(rp)
        w.writerow([hv, h(row[1])] + row[2:])
for src, dst in [("repo_arcs.csv", "repo_arcs_hashed.csv"), ("repo_arcs_student.csv", "repo_arcs_student_hashed.csv"), ("repo_history_audit_all.csv", "repo_history_audit_hashed.csv")]:
    t = pd.read_csv(os.path.join(V2, src)); t["repo_hash"] = t.repo.map(h); t.drop(columns=["repo"]).to_csv(os.path.join(P, "data_derived", dst), index=False)
r3 = pd.read_csv(os.path.join(V2, "signals_v3.csv"), dtype={"ai_tool_main": str}, low_memory=False)
r3["repo_hash"] = r3.repo.map(h); r3["org_hash"] = r3.org.fillna("").map(h)
r3[["repo_hash", "org_hash"] + [c for c in r3.columns if c not in ("repo", "org", "repo_hash", "org_hash")]].to_csv(os.path.join(P, "data_derived", "signals_v3_hashed.csv"), index=False)
for f in ("results_composition_v3.json", "results_composition_v3.md", "results_v2_extra_v3.json", "sensitivity_thresholds_v3.md", "results_inclusion_all_v3.json", "results_inclusion_all_v3.md", "results_sample_sensitivity_v3.json", "results_sample_sensitivity_v3.md"):
    if os.path.exists(os.path.join(V2, f)): shutil.copy(os.path.join(V2, f), os.path.join(P, "results", f))
for f in ("fig_composition_v3.pdf", "fig_composition_v3.png", "fig_trailer_v3.pdf", "fig_trailer_v3.png", "fig_yearfe_v3.pdf", "fig_yearfe_v3.png", "fig_contrasts_v3.pdf", "fig_contrasts_v3.png", "fig_registered_vs_raw_v3.pdf", "fig_registered_vs_raw_v3.png"):
    if os.path.exists(os.path.join(V2, f)): shutil.copy(os.path.join(V2, f), os.path.join(P, "figures", f))
# scrub org names from v3 composition results (LOO keys, dominant-org keys)
import re as _re
def _scrub(o):
    if isinstance(o, dict): return {(h(k) if ("/" in k or k.lower() in _orgs) else k): _scrub(v) for k, v in o.items()}
    if isinstance(o, list): return [_scrub(v) for v in o]
    return o
_orgs = set(r3.org.dropna().str.lower())
for fn in ("results_composition.json", "results_composition_v3.json"):
    fp = os.path.join(P, "results", fn); J = json.load(open(fp)); json.dump(_scrub(J), open(fp, "w"), indent=1, default=str)
for fn in ("results_composition.md", "results_composition_v3.md"):
    fp = os.path.join(P, "results", fn); txt = open(fp).read()
    for o in sorted(_orgs, key=len, reverse=True):
        if len(o) >= 4: txt = _re.sub(_re.escape(o), h(o), txt, flags=_re.I)
    open(fp, "w").write(txt)
for f in ("main.tex", "refs.bib"): shutil.copy(os.path.join(ROOT, "toce_v2", f), os.path.join(P, "manuscript", f))
print("v3 layer added; org names scrubbed from composition results")
