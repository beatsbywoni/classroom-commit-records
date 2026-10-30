# GitHub Classroom commit records before and after generative AI: replication package

This package accompanies a manuscript under double-anonymous review about what must be verified before commit records of public GitHub Classroom repositories are read as traces of students' work (the title and citation will be added on publication). It contains everything needed to reproduce every number, table and figure in the manuscript from the derived tables, the preregistered protocol and the results of the registered analysis exactly as the registered scripts produced them, and the results of the intermediate analyses that the manuscript's Appendix B describes.

## Contents

| Folder | What it holds |
|---|---|
| `scripts/` | Collection (`01`–`06`, bash), registered extraction and analysis (`07a`, `07b`, `08`, `09`), the intermediate pipelines (`10`–`21`), the pipeline of the reported analysis (`22`–`39`, `reml_ri.py`, `run_v4_parts.sh`), and the entry point `00_reproduce_from_package.py`. See "Pipeline" below. |
| `data_derived/v4/` | Tables of the reported analysis. `signals_v4_hashed.csv.gz`: one row per repository with all signals computed under the adopted activity rule, covariates, sample flags, assignment-copy flag and creation time (the table the paper uses). `signals_rule_*_hashed.csv.gz`: the same under the previous rule and six variants (Table 16 of the paper). `commit_features_v4_hashed.csv.gz`: for every non-bot commit, committer and author time, whether it predates repository creation (any amount, more than one day), how many repositories of the organization share its SHA, whether the author's identifiers match the repository name, the author's number of repositories and top-contributor share in the organization, and the outcome of every activity rule. `repo_record_hashed.csv`: per verified repository, creation time, assignment-copy flag, non-bot commit count and number of owner-matched authors. `repo_starter_hashed.csv`: whether the repository's root commit was made by the Classroom bot and how many lines it added (starter code). `arcs_*_hashed.csv`: same-file rerun runs under each rule. `row_counts.json`. |
| `data_derived/` | Tables of the earlier analyses (`commits_v2_hashed.csv.gz`, `commit_history_flags_hashed.csv.gz`, `signals_v3_hashed.csv.gz`, `signals_v2_hashed.csv.gz`, `sample_flags_hashed.csv.gz`, `registered_analysis_table_hashed.csv.gz`, thresholds). |
| `registration/` | The OSF preregistration text (August 6, 2026), the frozen SHA-256 manifest, the implementation-decision log D1–D10, and the registered results. |
| `results/v4/` | Results of the reported analysis, one JSON file per analysis part (`results_v4_era.json`, `results_v4_agent.json`, `results_v4_era_preswitch.json` and `results_v4_era_prebeta.json` (post-era repositories created before July 1 and January 1, 2024), `results_v4_agent_nostarter.json`, `results_v4_within_wide.json` (test inversion on the wider grid), `results_v4_era_regime.json` (an earlier restriction by the date of the first classified commit, superseded by the two restrictions by creation date), `results_v4_year.json`, `results_v4_low_msg.json`, `results_v4_extra.json`, `results_v4_stability.json`, `results_v4_samples_*.json`, `results_v4_rule_*_rules.json`, `results_v4_descriptives.json`, `results_v4_summary.json`), the trailer analysis (`results_trailer_v4.json`), record generation (`results_record_generation.json`) and the check of the assignment-copy rule against public repository pages (`results_copy_check.json`), the checks of the activity rules (`results_activity_validation.json`, `results_activity_review_v4.json`: stratum counts and judgments, no commit text), and the validation of the REML implementation (`results_reml_validation.json`). |
| `results/v5/` | The standardized estimates as reported: `results_v5_*.json` have the structure of the corresponding `results_v4_*.json`, with every standardized estimate of a contrast divided by one SD, that of the signal in the primary sample of the contrast (`37_common_sd.py`; `results_v5_sdref.json` gives the SDs, the per-signal analysis N, and the 224 checks of the conversion). `results_staff_review.json`: design-weighted and post-stratified estimates for the review of staff-like exclusions (`39_staff_review_estimates.py`; counts only). |
| `results/` | Results of the intermediate analyses (`results_composition_v3.*`, `results_v2*.json`, and others). |
| `figures/` | Figures of the paper (`fig_compare_v5`, `fig_registered_vs_raw_v3`, `fig_yearfe_v5`, `fig_trailer_v4`) and figures of the intermediate analyses. |
| `manuscript/` | LaTeX source of the submitted version (`main_v6.tex`, `tables5/` including `results_macros.tex`, which holds every result number cited in the text, `figs/`) and its bibliography. |
| `LICENSE`, `LICENSE-DATA.md` | Code under the MIT License; data, results, figures and documentation under CC BY 4.0. |
| `DEVIATIONS.md` | D1–D10 (registered implementation decisions) and E1–E15 (post-registration decisions) with dates, rationale and implementing scripts. |
| `AI_USE.md` | How a large language model was used in this research, per the ACM Policy on Authorship. |

