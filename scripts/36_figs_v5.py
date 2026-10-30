#!/usr/bin/env python3
"""논문 2 — 7차 작업지시서 판(v5) 그림. 결과 JSON에서 그린다(재적합 없음).
fig_compare_v5: 여섯 신호, 두 대비. 조직 전체 비교(원자료, 공변량, 상한 25·50·100, 랜덤절편)와 조직 내 비교를 위아래로 나눠 그리며,
  조직 내 비교의 90% 구간을 찾지 못한 경우(검정 역전에서 경계 없음)는 점 대신 화살표와 'no bound found' 표시로 그린다.
fig_yearfe_v5: 여섯 신호의 연도 효과(부록).
fig_registered_vs_raw_v3: 등록 분석의 표준화 진단(부록 A; 21_figs_from_json.py의 같은 그림을 그대로 옮김).
fig_trailer_v4: 트레일러 대비(부록 F; 30_figs_v4.py의 같은 그림을 그대로 옮김).
figure_data.json: 네 그림이 그리는 수치(재현 진입점이 배포본과 비교).
출력: <toce_v2>/figs/"""
import os, json, numpy as np
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
V2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v2")
_H = os.path.dirname(os.path.abspath(__file__)); _T = next((p for p in (os.path.join(_H, "..", "toce_v2"), os.path.join(_H, "..", "..", "toce_v2")) if os.path.isdir(p)), os.path.join(_H, "..", "toce_v2"))
OUT = os.environ.get("OUT", os.path.join(_T, "figs")); os.makedirs(OUT, exist_ok=True)
SIG6 = ["edit_size_log", "large_insert_share_200", "burst_share_30", "samefile_rerun_rate_k3", "test_touch_share", "time_dispersion"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large-insert share", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns", "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion"}
def J(n):
    """Read a result file; standardized estimates come from the common-SD version (37_common_sd.py) where it exists."""
    n5 = n.replace("results_v4_", "results_v5_")
    return json.load(open(os.path.join(V2, n5 if os.path.exists(os.path.join(V2, n5)) else n)))
FD = {}
# Figure 2 (Appendix A): registered within-cohort standardization against the raw scale; drawn with matplotlib defaults as in 21_figs_from_json.py
X = json.load(open(os.path.join(V2, "results_v2_extra_v3.json")))
REGN = ["Edit size", "Large inserts (era-specific P95)", "Burst share", "Same-file reruns", "Test-path touches", "Time dispersion", "Message distinctiveness", "AI-paste co-occurrence"]
diag = X["diag_registered"]
FD["fig_registered_vs_raw_v3"] = [{"signal": REGN[i], "raw_d": d_["raw_d"], "registered_z_diff": d_["registered_z_diff"]} for i, d_ in enumerate(diag)]
fig, ax = plt.subplots(figsize=(6.5, 4.0)); y = np.arange(len(diag))
ax.barh(y-0.18, [d_["raw_d"] for d_ in diag], height=0.36, color="black", label="Raw scale (Cohen's d)")
ax.barh(y+0.18, [d_["registered_z_diff"] for d_ in diag], height=0.36, color="#bbbbbb", label="Registered within-cohort z (mean difference)")
ax.set_yticks(y); ax.set_yticklabels(REGN, fontsize=8); ax.invert_yaxis(); ax.axvline(0, color="gray", lw=0.8); ax.set_xlabel("Post minus pre", fontsize=8); ax.tick_params(labelsize=8)
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_registered_vs_raw_v3.png"), dpi=200, bbox_inches="tight"); fig.savefig(os.path.join(OUT, "fig_registered_vs_raw_v3.pdf"), bbox_inches="tight"); plt.close(fig)

plt.rcParams.update({"font.size": 9})
XL = 0.95
fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.9), sharey=True)
for k, (name, title) in enumerate([("era", "A. Post-ChatGPT vs. pre"), ("agent", "B. Agentic era vs. early post")]):
    b = J(f"results_v4_{name}.json")[name]; ax = axes[k]; y = np.arange(len(SIG6))
    FD.setdefault("fig_compare_v5", {})[name] = {c: {"raw": b["raw"][c], "cov": b["raw_cov"][c]["d"], "cap25": b["cap"]["25"][c]["d"], "cap50": b["cap"]["50"][c]["d"], "cap50_ci90": b["cap"]["50"][c]["ci90"], "cap100": b["cap"]["100"][c]["d"], "ri": b["ri"][c]["d"], "within": b["within"][c]["d"], "within_ci90": b["within"][c]["ci90_d"], "within_no_bound": b["within"][c]["ci_grid_edge"]} for c in SIG6}
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
fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(os.path.join(OUT, "fig_compare_v5.pdf")); fig.savefig(os.path.join(OUT, "fig_compare_v5.png"), dpi=200); plt.close(fig)

