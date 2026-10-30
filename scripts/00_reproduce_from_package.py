#!/usr/bin/env python3
"""Reproduce the reported analysis from the files distributed in this package, and nothing else.

The analysis scripts were written for the author's working folder (scripts/ next to data/v2/ with unhashed
repository and organization names). This entry point builds that layout in a separate work folder from the
package's hashed derived tables, so that the scripts run unchanged, and compares what they produce with what
the package distributes. It never writes into the package.

What it does:
  1. reassembles the tables stored in 9 MB parts and checks them against SHA256SUMS_large_files.txt;
  2. copies scripts/ to <work>/scripts and writes the derived tables to <work>/data/v2 under the names the
     scripts expect, renaming repo_hash -> repo, org_hash -> org, sha_hash -> sha (the hashes keep every
     equality the analysis uses, and the rows keep their original order, so random draws are reproduced);
  3. copies the released result files (results/v4, results/v5, results/*.json) to <work>/data/v2, where the
     later steps read them, and to <work>/released for comparison;
  4. with --parts, re-fits the models of the named analysis parts of 25_analysis_v4.py from the derived tables
     (and, for rule_* names, the attribution-rule variants), compares every number in each re-fitted result
     file with the released one, and keeps the re-fitted files in <work>/refit (the later steps use the
     released files, so that their output can be compared exactly);
  5. runs 37_common_sd.py (common standardization, with its 224 deterministic checks), 38_text_numbers.py
     (the numbers cited in the text), 35_tables_v5.py (the generated tables), and 36_figs_v5.py (Figures 1 to
     4 and the data they plot), and compares the regenerated tables, text macros, and figure data with those
     in manuscript/;
  6. runs 40_check_manuscript.py, which checks the numbers typed in the manuscript source (tables written by
     hand and numbers in the text that are not macros) against the result files and derived tables.

The run fails (exit status 1) if any comparison fails; every difference is listed in
<work>/reproduction_report.json and summarized on the screen.

Tolerances (applied to every number in a result file; strings and booleans must be identical):
  * relative 1e-6 (absolute 1e-6 for numbers smaller than 1) by default; refitted random-intercept
    coefficients agree to about 1e-8, because the hashed organization labels change the order in which
    floating-point sums are accumulated;
  * relative 1e-5 for REML variance components and log-likelihoods (keys sigma2_u, sigma2, llf), which the
    optimizer determines less precisely than the coefficients;
  * absolute 1/2000 for wild-bootstrap p-values (key p_wild): they count 1,999 replicates, and ties among
    absolute bootstrap statistics can break differently when sums are accumulated in a different order.
Numbers within a tolerance but not identical are listed separately.

Steps that need the raw commit logs or the access-controlled review file (collection and extraction, owner
matching, assignment-copy detection, the commit review) cannot be run from this package; their outputs are
distributed as columns of the derived tables and as result files. See README.md.

Usage (from the package root):
  python scripts/00_reproduce_from_package.py --work /tmp/repro                       # steps 1-3, 5, 6 (about 1 minute)
  python scripts/00_reproduce_from_package.py --work /tmp/repro --parts era,agent     # also re-fit two parts
  python scripts/00_reproduce_from_package.py --work /tmp/repro --parts all --jobs 2  # re-fit every part (hours)
Requirements: Python 3.10 or later with numpy, pandas, scipy, statsmodels, matplotlib (versions used: Python
3.13, numpy 2.5, pandas 3.0, scipy 1.18, statsmodels 0.15, matplotlib 3.11).
"""
import argparse, glob, hashlib, json, os, platform, shutil, subprocess, sys, time

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENAME = {"repo_hash": "repo", "org_hash": "org", "sha_hash": "sha"}
PARTS = ["era", "agent", "era_regime", "agent_nostarter", "stability", "extra", "year", "low_msg",
         "samples_ge5", "samples_test_orgs_kept", "samples_copies_kept", "samples_tierAB", "samples_full_frame_ge3",
         "era_preswitch", "era_prebeta", "within_wide"]
