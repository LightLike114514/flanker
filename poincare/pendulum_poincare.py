#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""受迫、阻尼、非线性摆：庞加莱截面、步长检验与分形结构（单文件版）

模型
----
    dθ/dt = ω
    dω/dt = -(g/ℓ) sinθ - q ω + F_D sin(Ω_D t)

数值方法
--------
Euler–Cromer 积分；每步把 θ 约化到 [-π, π]；每个驱动周期用
“整数个整步 + 一个尾步”使采样严格落在 t_n = nT_D。

运行
----
    python pendulum_poincare.py            # 生成全部图与数据（约 2–3 分钟）
    python pendulum_poincare.py --quick    # 快速自检（约 5 秒，结果写入 figures_quick/）

输出
----
    figures/fig1_poincare_ic.png   三组初值的庞加莱截面
    figures/fig2_timestep.png      Δt = 0.04 / 0.02 / 0.01 对比
    figures/fig3_zoom.png          全局截面 + 三级局部放大
    figures/fig3_zoom1..3.png      各级放大单独保存
    figures/fig4_boxcount.png      盒计数与局部斜率
    figures/fig5_dt_zoom.png       局部细结构随步长的变化
    data/summary.json              全部数值指标
    data/poincare_*.npz            高分辨率截面数据
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time

import numpy as np

# ---------------------------------------------------------------------------
# 模型参数（教材中的典型混沌参数组）
# ---------------------------------------------------------------------------
G = 9.8
L = 9.8
Q = 0.5
FD = 1.2
OMEGA_D = 2.0 / 3.0
T_D = 2.0 * math.pi / OMEGA_D          # = 3π ≈ 9.42478

PI = math.pi
TWOPI = 2.0 * math.pi

INITIAL_CONDITIONS = [(0.2, 0.0), (0.8, 0.0), (-1.0, 0.5)]
IC_LABELS = [
    r"$(\theta_0,\omega_0)=(0.2,\ 0)$",
    r"$(\theta_0,\omega_0)=(0.8,\ 0)$",
    r"$(\theta_0,\omega_0)=(-1.0,\ 0.5)$",
]


