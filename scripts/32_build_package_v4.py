#!/usr/bin/env python3
"""논문 2 v4 — 공개 재현 패키지에 v4 층 추가 (replication_v2/).
식별자: 저장소·조직 이름과 커밋 SHA는 15_build_package.py와 같은 salted SHA-256(16자)로 치환. 작성자 식별자는 원래 저장하지 않음.
비공개: data/v2/private/ (수동 검토 파일, 커밋 제목 포함)은 복사하지 않는다. 결과 JSON에는 조직 이름이 없음(확인 후 복사).
"""
import hashlib, os, shutil, glob, gzip, csv, json
import pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2")
P = os.path.join(ROOT, "replication_v2"); DD = os.path.join(P, "data_derived", "v4"); RS = os.path.join(P, "results", "v4")
for d in (DD, RS, os.path.join(P, "scripts"), os.path.join(P, "figures"), os.path.join(P, "manuscript", "figs")): os.makedirs(d, exist_ok=True)
SALT = open(os.path.join(D, ".salt")).read().strip() + ":repo"
def h(x): return hashlib.sha256((SALT + str(x)).encode()).hexdigest()[:16]

def hash_table(src, dst, cols=("repo", "org")):
    r = pd.read_csv(src, low_memory=False, dtype={"ai_tool_main": str})
    for c in cols:
        if c in r: r[c + "_hash"] = r[c].fillna("").astype(str).map(h); r = r.drop(columns=[c])
    first = [c + "_hash" for c in cols if c + "_hash" in r]
    r[first + [c for c in r.columns if c not in first]].to_csv(dst, index=False, compression="gzip" if dst.endswith(".gz") else None)
    return len(r)

# 1. repository-level signal tables (adopted rule and variants)
n = {}
n["signals_v4"] = hash_table(os.path.join(V2, "signals_v4.csv"), os.path.join(DD, "signals_v4_hashed.csv.gz"))
for f in sorted(glob.glob(os.path.join(V2, "signals_rule_*.csv"))):
    name = os.path.basename(f)[:-4]; n[name] = hash_table(f, os.path.join(DD, name + "_hashed.csv.gz"))
# 2. repository record (creation time, assignment-copy flag, non-bot and owner-matched counts), starter-code table, rerun runs
n["repo_record"] = hash_table(os.path.join(V2, "flags_v4", "repo_record.csv"), os.path.join(DD, "repo_record_hashed.csv"))
n["repo_starter"] = hash_table(os.path.join(V2, "repo_starter.csv"), os.path.join(DD, "repo_starter_hashed.csv"), cols=("repo",))
for f in sorted(glob.glob(os.path.join(V2, "flags_v4", "arcs_*.csv"))):
    name = os.path.basename(f)[:-4]; n[name] = hash_table(f, os.path.join(DD, name + "_hashed.csv"), cols=("repo",))
# 3. commit-level features and every rule's outcome (repository and SHA hashed; no names, e-mails or messages)
with gzip.open(os.path.join(V2, "flags_v4", "commit_features.csv.gz"), "rt") as fi, gzip.open(os.path.join(DD, "commit_features_v4_hashed.csv.gz"), "wt", newline="") as fo:
    rd = csv.reader(fi); w = csv.writer(fo); hdr = next(rd); i_r, i_s = hdr.index("repo"), hdr.index("sha")
    w.writerow(["repo_hash", "sha_hash"] + [c for k, c in enumerate(hdr) if k not in (i_r, i_s)]); cache = {}; k_ = 0
    for row in rd:
        rp = row[i_r]; hv = cache.get(rp)
        if hv is None: hv = cache[rp] = h(rp)
        w.writerow([hv, h(row[i_s])] + [c for k, c in enumerate(row) if k not in (i_r, i_s)]); k_ += 1
n["commit_features"] = k_
# 4. results (aggregates only; checked for organization names before copying)
orgs = set(pd.read_csv(os.path.join(V2, "flags_v4", "repo_record.csv"), usecols=["org"]).org.dropna().astype(str)); orgs = {o for o in orgs if len(o) >= 6}
for f in sorted(glob.glob(os.path.join(V2, "results_v4*.json"))) + [os.path.join(V2, x) for x in ("results_trailer_v4.json", "results_record_generation.json", "results_activity_validation.json", "results_activity_review_v4.json", "results_reml_validation.json", "results_copy_check.json")]:
    t = open(f).read(); bad = [o for o in orgs if '"' + o + '"' in t]
    if bad: raise SystemExit(f"organization name in {f}: refusing to copy")
    shutil.copy(f, os.path.join(RS, os.path.basename(f)))
# 5. scripts, figures, manuscript
for f in glob.glob(os.path.join(ROOT, "scripts", "*")):
    b = os.path.basename(f)
    if b.endswith((".py", ".sh")) and not b.startswith(".") and ".bak" not in b: shutil.copy(f, os.path.join(P, "scripts", b))
TV = os.path.join(ROOT, "toce_v2")
for f in glob.glob(os.path.join(TV, "figs", "*_v4.*")) + glob.glob(os.path.join(TV, "figs", "*_v5.*")) + glob.glob(os.path.join(TV, "figs", "fig_registered_vs_raw_v3.*")): shutil.copy(f, os.path.join(P, "figures", os.path.basename(f)))
# manuscript: the submitted version only (main_v5.tex, tables5/, and the four figures it includes)
os.makedirs(os.path.join(P, "manuscript", "tables5"), exist_ok=True)
for f in ("main_v5.tex", "refs.bib"):
    if os.path.exists(os.path.join(TV, f)): shutil.copy(os.path.join(TV, f), os.path.join(P, "manuscript", f))
for f in glob.glob(os.path.join(TV, "tables5", "*.tex")): shutil.copy(f, os.path.join(P, "manuscript", "tables5", os.path.basename(f)))
for b in ("fig_compare_v5.pdf", "fig_yearfe_v5.pdf", "fig_trailer_v4.pdf", "fig_registered_vs_raw_v3.pdf"): shutil.copy(os.path.join(TV, "figs", b), os.path.join(P, "manuscript", "figs", b))
json.dump(n, open(os.path.join(DD, "row_counts.json"), "w"), indent=1)
print("v4 layer added:", json.dumps(n)); os.system(f'du -sh "{P}"/*')
