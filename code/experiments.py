"""运行全部数值实验, 保存可复现的数据。

用法:  python code/experiments.py
输出:  results/results.json, results/*.csv, results/u_task1.npy
"""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import sor2d

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

TOL = 1e-6
MAX_SWEEPS = 200_000


def jsonable(obj):
    """递归地把 numpy 类型转换为 Python 原生类型。"""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


# ---------------------------------------------------------------------------
# 带缓存的求解器, 保证同一组参数只算一次
# ---------------------------------------------------------------------------
_cache: dict[tuple, sor2d.SORResult] = {}


def solve(N, m, omega, tol=TOL, max_sweeps=MAX_SWEEPS, record_history=False):
    key = (N, round(m, 6), round(omega, 6), tol, max_sweeps, record_history)
    if key not in _cache:
        _cache[key] = sor2d.solve_sor(
            N,
            m,
            omega,
            tol=tol,
            max_sweeps=max_sweeps,
            record_history=record_history,
        )
    return _cache[key]


def scan(N, m, omegas, tol=TOL):
    rows = []
    for omega in omegas:
        r = solve(N, m, float(omega), tol=tol)
        rows.append(
            {
                "omega": round(float(omega), 6),
                "K": r.sweeps,
                "residual": r.residual,
                "converged": r.converged,
            }
        )
    return rows


def plateau(rows):
    """返回最小迭代次数对应的连通平台: (omega_lo, omega_hi, Kmin, mid)。"""
    kmin = min(row["K"] for row in rows)
    omegas = sorted(row["omega"] for row in rows if row["K"] == kmin)
    # 只保留相邻扫描点构成的连通段 (以最小间隔判定)
    gaps = np.diff(omegas)
    step = np.min(gaps) if len(gaps) else 0.0
    groups = [[omegas[0]]]
    for a, b in zip(omegas[:-1], omegas[1:]):
        if b - a <= step * 1.5 + 1e-9:
            groups[-1].append(b)
        else:
            groups.append([b])
    group = max(groups, key=len)
    return group[0], group[-1], kmin, 0.5 * (group[0] + group[-1])


def best_row(rows):
    kmin = min(row["K"] for row in rows)
    candidates = [row for row in rows if row["K"] == kmin]
    return min(candidates, key=lambda row: row["omega"]), kmin


# ---------------------------------------------------------------------------
# 响应指标
# ---------------------------------------------------------------------------
def symmetric_profile(u, i0, j0, N):
    """沿水平方向关于源点对称化的截面 u(i0, j0+k) (k=0,1,...)。

    i0, j0 为完整数组中的指标 (内部格点 1..N), N 为内部格点数。
    """
    kmax = min(j0 - 1, N - j0)
    k = np.arange(0, kmax + 1)
    prof = 0.5 * (u[i0, j0 + k] + u[i0, j0 - k])
    return k, prof


