"""根据 results/results.json 绘制报告插图。

用法:  python code/plot_figures.py
输出:  figures/*.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter, NullFormatter

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "font.family": "sans-serif",
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.labelsize": 9.5,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.grid": True,
        "grid.alpha": 0.26,
        "grid.linewidth": 0.55,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 120,
        "savefig.dpi": 320,
        "savefig.bbox": "tight",
    }
)

COLORS = {
    "0.2": "#0072B2",
    "0.5": "#D55E00",
    "1.0": "#009E73",
    "gs": "#555555",
    "theory": "#7F3C8D",
    "accent": "#CC3311",
}


def savefig(fig, name):
    path = FIGURES / name
    fig.savefig(path)
    plt.close(fig)
    print("  [figure]", path.name)


def sym_profile(u, i0, j0, N):
    kmax = min(j0 - 1, N - j0)
    k = np.arange(0, kmax + 1)
    return k, 0.5 * (u[i0, j0 + k] + u[i0, j0 - k])


def fig1(data):
    u = np.load(RESULTS / "u_task1.npy")
    t1 = data["task1"]
    N = t1["N"]
    i0, j0 = t1["source"]
    umax = u.max()

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15), constrained_layout=True)
    ax = axes[0]
    im = ax.imshow(
        u,
        origin="lower",
        extent=[0.5, N + 0.5, 0.5, N + 0.5],
        cmap="viridis",
        interpolation="nearest",
    )
    jj = np.arange(1, N + 1)
    ax.contour(
        jj,
        jj,
        u,
        levels=[1e-3 * umax, 1e-2 * umax, 1e-1 * umax],
        colors="white",
        linewidths=0.6,
        alpha=0.85,
    )
    ax.plot(j0 + 1, i0 + 1, marker="x", ms=7, mew=1.4, color="white")
    ax.annotate(
        "源点",
        xy=(j0 + 1, i0 + 1),
        xytext=(j0 + 4.5, i0 + 4.5),
        color="white",
        fontsize=8,
        arrowprops=dict(arrowstyle="->", color="white", lw=0.8),
    )
    ax.set_xlabel("$j$（格点）")
    ax.set_ylabel("$i$（格点）")
    ax.set_title("(a) $u_{i,j}$ 的二维分布")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("$u_{i,j}$", fontsize=8.5)
    cb.ax.tick_params(labelsize=7)
    ax.grid(False)

    ax = axes[1]
    j = np.arange(1, N + 1)
    ax.plot(j, u[i0, :], color=COLORS["0.5"], lw=1.7)
    ax.axvline(j0 + 1, color="0.45", ls="--", lw=0.9)
    ax.annotate(
        "源点 $j_0$",
        xy=(j0 + 1, umax * 0.45),
        xytext=(j0 - 7.5, umax * 0.62),
        color="0.35",
        fontsize=8,
        arrowprops=dict(arrowstyle="->", color="0.45", lw=0.8),
    )
    ax.set_xlabel("$j$（格点）")
    ax.set_ylabel("$u_{i_0,j}$")
    ax.set_title("(b) 过源点的水平截面")
    ax.set_xlim(0.5, N + 0.5)
    ax.set_ylim(-0.01, umax * 1.08)

    savefig(fig, "fig1_task1.png")


def fig2(data):
    runs = data["task2"]["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), constrained_layout=True)

    ax = axes[0]
    ax.axhline(1 / np.e, color="0.5", ls=":", lw=1.0)
    ax.text(12.0, 1 / np.e + 0.025, "$e^{-1}$", color="0.35", fontsize=8.5)
    for run in runs:
        mm = run["m"]
        color = COLORS[str(mm)]
        k = np.asarray(run["k"])
        norm = np.asarray(run["norm"])
        ax.plot(k, norm, "o-", ms=2.6, lw=1.1, color=color, label=f"$m={mm}$")
        if run["r_e"] is not None:
            ax.plot(
                run["r_e"],
                norm[run["r_e"]],
                "o",
                ms=6.5,
                mfc="white",
                mec=color,
                mew=1.2,
                zorder=5,
            )
    ax.set_xlabel("$|j-j_0|$（格点）")
    ax.set_ylabel("$u_{i_0,j}\\,/\\,u_{i_0,j_0}$")
    ax.set_title("(a) 归一化水平响应")
    ax.set_xlim(0, 22)
    ax.set_ylim(-0.02, 1.03)
    ax.legend(frameon=False, loc="upper right", handlelength=1.6)

    ax = axes[1]
    for run in runs:
        mm = run["m"]
        color = COLORS[str(mm)]
        k = np.asarray(run["k"])
        norm = np.asarray(run["norm"])
        ax.semilogy(k, norm, "o", ms=2.4, color=color, label=f"$m={mm}$")
        lo, hi = run["xi_fit_range"]
        kk = np.arange(max(0, lo - 1), hi + 2)
        coef = np.polyfit(np.arange(lo, hi + 1), np.log(norm[lo : hi + 1]), 1)
        ax.semilogy(kk, np.exp(np.polyval(coef, kk)), "--", lw=1.0, color=color, alpha=0.95)
        if mm == 0.2:
            xk = 15.5
        elif mm == 0.5:
            xk = 6.5
        else:
            xk = 3.2
        yk = np.exp(np.polyval(coef, xk)) * 2.4
        ax.annotate(
            f"$\\xi={run['xi']:.2f}$",
            xy=(xk, yk),
            color=color,
            fontsize=8,
            ha="left",
            va="bottom",
            bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2),
        )
    ax.set_xlabel("$|j-j_0|$（格点）")
    ax.set_ylabel("$u_{i_0,j}\\,/\\,u_{i_0,j_0}$")
    ax.set_title("(b) 半对数坐标与指数尾段拟合")
    ax.set_xlim(0, 33)
    ax.set_ylim(1e-5, 1.5)
    savefig(fig, "fig2_task2.png")


def fig3(data):
    t3 = data["task3"]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), constrained_layout=True)

    ax = axes[0]
    om = [row["omega"] for row in t3["coarse"]]
    K = [row["K"] for row in t3["coarse"]]
    ax.plot(om, K, "o-", color=COLORS["0.5"], ms=3.8, lw=1.2)
    ax.axhline(t3["K_GS"], color=COLORS["gs"], ls="--", lw=0.9)
    ax.text(1.04, t3["K_GS"] + 12, f"Gauss–Seidel: $K={t3['K_GS']}$", color=COLORS["gs"], fontsize=8)
    ax.axvline(t3["omega_th"], color=COLORS["theory"], ls=":", lw=1.1)
    ax.text(
        t3["omega_th"],
        0.97,
        f"$\\omega_{{\\rm th}}={t3['omega_th']:.3f}$",
        color=COLORS["theory"],
        fontsize=8,
        rotation=90,
        va="top",
        ha="right",
        transform=ax.get_xaxis_transform(),
    )
    ax.set_xlabel("$\\omega$")
    ax.set_ylabel("完整扫描次数 $K$")
    ax.set_title("(a) 粗扫：$\\omega=1.0,1.1,\\ldots,1.9,1.95$")
    ax.set_xlim(0.97, 2.0)

    ax = axes[1]
    rows = sorted(t3["fine"] + t3["ultra"], key=lambda r: r["omega"])
    om = [row["omega"] for row in rows]
    K = [row["K"] for row in rows]
    ax.plot(om, K, ".-", color=COLORS["0.5"], ms=4, lw=1.0)
    pl = t3["ultra_plateau"]
    ax.axhspan(pl["K"] - 0.18, pl["K"] + 0.18, color=COLORS["accent"], alpha=0.14, lw=0)
    ax.axvline(t3["omega_th"], color=COLORS["theory"], ls=":", lw=1.1)
    ax.text(
        t3["omega_th"],
        0.97,
        f"$\\omega_{{\\rm th}}={t3['omega_th']:.3f}$",
        color=COLORS["theory"],
        fontsize=8,
        rotation=90,
        va="top",
        ha="right",
        transform=ax.get_xaxis_transform(),
    )
    ax.annotate(
        f"平台 ${pl['omega_lo']:.3f}$–${pl['omega_hi']:.3f}$，$K={pl['K']}$",
        xy=(pl["mid"], 29.12),
        fontsize=7.8,
        color=COLORS["accent"],
        ha="center",
        va="bottom",
    )
    ax.set_xlabel("$\\omega$")
    ax.set_ylabel("完整扫描次数 $K$")
    ax.set_title("(b) 局部细扫与最优平台")
    ax.set_xlim(1.35, 1.505)
    ax.set_ylim(29.0, 34.6)
    savefig(fig, "fig3_task3.png")


def fig4(data):
    fig, ax = plt.subplots(figsize=(5.8, 4.0), constrained_layout=True)
    for mm in ("0.2", "0.5", "1.0"):
        t = data["task4"][mm]
        color = COLORS[mm]
        rows = sorted(t["coarse"], key=lambda r: r["omega"])
        ax.semilogy(
            [r["omega"] for r in rows],
            [r["K"] for r in rows],
            "o-",
            ms=2.8,
            lw=1.0,
            color=color,
            alpha=0.75,
            label=f"$m={mm}$",
        )
        ax.plot(
            t["best_omega"],
            t["K_best"],
            "*",
            ms=11,
            mfc=color,
            mec="white",
            mew=0.8,
            zorder=6,
        )
        ax.plot(1.0, t["K_GS"], "s", ms=5.5, mfc="white", mec=color, mew=1.2, zorder=6)
        ax.axvline(t["omega_th"], color=color, ls=":", lw=1.0, alpha=0.85)
        ax.text(
            t["omega_th"] - 0.008,
            0.965,
            f"$\\omega_{{\\rm th}}={t['omega_th']:.2f}$",
            color=color,
            fontsize=7.8,
            rotation=90,
            va="top",
            ha="right",
            transform=ax.get_xaxis_transform(),
        )
        ax.annotate(
            f"$\\omega={t['best_omega']:.2f}$",
            xy=(t["best_omega"], t["K_best"]),
            xytext=(0, 13),
            textcoords="offset points",
            fontsize=7.8,
            color=color,
            ha="center",
        )
    ax.set_xlabel("$\\omega$")
    ax.set_ylabel("完整扫描次数 $K$")
    ax.set_title("不同 $m$ 下收敛所需扫描次数")
    ax.set_xlim(0.96, 2.0)
    ax.set_ylim(15, 500)
    ax.set_yticks([20, 30, 50, 70, 100, 150, 200, 300, 400])
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    handles = [
        Line2D([], [], color=COLORS[mm], marker="o", ms=3, lw=1.0, label=f"$m={mm}$")
        for mm in ("0.2", "0.5", "1.0")
    ]
    handles += [
        Line2D([], [], color="0.3", marker="*", ms=8, lw=0, label="最优平台"),
        Line2D([], [], color="0.3", marker="s", ms=5, lw=0, mfc="white", label="Gauss–Seidel"),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right", ncol=1, handlelength=1.6)
    savefig(fig, "fig4_task4.png")


def fig5(data):
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25), constrained_layout=True)
    ax = axes[0]
    chosen = {1.0, 1.2, 1.49, 1.8, 1.95}
    palette = ["#4D4D4D", "#0072B2", "#009E73", "#E69F00", "#CC3311"]
    for color, curve in zip(palette, [c for c in data["residual_curves"] if c["omega"] in chosen]):
        hist = np.asarray(curve["history"])
        ax.semilogy(
            np.arange(len(hist)),
            hist,
            lw=1.15,
            color=color,
            label=f"$\\omega={curve['omega']:.2f}$",
        )
    ax.axhline(1e-6, color=COLORS["accent"], ls="--", lw=0.9)
    ax.text(4, 2.4e-6, "停止阈值 $10^{-6}$", color=COLORS["accent"], fontsize=8)
    ax.set_xlabel("扫描次数")
    ax.set_ylabel("$\\|r\\|_\\infty$")
    ax.set_title("(a) 残差收敛曲线（$N=63$, $m=0.5$）")
    ax.set_ylim(1e-11, 1.3)
    ax.set_xlim(0, 430)
    ax.legend(
        frameon=True,
        framealpha=0.92,
        edgecolor="none",
        loc="upper right",
        ncol=2,
        fontsize=7.2,
        handlelength=1.5,
        columnspacing=1.0,
    )

    ax = axes[1]
    th = data["theory"]
    om = np.linspace(1.0, 1.99, 500)
    rhoJ = th["rho_J"]
    rho = []
    for w in om:
        disc = max(0.0, w * w * rhoJ * rhoJ - 4.0 * (w - 1.0))
        rho.append((w * rhoJ + np.sqrt(disc)) ** 2 / 4.0 if w <= th["omega_th"] else w - 1.0)
    ax.plot(om, rho, "-", color=COLORS["theory"], lw=1.4, label="理论 $\\rho_{\\rm SOR}(\\omega)$")
    num = th["rho_num"]
    ax.plot(
        [row["omega"] for row in num],
        [row["rho_num"] for row in num],
        "o",
        ms=4,
        mfc="white",
        mec=COLORS["accent"],
        mew=1.1,
        label="数值谱半径（$N=31$）",
    )
    ax.axvline(th["omega_th"], color="0.45", ls=":", lw=0.9)
    ax.text(
        th["omega_th"] + 0.015,
        0.04,
        f"$\\omega_{{\\rm th}}={th['omega_th']:.3f}$",
        color="0.35",
        fontsize=8,
        rotation=90,
        va="bottom",
        ha="left",
        transform=ax.get_xaxis_transform(),
    )
    ax.set_xlabel("$\\omega$")
    ax.set_ylabel("$\\rho_{\\rm SOR}$")
    ax.set_title("(b) 谱半径：理论公式与数值对角化")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0.98, 2.0)
    ax.legend(frameon=False, loc="upper left", handlelength=1.6)
    savefig(fig, "fig5_theory.png")


def fig6(data):
    fig, ax = plt.subplots(figsize=(5.6, 3.9), constrained_layout=True)
    markers = {7: "o", 9: "s"}
    for N in (7, 9):
        rows = [row for row in data["verification"] if row["N"] == N]
        res = np.array([row["residual"] for row in rows])
        eps = np.array([row["eps_inf"] for row in rows])
        ax.loglog(res, eps, markers[N] + "-", ms=5, lw=1.0, label=f"$N={N}$")
        ainv = rows[0]["Ainv_inf"]
        xx = np.array([4e-11, 2e-4])
        ax.loglog(
            xx,
            ainv * xx,
            ":",
            color="0.5",
            lw=1.0,
            label="$\\|A^{-1}\\|_\\infty\\|r\\|_\\infty$（上界）" if N == 7 else None,
        )
    xx = np.array([4e-11, 2e-4])
    ax.loglog(xx, xx, "--", color=COLORS["accent"], lw=0.9, label="$\\epsilon_\\infty=\\|r\\|_\\infty$")
    ax.set_xlabel("$\\|r\\|_\\infty$")
    ax.set_ylabel("$\\epsilon_\\infty$")
    ax.set_title("直接解对照：解误差与残差的关系")
    handles, labels = ax.get_legend_handles_labels()
    order = [0, 2, 1, 3]
    ax.legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        frameon=False,
        loc="upper left",
        fontsize=7.5,
    )
    ax.set_xlim(4e-11, 2e-4)
    ax.set_ylim(1e-11, 1e-3)
    savefig(fig, "fig6_verification.png")


def main():
    with open(RESULTS / "results.json", encoding="utf-8") as fh:
        data = json.load(fh)
    fig1(data)
    fig2(data)
    fig3(data)
    fig4(data)
    fig5(data)
    fig6(data)


if __name__ == "__main__":
    main()
