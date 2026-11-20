"""Run all numerical experiments for the three-body assignment.

用法:
    python run_experiments.py

输出:
    results/trajectories.npz   轨迹、距离、扰动分离、步长对比数据
    results/summary.json       所有标量结果
    results/summary.csv        模式汇总表
    results/screening.csv      已发表候选轨道的筛选结果
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from three_body import (
    LAGRANGE_OMEGA,
    Simulation,
    angular_momentum,
    ic_butterfly_i,
    ic_figure_eight,
    ic_hierarchical,
    ic_lagrange,
    ic_moth_i,
    ic_symmetric_row,
    interpolate_states,
    lagrange_exact_trajectory,
    lagrange_force_residual,
    lagrange_growth_rate,
    lagrange_linear_eigenvalues,
    pair_distances,
    perturb,
    simulate,
    total_energy,
    trajectory_separation,
)

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
RESULTS.mkdir(exist_ok=True)

T_MAX = 50.0
CLOSE = 0.05
ESCAPE = 50.0
GRID_DT = 0.005
HIGH_ACC = dict(method="dp45", dt=0.002, max_step=0.005, rtol=1e-13, atol=1e-15)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def storage_grid(t_end: float, dt: float = GRID_DT) -> np.ndarray:
    n = int(np.floor(t_end / dt))
    grid = np.linspace(0.0, n * dt, n + 1)
    if grid[-1] < t_end - 1e-12:
        grid = np.append(grid, t_end)
    return grid


def pack_simulation(prefix: str, sim: Simulation, data: dict, dt: float = GRID_DT) -> np.ndarray:
    """把一条轨迹插值到均匀网格并写入 data, 返回时间网格."""
    t_grid = storage_grid(sim.t_end, dt)
    states = interpolate_states(sim, t_grid)
    data[f"{prefix}_t"] = t_grid
    data[f"{prefix}_states"] = states
    d = np.array([pair_distances(s[:, :2]) for s in states])
    data[f"{prefix}_d12"] = d[:, 0]
    data[f"{prefix}_d13"] = d[:, 1]
    data[f"{prefix}_d23"] = d[:, 2]
    data[f"{prefix}_energy"] = np.array(
        [total_energy(s) for s in states], dtype=float
    )
    return t_grid


def pack_exact_lagrange(data: dict, dt: float = GRID_DT) -> np.ndarray:
    t_grid = storage_grid(T_MAX, dt)
    states = lagrange_exact_trajectory(t_grid)
    data["A_t"] = t_grid
    data["A_states"] = states
    data["A_d12"] = np.ones_like(t_grid)
    data["A_d13"] = np.ones_like(t_grid)
    data["A_d23"] = np.ones_like(t_grid)
    data["A_energy"] = np.full_like(t_grid, -1.5)
    return t_grid


def separation_to_exact(sim: Simulation, t_grid: np.ndarray) -> np.ndarray:
    exact = lagrange_exact_trajectory(t_grid)
    p = interpolate_states(sim, t_grid)
    return np.sqrt(np.sum((p[:, :, :2] - exact[:, :, :2]) ** 2, axis=(1, 2)))


def fit_growth_rate(t: np.ndarray, delta: np.ndarray, t0: float, t1: float) -> float:
    mask = (t >= t0) & (t <= t1) & (delta > 0) & np.isfinite(delta)
    if np.sum(mask) < 5:
        return float("nan")
    slope, _ = np.polyfit(t[mask], np.log(delta[mask]), 1)
    return float(slope)


def summarize_sim(sim: Simulation) -> dict:
    return {
        "t_end": float(sim.t_end),
        "stop_reason": sim.stop_reason,
        "stopped": bool(sim.stopped),
        "dmin": float(sim.min_pair_distance),
        "dmax": float(sim.max_pair_distance),
        "energy0": float(sim.e0),
        "energy_max_abs_error": float(sim.max_energy_error),
        "energy_max_rel_error": float(sim.max_energy_error / abs(sim.e0)),
        "angular_momentum": float(angular_momentum(sim.states[0])),
        "steps": int(sim.step_count),
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    data: dict[str, np.ndarray] = {}
    summary: dict = {
        "meta": {
            "t_max": T_MAX,
            "close_threshold": CLOSE,
            "escape_radius": ESCAPE,
            "storage_grid_dt": GRID_DT,
            "high_accuracy": HIGH_ACC,
        }
    }

    # ---- Lagrange 解析解与线性稳定性 ----
    eigs = lagrange_linear_eigenvalues()
    lagrange_info = {
        "omega": float(LAGRANGE_OMEGA),
        "period": float(2 * np.pi / LAGRANGE_OMEGA),
        "energy": -1.5,
        "angular_momentum": float(np.sqrt(3.0)),
        "growth_rate": float(lagrange_growth_rate()),
        "eigenvalues": [[float(z.real), float(z.imag)] for z in eigs],
        "force_residual_max": float(
            max(lagrange_force_residual(t) for t in np.linspace(0, 50, 501))
        ),
        "circumradius": float(1 / np.sqrt(3.0)),
        "side": 1.0,
    }
    summary["lagrange"] = lagrange_info
    print(
        f"[Lagrange] omega={lagrange_info['omega']:.6f}, "
        f"T={lagrange_info['period']:.6f}, lambda={lagrange_info['growth_rate']:.6f}, "
        f"residual={lagrange_info['force_residual_max']:.2e}"
    )

    # ---- 模式 A: 解析轨道 ----
    pack_exact_lagrange(data)
    summary["modes"] = {}
    summary["modes"]["A"] = {
        "name": "等边三角形旋转（Lagrange）",
        "short": "Lagrange 三角形",
        "structure": "三体保持等边三角形刚性旋转；三对距离恒为 1，C3 对称。",
        "ic": ic_lagrange().tolist(),
        "exact": True,
        "period": float(2 * np.pi / LAGRANGE_OMEGA),
        "t_end": T_MAX,
        "stop_reason": "exact",
        "stopped": False,
        "dmin": 1.0,
        "dmax": 1.0,
        "energy0": -1.5,
        "energy_max_abs_error": 0.0,
        "energy_max_rel_error": 0.0,
        "angular_momentum": float(np.sqrt(3.0)),
        "steps": 0,
    }

    # ---- 模式 B/C/D: 未扰动与扰动 ----
    mode_defs = {
        "B": ("8 字形（figure-eight）", "8 字形", ic_figure_eight(), 6.3259,
              "三颗星沿同一条 8 字曲线依次运动，零角动量；最小距离约 0.69。"),
        "C": ("飞蛾 I（moth I）", "飞蛾 I", ic_moth_i(), 14.8939,
              "Šuvakov–Dmitrašinović 对称族中的 moth 轨道；有一次较近的双星式接近，最小距离约 0.079。"),
        "D": ("层级三体：紧密双星 + 远方第三体", "层级三体", ic_hierarchical(), None,
              "1、2 号星组成间距 0.4 的紧密双星，3 号星在半径约 2.67 的宽轨道上绕系统质心运动；两种时间尺度分离。"),
    }

    for key, (name, short, ic, period, structure) in mode_defs.items():
        print(f"[{key}] {name}: integrating ...")
        sim = simulate(ic, **HIGH_ACC)
        sim_pert = simulate(perturb(ic, 1e-4), **HIGH_ACC)
        pack_simulation(key, sim, data)
        pack_simulation(f"{key}_pert", sim_pert, data)

        t_common = storage_grid(min(sim.t_end, sim_pert.t_end))
        _, delta = trajectory_separation(sim, sim_pert, t_common)
        data[f"{key}_delta_t"] = t_common
        data[f"{key}_delta"] = delta

        info = {
            "name": name,
            "short": short,
            "structure": structure,
            "ic": ic.tolist(),
            "exact": False,
            "period": period,
            **summarize_sim(sim),
        }
        pert_info = {
            "ic": perturb(ic, 1e-4).tolist(),
            **summarize_sim(sim_pert),
            "delta_end": float(delta[-1]),
            "delta_max": float(np.max(delta)),
            "growth_rate_fit": fit_growth_rate(t_common, delta, 1.0, 6.0),
        }
        info["pert"] = pert_info
        summary["modes"][key] = info
        print(
            f"    unpert: t_end={info['t_end']:.2f} {info['stop_reason']:15s} "
            f"dmin={info['dmin']:.5f} dmax={info['dmax']:.5f}"
        )
        print(
            f"    pert  : t_end={pert_info['t_end']:.2f} {pert_info['stop_reason']:15s} "
            f"dmin={pert_info['dmin']:.5f} dmax={pert_info['dmax']:.5f} "
            f"delta_end={pert_info['delta_end']:.2e}"
        )

    # ---- 模式 A 的扰动实验（与解析解比较） ----
    print("[A] perturbed run and exact reference ...")
    ic_a = ic_lagrange()
    sim_a_pert = simulate(perturb(ic_a, 1e-4), **HIGH_ACC)
    pack_simulation("A_pert", sim_a_pert, data)
    t_a = storage_grid(sim_a_pert.t_end)
    delta_a = separation_to_exact(sim_a_pert, t_a)
    data["A_delta_t"] = t_a
    data["A_delta"] = delta_a

    # 扰动增长拟合 (取非线性饱和前)
    fit_a = fit_growth_rate(t_a, delta_a, 1.0, 6.0)
    summary["modes"]["A"]["pert"] = {
        "ic": perturb(ic_a, 1e-4).tolist(),
        **summarize_sim(sim_a_pert),
        "delta_end": float(delta_a[-1]),
        "delta_max": float(np.max(delta_a)),
        "growth_rate_fit": fit_a,
    }
    print(
        f"    pert: t_end={sim_a_pert.t_end:.2f} {sim_a_pert.stop_reason} "
        f"dmin={sim_a_pert.min_pair_distance:.5f} dmax={sim_a_pert.max_pair_distance:.5f} "
        f"delta_end={delta_a[-1]:.2e} fit_lambda={fit_a:.3f}"
    )

    # 未扰动数值积分与解析解的偏差 (说明双精度限制)
    print("[A] numerical precision runs ...")
    summary["modes"]["A"]["numerical_precision"] = {}
    for tag, kwargs in [
        ("rk4_dt002", dict(method="rk4", dt=0.002)),
        ("rk4_dt001", dict(method="rk4", dt=0.001)),
        ("dp45", dict(method="dp45", dt=0.002, max_step=0.005, rtol=1e-13, atol=1e-15)),
    ]:
        sim_num = simulate(ic_a, t_max=T_MAX, **kwargs)
        t_grid = storage_grid(sim_num.t_end)
        dev = separation_to_exact(sim_num, t_grid)
        data[f"A_num_{tag}_t"] = t_grid
        data[f"A_num_{tag}_dev"] = dev
        data[f"A_num_{tag}_energy_rel"] = np.abs(
            np.array([total_energy(s) for s in interpolate_states(sim_num, t_grid)])
            - sim_num.e0
        ) / abs(sim_num.e0)
        summary["modes"]["A"]["numerical_precision"][tag] = {
            **summarize_sim(sim_num),
            "dev_at": {
                str(tt): float(dev[np.searchsorted(t_grid, tt)])
                for tt in (5, 10, 15, 20, 25, 30, 35, 40, 45, 50)
                if tt <= t_grid[-1]
            },
        }
        print(
            f"    {tag:10s}: t_end={sim_num.t_end:.2f} {sim_num.stop_reason:15s} "
            f"dev(20)={dev[np.searchsorted(t_grid, 20)]:.2e} "
            f"dev(30)={dev[np.searchsorted(t_grid, 30)] if t_grid[-1] >= 30 else float('nan'):.2e}"
        )

    # ---- 步长与能量误差 ----
    print("[stepsize] RK4 dt = 0.002, 0.001, 0.0005 ...")
    summary["stepsize"] = {}
    step_modes = {"B": ic_figure_eight(), "C": ic_moth_i()}
    for key, ic in step_modes.items():
        sims = {}
        entries = []
        for dt, tag in [(0.002, "dt002"), (0.001, "dt001"), (0.0005, "dt0005")]:
            sim = simulate(ic, dt=dt, method="rk4", t_max=T_MAX)
            sims[tag] = sim
            d = np.array([pair_distances(s[:, :2]) for s in sim.states])
            dmin_series = d.min(axis=1)
            energy_rel = np.abs(sim.energies - sim.e0) / abs(sim.e0)
            data[f"step_{key}_{tag}_t"] = sim.t
            data[f"step_{key}_{tag}_dmin"] = dmin_series
            data[f"step_{key}_{tag}_energy_rel"] = energy_rel
            entries.append(
                {
                    "dt": dt,
                    "tag": tag,
                    "t_end": float(sim.t_end),
                    "stop_reason": sim.stop_reason,
                    "dmin": float(sim.min_pair_distance),
                    "dmax": float(sim.max_pair_distance),
                    "energy_max_abs": float(sim.max_energy_error),
                    "energy_max_rel": float(sim.max_energy_error / abs(sim.e0)),
                    "steps": int(sim.step_count),
                }
            )
            print(
                f"    {key} dt={dt:g}: dmin={sim.min_pair_distance:.6f} "
                f"dmax={sim.max_pair_distance:.6f} "
                f"Eerr_rel={sim.max_energy_error/abs(sim.e0):.3e}"
            )

        # 在 dt=0.002 的公共时间网格上比较 (两者时间点严格对齐, 不做插值)
        ref = sims["dt002"]
        ref_dmin = data[f"step_{key}_dt002_dmin"]
        for entry in entries:
            tag = entry["tag"]
            stride = int(round(0.002 / entry["dt"]))
            states = sims[tag].states[::stride]
            t_common = sims[tag].t[::stride]
            if len(states) != len(ref.states) or not np.allclose(t_common, ref.t):
                raise RuntimeError("step-size grids are not aligned")
            dpos = states[:, :, :2] - ref.states[:, :, :2]
            dvel = states[:, :, 2:] - ref.states[:, :, 2:]
            pos_diff = np.sqrt(np.sum(dpos * dpos, axis=(1, 2)))
            vel_diff = np.sqrt(np.sum(dvel * dvel, axis=(1, 2)))
            dmin_on = data[f"step_{key}_{tag}_dmin"][::stride]
            dmin_diff = np.abs(dmin_on - ref_dmin)
            data[f"step_{key}_{tag}_traj_diff"] = pos_diff
            data[f"step_{key}_{tag}_vel_diff"] = vel_diff
            data[f"step_{key}_{tag}_dmin_diff"] = dmin_diff
            entry["traj_diff_max"] = float(np.max(pos_diff))
            entry["vel_diff_max"] = float(np.max(vel_diff))
            entry["dmin_diff_max"] = float(np.max(dmin_diff))
        summary["stepsize"][key] = entries

    # ---- 已发表候选轨道筛选 ----
    print("[screening] published symmetric-family orbits ...")
    candidates = [
        ("butterfly I", 0.30689, 0.12551, 6.2356),
        ("butterfly II", 0.39295, 0.09758, 7.0039),
        ("bumblebee", 0.18428, 0.58719, 63.5345),
        ("moth I", 0.46444, 0.39606, 14.8939),
        ("moth II", 0.43917, 0.45297, 28.6703),
        ("butterfly III", 0.40592, 0.23016, 13.8658),
        ("moth III", 0.38344, 0.37736, 25.8406),
        ("goggles", 0.08330, 0.12789, 10.4668),
        ("butterfly IV", 0.350112, 0.07934, 79.4759),
        ("dragonfly", 0.08058, 0.58884, 21.2710),
        ("yarn", 0.55906, 0.34919, 55.5018),
        ("yin-yang I a", 0.51394, 0.30474, 17.3284),
        ("yin-yang I b", 0.28270, 0.32721, 10.9626),
        ("yin-yang II a", 0.41682, 0.33033, 55.7898),
        ("yin-yang II b", 0.41734, 0.31310, 54.2076),
    ]
    screening = []
    for name, vx, vy, period in candidates:
        ic = ic_symmetric_row(vx, vy)
        t_run = min(period, T_MAX)
        sim = simulate(
            ic,
            dt=0.002,
            method="dp45",
            t_max=t_run,
            max_step=0.01,
            rtol=1e-11,
            atol=1e-13,
            close_threshold=0.0,
            escape_radius=1e9,
        )
        valid = (sim.min_pair_distance >= CLOSE) and (sim.max_pair_distance < 10.0)
        screening.append(
            {
                "name": name,
                "vx": vx,
                "vy": vy,
                "period": period,
                "t_run": float(sim.t_end),
                "dmin": float(sim.min_pair_distance),
                "dmax": float(sim.max_pair_distance),
                "valid": bool(valid),
            }
        )
        print(
            f"    {name:16s} dmin={sim.min_pair_distance:.5f} "
            f"dmax={sim.max_pair_distance:.5f} valid={valid}"
        )
    summary["screening"] = screening
    with (RESULTS / "screening.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(screening[0].keys()))
        writer.writeheader()
        writer.writerows(screening)

    # ---- 保存 ----
    np.savez_compressed(RESULTS / "trajectories.npz", **data)
    with (RESULTS / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 模式汇总 CSV
    rows = []
    for key, info in summary["modes"].items():
        rows.append(
            {
                "mode": key,
                "name": info["name"],
                "t_end": info["t_end"],
                "stop_reason": info["stop_reason"],
                "dmin": info["dmin"],
                "dmax": info["dmax"],
                "energy0": info["energy0"],
                "energy_max_rel_error": info["energy_max_rel_error"],
                "angular_momentum": info["angular_momentum"],
                "pert_dmin": info["pert"]["dmin"],
                "pert_dmax": info["pert"]["dmax"],
                "pert_t_end": info["pert"]["t_end"],
                "pert_stop_reason": info["pert"]["stop_reason"],
                "delta_end": info["pert"]["delta_end"],
            }
        )
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved:")
    for path in [RESULTS / "trajectories.npz", RESULTS / "summary.json", RESULTS / "summary.csv", RESULTS / "screening.csv"]:
        print("  ", path)


if __name__ == "__main__":
    main()