Y = J("results_v4_year.json")["year"]
fig, axes = plt.subplots(3, 2, figsize=(8.5, 8.2)); axes = axes.ravel()
for i, c in enumerate(SIG6):
    ax = axes[i]; a = {int(k): v for k, v in Y["ri"][c]["effects"].items()}; b = {int(k): v for k, v in Y["cap50"][c]["effects"].items()}
    a[2019] = [0.0, 0.0]; b[2019] = [0.0, [0.0, 0.0]]; ys = sorted(a)
    FD.setdefault("fig_yearfe_v5", {})[c] = {"ri": {str(v): a[v] for v in ys}, "cap50": {str(v): b[v] for v in sorted(b)}}
    ax.axhline(0, color="gray", lw=0.8); ax.axvspan(2022.9, 2025.05, color="#f0f0f0"); ax.axvspan(2025.05, 2026.6, color="#dcdcdc")
    ax.errorbar([v - 0.1 for v in ys], [a[v][0] for v in ys], yerr=[a[v][1] for v in ys], fmt="o-", ms=3, lw=1, capsize=2, color="#777777", label="Random intercepts")
    yb = [v for v in ys if v in b]
    ax.errorbar([v + 0.1 for v in yb], [b[v][0] for v in yb], yerr=[[b[v][0] - b[v][1][0] for v in yb], [b[v][1][1] - b[v][0] for v in yb]], fmt="D-", ms=3, lw=1, capsize=2, color="black", label="Capped at 50")
    ax.set_title(SHORT[c], fontsize=10); ax.set_xticks(range(2017, 2027, 3)); ax.tick_params(labelsize=8)
    if i % 2 == 0: ax.set_ylabel("Effect vs. 2019 (SD units)", fontsize=8)
    if i == 0: ax.legend(fontsize=7.5, loc="upper left", frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_yearfe_v5.pdf")); fig.savefig(os.path.join(OUT, "fig_yearfe_v5.png"), dpi=200); plt.close(fig)

# Figure 4 (Appendix F): AI-trailer and human-co-author-trailer repositories, full frame; as in 30_figs_v4.py
SIG7 = SIG6 + ["msg_informativeness"]; SHORT7 = dict(SHORT, msg_informativeness="Message distinctiveness")
T = json.load(open(os.path.join(V2, "results_trailer_v4.json")))["full_frame_ge5"]
def se(d, p): z = stats.norm.isf(p / 2); return abs(d) / z if z > 1e-9 else np.nan
FD["fig_trailer_v4"] = {c: {"ai_d": T[c]["ai_d"], "ai_halfwidth95": 1.96 * se(T[c]["ai_d"], T[c]["ai_p"]), "human_d": T[c]["human_d"], "human_halfwidth95": 1.96 * se(T[c]["human_d"], T[c]["human_p"])} for c in SIG7}
fig, ax = plt.subplots(figsize=(5.6, 3.6)); y = np.arange(len(SIG7))
ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0); ax.axvline(0, color="gray", lw=0.8)
ax.errorbar([T[c]["ai_d"] for c in SIG7], y - 0.12, xerr=[1.96 * se(T[c]["ai_d"], T[c]["ai_p"]) for c in SIG7], fmt="o", ms=4, color="black", capsize=2, lw=1, label="AI trailer")
ax.errorbar([T[c]["human_d"] for c in SIG7], y + 0.12, xerr=[1.96 * se(T[c]["human_d"], T[c]["human_p"]) for c in SIG7], fmt="s", ms=4, color="#888888", capsize=2, lw=1, label="Human co-author trailer")
ax.set_yticks(y); ax.set_yticklabels([SHORT7[c] for c in SIG7]); ax.invert_yaxis(); ax.set_xlabel("Difference from other repositories, organization random intercepts (SD units)", fontsize=8)
ax.legend(fontsize=8, loc="lower right", frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_trailer_v4.pdf")); fig.savefig(os.path.join(OUT, "fig_trailer_v4.png"), dpi=200); plt.close(fig)

def _clean(o):
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (bool, np.bool_)): return bool(o)
    if isinstance(o, (int, np.integer)): return int(o)
    if isinstance(o, (float, np.floating)): return float(o) if np.isfinite(o) else None
    return o
json.dump(_clean(FD), open(os.path.join(OUT, "figure_data.json"), "w"), indent=1)
print("figures written to", OUT)
