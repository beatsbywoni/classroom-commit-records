# v2 교정 분석 결과 (Stage 3, 2026-10-30)

## 표본
- primary: {'n': 5610, 'pre': 2407, 'post': 3194, 'trailer': 81, 'orgs': 584}
- primary_ge5: {'n': 4034, 'pre': 1758, 'post': 2269, 'trailer': 76, 'orgs': 449}
- primary_incl_testorgs: {'n': 5734, 'pre': 2513, 'post': 3212, 'trailer': 81, 'orgs': 628}
- tierAB: {'n': 6605, 'pre': 2803, 'post': 3789, 'trailer': 131, 'orgs': 668}
- all_tiers_ge5: {'n': 22401, 'pre': 8905, 'post': 13363, 'trailer': 553, 'orgs': 15273}

## A. 신호별 era 대비 — 주 표본 (post − pre; 혼합모형 org RI, 공변량 log commits·저자수·언어군)
| 신호 | pre 평균 | post 평균 | raw d | 모형 d | 90% CI | Holm p | perm p | TOST ±0.10 |
|---|---|---|---|---|---|---|---|---|
| Edit size (log median churn) | 3.849 | 4.515 | +0.260 | -0.099 | [-0.167, -0.030] | 0.073 | 0.713 | NOT equiv |
| Large-insert share (>=200 added lines) | 0.222 | 0.304 | +0.287 | -0.048 | [-0.111, +0.015] | 0.64 | 0.757 | NOT equiv |
| Burst share (<30 min gap) | 0.520 | 0.561 | +0.134 | +0.477 | [+0.407, +0.548] | 4.7e-28 | 0.000 | NOT equiv |
| Same-file rerun rate (>=3 consecutive) | 0.234 | 0.408 | +0.042 | -0.003 | [-0.097, +0.090] | 1 | 0.838 | equiv |
| Test-path touch share | 0.077 | 0.056 | -0.133 | -0.226 | [-0.297, -0.154] | 1.4e-06 | 0.000 | NOT equiv |
| Time dispersion (IQR/span) | 0.442 | 0.442 | -0.001 | -0.015 | [-0.106, +0.076] | 1 | 0.844 | NOT equiv |
| Message informativeness | 0.146 | 0.128 | -0.376 | -0.132 | [-0.203, -0.061] | 0.011 | 0.000 | NOT equiv |
| shortcut_pooled | -0.073 | 0.056 | +0.315 | -0.072 | [-0.145, +0.001] | 0.11 | 0.690 | NOT equiv |

### 민감도 (모형 d, post−pre)
| 신호 | primary | primary_ge5 | primary_incl_testorgs | tierAB | all_tiers_ge5 | within-org(15 org) |
|---|---|---|---|---|---|---|
| edit_size_log | -0.099 | -0.227 | -0.079 | +0.004 | +0.069 | -0.056 (p=0.91) |
| large_insert_share_200 | -0.048 | -0.099 | -0.034 | +0.017 | +0.040 | -0.054 (p=0.9) |
| burst_share_30 | +0.477 | +0.412 | +0.486 | +0.424 | +0.287 | +0.446 (p=0.0064) |
| samefile_rerun_rate_k3 | -0.003 | -0.007 | -0.002 | +0.024 | +0.066 | -0.015 (p=0.1) |
| test_touch_share | -0.226 | -0.135 | -0.210 | -0.237 | -0.073 | -0.176 (p=0.22) |
| time_dispersion | -0.015 | -0.120 | -0.022 | +0.022 | -0.036 | -0.057 (p=0.64) |
| msg_informativeness | -0.132 | -0.228 | -0.163 | -0.131 | -0.165 | -0.126 (p=0.073) |

## B. 연속 시간 (주 표본, 2017+): 연간 기울기(SD/년) — t: 기본 추세, t_post: 2022-12 이후 추가, t_agent: 2025-02 이후 추가
- edit_size_log: t +0.301 (p=3.9e-21), +post -0.604 (p=8.8e-21), +agent +0.575 (p=9.2e-07)
- large_insert_share_200: t +0.208 (p=1.3e-12), +post -0.379 (p=1.6e-10), +agent +0.415 (p=0.00012)
- burst_share_30: t +0.085 (p=0.0097), +post +0.141 (p=0.035), +agent -0.202 (p=0.095)
- samefile_rerun_rate_k3: t +0.011 (p=0.79), +post -0.021 (p=0.81), +agent +0.005 (p=0.98)
- test_touch_share: t +0.025 (p=0.3), +post -0.106 (p=0.056), +agent +0.370 (p=0.00031)
- time_dispersion: t +0.140 (p=0.001), +post -0.325 (p=0.00018), +agent +0.332 (p=0.038)
- msg_informativeness: t -0.195 (p=4.4e-09), +post +0.316 (p=2.5e-06), +agent -0.042 (p=0.73)

