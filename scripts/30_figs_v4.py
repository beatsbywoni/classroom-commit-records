#!/usr/bin/env python3
"""논문 2 v4 — 그림 생성(결과 JSON에서; 모형 재적합 없음).
fig_composition_v4: 비교별 추정치(원자료, 공변량 보정, 상한 25·50·100, 랜덤절편)와 조직 내 비교(90% 구간; 무한 구간은 표시만)
fig_yearfe_v4: 연도 효과(랜덤절편 ±1.96 SE; 상한 50은 부트스트랩 95% 백분위 구간)
fig_trailer_v4: 트레일러 대비(전체 프레임; 95% 구간, Wald p에서 SE 역산)"""
import os, json, numpy as np
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
_H = os.path.dirname(os.path.abspath(__file__)); _T = next((p for p in (os.path.join(_H, "..", "toce_v2"), os.path.join(_H, "..", "..", "toce_v2")) if os.path.isdir(p)), os.path.join(_H, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "figs")); os.makedirs(OUT, exist_ok=True)
SIG = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion", "msg_informativeness"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large-insert share", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns",
         "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", "msg_informativeness": "Message distinctiveness"}
J = lambda n: json.load(open(os.path.join(V2, n)))
plt.rcParams.update({"font.size": 9})

# Figure: comparisons side by side
fig, axes = plt.subplots(1, 2, figsize=(9.8, 5.2), sharey=True)
for k, (name, title) in enumerate([("era", "A. Post-ChatGPT vs. pre"), ("agent", "B. Agentic era vs. early post")]):
    b = J(f"results_v4_{name}.json")[name]; ax = axes[k]; y = np.arange(len(SIG))
    for i, c in enumerate(SIG):
        path = [b["raw"][c], b["raw_cov"][c]["d"], b["cap"]["25"][c]["d"], b["cap"]["50"][c]["d"], b["cap"]["100"][c]["d"], b["ri"][c]["d"]]
        ax.plot(path, [i] * 6, color="#c8c8c8", lw=1.2, zorder=1)
    ax.scatter([b["raw"][c] for c in SIG], y, marker="s", facecolor="white", edgecolor="#555555", s=28, label="All repositories, raw", zorder=3)
    ax.scatter([b["raw_cov"][c]["d"] for c in SIG], y, marker="s", color="#aaaaaa", s=14, label="All repositories, covariates", zorder=3)
    ax.scatter([b["cap"]["25"][c]["d"] for c in SIG], y, marker="v", color="#999999", s=24, label="Capped at 25", zorder=3)
    lo = [b["cap"]["50"][c]["d"] - b["cap"]["50"][c]["ci90"][0] for c in SIG]; hi = [b["cap"]["50"][c]["ci90"][1] - b["cap"]["50"][c]["d"] for c in SIG]
    ax.errorbar([b["cap"]["50"][c]["d"] for c in SIG], y, xerr=[lo, hi], fmt="D", ms=5, color="black", capsize=2, lw=1, label="Capped at 50 (90% CI)", zorder=4)
    ax.scatter([b["cap"]["100"][c]["d"] for c in SIG], y, marker="^", color="#666666", s=24, label="Capped at 100", zorder=3)
    ax.scatter([b["ri"][c]["d"] for c in SIG], y, marker="o", color="#333333", s=26, label="Random intercepts", zorder=3)
    for i, c in enumerate(SIG):
        w = b["within"][c]
        if not w["ci_grid_edge"]:
            ax.plot(w["ci90_d"], [i + 0.3] * 2, color="black", lw=0.8, ls=(0, (2, 1.5)), zorder=2)
    ax.scatter([b["within"][c]["d"] for c in SIG], y + 0.3, marker="x", color="black", s=26, label="Within organizations (90% CI, if bounded)", zorder=3)
    ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0)
    ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG]); ax.set_title(title, fontsize=10.5)
    ax.set_xlabel("Standardized difference (SD units)"); ax.set_xlim(-0.95, 0.95)
