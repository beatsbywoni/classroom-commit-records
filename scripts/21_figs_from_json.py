#!/usr/bin/env python3
"""논문 2 v3 — 그림 1·3 재생성(저장된 결과 JSON에서; 모형 재적합 없음): 신호명을 본문과 일치시키고 범례가 자료를 가리지 않게 배치.
입력: data/v2/results_v2_extra{SUF}.json  출력: fig_registered_vs_raw{SUF}.pdf/png, fig_yearfe{SUF}.pdf/png"""
import os, json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); V2 = os.path.join(D, "v2"); SUF = os.environ.get("SUF", "_v3")
X = json.load(open(os.path.join(V2, "results_v2_extra" + SUF + ".json")))
SIG = ["edit_size_log","large_insert_share_200","burst_share_30","samefile_rerun_rate_k3","test_touch_share","time_dispersion","msg_informativeness"]
SHORT = {"edit_size_log": "Edit size", "large_insert_share_200": "Large inserts", "burst_share_30": "Burst share", "samefile_rerun_rate_k3": "Same-file reruns", "test_touch_share": "Test-path touches", "time_dispersion": "Time dispersion", "msg_informativeness": "Message distinctiveness"}
# Figure 3
yfe, yfc = X["year_fe"], X["year_fe_capped"]
fig, axes = plt.subplots(4, 2, figsize=(8.5, 10)); axes = axes.ravel()
for i, c in enumerate(SIG):
    ax = axes[i]; a = {int(k): v for k, v in yfe[c].items()}; b = {int(k): v for k, v in yfc[c].items()}; ys = sorted(a)
    ax.axhline(0, color="gray", lw=0.8); ax.axvspan(2022.9, 2025.05, color="#f0f0f0"); ax.axvspan(2025.05, 2026.6, color="#dcdcdc")
    ax.errorbar([y-0.1 for y in ys], [a[y][0] for y in ys], yerr=[a[y][1] for y in ys], fmt="o-", ms=3, lw=1, capsize=2, color="#777777", label="Org. random intercepts")
    yb = [y for y in ys if y in b]
    ax.errorbar([y+0.1 for y in yb], [b[y][0] for y in yb], yerr=[b[y][1] for y in yb], fmt="D-", ms=3, lw=1, capsize=2, color="black", label="Org. capped at 50")
    ax.set_title(SHORT[c], fontsize=10); ax.set_xticks(range(2017, 2027, 3)); ax.tick_params(labelsize=8)
    if i % 2 == 0: ax.set_ylabel("Effect vs. 2019 (SD units)", fontsize=8)
axes[7].axis("off")
h, l = axes[0].get_legend_handles_labels(); axes[7].legend(h, l, fontsize=9, loc="upper left", frameon=False)
axes[7].text(0, 0.62, "Year-of-first-commit effects relative to 2019;\ncovariates: log commits, authors, language family.\nGray: organization random intercepts, all repositories.\nBlack: same model with each organization capped\nat 50 repositories (mean of 5 random draws).\nLight band: January 2023 to January 2025.\nDark band: February 2025 onward. Bars: 95% CI.", fontsize=8.5, va="top")
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_yearfe" + SUF + ".png"), dpi=200); fig.savefig(os.path.join(V2, "fig_yearfe" + SUF + ".pdf"))
# Figure 1 (registered signal definitions; names aligned with the paper)
REGN = ["Edit size", "Large inserts (era-specific P95)", "Burst share", "Same-file reruns", "Test-path touches", "Time dispersion", "Message distinctiveness", "AI-paste co-occurrence"]
diag = X["diag_registered"]
fig, ax = plt.subplots(figsize=(6.5, 4.0)); y = np.arange(len(diag))
ax.barh(y-0.18, [d_["raw_d"] for d_ in diag], height=0.36, color="black", label="Raw scale (Cohen's d)")
ax.barh(y+0.18, [d_["registered_z_diff"] for d_ in diag], height=0.36, color="#bbbbbb", label="Registered within-cohort z (mean difference)")
ax.set_yticks(y); ax.set_yticklabels(REGN, fontsize=8); ax.invert_yaxis(); ax.axvline(0, color="gray", lw=0.8); ax.set_xlabel("Post minus pre", fontsize=8); ax.tick_params(labelsize=8)
ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(V2, "fig_registered_vs_raw" + SUF + ".png"), dpi=200, bbox_inches="tight"); fig.savefig(os.path.join(V2, "fig_registered_vs_raw" + SUF + ".pdf"), bbox_inches="tight")
print("figs 1 and 3 regenerated")
# Figure 2: estimates along the organization-weighting path (raw -> cap 25 -> cap 50 -> cap 100 -> random intercepts), plus within-organization FE
R = json.load(open(os.path.join(V2, "results_composition" + SUF + ".json")))
fig, axes = plt.subplots(1, 2, figsize=(9.8, 5.0), sharey=True)
for k, (name, title) in enumerate([("era", "A. Post-ChatGPT vs. pre"), ("agent", "B. Agentic era vs. early post")]):
    ax = axes[k]; b = R[name]; y = np.arange(len(SIG))
    for i, c in enumerate(SIG):
        path = [b["raw"][c], b["cap_sensitivity"]["25"][c]["d"], b["capped"][c]["d"], b["cap_sensitivity"]["100"][c]["d"], b["org_ri"][c]["d"]]
        ax.plot(path, [i]*5, color="#bbbbbb", lw=1.2, zorder=1)
    ax.scatter([b["raw"][c] for c in SIG], y, marker="s", facecolor="white", edgecolor="#555555", s=28, label="Raw (average repository)", zorder=3)
    ax.scatter([b["cap_sensitivity"]["25"][c]["d"] for c in SIG], y, marker="v", color="#999999", s=24, label="Capped at 25", zorder=3)
    ax.errorbar([b["capped"][c]["d"] for c in SIG], y, xerr=[1.96*b["capped"][c]["se_d"] for c in SIG], fmt="D", ms=5, color="black", capsize=2, lw=1, label="Capped at 50 (95% CI)", zorder=4)
    ax.scatter([b["cap_sensitivity"]["100"][c]["d"] for c in SIG], y, marker="^", color="#666666", s=24, label="Capped at 100", zorder=3)
    ax.scatter([b["org_ri"][c]["d"] for c in SIG], y, marker="o", color="#333333", s=26, label="Organization random intercepts", zorder=3)
    ax.scatter([b["within"][c]["d"] for c in SIG], y+0.3, marker="x", color="black", s=26, label="Within organizations (fixed effects)", zorder=3)
    ax.axvline(0, color="gray", lw=0.8); ax.axvspan(-0.1, 0.1, color="#f2f2f2", zorder=0)
    ax.set_yticks(y); ax.set_yticklabels([SHORT[c] for c in SIG], fontsize=9); ax.set_title(title, fontsize=11)
    ax.set_xlabel("Standardized difference (SD units)", fontsize=9); ax.tick_params(labelsize=9); ax.set_xlim(-0.9, 0.9)
axes[0].invert_yaxis()
h, l = axes[0].get_legend_handles_labels(); order = ["Raw (average repository)", "Capped at 25", "Capped at 50 (95% CI)", "Capped at 100", "Organization random intercepts", "Within organizations (fixed effects)"]; hl = dict(zip(l, h)); h = [hl[o] for o in order]; l = order
fig.legend(h, l, loc="lower center", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.09, 1, 1)); fig.savefig(os.path.join(V2, "fig_composition" + SUF + ".pdf")); fig.savefig(os.path.join(V2, "fig_composition" + SUF + ".png"), dpi=200)
print("fig 2 regenerated (weighting path)")