def decay_metrics(u, i0, j0, N):
    k, prof = symmetric_profile(u, i0, j0, N)
    norm = prof / prof[0]

    def crossing(level, start=1):
        idx = np.where((k >= start) & (norm < level))[0]
        return int(k[idx[0]]) if len(idx) else None

    r_e = crossing(1.0 / np.e, start=1)
    r_1pct = crossing(1e-2, start=1)

    # 在 1e-1 >= u/u0 >= 1e-3 的尾段做 log 线性拟合
    mask = (k >= 1) & (norm < 0.1) & (norm > 1e-3)
    if mask.sum() >= 3:
        coef = np.polyfit(k[mask], np.log(norm[mask]), 1)
        xi = -1.0 / coef[0]
        fit = np.polyval(coef, k[mask])
        resid = np.log(norm[mask]) - fit
        r2 = 1.0 - np.sum(resid**2) / np.sum(
            (np.log(norm[mask]) - np.log(norm[mask]).mean()) ** 2
        )
        fit_range = [int(k[mask][0]), int(k[mask][-1])]
    else:
        xi, r2, fit_range = float("nan"), float("nan"), [None, None]

    return {
        "k": k,
        "profile": prof,
        "norm": norm,
        "r_e": r_e,
        "r_1pct": r_1pct,
        "xi": float(xi),
        "xi_R2": float(r2),
        "xi_fit_range": fit_range,
    }


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------
def main() -> None:
    t_start = time.time()
    data: dict = {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "tol": TOL,
            "max_sweeps": MAX_SWEEPS,
            "sweep_order": "i 递增, j 递增 (lexicographic)",
            "initial_field": "u=0",
            "source_strength": 1.0,
        }
    }

    # -- 0. 向量化实现与朴素逐点实现的对照 --------------------------------
    print("[0] 实现对照 ...")
    N, m, omega = 31, 0.5, 1.5
    fast = solve(N, m, omega)
    naive = sor2d.solve_sor_naive(N, m, omega, tol=TOL)
    data["implementation"] = {
        "N": N,
        "m": m,
        "omega": omega,
        "K_fast": fast.sweeps,
        "K_naive": naive.sweeps,
        "max_abs_diff": float(np.max(np.abs(fast.u - naive.u))),
        "residual_fast": fast.residual,
        "residual_naive": naive.residual,
    }
    print(
        f"  K_fast={fast.sweeps}, K_naive={naive.sweeps}, "
        f"max|du|={data['implementation']['max_abs_diff']:.1e}"
    )

    # -- 1. 小网格直接解验证 ----------------------------------------------
    print("[1] 直接解验证 ...")
    verification = []
    for N in (7, 9):
        A_inv_norm = sor2d.infinity_norm_inverse(N, m)
        u_ref = sor2d.solve_direct(N, m)
        for tol in (1e-4, 1e-6, 1e-8, 1e-10):
            r = sor2d.solve_sor(N, m, 1.5, tol=tol)
            u_sor = r.u[1:-1, 1:-1]
            eps = float(np.max(np.abs(u_sor - u_ref)))
            verification.append(
                {
                    "N": N,
                    "m": m,
                    "omega": 1.5,
                    "tol": tol,
                    "K": r.sweeps,
                    "residual": r.residual,
                    "eps_inf": eps,
                    "eps_over_res": eps / r.residual,
                    "Ainv_inf": A_inv_norm,
                    "asymmetry": float(np.max(np.abs(u_sor - u_sor.T))),
                    "u_max": float(np.max(u_sor)),
                }
            )
            print(
                f"  N={N} tol={tol:.0e}: K={r.sweeps:3d}, "
                f"||r||={r.residual:.2e}, eps={eps:.2e}"
            )
    data["verification"] = verification

    # -- 2. 任务 1: N=31, m=0.5, omega=1.5 --------------------------------
    print("[2] 任务 1 ...")
    r1 = solve(31, 0.5, 1.5, record_history=True)
    u1 = r1.u[1:-1, 1:-1]
    i0, j0 = r1.i0, r1.j0
    imax, jmax = np.unravel_index(np.argmax(u1), u1.shape)
    k1, prof1 = symmetric_profile(r1.u, i0 + 1, j0 + 1, 31)
    np.save(RESULTS / "u_task1.npy", u1)
    data["task1"] = {
        "N": 31,
        "m": 0.5,
        "omega": 1.5,
        "K": r1.sweeps,
        "residual": r1.residual,
        "u_max": float(u1[i0, j0]),
        "argmax": [int(imax), int(jmax)],
        "source": [int(i0), int(j0)],
        "u_min": float(np.min(u1)),
        "symmetry_max_abs": float(np.max(np.abs(u1 - u1.T))),
        "symmetry_rel": float(np.max(np.abs(u1 - u1.T)) / np.max(u1)),
        "reverse_symmetry": float(
            np.max(np.abs(u1 - u1[::-1, :])) + np.max(np.abs(u1 - u1[:, ::-1]))
        ),
        "profile": prof1,
        "k": k1,
        "history": r1.history,
    }
    print(
        f"  K={r1.sweeps}, ||r||={r1.residual:.2e}, u_max={u1[i0, j0]:.6f}, "
        f"argmax={imax},{jmax}, sym={data['task1']['symmetry_rel']:.1e}"
    )

    # -- 3. 任务 2: N=63, m=0.2/0.5/1.0 -----------------------------------
    print("[3] 任务 2 ...")
    task2 = {"runs": [], "boundary": {}}
    for m in (0.2, 0.5, 1.0):
        r = solve(63, m, 1.5)
        u = r.u[1:-1, 1:-1]
        met = decay_metrics(r.u, r.i0 + 1, r.j0 + 1, 63)
        task2["runs"].append(
            {
                "m": m,
                "K": r.sweeps,
                "residual": r.residual,
                "u_max": float(u[r.i0, r.j0]),
                "r_e": met["r_e"],
                "r_1pct": met["r_1pct"],
                "xi": met["xi"],
                "xi_R2": met["xi_R2"],
                "xi_fit_range": met["xi_fit_range"],
                "k": met["k"],
                "norm": met["norm"],
            }
        )
        print(
            f"  m={m}: K={r.sweeps}, u_max={u[r.i0, r.j0]:.6f}, "
            f"r_e={met['r_e']}, r_1%={met['r_1pct']}, xi={met['xi']:.3f}"
        )

    # 边界影响: N=63 vs N=127 (同一物理格距, 区域扩大)
    print("  边界对照 N=63 vs N=127 ...")
    for m in (0.2, 0.5, 1.0):
        r63 = solve(63, m, 1.5)
        r127 = solve(127, m, 1.5)
        met63 = decay_metrics(r63.u, r63.i0 + 1, r63.j0 + 1, 63)
        met127 = decay_metrics(r127.u, r127.i0 + 1, r127.j0 + 1, 127)
        # 用 127 网格上同样的拟合窗口, 便于比较 xi
        kk = np.arange(met63["xi_fit_range"][0], met63["xi_fit_range"][1] + 1)
        n127 = met127["norm"][: len(met127["norm"])]
        coef = np.polyfit(kk, np.log(n127[kk]), 1)
        xi127_same = -1.0 / coef[0]
        p63 = met63["profile"][:32]
        p127 = met127["profile"][:32]
        diff = np.abs(p63 - p127) / met127["profile"][0]
        task2["boundary"][str(m)] = {
            "u0_63": met63["profile"][0],
            "u0_127": met127["profile"][0],
            "xi_63": met63["xi"],
            "xi_127_same_window": float(xi127_same),
            "xi_127_own_window": met127["xi"],
            "max_rel_diff_k_le_20": float(np.max(diff[:21])),
            "max_rel_diff_k_le_31": float(np.max(diff)),
            "profile_63": p63,
            "profile_127": p127,
            "k": met63["k"],
        }
        print(
            f"    m={m}: xi63={met63['xi']:.3f}, xi127={xi127_same:.3f}, "
            f"max diff(k<=20)={np.max(diff[:21]):.1e}"
        )
    data["task2"] = task2

    # -- 4. 任务 3: N=63, m=0.5, omega 扫描 -------------------------------
    print("[4] 任务 3 ...")
    coarse_grid = [round(x, 2) for x in np.arange(1.0, 1.91, 0.1)] + [1.95]
    coarse = scan(63, 0.5, coarse_grid)
    best_c, _ = best_row(coarse)
    lo = round(best_c["omega"] - 0.05, 3)
    hi = round(best_c["omega"] + 0.05, 3)
    fine_grid = [round(x, 3) for x in np.arange(lo, hi + 1e-9, 0.01)]
    fine = scan(63, 0.5, fine_grid)
    best_f, _ = best_row(fine)
    lo2 = round(best_f["omega"] - 0.02, 3)
    hi2 = round(best_f["omega"] + 0.02, 3)
    ultra_grid = [round(x, 3) for x in np.arange(lo2, hi2 + 1e-9, 0.002)]
    ultra = scan(63, 0.5, ultra_grid)
    pl = plateau(ultra)
    best_u = pl[3]
    k_best = pl[2]
    k_gs = solve(63, 0.5, 1.0).sweeps
    data["task3"] = {
        "N": 63,
        "m": 0.5,
        "coarse": coarse,
        "fine": fine,
        "ultra": ultra,
        "coarse_best": best_c,
        "fine_best": best_f,
        "ultra_plateau": {
            "omega_lo": pl[0],
            "omega_hi": pl[1],
            "K": pl[2],
            "mid": pl[3],
        },
        "K_GS": k_gs,
        "speedup": k_gs / k_best,
        "reduction": 1.0 - k_best / k_gs,
        "omega_th": sor2d.optimal_omega(63, 0.5),
        "rho_J": sor2d.jacobi_spectral_radius(63, 0.5),
    }
    print(
        f"  coarse best {best_c['omega']:.2f} (K={best_c['K']}), "
        f"fine best {best_f['omega']:.2f} (K={best_f['K']}), "
        f"ultra plateau {pl[0]:.3f}-{pl[1]:.3f} (K={pl[2]})"
    )

    # -- 5. 任务 4: m 对最优 omega 的影响 ---------------------------------
    print("[5] 任务 4 ...")
    task4 = {}
    for m in (0.2, 0.5, 1.0):
        coarse_grid = [round(x, 2) for x in np.arange(1.0, 1.951, 0.05)]
        c = scan(63, m, coarse_grid)
        bc, _ = best_row(c)
        fg = [
            round(x, 4)
            for x in np.arange(bc["omega"] - 0.10, bc["omega"] + 0.1001, 0.01)
        ]
        f = scan(63, m, fg)
        bf, _ = best_row(f)
        ug = [
            round(x, 4)
            for x in np.arange(bf["omega"] - 0.03, bf["omega"] + 0.0301, 0.001)
        ]
        uu = scan(63, m, ug)
        pl = plateau(uu)
        kgs = solve(63, m, 1.0).sweeps
        task4[str(m)] = {
            "m": m,
            "coarse": c,
            "fine": f,
            "ultra": uu,
            "best_omega": pl[3],
            "K_best": pl[2],
            "K_GS": kgs,
            "S": kgs / pl[2],
            "plateau": [pl[0], pl[1]],
            "omega_th": sor2d.optimal_omega(63, m),
            "rho_J": sor2d.jacobi_spectral_radius(63, m),
        }
        print(
            f"  m={m}: best omega={pl[3]:.4f} (plateau {pl[0]:.3f}-{pl[1]:.3f}), "
            f"K={pl[2]}, K_GS={kgs}, S={kgs/pl[2]:.2f}, wth={sor2d.optimal_omega(63,m):.4f}"
        )
    data["task4"] = task4

    # -- 6. 理论对照: 数值谱半径 -----------------------------------------
    print("[6] 谱半径核对 ...")
    N = 31
    m = 0.5
    A = sor2d.build_dense_matrix(N, m)
    D = np.diag(np.diag(A))
    L = np.tril(A, -1)
    U = np.triu(A, 1)
    rho_num = []
    for omega in (1.0, 1.2, 1.4, 1.48, 1.49, 1.50, 1.60, 1.80, 1.95):
        T = np.linalg.inv(D + omega * L) @ ((1 - omega) * D - omega * U)
        rho_num.append(
            {
                "omega": omega,
                "rho_num": float(np.max(np.abs(np.linalg.eigvals(T)))),
            }
        )
        print(f"  omega={omega:.2f}: rho_num={rho_num[-1]['rho_num']:.6f}")
    data["theory"] = {
        "N": N,
        "m": m,
        "rho_num": rho_num,
        "rho_J": sor2d.jacobi_spectral_radius(N, m),
        "omega_th": sor2d.optimal_omega(N, m),
        "omega_th_63": {str(mm): sor2d.optimal_omega(63, mm) for mm in (0.2, 0.5, 1.0)},
        "rho_J_63": {str(mm): sor2d.jacobi_spectral_radius(63, mm) for mm in (0.2, 0.5, 1.0)},
    }

    # -- 7. 残差收敛曲线 (选做 5) -----------------------------------------
    print("[7] 残差曲线 ...")
    curve_omegas = [1.0, 1.2, 1.4, 1.49, 1.6, 1.8, 1.95]
    curves = []
    for omega in curve_omegas:
        r = solve(63, 0.5, omega, tol=1e-10, max_sweeps=20_000, record_history=True)
        curves.append(
            {
                "omega": omega,
                "K": r.sweeps,
                "history": r.history,
                "residual": r.residual,
            }
        )
        print(f"  omega={omega:.2f}: K(1e-10)={r.sweeps}")
    data["residual_curves"] = curves

    # -- 8. 阈值对经验最优 omega 的影响 -----------------------------------
    print("[8] 阈值依赖性 ...")
    threshold_scan = []
    for tol in (1e-6, 1e-8, 1e-10, 1e-12):
        rows = scan(63, 0.5, [round(x, 2) for x in np.arange(1.30, 1.551, 0.01)], tol=tol)
        br, kmin = best_row(rows)
        threshold_scan.append(
            {
                "tol": tol,
                "best_omega": br["omega"],
                "K": br["K"],
                "K_GS": solve(63, 0.5, 1.0, tol=tol, max_sweeps=MAX_SWEEPS).sweeps,
                "rows": rows,
            }
        )
        print(f"  tol={tol:.0e}: best omega={br['omega']:.2f}, K={br['K']}")
    data["threshold_dependence"] = threshold_scan

    # -- 9. 导出 CSV -------------------------------------------------------
    for m in (0.2, 0.5, 1.0):
        rows = task4[str(m)]["ultra"]
        with open(RESULTS / f"scan_ultra_m{m}.csv", "w", encoding="utf-8-sig") as fh:
            fh.write("omega,K,residual\n")
            for row in rows:
                fh.write(f"{row['omega']:.6f},{row['K']},{row['residual']:.6e}\n")
    with open(RESULTS / "scan_coarse_m0.5.csv", "w", encoding="utf-8-sig") as fh:
        fh.write("omega,K,residual\n")
        for row in data["task3"]["coarse"]:
            fh.write(f"{row['omega']:.6f},{row['K']},{row['residual']:.6e}\n")

    data["elapsed_seconds"] = time.time() - t_start
    with open(RESULTS / "results.json", "w", encoding="utf-8") as fh:
        json.dump(jsonable(data), fh, ensure_ascii=False, indent=1)
    print(f"[done] {time.time()-t_start:.1f} s, results/results.json")


if __name__ == "__main__":
    main()