axes[0].invert_yaxis()
h, l = axes[0].get_legend_handles_labels(); hl = dict(zip(l, h))
order = ["All repositories, raw", "All repositories, covariates", "Capped at 25", "Capped at 50 (90% CI)", "Capped at 100", "Random intercepts", "Within organizations (90% CI, if bounded)"]
fig.legend([hl[o] for o in order], order, loc="lower center", ncol=4, fontsize=7.8, frameon=False, bbox_to_anchor=(0.5, -0.005))
fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(os.path.join(OUT, "fig_composition_v4.pdf")); fig.savefig(os.path.join(OUT, "fig_composition_v4.png"), dpi=200)

# Figure: year effects
Y = J("results_v4_year.json")["year"]
fig, axes = plt.subplots(4, 2, figsize=(8.5, 10)); axes = axes.ravel()
for i, c in enumerate(SIG):
    ax = axes[i]; a = {int(k): v for k, v in Y["ri"][c]["effects"].items()}; b = {int(k): v for k, v in Y["cap50"][c]["effects"].items()}
    a[2019] = [0.0, 0.0]; b[2019] = [0.0, [0.0, 0.0]]; ys = sorted(a)
    ax.axhline(0, color="gray", lw=0.8); ax.axvspan(2022.9, 2025.05, color="#f0f0f0"); ax.axvspan(2025.05, 2026.6, color="#dcdcdc")
    ax.errorbar([v - 0.1 for v in ys], [a[v][0] for v in ys], yerr=[a[v][1] for v in ys], fmt="o-", ms=3, lw=1, capsize=2, color="#777777", label="Random intercepts, all repositories")
    yb = [v for v in ys if v in b]
    ax.errorbar([v + 0.1 for v in yb], [b[v][0] for v in yb], yerr=[[b[v][0] - b[v][1][0] for v in yb], [b[v][1][1] - b[v][0] for v in yb]], fmt="D-", ms=3, lw=1, capsize=2, color="black", label="Capped at 50")
    ax.set_title(SHORT[c], fontsize=10); ax.set_xticks(range(2017, 2027, 3)); ax.tick_params(labelsize=8)
    if i % 2 == 0: ax.set_ylabel("Effect vs. 2019 (SD units)", fontsize=8)
axes[7].axis("off"); h, l = axes[0].get_legend_handles_labels(); axes[7].legend(h, l, fontsize=9, loc="upper left", frameon=False)
axes[7].text(0, 0.62, "Year-of-first-commit effects relative to 2019;\ncovariates: log commits, authors, language family.\nGray: organization random intercepts, bars 95% CI.\nBlack: each organization capped at 50 repositories\n(mean of 200 draws), bars 95% bootstrap interval\n(500 organization-bootstrap replicates).\nLight band: January 2023 to January 2025.\nDark band: February 2025 onward.", fontsize=8.5, va="top")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_yearfe_v4.pdf")); fig.savefig(os.path.join(OUT, "fig_yearfe_v4.png"), dpi=200)

# Figure: trailers (full frame)
T = J("results_trailer_v4.json")["full_frame_ge5"]
def se(d, p): z = stats.norm.isf(p / 2); return abs(d) / z if z > 1e-9 else np.nan
fig, ax = plt.subplots(figsize=(5.6, 3.6)); y = np.arange(len(SIG))
ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0); ax.axvline(0, color="gray", lw=0.8)
ax.errorbar([T[c]["ai_d"] for c in SIG], y - 0.12, xerr=[1.96 * se(T[c]["ai_d"], T[c]["ai_p"]) for c in SIG], fmt="o", ms=4, color="black", capsize=2, lw=1, label="AI trailer")
ax.errorbar([T[c]["human_d"] for c in SIG], y + 0.12, xerr=[1.96 * se(T[c]["human_d"], T[c]["human_p"]) for c in SIG], fmt="s", ms=4, color="#888888", capsize=2, lw=1, label="Human co-author trailer")
ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG]); ax.invert_yaxis(); ax.set_xlabel("Difference from other repositories, organization random intercepts (SD units)", fontsize=8)
ax.legend(fontsize=8, loc="lower right", frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_trailer_v4.pdf")); fig.savefig(os.path.join(OUT, "fig_trailer_v4.png"), dpi=200)
print("figures written to", OUT)
