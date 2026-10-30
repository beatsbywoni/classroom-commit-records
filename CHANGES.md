# Changes between released versions of this package

## v1.2.0 (October 30, 2026): version submitted for review

- Manuscript source: `manuscript/main.tex` (replaces `main_v6.tex`) with its bibliography reduced to the 39 cited works. Changes in the text: the natural-unit effect of edit size is described as a modeled percent difference in one plus the median lines per commit (the signal is `log(1 + median)`), and the table note gives the transformation; statements about large insertions, the retirement of Classroom, and the commit review were narrowed to what the evidence shows; Section 2.3 was folded into the end of Section 2.2; the methods statement on AI use (Section 3.6) and the Generative AI Disclosure were separated; Appendix B was shortened (the full decision log stays in `DEVIATIONS.md`); the ethics statement now says that no institutional ethics review was sought; the data statement now states what the package can and cannot re-run.
- References: every entry re-checked against the publisher's record (`REFERENCE_CHECK.md`); two years follow the ACM Digital Library record (Brown et al. 2022; Kazemitabaar et al. 2024), and several citing sentences were narrowed to what the cited work reports. No result changed.
- `35_tables_v5.py` now also writes the record-generation table, the review table, and the checks of the previous rule (previously typed into the manuscript; the generated tables are identical to the typed ones), the main table's caption takes the per-signal N from the result files, and the natural-units table typesets its signs as mathematical signs.
- `36_figs_v5.py` now writes all four figures of the paper (Figures 2 and 4 were previously drawn by `21_figs_from_json.py` and `30_figs_v4.py`; the regenerated images are pixel-identical) and `figure_data.json`, the numbers each figure plots.
- `38_text_numbers.py` stops if a result file would contradict the direction words used with two of its numbers.
- New `40_check_manuscript.py`: checks every number typed into the manuscript source against the result files and derived tables, or lists it as a design constant, date, or label, or as a recorded value with its source.
- `00_reproduce_from_package.py`: runs the new steps; re-fits any or all analysis parts and attribution-rule variants (`--parts all`, `--jobs`); compares re-fitted results with stated tolerances; builds tables, figures, and text numbers from the distributed results so that they can be compared exactly; refuses a work folder inside the package or one that is not empty; exits with status 1 on any failed comparison.
- The four figures of the paper as submitted are in `manuscript/figs/` (PDF and PNG, with `figure_data.json`).

## v1.1.0 (October 30, 2026)

Common standardization denominator for every comparison of a contrast (`37_common_sd.py`, `results/v5/`), design-based estimates for the review of staff-like exclusions (`39_staff_review_estimates.py`), text numbers generated from the result files (`38_text_numbers.py`), the reproduction entry point, and reference corrections.

## v1.0.0 (October 30, 2026)

First release of the package of the reported analysis.
