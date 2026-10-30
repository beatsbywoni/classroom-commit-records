# Reference check

Final check on October 30, 2026, against the reference list of the submitted PDF (39 works). Every entry was compared, field by field, with the publisher's own record: the ACM Digital Library record (citation export and landing page, read in a browser) for the 15 ACM works; Crossref, the Springer, SAGE, Wiley, IEEE, and Stata Journal records or the published article for the others; arXiv abstract pages for every version of each preprint; the DataCite record for the dataset; and the GitHub pages themselves. The sentences that cite each work were then checked against the work's text (abstract, and the relevant passage where the work supports a substantive claim). Earlier logs and automatically generated BibTeX were not relied on.

Conventions adopted:
- ACM works carry the year of the ACM Digital Library record's publication date (the date in ACM's own citation export), with volume, issue, and article number from the same record. Two years changed on this basis (see below).
- Where the publisher's metadata and the published article disagree, the published article was followed and the difference is recorded (Roodman et al.).
- Preprints cite the version whose title and author list they reproduce, and say which version.
- Nothing is marked verified unless the source was seen; open items are listed at the end.

Status: OK (no change), CHANGED (metadata changed in this check), CLAIM (citing sentence changed in this check), OPEN (not fully confirmed).

| Key | Status | Ground truth seen | Notes |
|---|---|---|---|
| bikangaada2026separate | OK, CLAIM | ACM DL record (TOCE 26(2), Article 17, 29 pp., online 2026-01-17, issue June 2026); Glasgow eprint 373378 and PDF | Survey of two cohorts; three of four difficulty subscales showed no significant difference (materials did). Sentence now says exactly that instead of "most difficulties unchanged". |
| bird2009promises | CHANGED | Crossref 10.1109/MSR.2009.5069475; author PDF | Proceedings title as in the IEEE record ("2009 6th IEEE International Working Conference on Mining Software Repositories"); the conference location, which the style printed as a publisher address, removed. Claim supported. |
| brown2014blackbox | OK | ACM DL record (SIGCSE '14, pp. 223-228) | Supported. |
| brown2017mistakes | OK | ACM DL record (TOCE 17(2), Article 7, 21 pp.) | Supported. |
| brown2022novice | CHANGED | ACM DL record (TOCE 23(1), Article 10, 24 pp., online 2022-12-29, issue March 2023) | Year 2023 to 2022, per the ACM DL publication date (in-text "Brown et al. 2022"). Supported. |
| cameron2008bootstrap | OK | Crossref 10.1162/rest.90.3.414; NBER t0344 | Supported (few clusters; cluster bootstrap-t). |
| cameron2015practitioner | OK | Crossref 10.3368/jhr.50.2.317; JHR landing page; author PDF | Crossref splits the first author's name wrongly; the landing page has "A. Colin Cameron", as the entry does. Supported. |
| codeworkout2020dataset | OK (record), CLAIM, OPEN | DataCite 10.60710/DATASET-3458 ("CodeWorkout data Spring 2019", DataShop, 2020); DataShop dataset 3458 page | The record covers Spring 2019. The analysis used two files, S19_All_Release_2_10_22.zip and F19_Release_All_05_23_22.zip; the text now names both and attributes only the Spring 2019 data to dataset 3458. OPEN: whether the Fall 2019 file is distributed in the Files tab of dataset 3458 (a DataShop login is needed to see the list; a 2023 EDM paper describes the dataset as both semesters and links to that tab). No DOI for the Fall 2019 release was found, and none is cited. |
| denny2024computing | OK | ACM DL record (CACM 67(2), 56-67, online 2024-01-25) | Supported (over-reliance discussed apart from misconduct). |
| enders2007centering | OK | Crossref 10.1037/1082-989X.12.2.121; published PDF | "CWC removes all between-cluster variation from the predictor." Supported. |
| finnieansley2022robots | OK | ACM DL record (ACE '22, pp. 10-19) | Supported for the first clause (abstract); the concern beyond integrity is carried by Denny et al. |
| github2019classroomboost | OK | GitHub Blog page (Aug 27, 2019; updated Apr 15, 2020) | Template import offered as an option in 2019. Supported. |
| github2023classroomchanges | OK | GitHub Changelog page (displayed Dec 8, 2023; URL slug 2023-12-07) | Supported. |
| github2024forksbeta | OK | GitHub Changelog page (Jan 22, 2024) | Public beta, opt-in per classroom. Supported. |
| github2024forksga | CHANGED | GitHub Community discussion #127455 (posted June 5, 2024; general release reported July 2, 2024) | Canonical URL github.com/orgs/community/discussions/127455 (the old URL redirects). Supported. |
| github2026classroomdeprecated | CHANGED | GitHub Changelog page (Aug 27, 2026) | Canonical URL with trailing slash. "As of August 28, 2026" Classroom is deprecated; repositories unaffected. Supported. |
| githubdocs2026template | OK | GitHub Docs page (read Oct 30, 2026) and the docs repository history | Living page; the two sentences relied on were added on July 16, 2024 and are unchanged in substance. Supported. |
| hsing2019github | OK | ACM DL record (SIGCSE '19, pp. 672-678; full title with subtitle) | Survey; cited as such. Supported. |
| hundhausen2017ide | CHANGED | ACM DL record (TOCE 17(3), Article 11, 26 pp.) | Author names as in the ACM record (C. D. Hundhausen, D. M. Olivares, A. S. Carter). Supported. |
| hundhausen2023github | OK | ACM DL record (TOCE 23(3), Article 33, 23 pp.); author copy | Second author Phill Conrad. Supported. |
| kalliamvakou2016promises | OK | Crossref 10.1007/s10664-015-9393-5; author copy | Perils I, III, V, XII, XIII. Supported. |
| kazemitabaar2024novices (was kazemitabaar2023novices) | CHANGED, CLAIM | ACM DL record (Koli Calling '23, Article 3, 12 pp., publication date 2024-02-06; Crossref print date 2023-11-13) | Year 2023 to 2024 per the ACM DL record, article number added, title "LLM-based" as in the record. Participants were 33 learners aged 10-17 in a self-paced setting; 46% of tasks used one prompt for the whole solution. The introduction now says "among young novices in a self-paced setting, prompting for whole solutions". |
| khosravani2026census | CHANGED (note) | arXiv 2606.24429 (only v1) | "Preprint, v1" added. Uses trailers with identity, bot signatures, and configuration files; trailer sentence now says "Git metadata and repository files". |
| liu2026debt | CHANGED (note) | arXiv 2603.28592 v1-v3 | v1 has five authors; the entry's six authors are v2/v3; "Preprint, v3" added. Supported. |
| loksa2022metacognition | OK, CLAIM | ACM DL record (TOCE 22(4), Article 39, 31 pp.) | The review describes monitoring and evaluation but does not map repair or testing onto them; the sentence now says these behaviors "can be read as behavioral traces of" them. |
| macak2021process | OK | Springer record and Crossref (EAIT 26(5), 5939-5969; names without diacritics in the publisher record) | Supported. |
| mao2026largescale | OK | arXiv 2603.27130 v1-v3 | v1 and v3 carry the cited title, v2 a different one; authors identical; "Preprint, v3". Identifies AI code from code comments; cited for that, not for trailers. |
| prather2023weird | OK, CLAIM | ACM DL record (TOCHI 31(1), Article 4, 31 pp., online 2023-11-29, issue February 2024); published PDF (ACM Reference Format "2023 ... (November 2023)") | Year 2023 by both the DL record and the article; no a/b with Prather et al. 2024. It reports accepting short and long suggestions, not handing over whole tasks, so the "whole tasks" clause now cites Kazemitabaar et al. only. |
| prather2024widening | OK, CLAIM | ACM DL record (ICER '24 Volume 1, pp. 469-486) | Lab study, not commit-level. "often produce whole solutions" changed to "can obtain whole solutions in a single step". |
| price2020progsnap2 | OK, CLAIM | ACM DL record (ITiCSE '20, pp. 356-362; author order as in the entry) | A format for programming process data in general; sentence changed from "autograder submission streams" to "programming process logs, including autograder submissions". |
| quispe2026coding | OK | arXiv 2605.25438 v1-v2 | v1 has another title and one author; the entry is v2 throughout ("Preprint, v2"). Trailer-based. Supported. |
| raudenbush2002hlm | CHANGED | Sage publisher page (2nd ed.); library catalog (c2002) | Edition printed "2nd ed." (was "2 ed."). Claim supported indirectly (see OPEN). |
| roodman2019boottest | OK | Published article PDF and the Stata Journal article page (Roodman, MacKinnon, Nielsen, Webb); Crossref deposit lists Nielsen second | Kept the order of the published article. The paper's recommended test is studentized; the manuscript states that its test compares coefficients. |
| rubin1987imputation | OK | Crossref 10.1002/9780470316696; library catalog | Cited for the combining rule (comparison column only). |
| shihab2025copilot | OK | ACM DL record (ICER '25 V.1, pp. 407-420; "Brownfield Coding Tasks"; Brian Wise Mulanda) | The arXiv preprint differs in title and one name; the entry follows the ACM record. Supported. |
| tufano2026selfadmitted | OK | Springer record (EMSE 31(4), article 108, 2026) | Self-admissions in commit messages, issues, and pull requests; not trailers. Supported. |
| wang2024multilingual | CHANGED (note) | arXiv 2402.05672 (only v1) | "Preprint, v1" added. Covers multilingual-e5-small. |
| webb2023reworking | OK | Crossref 10.1111/caje.12661 (56(3), 839-858); published introduction | Supported with Roodman et al. (six-point weights for few clusters; 2^G Rademacher draws). |
| yaremych2023centering | OK, CLAIM | Crossref 10.1037/met0000434; published PDF | "precision-weighted averages" stated for balanced designs; the sentence now says "approximately". |

Rendering: the final PDF was checked for broken characters, missing fields, and links. BibTeX reports four warnings, all harmless: no publisher address for the IEEE proceedings, and no page count for the Springer article, which has an article number only. `refs.bib` in the source package holds only the 39 cited works.

OPEN (not confirmed):
1. Whether F19_Release_All_05_23_22.zip is distributed with PSLC DataShop dataset 3458 (needs a DataShop login). The manuscript does not claim it.
2. Raudenbush and Bryk (2002) and Rubin (1987): the books themselves were not read; the cited results were confirmed in Yaremych et al. (2023) and in the standard statement of the combining rule.
3. Webb (2023): the sentence on 2^G bootstrap samples was seen in the working paper and in Roodman et al. (2019), not in the paywalled sections of the published article; it is cited with Roodman et al.
