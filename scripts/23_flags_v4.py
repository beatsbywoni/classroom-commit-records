#!/usr/bin/env python3
"""논문 2 v4 — 학생 활동 분류 규칙 재정의와 변형 규칙 (2026-10-30, 6차 작업지시서).

검증 Classroom 저장소의 원 로그를 한 번 읽어 비봇 커밋마다 다음을 계산한다.
  committer_ts / 저장소 생성 시각(repos_enumerated.jsonl) 비교, 같은 조직 내 SHA 공유 저장소 수,
  작성자(이메일 기준, 메모리 안에서만 사용)의 조직 내 저장소 수·최다 기여 비율,
  작성자 식별자(noreply 로그인·이메일 로컬파트·이름)가 저장소 이름 끝 로그인과 일치하는지.
이름·이메일은 저장하지 않는다.

규칙 (student = 1 이면 '규칙상 학생 활동으로 분류된 커밋'):
  v3      : 기존 규칙. 공유 SHA(≥2 저장소) → 상속, 작성자 ≥5 저장소이면서 최다 기여 <50% → 교수자형.
  v4      : (주 규칙) 저장소 생성 1일 이전에 커밋된 이력, 또는 공유 SHA이면서 생성 이전 → 기존 이력;
            생성 이후 공유 SHA가 ≥5 저장소에 걸치면 → 교수자 일괄 푸시;
            작성자 ≥5 저장소·최다 기여 <50% 이면서 저장소 이름과 일치하지 않으면 → 교수자형.
  v4_d0       : v4에서 생성 이전 기준을 1일이 아니라 0으로 (생성 직전 커밋도 제외)
  v4_shared   : v4에서 생성 이후 공유 SHA를 모두 제외 (기존 v3의 상속 정의 유지)
  v4_staff3   : 교수자형 기준 ≥3 저장소
  v4_staff10  : 교수자형 기준 ≥10 저장소
  v4_nostaff  : 교수자형 규칙 미적용
  v4_strict   : 저장소 이름과 일치하는 작성자의 커밋만 (일치 작성자가 있는 저장소로 제한됨)
저장소 수준: assignment_copy = 이름이 Classroom 과제 사본 구조({classroom-slug}-...)이고 이름과 일치하는 작성자가 없음.

출력: data/v2/flags_v4/{rule}.csv.gz (repo, sha, student), data/v2/flags_v4/arcs_{rule}.csv (repo, n_student, arcs2..4),
      data/v2/flags_v4/repo_record.csv (repo, created_ts, assignment_copy, n_nonbot, n_name_match_authors, ...),
      data/v2/flags_v4/commit_features.csv.gz (repo, sha, committer_ts, pre_creation_1d, pre_creation_0, shared_n, name_match, author_nrepos, author_top_share)
"""
import os, re, gzip, json, hashlib
from multiprocessing import Pool
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2")
LOGS = os.path.join(D, "logs"); OUT = os.path.join(V2, "flags_v4"); os.makedirs(OUT, exist_ok=True)
BOT_RE = re.compile(r"(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)", re.I)
NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$", re.I)
COPY_SIG = re.compile(r"classroom-[0-9a-f]{6}-", re.I)

def cands(name, email):
    c = set(); email = (email or "").strip(); name = (name or "").strip()
    m = NOREPLY.match(email)
    if m: c.add(m.group(1).lower())
    if "@" in email: c.add(email.split("@")[0].lower())
    if name:
        c.add(re.sub(r"[^a-z0-9]", "", name.lower())); c.add(re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))
    return {x for x in c if len(x) >= 3}

def matches(repo_name, cs):
    nl = repo_name.lower(); nn = re.sub(r"[^a-z0-9]", "", nl)
    for x in cs:
        if nl.endswith("-" + x) or nl == x or ("-" + x + "-") in nl or (len(x) >= 5 and nn.endswith(re.sub(r"[^a-z0-9]", "", x))):
            return True
    return False

