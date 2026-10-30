#!/usr/bin/env python3
"""논문 2 v4 — 과제 사본(assignment copy) 이름 규칙의 제한 확인 (2026-10-30, 7차 작업지시서).
이름 규칙과 독립적인 근거로 GitHub의 저장소 관계를 본다. Classroom의 과제 사본은 템플릿에서 생성되고(저장소 페이지의
"generated from" 표시), 학생 저장소들의 포크 원본이므로 포크 수가 0보다 클 것으로 예상된다. 비교군은 같은 기간(2024-07 이후)에
생성된 비사본 검증 저장소와 2024년 이전에 생성된 검증 저장소.
표본: seed 20261030으로 사본 40개, 같은 기간 비사본 40개, 2024년 이전 비사본 20개(검증 저장소, 테스트 조직 제외).
절차: 각 저장소의 공개 페이지(https://github.com/{owner}/{repo})에서 포크 수 표시("<strong>N</strong> forks")와 "generated from",
"forked from" 문구를 읽는다. 이 연구에서는 분석 환경의 네트워크 제한 때문에 같은 표본과 같은 판별식을 저자의 브라우저에서 실행했고
(2026-10-30), 그 집계를 아래 RESULT에 기록했다. 네트워크가 허용되는 환경에서는 이 스크립트를 그대로 실행해 재현할 수 있다.
출력: data/v2/results_copy_check.json (집계만; 저장소 이름은 쓰지 않는다)"""
import os, json, re, time, urllib.request
import numpy as np, pandas as pd
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
FORK_RE = re.compile(r"<span><strong>([\d,]+)</strong></span><span> forks?</span>")

def sample():
    rec = pd.read_csv(os.path.join(V2, "flags_v4", "repo_record.csv"))
    rec["org_test"] = rec.org.fillna("").str.contains(r"(?:test|demo|sandbox|sample|playground|staging|production)", case=False, regex=True).astype(int)
    rec = rec[rec.org_test == 0].copy(); rec["created"] = pd.to_datetime(rec.created_ts, unit="s")
    groups = {"copy_after_2024_07": (rec[(rec.assignment_copy == 1) & (rec.created >= "2024-07-01")], 40),
              "noncopy_after_2024_07": (rec[(rec.assignment_copy == 0) & (rec.created >= "2024-07-01")], 40),
              "noncopy_before_2024": (rec[(rec.assignment_copy == 0) & (rec.created < "2024-01-01")], 20)}
    rng = np.random.default_rng(20261030)
    return {g: list(d.iloc[rng.permutation(len(d))[:k]].repo) for g, (d, k) in groups.items()}

def check(repo):
    try:
        t = urllib.request.urlopen("https://github.com/" + repo, timeout=30).read().decode("utf-8", "replace")
    except Exception:
        return None
    m = FORK_RE.search(t)
    return {"forks": int(m.group(1).replace(",", "")) if m else None, "generated_from": bool(re.search("generated from", t, re.I)), "forked_from": bool(re.search("forked from", t, re.I))}

def summarize(rows):
    out = {}
    for g, lst in rows.items():
        ok = [r for r in lst if r]; f = sorted(r["forks"] or 0 for r in ok)
        out[g] = {"sampled": len(lst), "pages_read": len(ok), "with_forks": sum(v > 0 for v in f), "median_forks": f[len(f) // 2] if f else None,
                  "generated_from_template": sum(r["generated_from"] for r in ok), "forked_from": sum(r["forked_from"] for r in ok)}
    return out

# Aggregate of the run in the author's browser on 2026-10-30 (same sample and parsing as check()).
RESULT = {"copy_after_2024_07": {"sampled": 40, "pages_read": 40, "with_forks": 28, "median_forks": 3, "generated_from_template": 30, "forked_from": 0},
          "noncopy_after_2024_07": {"sampled": 40, "pages_read": 40, "with_forks": 9, "median_forks": 0, "generated_from_template": 10, "forked_from": 0},
          "noncopy_before_2024": {"sampled": 20, "pages_read": 20, "with_forks": 2, "median_forks": 0, "generated_from_template": 12, "forked_from": 0}}

if __name__ == "__main__":
    S = sample()
    if os.environ.get("RUN_NETWORK") == "1":
        rows = {g: [] for g in S}
        for g, lst in S.items():
            for repo in lst: rows[g].append(check(repo)); time.sleep(0.3)
        res = summarize(rows)
    else:
        res = RESULT
    json.dump({"procedure": __doc__.split("출력:")[0].strip(), "groups": res}, open(os.path.join(V2, "results_copy_check.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1))
