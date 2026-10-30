# 구성·지배 클러스터 점검 결과 (Stage 3d)

## post vs pre: n=5185, label1=3116, orgs=573; capped n≈2886; top-10 org sizes [750, 462, 341, 256, 243, 171, 148, 120, 98, 95]
| 신호 | raw d | org-RI d (p) | capped d [90% CI] equiv | LOO min..max (top10) | drop top5 | within-org d (wild p; orgs) | paired: median d, +/n (sign p) |
|---|---|---|---|---|---|---|---|
| Edit size | +0.14 | -0.28 (1.2e-13) | -0.02 [-0.15, +0.11] - | -0.32..-0.00 | +0.02 | -0.38 (0.19; 14) | -0.15, 5/14 (0.42) |
| Large inserts | +0.20 | -0.19 (1.2e-07) | -0.02 [-0.13, +0.09] - | -0.24..+0.02 | +0.01 | -0.28 (0.28; 14) | -0.02, 5/14 (0.42) |
| Burst share | +0.06 | +0.31 (1.2e-14) | +0.13 [+0.00, +0.25] - | +0.07..+0.38 | +0.11 | +0.43 (0.53; 14) | -0.27, 6/14 (0.79) |
| Same-file reruns | +0.04 | +0.04 (0.25) | +0.00 [-0.08, +0.09] EQ | +0.02..+0.04 | -0.05 | +0.04 (0.35; 14) | -0.00, 6/14 (0.79) |
| Test-path touches | -0.15 | -0.18 (1.2e-05) | -0.05 [-0.17, +0.06] - | -0.24..+0.03 | -0.04 | -0.33 (0.35; 14) | +0.00, 5/14 (0.42) |
| Time dispersion | -0.05 | -0.08 (0.071) | +0.02 [-0.08, +0.12] - | -0.09..+0.00 | +0.05 | -0.07 (0.98; 14) | +0.00, 7/14 (1.00) |
| Message distinctiveness | -0.36 | -0.20 (1.4e-07) | -0.19 [-0.29, -0.08] - | -0.24..-0.14 | -0.12 | -0.12 (0.27; 14) | +0.04, 7/14 (1.00) |
within-org sizes: [750, 341, 243, 148, 95, 23, 21, 9, 6, 6, 4, 2, 2, 2]

## agentic (2025-02+) vs early post: n=3116, label1=1436, orgs=397; capped n≈1601; top-10 org sizes [539, 462, 256, 193, 171, 120, 71, 63, 62, 60]
| 신호 | raw d | org-RI d (p) | capped d [90% CI] equiv | LOO min..max (top10) | drop top5 | within-org d (wild p; orgs) | paired: median d, +/n (sign p) |
|---|---|---|---|---|---|---|---|
| Edit size | +0.21 | -0.01 (0.87) | +0.03 [-0.10, +0.15] - | -0.02..+0.04 | +0.04 | +0.17 (0.02; 12) | -0.06, 5/12 (0.77) |
| Large inserts | +0.40 | +0.07 (0.17) | +0.00 [-0.11, +0.12] - | -0.00..+0.11 | -0.00 | +0.35 (0.20; 12) | -0.14, 2/12 (0.04) |
| Burst share | -0.30 | +0.08 (0.22) | +0.12 [-0.01, +0.26] - | +0.07..+0.16 | +0.18 | +0.11 (0.49; 12) | +0.16, 7/12 (0.77) |
| Same-file reruns | +0.05 | +0.05 (0.21) | -0.04 [-0.24, +0.16] - | +0.02..+0.07 | -0.23 | +0.09 (0.79; 12) | -0.01, 4/12 (0.39) |
| Test-path touches | +0.10 | +0.38 (2.5e-08) | +0.04 [-0.12, +0.19] - | -0.05..+0.48 | -0.04 | +0.69 (0.94; 12) | +0.00, 3/12 (0.15) |
| Time dispersion | +0.05 | -0.07 (0.31) | -0.02 [-0.14, +0.11] - | -0.09..-0.01 | -0.02 | -0.26 (0.59; 12) | +0.02, 5/10 (1.00) |
| Message distinctiveness | +0.22 | +0.26 (8.1e-06) | +0.17 [+0.05, +0.29] - | +0.15..+0.28 | +0.15 | +0.55 (0.03; 12) | -0.10, 5/12 (0.77) |
within-org sizes: [539, 46, 20, 17, 12, 8, 6, 6, 4, 3, 3, 3]

