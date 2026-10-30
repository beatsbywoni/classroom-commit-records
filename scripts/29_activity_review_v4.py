#!/usr/bin/env python3
"""논문 2 v4 — 학생 활동 분류 규칙 v4의 층화 수동 검토 표본 (2026-10-30, 6차 작업지시서 2번).

층: 규칙 v4 범주(유지·이름 일치 / 유지·불일치 / 제외·기존 이력 / 제외·교수자 일괄 푸시 / 제외·교수자형)
    × 시기(저장소 생성 2022-12-01 이전 / 2023-01-01 이후) × 조직 규모(비봇 커밋 기준 상위 조직들이 전체의 절반을 차지하는 '대형' / 나머지 '소형').
각 층에서 최대 8개 커밋을 무작위 추출(seed 20261030). 판단 근거로 커밋 제목, 저장소 생성 대비 시각, SHA 공유 저장소 수,
작성자 식별자-저장소 이름 일치 여부, 작성자의 조직 내 저장소 수·최다 기여 비율, 저장소 내 순서, 추가 줄 수를 기록한다.
이름·이메일은 기록하지 않는다. 커밋 제목이 들어 있는 검토 파일은 비공개(data/v2/private/).

1단계(기본): 표본과 근거를 data/v2/private/activity_review_v4_PRIVATE.csv 로 저장.
2단계(JUDGE=파일): 판단 열(judgment: S/I/U)이 채워진 파일을 읽어 층별·가중 오분류율을 계산해
      data/v2/results_activity_review_v4.json 으로 저장(제목 없이 집계만).
"""
import os, re, gzip, json, sys
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "data"); V2 = os.path.join(D, "v2")
PRIV = os.path.join(V2, "private"); os.makedirs(PRIV, exist_ok=True)
OUTP = os.path.join(PRIV, "activity_review_v4_PRIVATE.csv")
BOT_RE = re.compile(r"(\[bot\]|dependabot|github-actions|github classroom|renovate|copilot-swe-agent|web-flow)", re.I)
PER_CELL = 8
PRE_END, POST_START = pd.Timestamp("2022-12-01").timestamp(), pd.Timestamp("2023-01-01").timestamp()

def categories(c):
    hist = (c.pre_creation_1d == 1) | ((c.shared_n >= 2) & (c.pre_creation_0 == 1))
    push = ~hist & (c.shared_n >= 5)
    cat = np.where(c.v4 == 1, np.where(c.name_match == 1, "kept_match", "kept_nomatch"),
                   np.where(hist, "excl_history", np.where(push, "excl_push", "excl_staff")))
    return cat

def frame():
    c = pd.read_csv(os.path.join(V2, "flags_v4", "commit_features.csv.gz"))
    rec = pd.read_csv(os.path.join(V2, "flags_v4", "repo_record.csv"))
    # test, demo, and sandbox organizations: same name rule as 12_signals_v2.py (E5)
    rec["org_test"] = rec.org.fillna("").str.contains(r"(?:test|demo|sandbox|sample|playground|staging|production)", case=False, regex=True).astype(int)
    rec = rec[(rec.org_test == 0) & (rec.assignment_copy.fillna(0) == 0)]
    c = c.merge(rec[["repo", "org", "created_ts", "n_nonbot", "n_name_match"]], on="repo", how="inner")
    c["cat"] = categories(c)
    c["period"] = np.where(c.created_ts < PRE_END, "pre", np.where(c.created_ts >= POST_START, "post", "buffer"))
    oc = c.groupby("org").size().sort_values(ascending=False); cum = oc.cumsum() / oc.sum()
    large = set(oc.index[: int((cum < 0.5).sum()) + 1]); c["orgsize"] = np.where(c.org.isin(large), "large", "small")
    c["rank"] = c.groupby("repo").author_ts.rank(method="first").astype(int)
    return c, len(large), int(oc.size)

