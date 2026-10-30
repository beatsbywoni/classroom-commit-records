# OSF Preregistration v1.0 — The Struggle Signature (확정본, 2026-08-06)
### OSF 프로젝트: https://osf.io/zshu4/ · 이 문서가 등록 원문. v0.1의 ⟦TBD⟧ 전체 확정.

---

## 1. Study Information

**Title**: The Struggle Signature: Measuring Productive Struggle versus Shortcutting in Novice Programmers' Commit Streams in the Generative-AI Era

**Author**: Hongwon Jeong (Hanyang University ERICA), sole author.

**Registration type**: Secondary-data preregistration. **원자료 수집(2026-08-05~06)은 완료되었으나, 본 문서 등록 시점까지 어떠한 결과지표(outcome)도 계산되지 않았다.** 등록 이전에 관측한 것은 표본 기술통계뿐이며 그 전부를 §3에 공개한다(커밋 수·저자 수·연도·AI-trailer 유무 — outcome 아님). 지표 정의·모델·판정 규칙은 본 문서로 동결된다.

**Research questions**: RQ1 측정도구 개발(struggle vs shortcut), RQ2 GenAI 시대 변화, RQ3 이질성(widening gap), RQ4 수렴타당도.

**이론 정박**: Loksa et al. (2022, ACM TOCE, 10.1145/3487050) 메타인지/SRL; Prather et al. (2024, ICER, 10.1145/3632620.3671116) widening gap.

## 2. Sample (수집 완료분 기술 — outcome 미계산)

- 유니버스: GitHub 공개 저장소 `classroom in:name` ∪ `github-classroom in:name` ∪ `topic:github-classroom`, 열거 스냅샷 2026-08-05 (N=70,495; GitHub Classroom 플랫폼 종료 2026-08-28 직전).
- 클론·로그 추출 성공: 58,516 (실패 16). 총 커밋 1,252,609.
- **포함기준(동결)**: 커밋 ≥5 ∧ 사람 저자 ≥1 (봇 정규식 제외: `[bot]`, dependabot, github-actions, github classroom, renovate, copilot-swe-agent, web-flow) → **25,743개 저장소**.
- 시대 구분: pre-ChatGPT = 첫 커밋 < 2022-12-01 (**10,759**), post = ≥ 2023-01-01 (**14,846**), 2022-12는 완충 제외.
- AI-trailer 저장소(포함기준 내): **560** (agent: claude 압도적, copilot·cursor 順).
- 학생 식별: 이메일 정규화(소문자화; `*@users.noreply.github.com` → `gh:username`) 후 salted SHA-256 해시. 원문 비보존. **보수적 연결**(동일인 복수 이메일은 분리될 수 있음 → within-student 표본의 하한) — 고유 학생 **19,719명**, ≥2 저장소 **2,941명**(≥3: 800명), trailer·무trailer 동시 보유 **77명(107 매칭쌍)**.

## 3. Hypotheses (확증/탐색 구분 — 표본 실측 기반 확정)

**확증(confirmatory):**
- **H1 (AI-era shift)**: post-ChatGPT 저장소는 pre 대비 Shortcut composite가 높다 (β>0). 표본 25,605(pre+post).
- **H2a (AI-marker, between-repo)**: AI-trailer 저장소(560)는 같은 org·같은 시대의 무-trailer 저장소 대비 Shortcut composite가 높다 (org-매칭 비교).
- **H3 (widening gap)**: ≥2 저장소 학생(2,941명)에서, 학생의 기저 struggle(시간순 첫 저장소의 Struggle composite) × 후속 저장소 시대(pre/post)·trailer 상호작용이 음(-).
- **H5 (convergent validity)**: 커밋 기반 Struggle composite와 ProgSnap2 계열(CodeWorkout/CSEDM·iSnap) struggle 지표의 상관 **r ≥ 0.3**.

**탐색(exploratory) — 확증 아님을 명시:**
- **H2b**: within-student trailer 비교(77명·107쌍) — 방향 보고만.
- **H4**: 과정-성과 해리 — 성과 proxy(CI 통과)는 커밋 로그에 없음. GitHub Actions API로 확보 가능한 부분표본에 한해 탐색적으로 보고 (표본 확보 규칙: 포함기준 저장소 중 Actions 이력 존재분 전수 또는 API 한도 내 무작위 5,000개).