# ---------------------------------------------------------------------------
# Euler–Cromer 积分器
# ---------------------------------------------------------------------------
def integrate_periods(theta0, omega0, dt, n_periods, discard_periods=0):
    """积分 n_periods 个驱动周期，返回每个周期末的 (θ, ω)。

    每个周期分成 n_full 个长度为 dt 的整步，再加一个长度
    h = T_D - n_full*dt 的尾步，使采样严格发生在 t = n*T_D，
    避免插值平滑掉截面的细丝结构。
    """
    n_full = int(T_D // dt)
    h_last = T_D - n_full * dt
    if h_last < 1e-12:                 # dt 恰好整除 T_D 的退化情形
        n_full -= 1
        h_last = T_D - n_full * dt

    sin = math.sin
    theta, omega, t = float(theta0), float(omega0), 0.0
    gl, q, fd, om = G / L, Q, FD, OMEGA_D

    out_theta = np.empty(max(n_periods - discard_periods, 0))
    out_omega = np.empty_like(out_theta)
    k = 0

    for n in range(1, n_periods + 1):
        for _ in range(n_full):
            alpha = -gl * sin(theta) - q * omega + fd * sin(om * t)
            omega += alpha * dt
            theta += omega * dt
            if theta > PI:
                theta -= TWOPI
            elif theta < -PI:
                theta += TWOPI
            t += dt

        # 尾步：精确落在 t = n*T_D
        alpha = -gl * sin(theta) - q * omega + fd * sin(om * t)
        omega += alpha * h_last
        theta += omega * h_last
        if theta > PI:
            theta -= TWOPI
        elif theta < -PI:
            theta += TWOPI
        t = n * T_D                    # 消除浮点累积漂移

        if n > discard_periods:
            out_theta[k] = theta
            out_omega[k] = omega
            k += 1

    return out_theta, out_omega


def largest_lyapunov(theta0, omega0, dt, n_periods, delta0=1e-9):
    """两条相邻轨道的分离增长率，每周期重正化，得到 λ_max。"""
    theta_a, omega_a = float(theta0), float(omega0)
    theta_b, omega_b = float(theta0) + delta0, float(omega0)

    n_full = int(T_D // dt)
    h_last = T_D - n_full * dt
    if h_last < 1e-12:
        n_full -= 1
        h_last = T_D - n_full * dt

    sin = math.sin
    gl, q, fd, om = G / L, Q, FD, OMEGA_D

    def advance(theta, omega, t):
        for _ in range(n_full):
            alpha = -gl * sin(theta) - q * omega + fd * sin(om * t)
            omega += alpha * dt
            theta += omega * dt
            if theta > PI:
                theta -= TWOPI
            elif theta < -PI:
                theta += TWOPI
            t += dt
        alpha = -gl * sin(theta) - q * omega + fd * sin(om * t)
        omega += alpha * h_last
        theta += omega * h_last
        if theta > PI:
            theta -= TWOPI
        elif theta < -PI:
            theta += TWOPI
        return theta, omega

    total = 0.0
    for n in range(1, n_periods + 1):
        t = (n - 1) * T_D
        theta_a, omega_a = advance(theta_a, omega_a, t)
        theta_b, omega_b = advance(theta_b, omega_b, t)

        dtheta = (theta_b - theta_a + PI) % TWOPI - PI
        domega = omega_b - omega_a
        dist = math.hypot(dtheta, domega)
        if dist == 0.0:
            break
        total += math.log(dist / delta0)
        theta_b = theta_a + dtheta * (delta0 / dist)
        omega_b = omega_a + domega * (delta0 / dist)

    return total / (n_periods * T_D)


# ---------------------------------------------------------------------------
# 截面统计
# ---------------------------------------------------------------------------
def box_count(x, y, window, epsilons):
    """用边长 ε 的正方形网格覆盖窗口，返回非空格子数 N(ε)。"""
    x0, x1, y0, y1 = window
    m = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    x, y = x[m], y[m]
    counts = []
    for eps in epsilons:
        nx = max(int(math.ceil((x1 - x0) / eps)), 1)
        ny = max(int(math.ceil((y1 - y0) / eps)), 1)
        hist, _, _ = np.histogram2d(x, y, bins=(nx, ny),
                                    range=((x0, x1), (y0, y1)))
        counts.append(int(np.count_nonzero(hist)))
    return np.asarray(counts, dtype=float)


def section_overlap(x1, y1, x2, y2, window, bins=(120, 120)):
    """两个截面点集的粗粒化重叠度（Bhattacharyya 系数，0..1）。"""
    x0, x1_, y0, y1_ = window
    h1, _, _ = np.histogram2d(x1, y1, bins=bins, range=((x0, x1_), (y0, y1_)))
    h2, _, _ = np.histogram2d(x2, y2, bins=bins, range=((x0, x1_), (y0, y1_)))
    p = h1.ravel() / h1.sum()
    qv = h2.ravel() / h2.sum()
    return float(np.sum(np.sqrt(p * qv)))


def nearest_distance(a, b, n_a=1200, n_b=3000, seed=0):
    """a 中点到 b 点集的最近邻距离中位数（用于比较细丝位置）。"""
    A = np.column_stack(a)
    B = np.column_stack(b)
    rng = np.random.default_rng(seed)
    if len(A) > n_a:
        A = A[rng.choice(len(A), n_a, replace=False)]
    if len(B) > n_b:
        B = B[rng.choice(len(B), n_b, replace=False)]
    d = np.empty(len(A))
    for i in range(0, len(A), 100):
        blk = A[i:i + 100]
        d[i:i + 100] = np.min(
            np.hypot(blk[:, None, 0] - B[None, :, 0],
                     blk[:, None, 1] - B[None, :, 1]), axis=1)
    return float(np.median(d))


def stats(th, om):
    return {"mean_theta": float(th.mean()), "std_theta": float(th.std()),
            "mean_omega": float(om.mean()), "std_omega": float(om.std())}


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------
def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": ["Times New Roman", "SimSun"],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "font.size": 10.5,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "legend.fontsize": 9,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "axes.linewidth": 0.8,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
    })
    return plt