## Large files

Three compressed tables are stored in parts of 9 MB so that every file can be uploaded through the GitHub web interface: `data_derived/commits_v2_hashed.csv.gz`, `data_derived/commit_history_flags_hashed.csv.gz`, and `data_derived/v4/commit_features_v4_hashed.csv.gz`. Reassemble each before use and check it against `SHA256SUMS_large_files.txt` in the same folder:

```
cd data_derived && for f in commits_v2_hashed.csv.gz commit_history_flags_hashed.csv.gz; do cat $f.part* > $f; done && sha256sum -c SHA256SUMS_large_files.txt
cd v4 && cat commit_features_v4_hashed.csv.gz.part* > commit_features_v4_hashed.csv.gz && sha256sum -c SHA256SUMS_large_files.txt
```

## Reproducing the results from this package

`scripts/00_reproduce_from_package.py` runs the analysis from the files in this package only. It builds, in a separate work folder, the layout the scripts were written for (`scripts/` next to `data/v2/`): it reassembles the tables stored in parts and checks their SHA-256 sums, writes the hashed derived tables under the names the scripts expect (renaming `repo_hash`, `org_hash`, and `sha_hash` to `repo`, `org`, and `sha`; the hashes preserve every equality the analysis uses, and rows keep their original order, so random draws are reproduced), copies the released result files, and then runs the steps below, comparing every regenerated table and result with the released one and writing `reproduction_report.json`.

```
python scripts/00_reproduce_from_package.py --work /path/to/empty/folder              # about 1 minute
python scripts/00_reproduce_from_package.py --work /path/to/empty/folder --parts era  # also re-runs one analysis part
```

Environment used: Python 3.13 with numpy 2.5, pandas 3.0, scipy 1.18, statsmodels 0.15, and matplotlib 3.11 (Python 3.10 or later with recent versions of these packages should work). Analysis parts are those listed in `PARTS` of `25_analysis_v4.py`; `era` and `agent` take the longest (organization bootstraps with 1,000 replicates for three caps and seven signals).

What can be reproduced from this package, and what cannot:

| Step | From this package | Notes |
|---|---|---|
| All comparisons of the paper (`25_analysis_v4.py`, every part), common standardization (`37`), text numbers (`38`), tables (`35`), figures (`36`, `30`), REML validation (`26`), trailer model (`27`), record generation tables (`28`, from `repo_record` and `repo_starter`) | Yes | See the test below. |
| Collection and extraction (`01`–`03`, `11`), the commit-level flags and owner matching (`23`), assignment-copy detection | No | Need the raw logs and repository names, which are not distributed; their outputs are distributed as columns. |
| Commit review (`29`, `39`) | No | The judged file contains commit subjects and is access-controlled; the counts and estimates are distributed. |
| Check of the copy rule (`34`) | Partly | Re-runnable with network access to github.com (`RUN_NETWORK=1`) on the unhashed sample; the result recorded in the paper is stored in the script. |
| Registered analysis (`07a`–`09`) and intermediate analyses (`10`–`21`) | Partly | Their tables of results are distributed; re-running needs the raw logs. |

Test of this package (October 30, 2026), run on a copy of the package in a new folder: (1) without `--parts`, the 12 generated table and text-macro files were identical to those in `manuscript/tables5/`, and the 224 deterministic checks of `37_common_sd.py` passed on the hashed data; (2) with `--parts era`, the post-ChatGPT analysis was re-run from the hashed tables (about 25 minutes on two cores) and 664 of the 667 numbers in `results_v4_era.json` agreed with the released file to a relative tolerance of 1e-6, including every estimate, every capped bootstrap interval, and every within-organization interval (the re-run file also records 28 grid fields that the released file, produced by an earlier version of the within-organization function, does not); the exceptions were one organization variance (relative difference 1.1e-6) and two wild-bootstrap p-values that differ by one replicate in 2,000 (.2695 against .269, .9405 against .940), because ties among absolute bootstrap statistics break differently when floating-point sums are accumulated in a different order. The other analysis parts were not re-run in this test.

## Identifiers and privacy