RULES = ["rule_v3", "rule_v4_d0", "rule_v4_shared", "rule_v4_staff3", "rule_v4_staff10", "rule_v4_nostaff", "rule_v4_strict"]
TOL_REL, TOL_VAR, TOL_PWILD = 1e-6, 1e-5, 1.0 / 2000 + 1e-12

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def reassemble(folder, dest):
    """Concatenate <name>.partNN files listed in SHA256SUMS_large_files.txt into dest and verify them."""
    out = {}
    sums = os.path.join(folder, "SHA256SUMS_large_files.txt")
    if not os.path.exists(sums): return out
    for line in open(sums):
        digest, name = line.split()
        target = os.path.join(dest, name)
        with open(target, "wb") as w:
            for part in sorted(glob.glob(os.path.join(folder, name + ".part*"))):
                with open(part, "rb") as r: shutil.copyfileobj(r, w)
        if sha256(target) != digest: sys.exit(f"checksum mismatch for {name}")
        out[name] = target
    return out

def rename_csv(src, dst):
    import pandas as pd
    df = pd.read_csv(src, low_memory=False, dtype={"ai_tool_main": str})
    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})
    df.to_csv(dst, index=False, compression="gzip" if dst.endswith(".gz") else None)
    return len(df)

def flatten(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flatten(v, f"{prefix}[{i}]")
    else: yield prefix, x

def tolerance(key, ref):
    leaf = key.rsplit(".", 1)[-1]
    if leaf == "p_wild": return TOL_PWILD
    if leaf in ("sigma2_u", "sigma2", "llf"): return TOL_VAR * max(1.0, abs(ref))
    return TOL_REL * max(1.0, abs(ref))

def compare_json(new, ref, skip=("settings",)):
    """Compare every leaf of two JSON files. Returns (numbers compared, differences, within tolerance but not identical)."""
    A = {k: v for k, v in flatten(json.load(open(new))) if k.split(".")[0] not in skip}
    B = {k: v for k, v in flatten(json.load(open(ref))) if k.split(".")[0] not in skip}
    diff, near, n = [], [], 0
    for k in sorted(set(A) | set(B)):
        if k not in B: continue            # fields that only the re-run writes (recorded in the report, not compared)
        va, vb = A.get(k), B.get(k)
        num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        both_nan = isinstance(va, float) and isinstance(vb, float) and va != va and vb != vb
        n += 1
        if not (num(va) and num(vb)):
            if not (va == vb or both_nan): diff.append((k, va, vb))
            continue
        if va == vb or both_nan: continue
        (near if abs(va - vb) <= tolerance(k, vb) else diff).append((k, va, vb))
    only_new = sorted(set(A) - set(B))
    return n, diff, near, only_new

def run_jobs(jobs, n_parallel, cwd):
    """jobs: list of (name, cmd, env, log). Runs up to n_parallel at a time; returns {name: exit status}."""
    pending, running, status = list(jobs), [], {}
    while pending or running:
        while pending and len(running) < n_parallel:
            name, cmd, env, log = pending.pop(0)
            print(f"+ start {name}", flush=True)
            running.append((name, subprocess.Popen(cmd, env=env, cwd=cwd, stdout=open(log, "w"), stderr=subprocess.STDOUT), time.time()))
        for item in list(running):
            name, p, t0 = item
            if p.poll() is not None:
                status[name] = p.returncode; running.remove(item)
                print(f"  {name}: exit {p.returncode} after {round((time.time() - t0) / 60, 1)} min", flush=True)
        time.sleep(2)
    return status

def run(cmd, env, cwd):
    print("+", " ".join(os.path.basename(c) if c.endswith(".py") else c for c in cmd), flush=True)
    return subprocess.run(cmd, env=env, cwd=cwd).returncode

def versions():
    v = {"python": platform.python_version(), "platform": platform.platform()}
    for m in ("numpy", "pandas", "scipy", "statsmodels", "matplotlib"):
        try: v[m] = __import__(m).__version__
        except Exception as e: v[m] = f"not available ({e})"
    return v

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="new or empty folder for the run (outside the package)")
    ap.add_argument("--parts", default="", help="analysis parts to re-fit, comma-separated, or 'all' (16 parts and 7 rule variants)")
    ap.add_argument("--jobs", type=int, default=1, help="parts to run at the same time (each uses one core)")
    a = ap.parse_args()
    W = os.path.abspath(a.work)
    if W == PKG or W.startswith(PKG + os.sep): sys.exit("--work must be outside the package folder")
    if os.path.isdir(W) and os.listdir(W): sys.exit(f"--work {W} is not empty")
    V2 = os.path.join(W, "data", "v2"); OUT = os.path.join(W, "out"); REL = os.path.join(W, "released"); LOG = os.path.join(W, "logs")
    for d in (V2, os.path.join(V2, "flags_v4"), OUT, REL, LOG, os.path.join(W, "assembled")): os.makedirs(d, exist_ok=True)
    t_start = time.time(); report = {"versions": versions(), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "tolerances":
              {"default_relative": TOL_REL, "variance_components_relative": TOL_VAR, "p_wild_absolute": TOL_PWILD}, "failures": []}
    # 1-2. derived tables under the names the scripts expect
    asm = {}
    for folder in (os.path.join(PKG, "data_derived"), os.path.join(PKG, "data_derived", "v4")): asm.update(reassemble(folder, os.path.join(W, "assembled")))
    DD = os.path.join(PKG, "data_derived", "v4")
    jobs = [(os.path.join(DD, "signals_v4_hashed.csv.gz"), os.path.join(V2, "signals_v4.csv")),
            (os.path.join(DD, "repo_starter_hashed.csv"), os.path.join(V2, "repo_starter.csv")),
            (os.path.join(DD, "repo_record_hashed.csv"), os.path.join(V2, "flags_v4", "repo_record.csv"))]
    for f in sorted(glob.glob(os.path.join(DD, "signals_rule_*_hashed.csv.gz"))):
        jobs.append((f, os.path.join(V2, os.path.basename(f).replace("_hashed.csv.gz", ".csv"))))
    for f in sorted(glob.glob(os.path.join(DD, "arcs_*_hashed.csv"))):
        jobs.append((f, os.path.join(V2, "flags_v4", os.path.basename(f).replace("_hashed.csv", ".csv"))))
    jobs.append((asm["commit_features_v4_hashed.csv.gz"], os.path.join(V2, "flags_v4", "commit_features.csv.gz")))
    for src, dst in jobs: print(f"  {os.path.relpath(dst, W)}: {rename_csv(src, dst):,} rows", flush=True)
    shutil.copytree(os.path.join(PKG, "scripts"), os.path.join(W, "scripts"), dirs_exist_ok=True)
    # 3. released results: inputs of the later steps, and a copy for comparison
    for f in sorted(glob.glob(os.path.join(PKG, "results", "v4", "*.json")) + glob.glob(os.path.join(PKG, "results", "v5", "*.json")) + glob.glob(os.path.join(PKG, "results", "*.json"))):
        shutil.copy(f, V2); shutil.copy(f, REL)
    env = dict(os.environ, PYTHONHASHSEED="0", MPLBACKEND="Agg")
    S = os.path.join(W, "scripts")
    # 4. re-fit analysis parts and compare with the released results
    names = PARTS + RULES if a.parts.strip() == "all" else [p for p in a.parts.split(",") if p]
    unknown = [p for p in names if p not in PARTS + RULES]
    if unknown: sys.exit(f"unknown parts: {unknown}; known: {PARTS + RULES}")
    pj = []
    for p in names:
        if p in RULES:
            os.remove(os.path.join(V2, f"results_v4_{p}_rules.json"))
            pj.append((p, [sys.executable, os.path.join(S, "25_analysis_v4.py")], dict(env, MODE="rules", SIG_FILE=f"signals_{p}.csv", SUF=f"_{p}", B_BOOT="500"), os.path.join(LOG, f"{p}.log")))
        else:
            os.remove(os.path.join(V2, f"results_v4_{p}.json"))
            pj.append((p, [sys.executable, os.path.join(S, "25_analysis_v4.py")], dict(env, PART=p), os.path.join(LOG, f"{p}.log")))
    report["parts"] = {}
    if pj:
        st = run_jobs(pj, max(1, a.jobs), W)
        for p in names:
            fn = f"results_v4_{p}_rules.json" if p in RULES else f"results_v4_{p}.json"
            if st.get(p) != 0 or not os.path.exists(os.path.join(V2, fn)):
                report["parts"][p] = {"status": "failed to run", "log": os.path.relpath(os.path.join(LOG, f"{p}.log"), W)}; report["failures"].append(f"part {p} did not run"); continue
            n, diff, near, only_new = compare_json(os.path.join(V2, fn), os.path.join(REL, fn))
            report["parts"][p] = {"numbers_compared": n, "differences": len(diff), "within_tolerance_not_identical": len(near),
                                  "fields_only_in_rerun": len(only_new), "differences_list": diff[:50], "within_tolerance_list": near[:50]}
            if diff: report["failures"].append(f"part {p}: {len(diff)} numbers differ")
            print(f"== {p}: {n} numbers compared, {len(diff)} differ, {len(near)} within tolerance but not identical", flush=True)
            # keep the re-fitted file for inspection and restore the released one, so that the tables, figures, and
            # text numbers of step 5 are always built from the distributed results and can be compared exactly
            os.makedirs(os.path.join(W, "refit"), exist_ok=True)
            shutil.move(os.path.join(V2, fn), os.path.join(W, "refit", fn)); shutil.copy(os.path.join(REL, fn), os.path.join(V2, fn))
    # 5. common standardization, text numbers, tables, figures
    steps = [("37_common_sd.py", {}), ("38_text_numbers.py", {"OUT": os.path.join(OUT, "tables5")}),
             ("35_tables_v5.py", {"OUT": os.path.join(OUT, "tables5")}), ("36_figs_v5.py", {"OUT": os.path.join(OUT, "figs")})]
    for script, extra in steps:
        if run([sys.executable, os.path.join(S, script)], dict(env, **extra), W): report["failures"].append(f"{script} failed")
    tables = {"identical": [], "different": [], "missing_in_rerun": []}
    for ref in sorted(glob.glob(os.path.join(PKG, "manuscript", "tables5", "*.tex"))):
        f = os.path.join(OUT, "tables5", os.path.basename(ref))
        if not os.path.exists(f): tables["missing_in_rerun"].append(os.path.basename(ref))
        else: tables["identical" if open(f).read() == open(ref).read() else "different"].append(os.path.basename(ref))
    report["tables5"] = tables
    if tables["different"] or tables["missing_in_rerun"]: report["failures"].append(f"tables differ or missing: {tables['different'] + tables['missing_in_rerun']}")
    report["results_v5"] = {}
    for ref in sorted(glob.glob(os.path.join(REL, "results_v5_*.json"))):
        f = os.path.join(V2, os.path.basename(ref))
        n, diff, near, _ = compare_json(f, ref)
        report["results_v5"][os.path.basename(ref)] = {"numbers_compared": n, "differences": len(diff), "within_tolerance_not_identical": len(near), "differences_list": diff[:20]}
        if diff: report["failures"].append(f"{os.path.basename(ref)}: {len(diff)} numbers differ")
    fd_new, fd_ref = os.path.join(OUT, "figs", "figure_data.json"), os.path.join(PKG, "manuscript", "figs", "figure_data.json")
    if os.path.exists(fd_new) and os.path.exists(fd_ref):
        n, diff, near, _ = compare_json(fd_new, fd_ref)
        report["figure_data"] = {"numbers_compared": n, "differences": len(diff), "differences_list": diff[:20]}
        if diff: report["failures"].append(f"figure data: {len(diff)} numbers differ")
    else: report["failures"].append("figure data missing"); report["figure_data"] = "missing"
    # 6. numbers typed in the manuscript source
    rc = run([sys.executable, os.path.join(S, "40_check_manuscript.py"), "--tex", os.path.join(PKG, "manuscript", "main.tex"),
              "--results", V2, "--derived", V2, "--registration", os.path.join(PKG, "registration"), "--report", os.path.join(W, "manuscript_check.json")], env, W)
    report["manuscript_check"] = json.load(open(os.path.join(W, "manuscript_check.json"))) if os.path.exists(os.path.join(W, "manuscript_check.json")) else "missing"
    if rc: report["failures"].append("40_check_manuscript.py reported mismatches or unchecked numbers")
    report["minutes"] = round((time.time() - t_start) / 60, 1)
    json.dump(report, open(os.path.join(W, "reproduction_report.json"), "w"), indent=1, default=str)
    print(f"== tables identical to manuscript/tables5: {len(tables['identical'])}; different: {tables['different']}; missing: {tables['missing_in_rerun']}")
    print(f"== report: {os.path.join(W, 'reproduction_report.json')}")
    if report["failures"]:
        print("== FAILED:\n  " + "\n  ".join(report["failures"])); sys.exit(1)
    print("== all comparisons passed"); sys.exit(0)