### 연도 고정효과 d (2019 기준)
| 신호 | 2017 | 2018 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| edit_size_log | +0.04 | +0.23 | -0.31 | +0.54 | +0.98 | +0.46 | +0.55 | +0.54 | +0.52 |
| large_insert_share_200 | +0.08 | +0.34 | -0.03 | +0.64 | +0.95 | +0.56 | +0.73 | +0.75 | +0.74 |
| burst_share_30 | +0.31 | -0.17 | -0.48 | -0.52 | -0.62 | -0.06 | -0.25 | -0.19 | +0.10 |
| samefile_rerun_rate_k3 | -0.04 | +0.03 | -0.05 | -0.04 | -0.04 | -0.03 | -0.06 | -0.06 | -0.13 |
| test_touch_share | +0.68 | +0.36 | -0.10 | +0.11 | +0.58 | +0.04 | +0.21 | +0.45 | +0.66 |
| time_dispersion | -0.63 | -0.01 | -0.13 | +0.11 | +0.21 | +0.13 | +0.00 | -0.02 | +0.07 |
| msg_informativeness | +0.91 | -0.02 | +0.28 | +0.02 | -0.08 | -0.17 | -0.04 | +0.32 | +0.15 |

## C. AI-trailer 대비 (2024-01 이후, org 매칭) vs Signed-off-by placebo
### all_tiers_ge5: 창 n=10597, trailer 532, signed-off 41, 도구 {'claude': 432, 'copilot': 62, 'cursor': 33, 'devin': 3, 'aider': 2}
(사람 Co-authored-by 전용 저장소 127)
| 신호 | AI d (n) | Holm p | perm p | SO placebo d (n) | p | Human-coauthor placebo d (n) | p |
|---|---|---|---|---|---|---|---|
| edit_size_log | -0.017 (981) | 1 | 0.254 | -0.395 (46) | 0.67 | -0.202 (359) | 0.12 |
| large_insert_share_200 | +0.105 (981) | 0.53 | 0.072 | -0.546 (46) | 0.33 | +0.073 (359) | 0.61 |
| burst_share_30 | +0.326 (981) | 0.00088 | 0.000 | -0.498 (46) | 0.37 | +0.115 (359) | 0.5 |
| samefile_rerun_rate_k3 | -0.132 (981) | 0.53 | 0.076 | -1.085 (46) | 0.34 | +0.064 (359) | 0.63 |
| test_touch_share | +0.026 (981) | 1 | 0.608 | -0.290 (46) | 0.43 | +0.179 (359) | 0.18 |
| time_dispersion | -0.286 (981) | 0.0023 | 0.000 | +0.517 (46) | 0.49 | +0.170 (359) | 0.4 |
| msg_informativeness | +0.205 (981) | 0.087 | 0.049 | +1.315 (46) | 0.18 | +0.141 (359) | 0.21 |
| shortcut_pooled | -0.006 (981) | 0.94 | 0.391 | -0.537 (46) | 0.55 | -0.263 (359) | 0.11 |
### primary: 창 n=2125, trailer 78, signed-off 4, 도구 {'claude': 56, 'copilot': 18, 'cursor': 4}
(사람 Co-authored-by 전용 저장소 42)
| 신호 | AI d (n) | Holm p | perm p | SO placebo d (n) | p | Human-coauthor placebo d (n) | p |
|---|---|---|---|---|---|---|---|
| edit_size_log | +0.024 (484) | 1 | nan | +nan (7) | nan | -0.249 (205) | 0.11 |
| large_insert_share_200 | +0.119 (484) | 1 | nan | +nan (7) | nan | +0.004 (205) | 0.98 |
| burst_share_30 | +0.407 (484) | 0.7 | nan | +nan (7) | nan | +0.090 (205) | 0.6 |
| samefile_rerun_rate_k3 | -0.036 (484) | 0.7 | nan | +nan (7) | nan | +0.050 (205) | 0.79 |
| test_touch_share | +0.046 (484) | 1 | nan | +nan (7) | nan | +0.208 (205) | 0.22 |
| time_dispersion | -0.397 (428) | 0.021 | nan | +nan (7) | nan | +0.463 (183) | 0.012 |
| msg_informativeness | -0.055 (484) | 1 | nan | +nan (7) | nan | +0.054 (204) | 0.76 |
| shortcut_pooled | +0.050 (484) | 0.64 | nan | +nan (7) | nan | -0.390 (205) | 0.0088 |