**Placebo (특이성, 확증 설계의 일부):**
- **P1 (가짜 경계)**: pre 구간 내부 가짜 경계(2021-06-01)로 H1 재추정 → 효과 ≈ 0이어야 함.
- **P2 (가짜 trailer)**: `Signed-off-by` trailer를 가짜 처치로 H2a 재추정 → 효과 ≈ 0이어야 함.

## 4. Variables — 신호 8종 (v0.1 유지, 수치 동결)

| # | 신호 | 정의(동결) | σ |
|---|---|---|---|
| 1 | edit_granularity | 커밋당 (add+del) 라인 중앙값, log1p | − |
| 2 | large_paste_events | 단일 커밋 add ≥ 코호트(시대×언어군) P95 비율 | − |
| 3 | iteration_burst | 직전 커밋과 간격 <30분인 커밋 비율 | + |
| 4 | error_recovery_arc | 동일 파일 3회 이상 연속 재수정 아크 수 / 커밋 수 | + |
| 5 | test_engagement | 테스트 경로(test/, spec/, *_test.*, *Test.*) 수정 커밋 비율 | + |
| 6 | time_on_task_dispersion | 커밋 시각 IQR / 전체 기간 (0~1) | + |
| 7 | msg_informativeness | 다국어 임베딩(multilingual-e5-small) 기반 메시지 특이성 = 1 − 저장소 내 평균 코사인 | + |
| 8 | ai_paste_cooccurrence | trailer 커밋 ∧ large-paste 동시 발생 비율 | − |

- Within-student z-score(≥2 저장소 학생) / 단일 저장소 학생은 org×시대 코호트 z-score. σ 방향 정렬 동등가중 평균 = **Struggle composite**; 신호 2·8 = **Shortcut 축** 분리 보고.
- 가중 대안(PCA 1주성분)은 robustness로만.

## 5. Analysis Plan (동결)

- **H1/H2a**: `Shortcut_{r} ~ era (또는 trailer) + log(n_commits) + n_authors + (1|org) + (1|first_year)`; permutation 1e4 (라벨 org 내 재배치) 병행.
- **H3**: `Struggle_{s,a(later)} ~ baseline_struggle_s × era + baseline × trailer + (1|student) + (1|org)`.
- **H5**: Pearson r + Spearman ρ, 사전 임계 r≥0.3.
- **TOST 등가 마진**(H1·H2a의 null 능동 판정): Cohen's d = ±0.10.
- **다중비교**: 확증 4개 가설 Holm 보정.
- **Robustness(동결)**: leave-one-org-out(상위 20 org), leave-one-year-out, 경계 이동(2022-06/2023-06), 신호 leave-one-out, solo-저장소 한정 재추정, PCA 가중.
- **Silent-AI 편의**: 무-trailer 군의 미탐지 AI 사용은 H2a를 0 방향으로 희석 → 관측 효과는 하한임을 명시.

## 6. Ethics
공개 저장소만; 식별자 salted 해시(원문·salt 비공개); 집계 보고(org·개인 재식별 금지); 파생 지표 테이블·코드만 공개, 원 로그 비공개(심사자 요청 시 한정 제공); GitHub ToS 준수; 선택편향(공개 선택 강의) 한계 명시; 소속기관 공개데이터 2차분석 면제 규정 확인 후 기재.

## 7. 동결 증빙
- 수집·분석 스크립트: `scripts/01~06` (파일럿·열거·클론·통계·연결) + 지표 계산 코드(07, 등록 후 작성이 아니라 **등록과 동시에 해시 고정**).
- git 해시: ⟦등록 직전 `git init` + commit 후 해시 기입⟧
- 데이터 스냅샷: repos_enumerated.jsonl (2026-08-05), logs 58,516개 (2026-08-05~06).

## 8. 등록 절차 메모
- OSF 프로젝트 zshu4 → Registrations → **OSF Preregistration** 템플릿.
- 본 문서를 OSF Files에 업로드 + 양식 각 항목에 §1~7 요약 기입.
- 공개 설정: 즉시 공개(권장 — 스쿠핑 방어에 타임스탬프가 곧 무기) 또는 embargo.
