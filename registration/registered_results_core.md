# 08 확증 분석 결과 (등록: osf.io/zshu4, Accepted 2026-08-06)

분석표본: 22,071 repos (pre 8,740 / post 13,198 / trailer 552)

## H1 (post > pre) → **EQUIVALENT (TOST)**
- β=-0.0090 (SE 0.0047) | 표준화 d=-0.027 | 95% CI [-0.0183, 0.0002]
- p=5.64e-02 | Holm p=1.13e-01 | permutation p=0.2305 | n=21,938 (org RI)
- TOST 90% CI(d) [-0.050, -0.004] → 등가=True

## H2a (trailer > non-trailer) → **CONFOUNDED (placebo fail)**
- β=0.1664 (SE 0.0399) | 표준화 d=0.298 | 95% CI [0.0881, 0.2447]
- p=3.11e-05 | Holm p=9.34e-05 | permutation p=0.0036 | n=1,276 (org RI + year VC)
- TOST 90% CI(d) [0.180, 0.416] → 등가=False

Placebo P1(가짜 경계): d=0.001, p=0.975 → pass=True
Placebo P2(Signed-off-by): d=0.158, p=0.016 → pass=False (n=1,565)

## H3 (widening gap) → **NOT SUPPORTED** (학생 2,124명 / 관측 4,669 / student RI)
- baseline:post01: β=0.0249 (SE 0.0388), p=5.21e-01
- baseline:trailer: β=0.2008 (SE 0.0928), p=3.05e-02

## 신호별 z 프로파일 (탐색; 신호, σ, pre 평균, post 평균)
- ('sig1_edit_granularity', -1, -0.0376, -0.0258)
- ('sig2_large_paste', -1, -0.0333, -0.0218)
- ('sig3_iteration_burst', 1, 0.0004, 0.0115)
- ('sig4_error_recovery', 1, 0.0011, -0.0006)
- ('sig5_test_engagement', 1, -0.0111, -0.0061)
- ('sig6_dispersion', 1, -0.0139, 0.0052)
- ('sig7_msg_informativeness', 1, 0.0061, 0.0382)
- ('sig8_ai_paste_cooccur', -1, -0.0004, 0.0006)

주: H5(수렴타당도)는 DataShop/iSnap 확보 후 09에서 — 최종 Holm은 4검정으로 재계산
Robustness 수치: results_core.json 'robustness' 필드