## trailer 보급률(연도, 사람커밋≥3 전체): 2021: 0.2% (4/2522), 2022: 0.1% (4/3124), 2023: 0.1% (4/3707), 2024: 0.3% (9/3507), 2025: 1.6% (82/5271), 2026: 8.6% (517/5999)

## 기술통계(주 표본): {"year_n": {"2010.0": 2, "2014.0": 7, "2015.0": 23, "2016.0": 51, "2017.0": 194, "2018.0": 142, "2019.0": 325, "2020.0": 550, "2021.0": 460, "2022.0": 662, "2023.0": 1069, "2024.0": 652, "2025.0": 886, "2026.0": 587}, "lang": {"other": 1142, "web_markup": 1007, "js_ts": 1003, "c_cpp": 874, "python": 604, "notebook": 385, "java_kotlin": 308, "csharp": 287}, "span_days_median": 7.045451388888889, "commits_median": 8.0, "solo_share": 0.5260249554367201, "students": 3674, "students_multi": 716, "org_n_median": 1.0, "org_top": {redacted in public package}, "lang_by_era": {"buffer": {"c_cpp": 0.111, "csharp": 0.0, "java_kotlin": 0.0, "js_ts": 0.333, "notebook": 0.333, "other": 0.111, "python": 0.111, "web_markup": 0.0}, "post": {"c_cpp": 0.17, "csharp": 0.047, "java_kotlin": 0.051, "js_ts": 0.159, "notebook": 0.059, "other": 0.16, "python": 0.13, "web_markup": 0.223}, "pre": {"c_cpp": 0.137, "csharp": 0.057, "java_kotlin": 0.061, "js_ts": 0.204, "notebook": 0.08, "other": 0.262, "python": 0.078, "web_markup": 0.123}}}

## E. 3시기 대비 (주 표본)
### 에이전트 도구기(2025-02+) vs 초기 post(2023-01..2025-01): org RI n=3194 (label1 1447, orgs 398); within-org n=682, orgs 12
| 신호 | org-RI d | Holm p | within-org d | p |
|---|---|---|---|---|
| edit_size_log | +0.025 | 1 | -0.158 | 4.4e-09 |
| large_insert_share_200 | +0.191 | 0.032 | -0.059 | 0.19 |
| burst_share_30 | +0.051 | 1 | -0.120 | 0.086 |
| samefile_rerun_rate_k3 | -0.025 | 1 | -0.068 | 1.6e-15 |
| test_touch_share | +0.560 | 3.4e-11 | +0.565 | 0.00098 |
| time_dispersion | -0.150 | 0.58 | -0.186 | 0.011 |
| msg_informativeness | +0.381 | 8e-06 | +0.335 | 2.3e-05 |
### pre 내부: 팬데믹기(2020-03..2022-11) vs 그 이전(2017..2020-02): n=2324 (label1 1650, orgs 189)
| 신호 | org-RI d | Holm p |
|---|---|---|
| edit_size_log | -0.288 | 0.56 |
| large_insert_share_200 | +0.069 | 1 |
| burst_share_30 | -0.175 | 1 |
| samefile_rerun_rate_k3 | -0.161 | 1 |
| test_touch_share | +0.071 | 1 |
| time_dispersion | -0.469 | 0.28 |
| msg_informativeness | +0.191 | 1 |
### post vs 팬데믹 이전 pre(2017..2020-02)만: n=3868 (label1 3194, orgs 465)
| 신호 | org-RI d | Holm p |
|---|---|---|
| edit_size_log | +0.146 | 1 |
| large_insert_share_200 | +0.154 | 1 |
| burst_share_30 | +0.289 | 0.035 |
| samefile_rerun_rate_k3 | +0.014 | 1 |
| test_touch_share | -0.328 | 1 |
| time_dispersion | +0.594 | 0.71 |
| msg_informativeness | +0.154 | 1 |

## 언어군 구성(주 표본, 열 비율): {"buffer": {"c_cpp": 0.111, "csharp": 0.0, "java_kotlin": 0.0, "js_ts": 0.333, "notebook": 0.333, "other": 0.111, "python": 0.111, "web_markup": 0.0}, "post": {"c_cpp": 0.17, "csharp": 0.047, "java_kotlin": 0.051, "js_ts": 0.159, "notebook": 0.059, "other": 0.16, "python": 0.13, "web_markup": 0.223}, "pre": {"c_cpp": 0.137, "csharp": 0.057, "java_kotlin": 0.061, "js_ts": 0.204, "notebook": 0.08, "other": 0.262, "python": 0.078, "web_markup": 0.123}}