def poincare_axes(ax, title=None):
    ax.set_xlim(-PI, PI)
    ax.set_ylim(-2.6, 2.6)
    ax.set_xlabel(r"$\theta$ (rad)")
    ax.set_ylabel(r"$\omega$ (rad s$^{-1}$)")
    ax.set_xticks([-PI, -PI / 2, 0, PI / 2, PI])
    ax.set_xticklabels([r"$-\pi$", r"$-\pi/2$", "0", r"$\pi/2$", r"$\pi$"])
    if title:
        ax.set_title(title)


def plot_initial_conditions(sections, outdir, plt):
    """图 1：三组初值的截面 + 叠加。"""
    keys = list(sections)
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.6))
    for ax, key, lab in zip(axes.ravel()[:3], keys, IC_LABELS):
        th, om = sections[key]
        ax.plot(th, om, ".", ms=1.1, color="#1f4e9c", alpha=0.75,
                markeredgewidth=0)
        poincare_axes(ax, lab)
        ax.text(0.04, 0.94, f"$N={len(th)}$", transform=ax.transAxes,
                va="top", fontsize=9)

    ax = axes.ravel()[3]
    colors = ["#1f4e9c", "#c0392b", "#1e8449"]
    for key, lab, c in zip(keys, IC_LABELS, colors):
        th, om = sections[key]
        ax.plot(th, om, ".", ms=1.0, color=c, alpha=0.55,
                markeredgewidth=0, label=lab)
    poincare_axes(ax, "三组初值叠加")
    ax.legend(loc="upper right", markerscale=6, frameon=False,
              handletextpad=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig1_poincare_ic.png"))
    plt.close(fig)


def plot_timestep(step_sections, dts, outdir, plt):
    """图 2：Δt = 0.04 / 0.02 / 0.01 的截面。"""
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.5),
                            sharex=True, sharey=True)
    for ax, dt in zip(axes, dts):
        th, om = step_sections[dt]
        ax.plot(th, om, ".", ms=1.0, color="#1f4e9c", alpha=0.7,
                markeredgewidth=0)
        poincare_axes(ax, rf"$\Delta t={dt}$")
        ax.text(0.04, 0.94, f"$N={len(th)}$", transform=ax.transAxes,
                va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig2_timestep.png"))
    plt.close(fig)


def plot_timestep_fine(fine, outdir, plt, win):
    """图 5：同一局部区域在三种步长下的细结构。"""
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.6),
                            sharex=True, sharey=True)
    for ax, (dt, (th, om)) in zip(axes, fine.items()):
        m = ((th >= win[0]) & (th <= win[1]) &
             (om >= win[2]) & (om <= win[3]))
        ax.plot(th[m], om[m], ".", ms=1.1, color="#1f4e9c", alpha=0.65,
                markeredgewidth=0)
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_xlabel(r"$\theta$ (rad)")
        if ax is axes[0]:
            ax.set_ylabel(r"$\omega$ (rad s$^{-1}$)")
        ax.set_title(f"Δt = {dt}（N = {int(m.sum()):,}）", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig5_dt_zoom.png"))
    plt.close(fig)


def plot_zoom(th, om, outdir, plt, wins):
    """图 3：全局截面 + 三级局部放大，返回各级点数。"""
    from matplotlib.patches import Rectangle

    def mask_of(win):
        return ((th >= win[0]) & (th <= win[1]) &
                (om >= win[2]) & (om <= win[3]))

    masks = [mask_of(w) for w in wins]

    fig = plt.figure(figsize=(9.8, 8.9))
    gs = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.27)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    # (a) 全局
    ax0.plot(th, om, ".", ms=0.25, color="#1f4e9c", alpha=0.35,
             markeredgewidth=0, rasterized=True)
    poincare_axes(ax0)
    ax0.set_title(f"全局截面（N = {len(th):,}）", fontsize=10)
    w1 = wins[0]
    ax0.add_patch(Rectangle((w1[0], w1[2]), w1[1] - w1[0], w1[3] - w1[2],
                            fill=False, ec="#c0392b", lw=1.0))
    ax0.annotate("1 级放大", xy=(w1[0], w1[3]), xytext=(1.15, -0.05),
                 color="#c0392b", fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.7))

    # (b)–(d) 逐级放大
    specs = [
        (ax1, 0, 0.8, 0.55,
         f"1 级：{wins[0][0]:.2f}≤θ≤{wins[0][1]:.2f}，"
         f"{wins[0][2]:.2f}≤ω≤{wins[0][3]:.2f}（N={int(masks[0].sum()):,}）", 1),
        (ax2, 1, 1.2, 0.7,
         f"2 级：{wins[1][0]:.2f}≤θ≤{wins[1][1]:.2f}，"
         f"{wins[1][2]:.2f}≤ω≤{wins[1][3]:.2f}（N={int(masks[1].sum()):,}）", 2),
        (ax3, 2, 1.6, 0.8,
         f"3 级：{wins[2][0]:.3f}≤θ≤{wins[2][1]:.3f}，"
         f"{wins[2][2]:.3f}≤ω≤{wins[2][3]:.3f}（N={int(masks[2].sum())}）", None),
    ]
    for ax, idx, ms, alpha, title, nxt in specs:
        win, m = wins[idx], masks[idx]
        ax.plot(th[m], om[m], ".", ms=ms, color="#1f4e9c",
                alpha=alpha, markeredgewidth=0)
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_xlabel(r"$\theta$ (rad)", fontsize=10)
        ax.set_ylabel(r"$\omega$ (rad s$^{-1}$)", fontsize=10)
        ax.tick_params(labelsize=9)
        ax.set_title(title, fontsize=8.5, pad=4)
        if nxt is not None:
            nw = wins[nxt]
            ax.add_patch(Rectangle((nw[0], nw[2]), nw[1] - nw[0],
                                   nw[3] - nw[2], fill=False,
                                   ec="#c0392b", lw=1.0))

    for ax, tag in zip([ax0, ax1, ax2, ax3], ["(a)", "(b)", "(c)", "(d)"]):
        ax.text(0.035, 0.955, tag, transform=ax.transAxes, va="top",
                fontsize=11, fontweight="bold")

    fig.savefig(os.path.join(outdir, "fig3_zoom.png"))
    plt.close(fig)

    # 各级放大单独保存
    for tag, win, m, ms in zip(["zoom1", "zoom2", "zoom3"],
                               wins, masks, [0.8, 1.3, 1.8]):
        fig, ax = plt.subplots(figsize=(4.6, 4.0))
        ax.plot(th[m], om[m], ".", ms=ms, color="#1f4e9c",
                alpha=0.7, markeredgewidth=0)
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_xlabel(r"$\theta$ (rad)")
        ax.set_ylabel(r"$\omega$ (rad s$^{-1}$)")
        ax.set_title(f"$N={int(m.sum())}$", fontsize=9)
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, f"fig3_{tag}.png"))
        plt.close(fig)

    return [int(m.sum()) for m in masks]