Repository names, organization names and commit SHAs are replaced by salted SHA-256 hashes (16 hex characters; one salt for all three, so that a SHA shared by two repositories of one organization is still detectable as shared). Author identities were hashed at scan time with a different salt, and the identity matching of the activity rule stores only whether a match occurred. Neither salt is distributed. Commit messages are not distributed. Raw `git log` output for the 58,516 repositories and the manual-review file (which contains commit subject lines) are not distributed because they contain names, e-mail addresses and free text; they are available to reviewers and editors on request under access control.

## Pipeline of the reported analysis

1. `01_pilot_count.sh` … `03_clone_extract.sh`: enumerate the frame through the GitHub Search API (which excludes forks unless asked) and clone each repository bare, extracting `git log --all --numstat`. Requires a GitHub token and network access; outputs are the raw logs (not distributed).
2. `11_extract_commits_v2.py`, `10_sample_v2.py`: commit-level table and sampling-frame flags.
3. `23_flags_v4.py`: one pass over the raw logs computing, for every non-bot commit in verified repositories, timing relative to repository creation, SHA sharing, owner match and author activity, and the outcome of the adopted activity rule and its variants; repository record with assignment-copy detection (`commit_features`, `repo_record`, `arcs_*`).
4. `12_signals_v2.py` with `FLAGS_FILE`, `ARCS_FILE`, `RECORD_FILE` and `OUT_NAME`: repository-level signals under each rule (`signals_v4`, `signals_rule_*`).
5. `22_activity_audit.py`, `29_activity_review_v4.py`: checks of the activity rules against timing and identity; stratified review sample and, given the judged file, stratum and weighted rates (`results_activity_validation.json`, `results_activity_review_v4.json`).
6. `33_starter_code.py`: root commits by the Classroom bot (starter code). `28_record_generation.py`: verified repositories by creation half-year, assignment copies, starter-code share, observation time. `34_verify_copies.py`: records the check of the assignment-copy name rule on sampled repositories against their public pages (number of forks; generated from a template); the pages were read in a browser session, and the script documents the samples and stores the result.
7. `25_analysis_v4.py` (run part by part with `PART=...`, or all parts with `run_v4_parts.sh`): all comparisons, using `reml_ri.py` for random-intercept models; contribution-capped estimates with organization-bootstrap intervals; within-organization comparisons with restricted wild cluster bootstrap and test inversion; year effects; low-commit repositories; thresholds; samples; rule variants (`MODE=rules`); stability.
8. `26_validate_reml.py`: the REML implementation against statsmodels (Nelder–Mead, BFGS, L-BFGS).
9. `27_trailer_v4.py`: AI and human-co-author trailer model.
10. `37_common_sd.py`: re-expresses every standardized estimate of a contrast in one unit (the SD of the signal in the primary sample of the contrast), recomputing and checking the deterministic coefficients; writes `results_v5_*.json`.
11. `38_text_numbers.py`: writes `results_macros.tex`, one LaTeX macro per result number cited in the text, from the result files. `36_figs_v5.py`, `35_tables_v5.py` (and `30_figs_v4.py` for the trailer figure): figures and LaTeX tables of the submitted manuscript from the result files (no refitting). `31_tables_v4.py` produced the tables of an earlier draft.
12. `39_staff_review_estimates.py`: design-based estimates for the staff-like category of the commit review (needs the access-controlled review file; its output is distributed).
13. `32_build_package_v4.py`: assembles this layer of the package (hashing identifiers).

Steps 4 to 11 run from the distributed tables on a laptop; the full set of analysis parts takes about two hours on two cores, most of it the full-frame sample sensitivity. The scripts are provided in the form that was run on the unhashed data; `00_reproduce_from_package.py` (above) builds the layout and column names they expect from the hashed tables. Two steps need information that hashing removes and are reproducible only from the raw logs: owner matching (which compares author identifiers with the repository name) and assignment-copy detection (which reads the repository name); their outputs are distributed as columns.

## Pipelines of the earlier analyses

`13_analysis_v2.py`, `14_figures_v2.py`, `16_composition_v2.py`, `17_history_flags.py`, `18_arcs_student.py`, `19_inclusion_all.py`, `20_sample_sensitivity.py`, `21_figs_from_json.py` reproduce the intermediate analyses described in Appendix B of the paper; `07a`, `07b`, `08`, `09` reproduce the registered analysis. DEVIATIONS.md maps each decision to its script.

## Citation

Jeong, H. (2026). GitHub Classroom commit records before and after generative AI: replication package (activity attribution, platform change, organization weighting) (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.23797543 (all versions: https://doi.org/10.5281/zenodo.23797542)
