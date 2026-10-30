#!/usr/bin/env python3
"""Reproduce the reported analysis from the files distributed in this package, and nothing else.

The analysis scripts were written for the author's working folder (scripts/ next to data/v2/ with unhashed
repository and organization names). This entry point builds that layout in a separate work folder from the
package's hashed derived tables, so the scripts run unchanged:

  1. reassembles the tables stored in 9 MB parts and checks them against SHA256SUMS_large_files.txt;
  2. copies scripts/ to <work>/scripts and writes the derived tables to <work>/data/v2 under the names the
     scripts expect, renaming repo_hash -> repo, org_hash -> org, sha_hash -> sha (the hashes keep every
     equality the analysis uses, and the rows keep their original order, so random draws are reproduced);
  3. copies the released result files to <work>/data/v2 (the inputs of the table, figure, and text steps) and
     to <work>/released for comparison;
  4. optionally re-runs analysis parts of 25_analysis_v4.py (--parts era,agent,...) and compares every number
     in each re-run result file with the released one;
  5. runs 37_common_sd.py (common standardization), 38_text_numbers.py (numbers cited in the text),
     35_tables_v5.py (tables), and 36_figs_v5.py (figures), writing to <work>/out, and compares the
     regenerated tables and text macros with those in manuscript/.

Steps that need the raw commit logs (collection, extraction, owner matching, assignment-copy detection, the
commit review, which contains commit subjects) cannot be run from this package; their outputs are distributed.

Usage (from the package root):
  python scripts/00_reproduce_from_package.py --work /tmp/repro                 # tables, figures, text numbers
  python scripts/00_reproduce_from_package.py --work /tmp/repro --parts era     # also re-run one analysis part
Requirements: Python 3.10 or later with numpy, pandas, scipy, statsmodels, matplotlib (versions used: Python
3.13, numpy 2.5, pandas 3.0, scipy 1.18, statsmodels 0.15, matplotlib 3.11).
"""
import argparse, glob, gzip, hashlib, json, os, shutil, subprocess, sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENAME = {"repo_hash": "repo", "org_hash": "org", "sha_hash": "sha"}
# numbers are compared to a relative tolerance of 1e-6: refitted random-intercept models agree to about 1e-8,
# because the hashed organization labels change the order in which floating-point sums are accumulated
TOL = 1e-6

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

def run(cmd, env, cwd):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, env=env, cwd=cwd)
    if r.returncode: sys.exit(f"step failed: {' '.join(cmd)}")

def flatten(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flatten(v, f"{prefix}[{i}]")
    else: yield prefix, x

def compare_json(a, b, skip=("settings",)):
    A = {k: v for k, v in flatten(json.load(open(a))) if not k.split(".")[0] in skip}
    B = {k: v for k, v in flatten(json.load(open(b))) if not k.split(".")[0] in skip}
    diff, n = [], 0
    for k in sorted(set(A) | set(B)):
        va, vb = A.get(k), B.get(k)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            n += 1
            if abs(va - vb) > TOL * max(1.0, abs(vb)): diff.append((k, va, vb))
        elif va != vb and not (va is None and vb is None):
            n += 1; diff.append((k, va, vb))
    return n, diff

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="empty or new folder for the run")
    ap.add_argument("--parts", default="", help="comma-separated analysis parts of 25_analysis_v4.py to re-run (e.g. era,agent)")
    a = ap.parse_args()
    W = os.path.abspath(a.work); V2 = os.path.join(W, "data", "v2"); OUT = os.path.join(W, "out"); REL = os.path.join(W, "released")
    for d in (V2, os.path.join(V2, "flags_v4"), OUT, REL, os.path.join(W, "assembled")): os.makedirs(d, exist_ok=True)
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
    for f in glob.glob(os.path.join(PKG, "results", "v4", "*.json")) + glob.glob(os.path.join(PKG, "results", "v5", "*.json")):
        shutil.copy(f, V2); shutil.copy(f, REL)
    env = dict(os.environ, PYTHONHASHSEED="0")
    S = os.path.join(W, "scripts")
    # 4. re-run analysis parts and compare with the released results
    report = {}
    for part in [p for p in a.parts.split(",") if p]:
        run([sys.executable, os.path.join(S, "25_analysis_v4.py")], dict(env, PART=part), W)
        n, diff = compare_json(os.path.join(V2, f"results_v4_{part}.json"), os.path.join(REL, f"results_v4_{part}.json"))
        report[part] = {"numbers_compared": n, "differences": len(diff), "first_differences": diff[:10]}
        print(f"== {part}: {n} numbers compared, {len(diff)} differ", flush=True)
    # 5. common standardization, text numbers, tables, figures
    run([sys.executable, os.path.join(S, "37_common_sd.py")], env, W)
    run([sys.executable, os.path.join(S, "38_text_numbers.py")], dict(env, OUT=os.path.join(OUT, "tables5")), W)
    run([sys.executable, os.path.join(S, "35_tables_v5.py")], dict(env, OUT=os.path.join(OUT, "tables5")), W)
    run([sys.executable, os.path.join(S, "36_figs_v5.py")], dict(env, OUT=os.path.join(OUT, "figs")), W)
    same, differ = [], []
    for f in sorted(glob.glob(os.path.join(OUT, "tables5", "*.tex"))):
        ref = os.path.join(PKG, "manuscript", "tables5", os.path.basename(f))
        if os.path.exists(ref): (same if open(f).read() == open(ref).read() else differ).append(os.path.basename(f))
    for f in sorted(glob.glob(os.path.join(V2, "results_v5_*.json"))):
        ref = os.path.join(REL, os.path.basename(f))
        if os.path.exists(ref):
            n, diff = compare_json(f, ref); report[os.path.basename(f)] = {"numbers_compared": n, "differences": len(diff), "first_differences": diff[:5]}
    report["tables_identical"] = same; report["tables_different"] = differ
    json.dump(report, open(os.path.join(W, "reproduction_report.json"), "w"), indent=1, default=str)
    print(f"== tables identical to manuscript/tables5: {len(same)}; different: {differ}")
    print(f"== report: {os.path.join(W, 'reproduction_report.json')}")
