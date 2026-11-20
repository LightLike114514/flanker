"""Generate all figures for the three-body report.

用法:
    python make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
FIGURES = BASE / "figures"
FIGURES.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "font.family": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.dpi": 200,
        "savefig.dpi": 220,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

STAR_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c"]
MODE_COLORS = {"A": "#6a3d9a", "B": "#1f78b4", "C": "#33a02c", "D": "#e31a1c"}
GRAY = "#8c8c8c"


def load() -> tuple[dict, dict]:
    data = dict(np.load(RESULTS / "trajectories.npz"))
    with (RESULTS / "summary.json").open(encoding="utf-8") as f:
        summary = json.load(f)
    return data, summary


def interp_states(states: np.ndarray, t_src: np.ndarray, t_dst: np.ndarray) -> np.ndarray:
    flat = states.reshape(len(states), -1)
    out = np.array(
        [np.interp(t_dst, t_src, flat[:, k]) for k in range(flat.shape[1])]
    ).T
    return out.reshape(len(t_dst), 3, 4)


def add_threshold(ax, ylim=None):
    ax.axhspan(1e-4, 0.05, color="#d62728", alpha=0.08, lw=0)
    ax.axhline(0.05, color="#d62728", ls="--", lw=0.9)
    ax.axhline(10.0, color="#555555", ls=":", lw=0.9)
    if ylim is not None:
        ax.set_ylim(*ylim)


# ---------------------------------------------------------------------------
# 图 1: 四种模式的轨迹
# ---------------------------------------------------------------------------
def fig1(data, summary):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 9.2))
    ax = axes[0, 0]

    # A: 旋转三角形快照 + 外接圆
    t_a = data["A_t"]
    states_a = data["A_states"]
    radius = 1 / np.sqrt(3)
    theta = np.linspace(0, 2 * np.pi, 400)
    ax.plot(radius * np.cos(theta), radius * np.sin(theta), "--", color=GRAY, lw=0.9)
    snap_times = [0.0, 2.5, 5.0, 7.5, 10.0]
    cmap = plt.cm.viridis(np.linspace(0.15, 0.9, len(snap_times)))
    for t_snap, color in zip(snap_times, cmap):
        idx = int(np.searchsorted(t_a, t_snap))
        s = states_a[idx]
        tri = np.vstack([s[:, :2], s[0, :2]])
        ax.plot(tri[:, 0], tri[:, 1], "-", color=color, lw=1.2, alpha=0.9)
        ax.scatter(s[:, 0], s[:, 1], s=22, color=[color], edgecolor="white", lw=0.5, zorder=5)
    ax.scatter([], [], s=22, color="#440154", label="恒星位置（不同时刻）")
    ax.plot([], [], "--", color=GRAY, label="外接圆半径 $1/\\sqrt{3}$")
    ax.set_aspect("equal")
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(-0.8, 0.8)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title("模式 A：等边三角形旋转（解析解）\n$\\omega=\\sqrt{3}$，$d_{ij}\\equiv 1$")
    ax.legend(loc="upper right", frameon=False)

    # B: 8 字形
    ax = axes[0, 1]
    t_b = data["B_t"]
    s_b = data["B_states"]
    for i in range(3):
        ax.plot(s_b[:, i, 0], s_b[:, i, 1], color=STAR_COLORS[i], lw=1.0, alpha=0.55,
                label=f"恒星 {i + 1}")
    # 几个时刻的三星位置，显示舞蹈型运动
    for t_snap in [0.0, 1.6, 3.2, 4.8]:
        idx = int(np.searchsorted(t_b, t_snap))
        ax.scatter(s_b[idx, :, 0], s_b[idx, :, 1], s=16, c=STAR_COLORS,
                   edgecolor="white", lw=0.4, zorder=5)
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-0.55, 0.55)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    info = summary["modes"]["B"]
    ax.set_title(f"模式 B：8 字形\n$d_{{\\min}}={info['dmin']:.3f}$，$d_{{\\max}}={info['dmax']:.3f}$")
    ax.text(0.02, 0.04, "三颗星共用同一条 8 字曲线（相位不同）", transform=ax.transAxes, fontsize=8)


    # C: 飞蛾
    ax = axes[1, 0]
    t_c = data["C_t"]
    s_c = data["C_states"]
    for i in range(3):
        ax.plot(s_c[:, i, 0], s_c[:, i, 1], color=STAR_COLORS[i], lw=1.0, alpha=0.55,
                label=f"恒星 {i + 1}")
    for t_snap in [0.0, 3.5, 7.0, 10.5]:
        idx = int(np.searchsorted(t_c, t_snap))
        ax.scatter(s_c[idx, :, 0], s_c[idx, :, 1], s=16, c=STAR_COLORS,
                   edgecolor="white", lw=0.4, zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    info = summary["modes"]["C"]
    ax.set_title(f"模式 C：飞蛾 I\n$d_{{\\min}}={info['dmin']:.3f}$，$d_{{\\max}}={info['dmax']:.3f}$")

    # D: 层级三体
    ax = axes[1, 1]
    t_d = data["D_t"]
    s_d = data["D_states"]
    for i in range(3):
        ax.plot(s_d[:, i, 0], s_d[:, i, 1], color=STAR_COLORS[i], lw=1.0, alpha=0.7,
                label=f"恒星 {i + 1}")
    ax.scatter(s_d[0, :, 0], s_d[0, :, 1], s=26, c=STAR_COLORS, edgecolor="white", lw=0.6, zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    info = summary["modes"]["D"]
    ax.set_title(f"模式 D：层级三体（双星 + 第三体）\n$d_{{\\min}}={info['dmin']:.3f}$，$d_{{\\max}}={info['dmax']:.3f}$")

    # 双星相对轨道插图
    axins = ax.inset_axes([0.10, 0.58, 0.28, 0.28])
    rel = s_d[:, 0, :2] - s_d[:, 1, :2]
    axins.plot(rel[:, 0], rel[:, 1], color="#6a3d9a", lw=0.8)
    axins.set_aspect("equal")
    axins.set_title("1–2 相对轨道", fontsize=7, pad=2)
    axins.tick_params(labelsize=6)
    axins.grid(alpha=0.2)
    axins.set_facecolor("white")
    axins.patch.set_alpha(1.0)

    handles = [Line2D([0], [0], color=c, lw=1.2) for c in STAR_COLORS]
    fig.legend(handles, ["恒星 1", "恒星 2", "恒星 3"], loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIGURES / "fig1_trajectories.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 2: 恒星间距离
# ---------------------------------------------------------------------------
def fig2(data, summary):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 8.4), sharex=False)
    configs = [
        ("A", "模式 A：等边三角形", (0.5, 2.0)),
        ("B", "模式 B：8 字形", (0.4, 3.0)),
        ("C", "模式 C：飞蛾 I", (0.04, 3.0)),
        ("D", "模式 D：层级三体", (0.2, 6.0)),
    ]
    for ax, (key, title, ylim) in zip(axes.ravel(), configs):
        info = summary["modes"][key]
        t = data[f"{key}_t"]
        if key == "A":
            ax.semilogy(t, data["A_d12"], color=MODE_COLORS["A"], lw=1.5,
                        label="$d_{12}=d_{13}=d_{23}=1$（解析）")
        else:
            for j, (p, q) in enumerate([(1, 2), (1, 3), (2, 3)]):
                ax.semilogy(t, data[f"{key}_d{p}{q}"], color=STAR_COLORS[j], lw=0.9,
                            alpha=0.9, label=f"$d_{{{p}{q}}}$")
        add_threshold(ax, ylim)
        ax.set_xlim(0, 50)
        ax.set_xlabel("t")
        ax.set_ylabel("距离")
        ax.set_title(
            f"{title}\n$d_{{\\min}}={info['dmin']:.4f}$，$d_{{\\max}}={info['dmax']:.4f}$"
        )
        ax.legend(loc="lower right", frameon=True, framealpha=0.9, ncol=1 if key == "A" else 3)

    # D: 双星间距放大，显示潮汐引起的小振荡
    ax = axes[1, 1]
    axins = ax.inset_axes([0.14, 0.30, 0.28, 0.26])
    t_d = data["D_t"]
    d12 = data["D_d12"]
    mask = t_d <= 10
    axins.plot(t_d[mask], d12[mask], color=STAR_COLORS[0], lw=0.9)
    axins.set_xlim(0, 10)
    axins.set_ylim(0.395, 0.405)
    axins.set_title("$d_{12}$ 放大", fontsize=7, pad=2)
    axins.tick_params(labelsize=6)
    axins.grid(alpha=0.2)
    axins.set_facecolor("white")
    axins.patch.set_alpha(1.0)

    fig.tight_layout()
    fig.savefig(FIGURES / "fig2_distances.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 3: 扰动前后的轨迹
# ---------------------------------------------------------------------------
def fig3(data, summary):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 9.0))

    # A
    ax = axes[0, 0]
    t_a = data["A_t"]
    s_a = data["A_states"]
    ax.plot(s_a[:, 0, 0], s_a[:, 0, 1], "--", color=GRAY, lw=0.9, label="未扰动（解析圆）")
    t_p = data["A_pert_t"]
    s_p = data["A_pert_states"]
    for i in range(3):
        ax.plot(s_p[:, i, 0], s_p[:, i, 1], color=STAR_COLORS[i], lw=0.9, alpha=0.8,
                label=f"扰动后恒星 {i + 1}")
    ax.scatter(s_p[0, :, 0], s_p[0, :, 1], s=22, c=STAR_COLORS, edgecolor="white", lw=0.5, zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    info = summary["modes"]["A"]["pert"]
    ax.set_title(
        "模式 A：$10^{-4}$ 扰动后三角形瓦解\n"
        f"$t_{{\\rm stop}}={info['t_end']:.2f}$，$d_{{\\min}}={info['dmin']:.4f}$"
    )
    ax.legend(loc="upper left", frameon=False, fontsize=7.5)

    # B/C/D: 只画恒星 1，另外用插图放大扰动位移
    for ax, key in zip([axes[0, 1], axes[1, 0], axes[1, 1]], ["B", "C", "D"]):
        t = data[f"{key}_t"]
        s0 = data[f"{key}_states"]
        tp = data[f"{key}_pert_t"]
        sp = data[f"{key}_pert_states"]
        sp_on = interp_states(sp, tp, t)
        ax.plot(s0[:, 0, 0], s0[:, 0, 1], color=GRAY, lw=1.0, label="未扰动（恒星 1）")
        ax.plot(sp_on[:, 0, 0], sp_on[:, 0, 1], color="#d62728", lw=1.0, ls="--",
                label="扰动后（恒星 1）")
        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        info = summary["modes"][key]
        p = info["pert"]
        ax.set_title(
            f"模式 {key}：扰动前后轨迹\n"
            f"$t_{{\\rm end}}={p['t_end']:.1f}$，$\\delta(50)={p['delta_end']:.2e}$"
        )
        ax.legend(loc="upper right", frameon=False, fontsize=7.5)

        # 插图: 扰动位移 Δr1 (去掉刻度, 只保留形状)
        axins = ax.inset_axes([0.66, 0.10, 0.28, 0.28])
        dr = sp_on[:, 0, :2] - s0[:, 0, :2]
        axins.plot(dr[:, 0], dr[:, 1], color="#d62728", lw=0.8)
        lim = 1.15 * max(np.max(np.abs(dr)), 1e-9)
        axins.set_xlim(-lim, lim)
        axins.set_ylim(-lim, lim)
        axins.set_aspect("equal")
        axins.set_xticks([])
        axins.set_yticks([])
        axins.set_facecolor("white")
        axins.patch.set_alpha(1.0)
        for spine in axins.spines.values():
            spine.set_color("#999999")
            spine.set_linewidth(0.6)
        ax.text(0.02, 0.04, f"$\\Delta r_1$ max = {np.max(np.abs(dr)):.1e}",
                transform=ax.transAxes, fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))

    fig.tight_layout()
    fig.savefig(FIGURES / "fig3_perturbation.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 4: 扰动分离与模式 A 的数值精度
# ---------------------------------------------------------------------------
def fig4(data, summary):
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6))

    ax = axes[0]
    for key in ["A", "B", "C", "D"]:
        t = data[f"{key}_delta_t"]
        delta = data[f"{key}_delta"]
        mask = delta > 0
        ax.semilogy(t[mask], delta[mask], color=MODE_COLORS[key], lw=1.4,
                    label=f"模式 {key}")
    # A 的指数拟合
    info_a = summary["modes"]["A"]["pert"]
    slope = info_a["growth_rate_fit"]
    t_fit = np.linspace(1.0, 7.0, 100)
    # 由 t=1 处的数值确定常数
    t_a = data["A_delta_t"]
    d_a = data["A_delta"]
    d1 = float(np.interp(1.0, t_a, d_a))
    ax.semilogy(t_fit, d1 * np.exp(slope * (t_fit - 1.0)), "k--", lw=0.9,
                label=f"A 拟合 $\\lambda={slope:.2f}$")
    ax.set_xlim(0, 50)
    ax.set_ylim(1e-5, 3)
    ax.set_xlabel("t")
    ax.set_ylabel("$\\delta(t)=\\sqrt{\\sum_i |\\Delta r_i|^2}$")
    ax.set_title("扰动分离随时间的演化")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), frameon=False, ncol=3, fontsize=8)

    ax = axes[1]

    def running_max(t, y, width=0.25):
        """分窗取最大值, 去掉高频振荡, 显示误差包络."""
        edges = np.arange(t[0], t[-1] + width, width)
        idx = np.digitize(t, edges)
        tt, yy = [], []
        for k in range(1, len(edges)):
            mask = idx == k
            if np.any(mask):
                tt.append(float(t[mask].mean()))
                yy.append(float(np.max(y[mask])))
        return np.asarray(tt), np.asarray(yy)

    labels = {"rk4_dt002": "RK4 $\\Delta t=0.002$", "rk4_dt001": "RK4 $\\Delta t=0.001$", "dp45": "自适应 DP45"}
    for tag, style in [
        ("rk4_dt002", dict(color="#1f77b4", ls="-", lw=1.2)),
        ("rk4_dt001", dict(color="#2ca02c", ls="-", lw=1.2)),
        ("dp45", dict(color="#ff7f0e", ls="-", lw=1.2)),
    ]:
        t = data[f"A_num_{tag}_t"]
        dev = data[f"A_num_{tag}_dev"]
        mask = dev > 0
        te, de = running_max(t[mask], dev[mask])
        ax.semilogy(te, np.maximum(de, 1e-16), label=labels[tag], **style)
    # 物理扰动 1e-4 曲线
    ax.semilogy(t_a[d_a > 0], d_a[d_a > 0], color="#d62728", lw=1.4,
                label="物理扰动 $10^{-4}$")
    # 理论增长率参考线
    t_ref = np.linspace(1, 30, 100)
    ax.semilogy(t_ref, 1e-12 * np.exp(1.2247449 * (t_ref - 1)), "k:", lw=1.0,
                label="$e^{1.2247t}$ 参考")
    ax.set_xlim(0, 50)
    ax.set_ylim(1e-14, 3)
    ax.set_xlabel("t")
    ax.set_ylabel("$\\max_i |r_i^{\\rm num}-r_i^{\\rm exact}|$")
    ax.set_title("模式 A：数值误差与物理扰动都被同一不稳定模式放大")
    ax.legend(loc="lower right", frameon=False, fontsize=7.5)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    fig.savefig(FIGURES / "fig4_separation.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 5: 步长与能量误差
# ---------------------------------------------------------------------------
def fig5(data, summary):
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), sharey=False)
    for ax, key in zip(axes, ["B", "C"]):
        for entry in summary["stepsize"][key]:
            tag = entry["tag"]
            t = data[f"step_{key}_{tag}_t"]
            e = data[f"step_{key}_{tag}_energy_rel"]
            stride = max(1, len(t) // 6000)
            label = f"$\\Delta t={entry['dt']:g}$（max {entry['energy_max_rel']:.1e}）"
            ax.semilogy(t[::stride], np.maximum(e[::stride], 1e-16), lw=1.1, label=label)
        ax.set_xlabel("t")
        ax.set_ylabel("$|E(t)-E(0)|/|E(0)|$")
        name = "8 字形" if key == "B" else "飞蛾 I"
        ax.set_title(f"模式 {key}（{name}）：RK4 能量误差")
        ax.set_xlim(0, 50)
        ax.legend(loc="best", frameon=True, framealpha=0.92, fontsize=8)
        ax.grid(True, which="both", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig5_energy_stepsize.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 6: 步长与恒星间距离
# ---------------------------------------------------------------------------
def fig6(data, summary):
    fig, axes = plt.subplots(2, 2, figsize=(10.6, 8.0))
    for col, key in enumerate(["B", "C"]):
        ax = axes[0, col]
        for entry in summary["stepsize"][key]:
            tag = entry["tag"]
            t = data[f"step_{key}_{tag}_t"]
            dmin = data[f"step_{key}_{tag}_dmin"]
            stride = max(1, len(t) // 6000)
            ax.plot(t[::stride], dmin[::stride], lw=1.0, label=f"$\\Delta t={entry['dt']:g}$")
        ax.set_xlim(0, 50)
        ax.set_xlabel("t")
        ax.set_ylabel("$d_{\\min}(t)$")
        name = "8 字形" if key == "B" else "飞蛾 I"
        ax.set_title(f"模式 {key}（{name}）：最小恒星间距离对步长的敏感性")
        ax.legend(loc="best", frameon=True, framealpha=0.92, fontsize=8)

        ax = axes[1, col]
        t_diff = data[f"step_{key}_dt002_t"]
        stride_diff = max(1, len(t_diff) // 6000)
        for entry in summary["stepsize"][key]:
            tag = entry["tag"]
            if tag == "dt002":
                continue
            diff = data[f"step_{key}_{tag}_dmin_diff"]
            ax.semilogy(t_diff[::stride_diff], np.maximum(diff[::stride_diff], 1e-16), lw=1.0,
                        label=f"$\\Delta t={entry['dt']:g}$")
        ax.set_xlim(0, 50)
        ax.set_xlabel("t")
        ax.set_ylabel("$|d_{\\min}-d_{\\min}^{\\Delta t=0.002}|$")
        ax.set_title("与 $\\Delta t=0.002$ 的差")
        ax.legend(loc="best", frameon=True, framealpha=0.92, fontsize=8)
        ax.grid(True, which="both", alpha=0.2)

    # 飞蛾近距离处放大
    axins = axes[0, 1].inset_axes([0.58, 0.08, 0.36, 0.30])
    for entry in summary["stepsize"]["C"]:
        tag = entry["tag"]
        t = data[f"step_C_{tag}_t"]
        dmin = data[f"step_C_{tag}_dmin"]
        mask = (t >= 8.5) & (t <= 11.0)
        axins.plot(t[mask], dmin[mask], lw=1.0)
    axins.set_xlim(8.5, 11.0)
    axins.set_ylim(0.07, 0.35)
    axins.set_title("近距离放大", fontsize=7, pad=2, backgroundcolor="white")
    axins.tick_params(labelsize=6)
    axins.grid(alpha=0.2)
    axins.set_facecolor("white")
    axins.patch.set_alpha(1.0)

    fig.tight_layout()
    fig.savefig(FIGURES / "fig6_distance_stepsize.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 图 7: 候选轨道筛选
# ---------------------------------------------------------------------------
def fig7(data, summary):
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    screening = summary["screening"]
    x = np.array([s["dmin"] for s in screening])
    y = np.array([s["dmax"] for s in screening])
    ax.scatter(x, y, s=38, c="#1f77b4", edgecolor="white", lw=0.6, zorder=4,
               label="已发表候选（Šuvakov 族）")
    labels = {"butterfly I", "moth I", "goggles", "yarn"}
    for s in screening:
        if s["name"] in labels:
            offsets = {"butterfly I": (4, 7), "moth I": (5, 4), "goggles": (4, -11), "yarn": (4, 4)}
            ax.annotate(s["name"], (s["dmin"], s["dmax"]), xytext=offsets.get(s["name"], (4, 4)),
                        textcoords="offset points", fontsize=7.5)
    # 本文模式
    mode_points = {
        "A": (summary["modes"]["A"]["dmin"], summary["modes"]["A"]["dmax"]),
        "B": (summary["modes"]["B"]["dmin"], summary["modes"]["B"]["dmax"]),
        "C": (summary["modes"]["C"]["dmin"], summary["modes"]["C"]["dmax"]),
        "D": (summary["modes"]["D"]["dmin"], summary["modes"]["D"]["dmax"]),
    }
    for key, (xx, yy) in mode_points.items():
        ax.scatter([xx], [yy], marker="*", s=170, color=MODE_COLORS[key],
                   edgecolor="black", lw=0.4, zorder=6)
        ax.annotate(f"{key}", (xx, yy), xytext=(7, -11), textcoords="offset points",
                    fontsize=9, color=MODE_COLORS[key], fontweight="bold")
    ax.scatter([], [], marker="*", s=150, color="#444444", edgecolor="black", lw=0.4,
               label="本文模式 A–D")

    ax.axvspan(0.05, 10, color="#2ca02c", alpha=0.06, lw=0)
    ax.axvline(0.05, color="#d62728", ls="--", lw=1.0, label="$d_{\\min}=0.05$")
    ax.axhline(10, color="#555555", ls=":", lw=1.0, label="$d_{\\max}=10$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.003, 3)
    ax.set_ylim(0.8, 30)
    ax.set_xlabel("最小距离 $d_{\\min}$")
    ax.set_ylabel("最大距离 $d_{\\max}$")
    ax.set_title("候选轨道是否满足 $0.05\\leq d_{ij}<10$")
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=8)
    ax.grid(True, which="both", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig7_screening.png")
    plt.close(fig)


def main():
    data, summary = load()
    fig1(data, summary)
    fig2(data, summary)
    fig3(data, summary)
    fig4(data, summary)
    fig5(data, summary)
    fig6(data, summary)
    fig7(data, summary)
    print("Figures written to", FIGURES)


if __name__ == "__main__":
    main()
