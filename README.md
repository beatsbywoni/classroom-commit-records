# GitHub Classroom commit records before and after generative AI: replication package

This package accompanies a manuscript under double-anonymous review about what must be verified before commit records of public GitHub Classroom repositories are read as traces of students' work (the title and citation will be added on publication). It contains everything needed to reproduce every number, table and figure in the manuscript from the derived tables, the preregistered protocol and the results of the registered analysis exactly as the registered scripts produced them, and the results of the intermediate analyses that the manuscript's Appendix B describes.

## Contents

| Folder | What it holds |
|---|---|
| `scripts/` | Collection (`01`–`06`, bash), registered extraction and analysis (`07a`, `07b`, `08`, `09`), the intermediate pipelines (`10`–`21`), and the pipeline of the reported analysis (`22`–`36`, `reml_ri.py`, `run_v4_parts.sh`). See "Pipeline" below. |
| `data_derived/v4/` | Tables of the reported analysis. `signals_v4_hashed.csv.gz`: one row per repository with all signals computed under the adopted activity rule, covariates, sample flags, assignment-copy flag and creation time (the table the paper uses). `signals_rule_*_hashed.csv.gz`: the same under the previous rule and six variants (Table 16 of the paper). `commit_features_v4_hashed.csv.gz`: for every non-bot commit, committer and author time, whether it predates repository creation (any amount, more than one day), how many repositories of the organization share its SHA, whether the author's identifiers match the repository name, the author's number of repositories and top-contributor share in the organization, and the outcome of every activity rule. `repo_record_hashed.csv`: per verified repository, creation time, assignment-copy flag, non-bot commit count and number of owner-matched authors. `repo_starter_hashed.csv`: whether the repository's root commit was made by the Classroom bot and how many lines it added (starter code). `arcs_*_hashed.csv`: same-file rerun runs under each rule. `row_counts.json`. |
| `data_derived/` | Tables of the earlier analyses (`commits_v2_hashed.csv.gz`, `commit_history_flags_hashed.csv.gz`, `signals_v3_hashed.csv.gz`, `signals_v2_hashed.csv.gz`, `sample_flags_hashed.csv.gz`, `registered_analysis_table_hashed.csv.gz`, thresholds). |
| `registration/` | The OSF preregistration text (August 6, 2026), the frozen SHA-256 manifest, the implementation-decision log D1–D10, and the registered results. |
| `results/v4/` | Results of the reported analysis, one JSON file per analysis part (`results_v4_era.json`, `results_v4_agent.json`, `results_v4_era_preswitch.json` and `results_v4_era_prebeta.json` (post-era repositories created before July 1 and January 1, 2024), `results_v4_agent_nostarter.json`, `results_v4_within_wide.json` (test inversion on the wider grid), `results_v4_era_regime.json` (an earlier restriction by the date of the first classified commit, superseded by the two restrictions by creation date), `results_v4_year.json`, `results_v4_low_msg.json`, `results_v4_extra.json`, `results_v4_stability.json`, `results_v4_samples_*.json`, `results_v4_rule_*_rules.json`, `results_v4_descriptives.json`, `results_v4_summary.json`), the trailer analysis (`results_trailer_v4.json`), record generation (`results_record_generation.json`) and the check of the assignment-copy rule against public repository pages (`results_copy_check.json`), the checks of the activity rules (`results_activity_validation.json`, `results_activity_review_v4.json`: stratum counts and judgments, no commit text), and the validation of the REML implementation (`results_reml_validation.json`). |
| `results/` | Results of the intermediate analyses (`results_composition_v3.*`, `results_v2*.json`, and others). |
| `figures/` | Figures of the paper (`fig_compare_v5`, `fig_registered_vs_raw_v3`, `fig_yearfe_v5`, `fig_trailer_v4`) and figures of the intermediate analyses. |
| `manuscript/` | LaTeX source of the submitted version (`main_v5.tex`, `tables5/`, `figs/`) and its bibliography. |
| `LICENSE`, `LICENSE-DATA.md` | Code under the MIT License; data, results, figures and documentation under CC BY 4.0. |
| `DEVIATIONS.md` | D1–D10 (registered implementation decisions) and E1–E14 (post-registration decisions) with dates, rationale and implementing scripts. |
| `AI_USE.md` | How a large language model was used in this research, per the ACM Policy on Authorship. |

## Large files

Three compressed tables are stored in parts of 9 MB so that every file can be uploaded through the GitHub web interface: `data_derived/commits_v2_hashed.csv.gz`, `data_derived/commit_history_flags_hashed.csv.gz`, and `data_derived/v4/commit_features_v4_hashed.csv.gz`. Reassemble each before use and check it against `SHA256SUMS_large_files.txt` in the same folder:

```
cd data_derived && for f in commits_v2_hashed.csv.gz commit_history_flags_hashed.csv.gz; do cat $f.part* > $f; done && sha256sum -c SHA256SUMS_large_files.txt
cd v4 && cat commit_features_v4_hashed.csv.gz.part* > commit_features_v4_hashed.csv.gz && sha256sum -c SHA256SUMS_large_files.txt
```

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
10. `36_figs_v5.py`, `35_tables_v5.py` (and `30_figs_v4.py` for the trailer figure): figures and LaTeX tables of the submitted manuscript from the result files (no refitting). `31_tables_v4.py` produced the tables of an earlier draft.
11. `32_build_package_v4.py`: assembles this layer of the package (hashing identifiers).

Steps 4–10 run from the distributed tables on a laptop (Python 3.10+, pandas, numpy, scipy, statsmodels 0.14+, matplotlib); the full set of analysis parts takes about two hours on two cores, most of it the full-frame sample sensitivity. Because repository names and SHAs are hashed in the distributed tables, the scripts are provided in the form that was run on the unhashed data; a reader reproducing from the hashed tables should join on `repo_hash`, `org_hash` and `sha_hash` instead of `repo`, `org` and `sha`. Two steps need information that hashing removes and are reproducible only from the raw logs: owner matching (which compares author identifiers with the repository name) and assignment-copy detection (which reads the repository name); their outputs are distributed as columns.

## Pipelines of the earlier analyses

`13_analysis_v2.py`, `14_figures_v2.py`, `16_composition_v2.py`, `17_history_flags.py`, `18_arcs_student.py`, `19_inclusion_all.py`, `20_sample_sensitivity.py`, `21_figs_from_json.py` reproduce the intermediate analyses described in Appendix B of the paper; `07a`, `07b`, `08`, `09` reproduce the registered analysis. DEVIATIONS.md maps each decision to its script.

## Citation

[Zenodo DOI to be inserted.]