def parse(fname):
    repo = fname[:-7].replace("__", "/", 1); rname = repo.split("/", 1)[1]
    try:
        with gzip.open(os.path.join(LOGS, fname), "rt", encoding="utf-8", errors="replace") as f: text = f.read()
    except Exception:
        return []
    out = []
    for rec in text.split("\x1e"):
        p = rec.split("\x1f")
        if len(p) < 7: continue
        an, ae = p[1], p[2]
        if BOT_RE.search((an + "|" + ae).lower()): continue
        try: at, ct = int(p[3]), int(p[4])
        except ValueError: continue
        tail = p[7] if len(p) > 7 else ""
        fs = tuple(sorted({l.split("\t")[2] for l in tail.splitlines() if len(l.split("\t")) == 3}))
        aid = hashlib.sha1(((ae or "").lower().strip() or an.lower().strip()).encode()).hexdigest()[:16]
        out.append((repo, p[0].strip()[:12], at, ct, aid, int(matches(rname, cands(an, ae))), fs))
    return out

def arcs_of(rows):
    rows = sorted(rows, key=lambda r: r[0]); arcs = {2: 0, 3: 0, 4: 0}; run = {}; prev = set()
    for _, fs in rows:
        new = {}
        for fp in fs:
            r = run.get(fp, 0) + 1 if fp in prev else 1; new[fp] = r
            if r in arcs: arcs[r] += 1
        run = new; prev = set(fs)
    return arcs