def plot_boxcount(th, om, win, outdir, plt, quick=False):
    """图 4：盒计数 log N–log(1/ε) 与局部斜率，返回 (ε, N, D_B, R²)。"""
    if quick:
        eps = np.array([0.2, 0.1, 0.05, 0.025, 0.0125])
        fit = eps <= 0.05
    else:
        eps = np.array([0.05, 0.025, 0.0125, 0.00625,
                        0.003125, 0.0015625, 0.00078125])
        fit = eps <= 0.0125
    N = box_count(th, om, win, eps)
    x_fit = np.log(1.0 / eps[fit])
    y_fit = np.log(N[fit])
    slope, intercept = np.polyfit(x_fit, y_fit, 1)
    pred = slope * x_fit + intercept
    r2 = 1.0 - np.sum((y_fit - pred) ** 2) / np.sum(
        (y_fit - y_fit.mean()) ** 2)

    x = np.log(1.0 / eps)
    y = np.log(N)

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.9),
                             gridspec_kw={"width_ratios": [1.12, 1.0]})
    ax = axes[0]
    ax.plot(x[fit], y[fit], "o", ms=5.5, color="#1f4e9c", label="参与拟合")
    ax.plot(x[~fit], y[~fit], "o", ms=5.5, mfc="none", color="#7f8c8d",
            label="未参与拟合")
    xx = np.linspace(x_fit.min(), x_fit.max(), 50)
    ax.plot(xx, slope * xx + intercept, "-", color="#c0392b", lw=1.2,
            label=rf"$D_B={slope:.2f}$")
    ax.set_xlabel(r"$\log(1/\varepsilon)$")
    ax.set_ylabel(r"$\log N(\varepsilon)$")
    ax.set_title("盒计数（1 级放大区）")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.25, lw=0.5)

    ax = axes[1]
    ax.axhline(1.0, color="k", lw=0.6, ls="--")
    ax.plot(0.5 * (x[:-1] + x[1:]), np.diff(y) / np.diff(x), "s-",
            ms=4.5, lw=1.0, color="#1e8449")
    ax.set_xlabel(r"$\log(1/\varepsilon)$")
    ax.set_ylabel("局部斜率")
    ax.set_title("局部斜率随尺度的变化")
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig4_boxcount.png"))
    plt.close(fig)

    return eps, N, float(slope), float(r2)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="快速测试（点数较少）")
    parser.add_argument("--outdir", default="figures", help="图件输出目录")
    args = parser.parse_args()

    quick = args.quick
    if quick and args.outdir == "figures":
        args.outdir = "figures_quick"      # 快速模式不覆盖正式图件

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    plt = setup_matplotlib()
    t_start = time.time()

    dt_main = 0.04 if quick else 0.01
    n_keep = 600 if quick else 2000
    n_discard = 300
    n_total = n_discard + n_keep

    # ---------------- (1) 三组初值的庞加莱截面 ----------------
    sections = {}
    for th0, om0 in INITIAL_CONDITIONS:
        th, om = integrate_periods(th0, om0, dt_main, n_total, n_discard)
        sections[(th0, om0)] = (th, om)
        print(f"IC ({th0}, {om0}): {len(th)} points, "
              f"θ∈[{th.min():.3f}, {th.max():.3f}], "
              f"ω∈[{om.min():.3f}, {om.max():.3f}]")

    keys = list(sections)
    overlaps_ic = {}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = sections[keys[i]], sections[keys[j]]
            overlaps_ic[f"{keys[i]} vs {keys[j]}"] = section_overlap(
                a[0], a[1], b[0], b[1], (-PI, PI, -2.6, 2.6))
    plot_initial_conditions(sections, args.outdir, plt)
    print("图 1 完成")

    # ---------------- (2) 时间步长检验 ----------------
    dts = [0.04, 0.02, 0.01]
    step_sections = {}
    for dt in dts:
        step_sections[dt] = integrate_periods(0.2, 0.0, dt, n_total, n_discard)
    plot_timestep(step_sections, dts, args.outdir, plt)
    print("图 2 完成")

    overlaps_dt = {}
    for i in range(len(dts)):
        for j in range(i + 1, len(dts)):
            a, b = step_sections[dts[i]], step_sections[dts[j]]
            overlaps_dt[f"{dts[i]} vs {dts[j]}"] = section_overlap(
                a[0], a[1], b[0], b[1], (-PI, PI, -2.6, 2.6))

    # ---------------- 高分辨率截面 ----------------
    n_hr = 6000 if quick else 600000
    th_hr, om_hr = integrate_periods(0.2, 0.0, 0.01,
                                     n_discard + n_hr, n_discard)
    if not quick:
        np.savez_compressed("data/poincare_hr.npz",
                            theta=th_hr, omega=om_hr)
    print(f"高分辨率截面：{len(th_hr)} 点")

    # ---------------- (3) 全局图与三级放大 ----------------
    win1 = (2.00, 2.70, -1.50, -0.30)     # θ>2 的带状区域
    win2 = (2.14, 2.22, -1.31, -1.24)     # “发卡”回折处
    win3 = (2.160, 2.175, -1.293, -1.281)  # 束内亚结构
    zoom_counts = plot_zoom(th_hr, om_hr, args.outdir, plt,
                            [win1, win2, win3])
    print(f"图 3 完成：N = {zoom_counts}")

    # ---------------- (4) 盒计数维数 ----------------
    eps, N, d_box, r2 = plot_boxcount(th_hr, om_hr, win1, args.outdir, plt,
                                      quick=quick)
    print(f"图 4 完成：D_B = {d_box:.3f}（R2 = {r2:.4f}）")

    # ---------------- 细结构的时间步长比较 ----------------
    n_fine = 3000 if quick else 300000
    fine = {}
    for dt in (0.04, 0.02):
        fine[dt] = integrate_periods(0.2, 0.0, dt,
                                     n_discard + n_fine, n_discard)
        if not quick:
            np.savez_compressed(f"data/poincare_dt{dt}.npz",
                                theta=fine[dt][0], omega=fine[dt][1])
    fine[0.01] = (th_hr, om_hr)
    plot_timestep_fine(fine, args.outdir, plt, win2)
    print("图 5 完成")

    # 用 Δt=0.04、0.02 的数据复核盒维数
    fit = eps <= (0.05 if quick else 0.0125)
    d_box_dt = {}
    for dt in (0.04, 0.02):
        Nd = box_count(fine[dt][0], fine[dt][1], win1, eps)
        d_box_dt[dt] = float(np.polyfit(np.log(1.0 / eps[fit]),
                                        np.log(Nd[fit]), 1)[0])
    print(f"盒维数随步长：{d_box_dt}")

    def in_win(th, om, win):
        m = ((th >= win[0]) & (th <= win[1]) &
             (om >= win[2]) & (om <= win[3]))
        return th[m], om[m]

    th_ref, om_ref = in_win(th_hr, om_hr, win2)
    nn_dt = {}
    for dt in (0.04, 0.02):
        th, om = in_win(*fine[dt], win2)
        nn_dt[dt] = nearest_distance((th, om), (th_ref, om_ref))
    print(f"细丝最近邻中位数：{nn_dt}")

    # ---------------- 最大 Lyapunov 指数 ----------------
    lyap = largest_lyapunov(0.2, 0.0, 0.01, 1200)
    lam1_map = lyap * T_D
    lam2_map = -Q * T_D - lam1_map
    dky = 1.0 + lam1_map / abs(lam2_map)
    print(f"lambda_max = {lyap:.4f}，D_KY = {dky:.3f}")

    # ---------------- 汇总 ----------------
    summary = {
        "params": {"g": G, "l": L, "q": Q, "F_D": FD,
                   "Omega_D": OMEGA_D, "T_D": T_D},
        "dt_main": dt_main, "n_keep": n_keep, "n_discard": n_discard,
        "overlaps_ic": overlaps_ic,
        "stats_ic": {str(k): stats(*v) for k, v in sections.items()},
        "overlaps_dt": overlaps_dt,
        "stats_dt": {str(k): stats(*v) for k, v in step_sections.items()},
        "box_eps": eps.tolist(), "box_N": N.astype(int).tolist(),
        "D_box": d_box, "D_box_R2": r2,
        "D_box_dt": {str(k): v for k, v in d_box_dt.items()},
        "lambda_max": float(lyap), "lambda_1_map": float(lam1_map),
        "lambda_2_map": float(lam2_map), "D_KY": float(dky),
        "nearest_dt": {str(k): v for k, v in nn_dt.items()},
        "zoom1_points": zoom_counts[0], "zoom2_points": zoom_counts[1],
        "zoom3_points": zoom_counts[2],
        "runtime_s": time.time() - t_start,
    }
    summary_path = ("data/summary_quick.json" if quick else "data/summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"完成，用时 {time.time() - t_start:.1f} s")


if __name__ == "__main__":
    main()
