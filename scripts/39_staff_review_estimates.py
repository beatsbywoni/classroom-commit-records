#!/usr/bin/env python3
"""Paper 2, 8th work order, item 3: estimates of the share of staff-like exclusions judged student work, respecting the
review design.

The review sampled up to eight commits per cell of rule outcome x period x organization size (29_activity_review_v4.py),
so commits in different cells had different inclusion probabilities (8 / cell population). An earlier draft regrouped the
staff-like sample by author breadth and multiplied unweighted proportions by the population breadth shares, which ignores
those probabilities. This script reports, for the 32 reviewed staff-like commits:
  design      the design-weighted (Horvitz-Thompson) share judged student work, weights = cell population / cell sample;
  poststrat   a post-stratified estimate: within each design cell, the sample is split by author breadth (authors active in
              50 or more repositories of an organization vs 5 to 49), each cell x breadth share is estimated from the
              commits sampled in it and weighted by its population count; cell x breadth groups with no sampled commit
              are listed (their population is not covered and is reported, not imputed);
  counts      judgments by breadth and cell, and the population of each cell x breadth group.
Output: data/v2/results_staff_review.json (counts only; no commit text).
"""
import os, json, importlib.util
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("R", os.path.join(HERE, "29_activity_review_v4.py")); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
V2 = R.V2
c, _, _ = R.frame(); c = c[(c.period != "buffer") & (c.cat == "excl_staff")].copy()
c["breadth"] = np.where(c.nrep4 >= 50, "50plus", "5to49")
s = pd.read_csv(os.path.join(V2, "private", "activity_review_v4_PRIVATE.csv")); s = s[s.cat == "excl_staff"].copy()
s["judgment"] = s.judgment.str.strip().str.upper()
s = s.merge(c[["repo", "sha", "breadth", "org"]], on=["repo", "sha"], how="left")
assert s.breadth.notna().all()
popc = c.groupby(["period", "orgsize"]).size(); popcb = c.groupby(["period", "orgsize", "breadth"]).size()
nc = s.groupby(["period", "orgsize"]).size()
s["w"] = [popc[(p, o)] / nc[(p, o)] for p, o in zip(s.period, s.orgsize)]
design = float((s.w * (s.judgment == "S")).sum() / s.w.sum())
design_U = float((s.w * (s.judgment == "U")).sum() / s.w.sum())
# post-stratification within design cells by author breadth
rows, covered, tot = [], 0, int(len(c))
num = 0.0
for (p, o, b), N in popcb.items():
    g = s[(s.period == p) & (s.orgsize == o) & (s.breadth == b)]
    rows.append({"period": p, "orgsize": o, "breadth": b, "pop": int(N), "n": int(len(g)), "S": int((g.judgment == "S").sum()),
                 "I": int((g.judgment == "I").sum()), "U": int((g.judgment == "U").sum())})
    if len(g): covered += int(N); num += N * (g.judgment == "S").mean()
poststrat = num / covered if covered else float("nan")
out = {"population": tot, "sampled": int(len(s)),
       "by_breadth": {b: {"pop": int((c.breadth == b).sum()), "n": int((s.breadth == b).sum()), "S": int(((s.breadth == b) & (s.judgment == "S")).sum()),
                          "I": int(((s.breadth == b) & (s.judgment == "I")).sum()), "U": int(((s.breadth == b) & (s.judgment == "U")).sum()),
                          "orgs_in_pop": int(c[c.breadth == b].org.nunique()), "orgs_in_sample": int(s[s.breadth == b].org.nunique())} for b in ("50plus", "5to49")},
       "cells": rows, "design_weighted_S": design, "design_weighted_U": design_U,
       "poststratified_S": poststrat, "poststratified_population_covered": covered,
       "sample_orgs": int(s.org.nunique()), "sample_repos": int(s.repo.nunique())}
json.dump(out, open(os.path.join(V2, "results_staff_review.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