if __name__ == "__main__":
    created = {}
    for line in open(os.path.join(D, "repos_enumerated.jsonl")):
        r = json.loads(line); created[r["full_name"]] = int(pd.Timestamp(r["created_at"]).timestamp())
    files = sorted(f for f in os.listdir(LOGS) if f.endswith(".log.gz"))
    with Pool(2) as pool:
        parts = pool.map(parse, files, chunksize=200)
    rows = [r for part in parts for r in part]
    c = pd.DataFrame(rows, columns=["repo", "sha", "author_ts", "committer_ts", "aid", "name_match", "files"])
    c["org"] = c.repo.str.split("/").str[0]; c["created_ts"] = c.repo.map(created)
    print("non-bot commits", len(c), "repos", c.repo.nunique())
    # features
    c["pre_creation_0"] = (c.committer_ts < c.created_ts - 60).astype(int)
    c["pre_creation_1d"] = (c.committer_ts < c.created_ts - 86400).astype(int)
    c["shared_n"] = c.groupby(["org", "sha"]).repo.transform("nunique")
    # author stats within org (computed on commits that are not pre-existing history, as in v3 which excluded inherited)
    def author_stats(df):
        top = df.groupby(["repo", "aid"]).size().reset_index(name="n").sort_values(["repo", "n"], ascending=[True, False]).drop_duplicates("repo")
        top["org"] = top.repo.str.split("/").str[0]
        nrep = df.groupby(["org", "aid"]).repo.nunique().rename("author_nrepos")
        ntop = top.groupby(["org", "aid"]).size().rename("n_top")
        st = pd.concat([nrep, ntop], axis=1).fillna({"n_top": 0}); st["author_top_share"] = st.n_top / st.author_nrepos
        return st.reset_index()
    # v3 base: author stats on non-shared commits
    st3 = author_stats(c[c.shared_n < 2]); c = c.merge(st3[["org", "aid", "author_nrepos", "author_top_share"]], on=["org", "aid"], how="left")
    hist4 = (c.pre_creation_1d == 1) | ((c.shared_n >= 2) & (c.pre_creation_0 == 1))
    st4 = author_stats(c[~hist4]).rename(columns={"author_nrepos": "nrep4", "author_top_share": "top4"})
    c = c.merge(st4[["org", "aid", "nrep4", "top4"]], on=["org", "aid"], how="left")
    for k in ("author_nrepos", "nrep4"): c[k] = c[k].fillna(0)
    for k in ("author_top_share", "top4"): c[k] = c[k].fillna(1)
    inh3 = c.shared_n >= 2
    staff3 = (~inh3) & (c.author_nrepos >= 5) & (c.author_top_share < 0.5)
    push4 = (~hist4) & (c.shared_n >= 5) & (c.pre_creation_0 == 0)
    def staff4(k): return (~hist4) & (~push4) & (c.nrep4 >= k) & (c.top4 < 0.5) & (c.name_match == 0)
    RULES = {
        "v3": ~(inh3 | staff3),
        "v4": ~(hist4 | push4 | staff4(5)),
        "v4_d0": ~((c.pre_creation_0 == 1) | push4 | staff4(5)),
        "v4_shared": ~(hist4 | (c.shared_n >= 2) | staff4(5)),
        "v4_staff3": ~(hist4 | push4 | staff4(3)),
        "v4_staff10": ~(hist4 | push4 | staff4(10)),
        "v4_nostaff": ~(hist4 | push4),
        "v4_strict": ~(hist4 | push4) & (c.name_match == 1),
    }
    # repo-level record features
    rr = c.groupby("repo").agg(n_nonbot=("sha", "size"), n_name_match=("name_match", "sum"), created_ts=("created_ts", "first")).reset_index()
    rr["org"] = rr.repo.str.split("/").str[0]; rr["name"] = rr.repo.str.split("/").str[1]
    rr["copy_signature"] = [bool(COPY_SIG.search(n.lower())) or n.lower().startswith(o.lower() + "-classroom") for n, o in zip(rr.name, rr.org)]
    rr["assignment_copy"] = (rr.copy_signature & (rr.n_name_match == 0)).astype(int)
    # also repos with no non-bot commits (bot only): signature from enumerated list
    allv = pd.read_csv(os.path.join(V2, "sample_flags.csv"), usecols=["repo", "ghc_verified"], low_memory=False)
    allv = allv[allv.ghc_verified == 1][["repo"]].copy(); allv["org"] = allv.repo.str.split("/").str[0]; allv["name"] = allv.repo.str.split("/").str[1]
    allv["copy_signature"] = [bool(COPY_SIG.search(n.lower())) or n.lower().startswith(o.lower() + "-classroom") for n, o in zip(allv.name, allv.org)]
    allv["created_ts"] = allv.repo.map(created)
    allv = allv.merge(rr[["repo", "n_nonbot", "n_name_match"]], on="repo", how="left").fillna({"n_nonbot": 0, "n_name_match": 0})
    allv["assignment_copy"] = (allv.copy_signature & (allv.n_name_match == 0)).astype(int)
    allv.drop(columns=["name"]).to_csv(os.path.join(OUT, "repo_record.csv"), index=False)
    feats = c[["repo", "sha", "author_ts", "committer_ts", "pre_creation_0", "pre_creation_1d", "shared_n", "name_match", "author_nrepos", "author_top_share", "nrep4", "top4"]].copy()
    for name, mask in RULES.items():
        feats[name] = mask.astype(int).to_numpy()
    feats.to_csv(os.path.join(OUT, "commit_features.csv.gz"), index=False, compression="gzip")
    for name, mask in RULES.items():
        sub = c[mask.to_numpy()]
        sub[["repo", "sha"]].assign(student=1).to_csv(os.path.join(OUT, f"{name}.csv.gz"), index=False, compression="gzip")
        ar = []
        for repo, g in sub.groupby("repo"):
            a = arcs_of(list(zip(g.author_ts, g.files))); ar.append((repo, len(g), a[2], a[3], a[4]))
        pd.DataFrame(ar, columns=["repo", "n_student", "arcs2", "arcs3", "arcs4"]).to_csv(os.path.join(OUT, f"arcs_{name}.csv"), index=False)
        print(name, "student commits", int(mask.sum()), "repos", sub.repo.nunique(), flush=True)
    # agreement of recomputed v3 with the v3 flag file
    hf = pd.read_csv(os.path.join(V2, "commit_history_flags.csv.gz"), dtype={"sha": str})
    chk = feats[["repo", "sha", "v3"]].merge(hf[["repo", "sha", "student"]], on=["repo", "sha"], how="inner")
    print("v3 recomputed vs file: n", len(chk), "agreement", round(float((chk.v3 == chk.student).mean()), 4))