def subjects(rows):
    """Commit subject and added lines for the sampled commits, read from the raw logs (kept private)."""
    out = {}
    for repo, g in rows.groupby("repo"):
        fn = os.path.join(D, "logs", repo.replace("/", "__", 1) + ".log.gz"); want = set(g.sha)
        try: text = gzip.open(fn, "rt", encoding="utf-8", errors="replace").read()
        except Exception: continue
        for rec in text.split("\x1e"):
            p = rec.split("\x1f")
            if len(p) < 7: continue
            sha = p[0].strip()[:12]
            if sha not in want: continue
            tail = p[7] if len(p) > 7 else ""; add = 0; nf = 0
            for l in tail.splitlines():
                q = l.split("\t")
                if len(q) == 3:
                    nf += 1
                    if q[0].isdigit(): add += int(q[0])
            out[(repo, sha)] = (p[6].strip()[:120], add, nf)
    return out

if __name__ == "__main__":
    J = os.environ.get("JUDGE")
    c, n_large, n_orgs = frame(); c = c[c.period != "buffer"]
    pop = c.groupby(["cat", "period", "orgsize"]).size().rename("pop")
    if not J:
        rng = np.random.default_rng(20261030); picks = []
        for key, g in c.groupby(["cat", "period", "orgsize"]):
            picks.append(g.iloc[rng.permutation(len(g))[:PER_CELL]])
        s = pd.concat(picks)
        sub = subjects(s)
        s["subject"] = [sub.get((r, h), ("", np.nan, np.nan))[0] for r, h in zip(s.repo, s.sha)]
        s["added"] = [sub.get((r, h), ("", np.nan, np.nan))[1] for r, h in zip(s.repo, s.sha)]
        s["files"] = [sub.get((r, h), ("", np.nan, np.nan))[2] for r, h in zip(s.repo, s.sha)]
        s["days_from_creation"] = ((s.committer_ts - s.created_ts) / 86400).round(2)
        s["repo_name"] = s.repo.str.split("/", n=1).str[1]
        cols = ["cat", "period", "orgsize", "repo", "repo_name", "sha", "rank", "n_nonbot", "n_name_match", "days_from_creation", "shared_n",
                "name_match", "author_nrepos", "author_top_share", "added", "files", "subject"]
        s = s[cols].reset_index(drop=True); s["judgment"] = ""; s["note"] = ""
        s.to_csv(OUTP, index=False)
        print("sample", len(s), "large orgs", n_large, "of", n_orgs); print(pop.to_string())
        sys.exit(0)
    s = pd.read_csv(J); s["judgment"] = s.judgment.str.strip().str.upper()
    res = {"procedure": "Stratified random sample (seed 20261030), up to 8 commits per cell of rule category x period (repository created before 2022-12-01 or from 2023-01-01) x organization size (large: the organizations that together hold half of the non-bot commits). Judgments S (student work in this repository), I (pre-existing history, instructor or platform content), U (undeterminable) from the recorded evidence.",
           "n_large_orgs": n_large, "n_orgs": n_orgs, "cells": [], "by_category": {}, "weighted": {}}
    for key, g in s.groupby(["cat", "period", "orgsize"]):
        res["cells"].append({"cat": key[0], "period": key[1], "orgsize": key[2], "pop": int(pop.get(key, 0)), "n": int(len(g)),
                             "S": int((g.judgment == "S").sum()), "I": int((g.judgment == "I").sum()), "U": int((g.judgment == "U").sum())})
    cells = pd.DataFrame(res["cells"])
    for cat, g in cells.groupby("cat"):
        w = g["pop"] / g["pop"].sum()
        res["by_category"][cat] = {"pop": int(g["pop"].sum()), "n": int(g.n.sum()), "S": int(g.S.sum()), "I": int(g.I.sum()), "U": int(g.U.sum()),
                                   "w_S": float((w * g.S / g.n).sum()), "w_I": float((w * g.I / g.n).sum()), "w_U": float((w * g.U / g.n).sum())}
    kept = cells[cells.cat.str.startswith("kept")]; excl = cells[cells.cat.str.startswith("excl")]
    def wrate(df, col):
        w = df["pop"] / df["pop"].sum(); return float((w * df[col] / df.n).sum())
    res["weighted"] = {"kept_not_student": wrate(kept, "I"), "kept_undeterminable": wrate(kept, "U"), "excluded_student": wrate(excl, "S"), "excluded_undeterminable": wrate(excl, "U")}
    for per in ("pre", "post"):
        for sz in ("large", "small"):
            k = kept[(kept.period == per) & (kept.orgsize == sz)]; e = excl[(excl.period == per) & (excl.orgsize == sz)]
            res["weighted"][f"{per}_{sz}"] = {"kept_not_student": wrate(k, "I"), "kept_undeterminable": wrate(k, "U"), "excluded_student": wrate(e, "S"), "excluded_undeterminable": wrate(e, "U")}
    # staff threshold: how many commits each variant reclassifies relative to v4
    allc = pd.read_csv(os.path.join(V2, "flags_v4", "commit_features.csv.gz"), usecols=["repo", "v4", "v4_staff3", "v4_staff10", "v4_nostaff", "v4_d0", "v4_shared", "v4_strict", "v3"])
    allc = allc[allc.repo.isin(c.repo.unique())]
    res["variants_vs_v4"] = {v: {"to_excluded": int(((allc.v4 == 1) & (allc[v] == 0)).sum()), "to_student": int(((allc.v4 == 0) & (allc[v] == 1)).sum()), "student": int(allc[v].sum())}
                             for v in ["v3", "v4_d0", "v4_shared", "v4_staff3", "v4_staff10", "v4_nostaff", "v4_strict"]}
    res["v4_student"] = int(allc.v4.sum()); res["n_nonbot"] = int(len(allc))
    # staff-like exclusions by author breadth (commits by authors active in 50+ repositories vs 5-49), with the judged sample in each part
    st = c[c.cat == "excl_staff"].copy(); st["breadth"] = (st.nrep4 >= 50).map({True: "50plus", False: "5to49"})
    sj = s[s.cat == "excl_staff"].merge(c[["repo", "sha", "nrep4"]], on=["repo", "sha"], how="left"); sj["breadth"] = (sj.nrep4 >= 50).map({True: "50plus", False: "5to49"})
    res["staff_breadth"] = {b: {"commits": int((st.breadth == b).sum()), "share": float((st.breadth == b).mean()), "top_org_commits": int(st[st.breadth == b].org.value_counts().iloc[0]) if (st.breadth == b).any() else 0,
                                "S": int(((sj.breadth == b) & (sj.judgment == "S")).sum()), "I": int(((sj.breadth == b) & (sj.judgment == "I")).sum()), "U": int(((sj.breadth == b) & (sj.judgment == "U")).sum())} for b in ("50plus", "5to49")}
    # checks of the previous rule (Table 2): previous-rule categories against timing and owner match, all non-bot commits outside test organizations
    cf = pd.read_csv(os.path.join(V2, "flags_v4", "commit_features.csv.gz")); rec = pd.read_csv(os.path.join(V2, "flags_v4", "repo_record.csv"))
    rec["org_test"] = rec.org.fillna("").str.contains(r"(?:test|demo|sandbox|sample|playground|staging|production)", case=False, regex=True).astype(int)
    f = cf.merge(rec[rec.org_test == 0][["repo"]], on="repo"); inh = f.shared_n >= 2; stf = ~inh & (f.author_nrepos >= 5) & (f.author_top_share < 0.5); kept = f.v3 == 1
    cats = {"shared_before": inh & (f.pre_creation_0 == 1), "shared_after": inh & (f.pre_creation_0 == 0), "staff_match": stf & (f.name_match == 1), "staff_nomatch": stf & (f.name_match == 0),
            "kept_before": kept & (f.pre_creation_0 == 1), "kept_nomatch_after": kept & (f.pre_creation_0 == 0) & (f.name_match == 0)}
    res["previous_rule_checks"] = {"n_nonbot": int(len(f)), **{k: {"commits": int(m.sum()), "before_creation": float(f[m].pre_creation_0.mean()), "before_creation_1d": float(f[m].pre_creation_1d.mean()), "owner_match": float(f[m].name_match.mean())} for k, m in cats.items()}}

    json.dump(res, open(os.path.join(V2, "results_activity_review_v4.json"), "w"), indent=1)
    print(json.dumps(res["by_category"], indent=1)); print(json.dumps(res["weighted"], indent=1)); print(json.dumps(res["variants_vs_v4"], indent=1))