## trailer (all_tiers_ge5): n=1137, AI=523, human-only=128, orgs=495, tools={'claude': 426, 'copilot': 61, 'cursor': 31, 'devin': 3, 'aider': 2}
| 신호 | AI d (p) | human d (p) | AI−human d (p, Holm) |
|---|---|---|---|
| Edit size | +0.01 (0.867) | -0.17 (0.085) | +0.18 ± 0.18 (0.051, 0.307) |
| Large inserts | +0.12 (0.103) | +0.04 (0.708) | +0.08 ± 0.17 (0.341, 1.000) |
| Burst share | +0.35 (0.000) | +0.23 (0.023) | +0.12 ± 0.19 (0.224, 1.000) |
| Same-file reruns | -0.01 (0.892) | -0.01 (0.937) | -0.00 ± 0.20 (0.987, 1.000) |
| Test-path touches | +0.01 (0.855) | +0.05 (0.608) | -0.04 ± 0.19 (0.694, 1.000) |
| Time dispersion | -0.21 (0.013) | +0.10 (0.351) | -0.31 ± 0.20 (0.003, 0.018) |
| Message distinctiveness | +0.22 (0.007) | +0.20 (0.060) | +0.02 ± 0.20 (0.819, 1.000) |

## trailer (primary): n=492, AI=74, human-only=42, orgs=12, tools={'claude': 54, 'copilot': 16, 'cursor': 4}
| 신호 | AI d (p) | human d (p) | AI−human d (p, Holm) |
|---|---|---|---|
| Edit size | -0.02 (0.836) | -0.16 (0.244) | +0.14 ± 0.32 (0.398, 1.000) |
| Large inserts | +0.08 (0.485) | +0.02 (0.910) | +0.06 ± 0.32 (0.702, 1.000) |
| Burst share | +0.46 (0.000) | +0.17 (0.300) | +0.30 ± 0.37 (0.113, 0.563) |
| Same-file reruns | -0.03 (0.807) | +0.00 (0.995) | -0.04 ± 0.41 (0.865, 1.000) |
| Test-path touches | -0.12 (0.395) | +0.22 (0.188) | -0.34 ± 0.40 (0.090, 0.538) |
| Time dispersion | -0.33 (0.015) | +0.32 (0.065) | -0.65 ± 0.40 (0.001, 0.009) |
| Message distinctiveness | -0.03 (0.809) | +0.13 (0.463) | -0.16 ± 0.40 (0.428, 1.000) |


