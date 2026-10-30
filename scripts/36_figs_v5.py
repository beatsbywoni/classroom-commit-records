#!/usr/bin/env python3
"""논문 2 — 7차 작업지시서 판(v5) 그림. 결과 JSON에서 그린다(재적합 없음).
fig_compare_v5: 여섯 신호, 두 대비. 조직 전체 비교(원자료, 공변량, 상한 25·50·100, 랜덤절편)와 조직 내 비교를 위아래로 나눠 그리며,
  조직 내 비교의 90% 구간을 찾지 못한 경우(검정 역전에서 경계 없음)는 점 대신 화살표와 'no bound found' 표시로 그린다.
fig_yearfe_v5: 여섯 신호의 연도 효과(부록).
출력: <toce_v2>/figs/"""
import os, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
_H = os.path.dirname(os.path.abspath(__file__)); _T = next((p for p in (os.path.join(_H, "..", "toce_v2"), os.path.join(_H, "..", "..", "toce_v2")) if os.path.isdir(p)), os.path.join(_H, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "figs")); os.makedirs(OUT, exist_ok=True)
SIG6 = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large-insert share", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns", "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion"}
J = lambda n: json.load(open(os.path.join(V2, n)))
plt.rcParams.update({"font.size": 9})
XL = 0.95
fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.9), sharey=True)
for k, (name, title) in enumerate([("era", "A. Post-ChatGPT vs. pre"), ("agent", "B. Agentic era vs. early post")]):
    b = J(f"results_v4_{name}.json")[name]; ax = axes[k]; y = np.arange(len(SIG6))
    for i, c in enumerate(SIG6):
        path = [b["raw"][c], b["raw_cov"][c]["d"], b["cap"]["25"][c]["d"], b["cap"]["50"][c]["d"], b["cap"]["100"][c]["d"], b["ri"][c]["d"]]
        ax.plot(path, [i] * 6, color="#c8c8c8", lw=1.2, zorder=1)
    ax.scatter([b["raw"][c] for c in SIG6], y, marker="s", facecolor="white", edgecolor="#555555", s=28, label="All repositories, raw", zorder=3)
    ax.scatter([b["raw_cov"][c]["d"] for c in SIG6], y, marker="s", color="#aaaaaa", s=14, label="All repositories, covariates", zorder=3)
    ax.scatter([b["cap"]["25"][c]["d"] for c in SIG6], y, marker="v", color="#999999", s=24, label="Capped at 25", zorder=3)
    lo = [b["cap"]["50"][c]["d"] - b["cap"]["50"][c]["ci90"][0] for c in SIG6]; hi = [b["cap"]["50"][c]["ci90"][1] - b["cap"]["50"][c]["d"] for c in SIG6]
    ax.errorbar([b["cap"]["50"][c]["d"] for c in SIG6], y, xerr=[lo, hi], fmt="D", ms=5, color="black", capsize=2, lw=1, label="Capped at 50 (90% CI)", zorder=4)
    ax.scatter([b["cap"]["100"][c]["d"] for c in SIG6], y, marker="^", color="#666666", s=24, label="Capped at 100", zorder=3)
    ax.scatter([b["ri"][c]["d"] for c in SIG6], y, marker="o", color="#333333", s=26, label="Random intercepts", zorder=3)
    for i, c in enumerate(SIG6):
        w = b["within"][c]; yy = i + 0.32
        if not w["ci_grid_edge"]:
            ax.plot(w["ci90_d"], [yy] * 2, color="black", lw=0.9, ls=(0, (2, 1.5)), zorder=2)
            ax.scatter([w["d"]], [yy], marker="x", color="black", s=26, zorder=3)
        else:
            # no bound found: dotted line across the panel with arrowheads at both edges, hollow marker at the estimate
            ax.annotate("", xy=(-XL, yy), xytext=(XL, yy), arrowprops=dict(arrowstyle="<->", color="#777777", lw=0.8, ls=":"), zorder=2)
            ax.scatter([w["d"]], [yy], marker="o", facecolor="white", edgecolor="black", s=22, zorder=3)
            ax.text(XL - 0.02, yy - 0.1, "no bound found", ha="right", va="bottom", fontsize=6.5, color="#555555")
    ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0)
    ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG6]); ax.set_title(title, fontsize=10.5)
    ax.set_xlabel("Standardized difference (SD units)"); ax.set_xlim(-XL, XL)
axes[0].invert_yaxis()
h, l = axes[0].get_legend_handles_labels(); hl = dict(zip(l, h))
from matplotlib.lines import Line2D
hl["Within organizations (90% CI)"] = Line2D([0], [0], color="black", lw=0.9, ls=(0, (2, 1.5)), marker="x", ms=5)
hl["Within, no bound found"] = Line2D([0], [0], color="#777777", lw=0.8, ls=":", marker="o", ms=4, markerfacecolor="white", markeredgecolor="black")
order = ["All repositories, raw", "All repositories, covariates", "Capped at 25", "Capped at 50 (90% CI)", "Capped at 100", "Random intercepts", "Within organizations (90% CI)", "Within, no bound found"]
fig.legend([hl[o] for o in order], order, loc="lower center", ncol=4, fontsize=7.8, frameon=False, bbox_to_anchor=(0.5, -0.005))
fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(os.path.join(OUT, "fig_compare_v5.pdf")); fig.savefig(os.path.join(OUT, "fig_compare_v5.png"), dpi=200)

Y = J("results_v4_year.json")["year"]
fig, axes = plt.subplots(3, 2, figsize=(8.5, 8.2)); axes = axes.ravel()
for i, c in enumerate(SIG6):
    ax = axes[i]; a = {int(k): v for k, v in Y["ri"][c]["effects"].items()}; b = {int(k): v for k, v in Y["cap50"][c]["effects"].items()}
    a[2019] = [0.0, 0.0]; b[2019] = [0.0, [0.0, 0.0]]; ys = sorted(a)
    ax.axhline(0, color="gray", lw=0.8); ax.axvspan(2022.9, 2025.05, color="#f0f0f0"); ax.axvspan(2025.05, 2026.6, color="#dcdcdc")
    ax.errorbar([v - 0.1 for v in ys], [a[v][0] for v in ys], yerr=[a[v][1] for v in ys], fmt="o-", ms=3, lw=1, capsize=2, color="#777777", label="Random intercepts")
    yb = [v for v in ys if v in b]
    ax.errorbar([v + 0.1 for v in yb], [b[v][0] for v in yb], yerr=[[b[v][0] - b[v][1][0] for v in yb], [b[v][1][1] - b[v][0] for v in yb]], fmt="D-", ms=3, lw=1, capsize=2, color="black", label="Capped at 50")
    ax.set_title(SHORT[c], fontsize=10); ax.set_xticks(range(2017, 2027, 3)); ax.tick_params(labelsize=8)
    if i % 2 == 0: ax.set_ylabel("Effect vs. 2019 (SD units)", fontsize=8)
    if i == 0: ax.legend(fontsize=7.5, loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_yearfe_v5.pdf")); fig.savefig(os.path.join(OUT, "fig_yearfe_v5.png"), dpi=200)
print("figures written to", OUT)