## v3 추가 분석
### 원단위(캡) 효과 post−pre: β [90% CI], pre/post 평균
- edit_size_log: β=-0.0279 [-0.2839, +0.2282] | pre 4.0229 post 4.3638
- large_insert_share_200: β=-0.0035 [-0.0301, +0.0230] | pre 0.2326 post 0.2886
- burst_share_30: β=+0.0371 [-0.0024, +0.0766] | pre 0.5234 post 0.5422
- samefile_rerun_rate_k3: β=+0.0192 [-0.1446, +0.1831] | pre 0.2597 post 0.4441
- test_touch_share: β=-0.0086 [-0.0273, +0.0101] | pre 0.0808 post 0.0568
- time_dispersion: β=+0.0059 [-0.0226, +0.0343] | pre 0.4539 post 0.4388
- msg_informativeness: β=-0.0092 [-0.0140, -0.0044] | pre 0.1449 post 0.1274
### 2023 vs 2022 직접 대비 (d, p): RI | capped
- edit_size_log: RI -0.56 (p=0.000) | capped -0.25 (p=0.182)
- large_insert_share_200: RI -0.41 (p=0.000) | capped -0.13 (p=0.403)
- burst_share_30: RI +0.48 (p=0.000) | capped +0.15 (p=0.339)
- samefile_rerun_rate_k3: RI +0.00 (p=0.938) | capped -0.06 (p=0.577)
- test_touch_share: RI -0.53 (p=0.000) | capped -0.35 (p=0.002)
- time_dispersion: RI -0.07 (p=0.319) | capped +0.12 (p=0.262)
- msg_informativeness: RI -0.13 (p=0.012) | capped -0.13 (p=0.280)
### trailer + year FE (all_tiers_ge5): n=1137, AI=523, human=128, orgs=495, orgs with AI & non-trailer peer=36, orgs with both AI&human=6; year mix AI {2026.0: 442, 2025.0: 73, 2024.0: 8} human {2026.0: 60, 2025.0: 38, 2024.0: 30}
- edit_size_log: AI -0.06 (p=0.486) human -0.18 (p=0.062) diff +0.12 ±0.18 p=0.187 Holm=1.000 | FE diff +0.20 wild p=0.567 Holm=1.000 | n=1137
- large_insert_share_200: AI +0.04 (p=0.572) human +0.02 (p=0.811) diff +0.02 ±0.18 p=0.815 Holm=1.000 | FE diff +0.21 wild p=0.373 Holm=1.000 | n=1137
- burst_share_30: AI +0.32 (p=0.000) human +0.23 (p=0.026) diff +0.10 ±0.19 p=0.321 Holm=1.000 | FE diff +0.23 wild p=0.686 Holm=1.000 | n=1137
- samefile_rerun_rate_k3: AI +0.01 (p=0.859) human -0.00 (p=0.967) diff +0.02 ±0.21 p=0.857 Holm=1.000 | FE diff -0.00 wild p=0.933 Holm=1.000 | n=1137
- test_touch_share: AI -0.07 (p=0.420) human +0.04 (p=0.711) diff -0.11 ±0.20 p=0.288 Holm=1.000 | FE diff -0.23 wild p=0.589 Holm=1.000 | n=1137
- time_dispersion: AI -0.21 (p=0.018) human +0.10 (p=0.350) diff -0.32 ±0.21 p=0.003 Holm=0.021 | FE diff -0.39 wild p=0.270 Holm=1.000 | n=1137
- msg_informativeness: AI +0.28 (p=0.001) human +0.21 (p=0.046) diff +0.07 ±0.20 p=0.469 Holm=1.000 | FE diff +0.16 wild p=0.158 Holm=1.000 | n=1137
### trailer + year FE (primary): n=492, AI=74, human=42, orgs=12, orgs with AI & non-trailer peer=5, orgs with both AI&human=2; year mix AI {2026.0: 71, 2025.0: 3} human {2025.0: 22, 2026.0: 15, 2024.0: 5}
- edit_size_log: AI +0.00 (p=0.970) human -0.20 (p=0.153) diff +0.20 ±0.32 p=0.216 Holm=0.864 | FE diff +0.24 wild p=0.663 Holm=1.000 | n=492
- large_insert_share_200: AI +0.11 (p=0.330) human -0.05 (p=0.729) diff +0.16 ±0.32 p=0.331 Holm=0.992 | FE diff +0.22 wild p=0.729 Holm=1.000 | n=492
- burst_share_30: AI +0.48 (p=0.000) human +0.18 (p=0.275) diff +0.30 ±0.37 p=0.115 Holm=0.688 | FE diff +0.31 wild p=0.504 Holm=1.000 | n=492
- samefile_rerun_rate_k3: AI -0.05 (p=0.728) human -0.00 (p=0.978) diff -0.05 ±0.42 p=0.831 Holm=0.992 | FE diff -0.04 wild p=0.177 Holm=0.885 | n=492
- test_touch_share: AI -0.19 (p=0.170) human +0.11 (p=0.533) diff -0.30 ±0.40 p=0.138 Holm=0.690 | FE diff -0.38 wild p=0.008 Holm=0.056 | n=492
- time_dispersion: AI -0.35 (p=0.013) human +0.35 (p=0.045) diff -0.70 ±0.40 p=0.001 Holm=0.004 | FE diff -0.75 wild p=0.186 Holm=0.885 | n=427
- msg_informativeness: AI -0.07 (p=0.597) human +0.09 (p=0.624) diff -0.16 ±0.41 p=0.434 Holm=0.992 | FE diff -0.18 wild p=0.139 Holm=0.834 | n=491
### era: raw+covariates (no org) d (p) | cap 25 d [90%] | cap 100 d [90%]
- edit_size_log: +0.13 (p=0.367) | +0.04 [-0.09, +0.17] | -0.07 [-0.18, +0.03]
- large_insert_share_200: +0.19 (p=0.214) | +0.01 [-0.11, +0.13] | -0.05 [-0.14, +0.05]
- burst_share_30: +0.07 (p=0.622) | +0.10 [-0.02, +0.22] | +0.14 [+0.05, +0.24]
- samefile_rerun_rate_k3: +0.04 (p=0.104) | -0.02 [-0.11, +0.08] | +0.01 [-0.07, +0.09]
- test_touch_share: -0.15 (p=0.245) | -0.05 [-0.17, +0.06] | -0.05 [-0.16, +0.05]
- time_dispersion: -0.03 (p=0.567) | +0.04 [-0.06, +0.14] | +0.02 [-0.07, +0.11]
- msg_informativeness: -0.36 (p=0.012) | -0.18 [-0.29, -0.07] | -0.20 [-0.29, -0.11]
### agent: raw+covariates (no org) d (p) | cap 25 d [90%] | cap 100 d [90%]
- edit_size_log: +0.17 (p=0.334) | +0.06 [-0.07, +0.18] | +0.02 [-0.10, +0.14]
- large_insert_share_200: +0.34 (p=0.089) | +0.02 [-0.11, +0.14] | +0.02 [-0.10, +0.13]
- burst_share_30: -0.26 (p=0.115) | +0.14 [+0.01, +0.27] | +0.11 [-0.01, +0.24]
- samefile_rerun_rate_k3: +0.05 (p=0.081) | -0.12 [-0.36, +0.11] | -0.02 [-0.20, +0.16]
- test_touch_share: +0.21 (p=0.077) | -0.00 [-0.15, +0.14] | +0.12 [-0.04, +0.28]
- time_dispersion: +0.04 (p=0.542) | -0.03 [-0.17, +0.10] | -0.02 [-0.15, +0.10]
- msg_informativeness: +0.20 (p=0.364) | +0.16 [+0.04, +0.29] | +0.18 [+0.06, +0.29]
### 저커밋(1–2 학생 커밋) 저장소: n=4701 (pre 2144 / post 2557), orgs 535
- edit_size_log: raw -0.05 | RI -0.36 (p=0.000) | capped -0.27 [-0.39, -0.14] | pre 5.005 post 4.867
- large_insert_share_200: raw +0.20 | RI -0.35 (p=0.000) | capped -0.30 [-0.42, -0.19] | pre 0.248 post 0.336
- max_insert_log: raw -0.04 | RI -0.38 (p=0.000) | capped -0.27 [-0.41, -0.14] | pre 4.874 post 4.765
- test_touch_share: raw -0.41 | RI -0.36 (p=0.000) | capped -0.21 [-0.33, -0.09] | pre 0.167 post 0.051
### 포함 확률(학생 커밋 수 분포, 행 비율): {"buffer": {"1": 0.5312, "2": 0.1562, "3+": 0.3125}, "post": {"1": 0.2979, "2": 0.1528, "3+": 0.5493}, "pre": {"1": 0.3499, "2": 0.159, "3+": 0.4911}}
counts: {"buffer": {"1": 17, "2": 5, "3+": 10}, "post": {"1": 1690, "2": 867, "3+": 3116}, "pre": {"1": 1474, "2": 670, "3+": 2069}}
