r"""平面等质量三体问题的核心物理与数值积分.

单位约定
--------
G = 1, m1 = m2 = m3 = 1. 位置、速度、时间均取无量纲单位.
状态数组形状为 (3, 4), 每行是 (x, y, vx, vy).

运动方程
--------
\ddot r_i = sum_{j != i} (r_j - r_i) / |r_j - r_i|^3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

G = 1.0
MASS = np.ones(3, dtype=float)


# ---------------------------------------------------------------------------
# 基本物理量
# ---------------------------------------------------------------------------
def accelerations(pos: np.ndarray) -> np.ndarray:
    """返回三颗恒星的加速度, pos 形状 (3, 2)."""
    pos = np.asarray(pos, dtype=float)
    diff = pos[None, :, :] - pos[:, None, :]  # diff[i, j] = r_j - r_i
    r2 = np.einsum("ijk,ijk->ij", diff, diff)
    np.fill_diagonal(r2, np.inf)
    inv_r3 = r2 ** (-1.5)
    return np.einsum("ij,ijk->ik", inv_r3, diff)


def rhs(state: np.ndarray) -> np.ndarray:
    """状态导数 d/dt (r, v) = (v, a)."""
    state = np.asarray(state, dtype=float)
    out = np.empty_like(state)
    out[:, :2] = state[:, 2:]
    out[:, 2:] = accelerations(state[:, :2])
    return out


def pair_distances(pos: np.ndarray) -> np.ndarray:
    """返回 (d12, d13, d23)."""
    pos = np.asarray(pos, dtype=float)
    d12 = np.linalg.norm(pos[1] - pos[0])
    d13 = np.linalg.norm(pos[2] - pos[0])
    d23 = np.linalg.norm(pos[2] - pos[1])
    return np.array([d12, d13, d23])


def total_energy(state: np.ndarray) -> float:
    """总机械能 E = T + U (G = m = 1)."""
    state = np.asarray(state, dtype=float)
    vel = state[:, 2:]
    kinetic = 0.5 * np.sum(vel * vel)
    r = pair_distances(state[:, :2])
    potential = -np.sum(1.0 / r)
    return float(kinetic + potential)


def total_momentum(state: np.ndarray) -> np.ndarray:
    return np.sum(state[:, 2:], axis=0)


def angular_momentum(state: np.ndarray) -> float:
    pos = state[:, :2]
    vel = state[:, 2:]
    return float(np.sum(pos[:, 0] * vel[:, 1] - pos[:, 1] * vel[:, 0]))


def centre_of_mass(state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """返回质心位置与速度 (等质量)."""
    return state[:, :2].mean(axis=0), state[:, 2:].mean(axis=0)


def subtract_com_velocity(state: np.ndarray) -> np.ndarray:
    """把总动量归零 (只减质心速度, 不改变相对运动)."""
    out = np.array(state, dtype=float, copy=True)
    out[:, 2:] -= out[:, 2:].mean(axis=0)
    return out


def centre_positions(state: np.ndarray) -> np.ndarray:
    """把质心平移到原点, 返回新状态 (不改变相对运动)."""
    out = np.array(state, dtype=float, copy=True)
    out[:, :2] -= out[:, :2].mean(axis=0)
    return out


# ---------------------------------------------------------------------------
# 初始条件
# ---------------------------------------------------------------------------
def ic_lagrange() -> np.ndarray:
    """模式 A: 等边三角形旋转 (Lagrange 解).

    边长 a = 1, 外接圆半径 R = 1/sqrt(3), omega = sqrt(3).
    """
    s3 = np.sqrt(3.0)
    pos = np.array(
        [
            [1.0 / s3, 0.0],
            [-1.0 / (2.0 * s3), 0.5],
            [-1.0 / (2.0 * s3), -0.5],
        ]
    )
    omega = np.sqrt(3.0)
    vel = omega * np.column_stack((-pos[:, 1], pos[:, 0]))
    return np.hstack((pos, vel))


def ic_figure_eight() -> np.ndarray:
    """模式 B: Chenciner-Montgomery 8 字形 (题目给定初值)."""
    return np.array(
        [
            [0.97000436, -0.24308753, 0.46620369, 0.43236573],
            [-0.97000436, 0.24308753, 0.46620369, 0.43236573],
            [0.0, 0.0, -0.93240738, -0.86473146],
        ]
    )


def ic_symmetric_row(vx: float, vy: float, x: float = 1.0) -> np.ndarray:
    """零角动量对称族: r1=(-x,0), r2=(x,0), r3=0, v1=v2=(vx,vy), v3=-2(vx,vy).

    Šuvakov & Dmitrašinović (2013) 的初值即取 x = 1.
    """
    return np.array(
        [
            [-x, 0.0, vx, vy],
            [x, 0.0, vx, vy],
            [0.0, 0.0, -2.0 * vx, -2.0 * vy],
        ]
    )


def ic_butterfly_i() -> np.ndarray:
    """蝴蝶 I (Šuvakov & Dmitrašinović 2013, T ≈ 6.2356)."""
    return ic_symmetric_row(0.30689, 0.12551)


def ic_moth_i() -> np.ndarray:
    """飞蛾 I (Šuvakov & Dmitrašinović 2013, T ≈ 14.8939)."""
    return ic_symmetric_row(0.46444, 0.39606)


def ic_hierarchical(
    binary_separation: float = 0.4,
    outer_separation: float = 4.0,
) -> np.ndarray:
    """层级三体: 紧密圆双星 + 远处第三体, 整体质心静止.

    双星 (1,2) 间距 d, 绕共同质心做圆运动; 双星质心与星 3 的
    相对轨道半径 R, 也取圆轨道. 所有运动在同一平面内.
    """
    d = float(binary_separation)
    R = float(outer_separation)

    # 双星内部: 每颗星到双星质心 d/2, 相对速度 v_int = sqrt(1/(2d))
    v_int = np.sqrt(1.0 / (2.0 * d))

    # 外层二体 (双星总质量 2, 星 3 质量 1): 相对速度 sqrt(3/R)
    v_rel = np.sqrt(3.0 / R)
    r_bin = np.array([-R / 3.0, 0.0])
    r3 = np.array([2.0 * R / 3.0, 0.0])
    v_bin = np.array([0.0, -v_rel / 3.0])
    v3 = np.array([0.0, 2.0 * v_rel / 3.0])

    state = np.zeros((3, 4))
    state[0, :2] = r_bin + np.array([-d / 2.0, 0.0])
    state[1, :2] = r_bin + np.array([d / 2.0, 0.0])
    state[2, :2] = r3
    state[0, 2:] = v_bin + np.array([0.0, v_int])
    state[1, 2:] = v_bin + np.array([0.0, -v_int])
    state[2, 2:] = v3
    return state


def perturb(state: np.ndarray, dvx: float = 1e-4) -> np.ndarray:
    """给恒星 1 的 vx 加 dvx, 再把总动量归零."""
    out = np.array(state, dtype=float, copy=True)
    out[0, 2] += dvx
    return subtract_com_velocity(out)


# ---------------------------------------------------------------------------
# Lagrange 等边三角形解析解与线性稳定性
# ---------------------------------------------------------------------------
LAGRANGE_OMEGA = np.sqrt(3.0)


def lagrange_exact_state(t: float, ic: np.ndarray | None = None) -> np.ndarray:
    """模式 A 的解析解: 整个三角形以 omega = sqrt(3) 刚性旋转."""
    if ic is None:
        ic = ic_lagrange()
    omega = LAGRANGE_OMEGA
    c, s = np.cos(omega * t), np.sin(omega * t)
    rot = np.array([[c, -s], [s, c]])
    out = np.array(ic, dtype=float, copy=True)
    out[:, :2] = ic[:, :2] @ rot.T
    out[:, 2:] = ic[:, 2:] @ rot.T
    return out


def lagrange_exact_trajectory(t_array: np.ndarray) -> np.ndarray:
    """返回 (len(t), 3, 4) 的解析轨迹."""
    return np.array([lagrange_exact_state(float(t)) for t in t_array])


def lagrange_force_residual(t: float) -> float:
    """解析解代入运动方程的最大残差 |a_i + omega^2 r_i|."""
    state = lagrange_exact_state(t)
    a = accelerations(state[:, :2])
    return float(np.max(np.abs(a + LAGRANGE_OMEGA**2 * state[:, :2])))


def lagrange_linear_eigenvalues() -> np.ndarray:
    """旋转系中 Lagrange 解线性化后的 12 个特征值.

    旋转系方程: delta r'' = -H delta r - 2 omega J delta r',
    H 为势能 U 的 Hessian. 返回按实部降序排列的特征值.
    """
    ic = ic_lagrange()
    pos = ic[:, :2]
    omega = LAGRANGE_OMEGA

    # H = d(grad U)/dr = -d(a)/dr, 用中心差分
    eps = 1e-6
    hessian = np.zeros((6, 6))
    for k in range(6):
        e = np.zeros(6)
        e[k] = eps
        a_plus = accelerations((pos.ravel() + e).reshape(3, 2)).ravel()
        a_minus = accelerations((pos.ravel() - e).reshape(3, 2)).ravel()
        hessian[:, k] = -(a_plus - a_minus) / (2.0 * eps)

    j2 = np.array([[0.0, -1.0], [1.0, 0.0]])
    coriolis = -2.0 * omega * np.kron(np.eye(3), j2)
    matrix = np.zeros((12, 12))
    matrix[:6, 6:] = np.eye(6)
    # delta r'' = (-H + omega^2 I) delta r - 2 omega J delta r'
    matrix[6:, :6] = -hessian + omega**2 * np.eye(6)
    matrix[6:, 6:] = coriolis
    eigenvalues = np.linalg.eigvals(matrix)
    order = np.argsort(-eigenvalues.real)
    return eigenvalues[order]


def lagrange_growth_rate() -> float:
    """Lagrange 解的最大线性增长率 (实部)."""
    return float(np.max(lagrange_linear_eigenvalues().real))


# ---------------------------------------------------------------------------
# 固定步长 RK4
# ---------------------------------------------------------------------------
def rk4_step(state: np.ndarray, dt: float) -> np.ndarray:
    k1 = rhs(state)
    k2 = rhs(state + 0.5 * dt * k1)
    k3 = rhs(state + 0.5 * dt * k2)
    k4 = rhs(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# ---------------------------------------------------------------------------
# 自适应 Dormand-Prince RK45
# ---------------------------------------------------------------------------
_C = np.array([0.0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1.0, 1.0])
_A = (
    (),
    (1 / 5,),
    (3 / 40, 9 / 40),
    (44 / 45, -56 / 15, 32 / 9),
    (19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729),
    (9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656),
    (35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84),
)
_B5 = np.array([35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0.0])
_B4 = np.array(
    [5179 / 57600, 0.0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40]
)


def _dp_step(state: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """返回 5 阶解与 4 阶解, 用于误差估计."""
    k = np.empty((7, 3, 4))
    k[0] = rhs(state)
    for s in range(1, 7):
        acc = np.zeros_like(state)
        for j in range(s):
            acc += _A[s][j] * k[j]
        k[s] = rhs(state + h * acc)
    y5 = state + h * np.tensordot(_B5, k, axes=(0, 0))
    y4 = state + h * np.tensordot(_B4, k, axes=(0, 0))
    return y5, y4


# ---------------------------------------------------------------------------
# 模拟结果与驱动
# ---------------------------------------------------------------------------
@dataclass
class Simulation:
    label: str
    t: np.ndarray
    states: np.ndarray
    energies: np.ndarray
    dmin_series: np.ndarray
    dmax_series: np.ndarray
    stop_time: float
    stop_reason: str
    dt_nominal: float
    step_count: int
    meta: dict = field(default_factory=dict)

    @property
    def e0(self) -> float:
        return float(self.energies[0])

    @property
    def min_pair_distance(self) -> float:
        return float(np.min(self.dmin_series))

    @property
    def max_pair_distance(self) -> float:
        return float(np.max(self.dmax_series))

    @property
    def max_energy_error(self) -> float:
        return float(np.max(np.abs(self.energies - self.e0)))

    @property
    def final_energy_error(self) -> float:
        return float(abs(self.energies[-1] - self.e0))

    @property
    def stopped(self) -> bool:
        return self.stop_reason != "completed"

    @property
    def t_end(self) -> float:
        return float(self.t[-1])


def _empty_arrays() -> tuple[list[float], list[np.ndarray], list[float], list[float], list[float]]:
    return [], [], [], [], []


def simulate(
    initial_state: np.ndarray,
    dt: float = 0.001,
    t_max: float = 50.0,
    *,
    label: str = "",
    method: str = "rk4",
    close_threshold: float = 0.05,
    escape_radius: float = 50.0,
    save_every: int = 1,
    rtol: float = 1e-12,
    atol: float = 1e-14,
    max_step: float = 0.01,
    energy_check_every: int = 1,
) -> Simulation:
    """积分三体系统, 返回轨迹与诊断量.

    method = "rk4": 固定步长 dt.
    method = "dp45": 自适应 Dormand-Prince, dt 为初始步长.

    停止条件: 任意两星距离 < close_threshold, 或最大半径 > escape_radius,
    或到达 t_max. 返回结果中保留停止前的全部采样.
    """
    state = np.array(initial_state, dtype=float, copy=True)
    t = 0.0
    ts, states, energies, dmins, dmaxs = _empty_arrays()

    d0 = pair_distances(state[:, :2])
    e0 = total_energy(state)
    ts.append(0.0)
    states.append(state.copy())
    energies.append(e0)
    dmins.append(float(np.min(d0)))
    dmaxs.append(float(np.max(d0)))

    stop_reason = "completed"
    stop_time = t_max
    steps = 0
    h = float(dt)

    # 初始自适应步长不超过 max_step
    if method == "dp45":
        h = min(h, max_step)

    while t < t_max - 1e-14:
        if method == "rk4":
            h_use = min(dt, t_max - t)
            new_state = rk4_step(state, h_use)
            t += h_use
            steps += 1
            accept = True
        elif method == "dp45":
            h_use = min(h, t_max - t, max_step)
            y5, y4 = _dp_step(state, h_use)
            # 缩放误差范数 (位置与速度分别缩放)
            scale = atol + rtol * np.maximum(np.abs(state), np.abs(y5))
            err = float(np.sqrt(np.mean(((y5 - y4) / scale) ** 2)))
            accept = err <= 1.0 or h_use <= 1e-12
            if accept:
                new_state = y5
                t += h_use
                steps += 1
                # 步长控制
                factor = 0.9 * err ** (-0.2) if err > 0 else 5.0
                h = min(max(h_use * min(5.0, max(0.2, factor)), 1e-12), max_step)
            else:
                h = max(h_use * max(0.2, 0.9 * err ** (-0.2)), 1e-12)
                continue
        else:
            raise ValueError(f"unknown method: {method}")

        state = new_state

        # 每步都检查近距离/逃逸, 保证停止时间准确
        d = pair_distances(state[:, :2])
        if np.min(d) < close_threshold:
            # 记录停止前状态
            ts.append(t)
            states.append(state.copy())
            energies.append(total_energy(state))
            dmins.append(float(np.min(d)))
            dmaxs.append(float(np.max(d)))
            stop_reason = "close_encounter"
            stop_time = t
            break
        rmax = float(np.max(np.linalg.norm(state[:, :2], axis=1)))
        if rmax > escape_radius:
            ts.append(t)
            states.append(state.copy())
            energies.append(total_energy(state))
            dmins.append(float(np.min(d)))
            dmaxs.append(float(np.max(d)))
            stop_reason = "escape"
            stop_time = t
            break

        if steps % save_every == 0:
            ts.append(t)
            states.append(state.copy())
            energies.append(total_energy(state))
            dmins.append(float(np.min(d)))
            dmaxs.append(float(np.max(d)))

    # 若最后一步未保存 (save_every > 1), 补上终点
    if ts[-1] < t - 1e-15:
        ts.append(t)
        states.append(state.copy())
        energies.append(total_energy(state))
        d = pair_distances(state[:, :2])
        dmins.append(float(np.min(d)))
        dmaxs.append(float(np.max(d)))

    return Simulation(
        label=label,
        t=np.asarray(ts),
        states=np.asarray(states),
        energies=np.asarray(energies),
        dmin_series=np.asarray(dmins),
        dmax_series=np.asarray(dmaxs),
        stop_time=float(stop_time),
        stop_reason=stop_reason,
        dt_nominal=float(dt),
        step_count=steps,
        meta={"method": method, "t_max": t_max},
    )


def interpolate_states(sim: Simulation, t_grid: np.ndarray) -> np.ndarray:
    """把轨迹线性插值到给定时间网格, 返回 (len(t_grid), 3, 4)."""
    flat = sim.states.reshape(len(sim.t), -1)
    out = np.empty((len(t_grid), flat.shape[1]))
    for k in range(flat.shape[1]):
        out[:, k] = np.interp(t_grid, sim.t, flat[:, k])
    return out.reshape(len(t_grid), 3, 4)


def trajectory_separation(
    sim_a: Simulation, sim_b: Simulation, t_grid: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """两条轨迹的逐点欧氏分离 ||r_i^a - r_i^b|| 的均方根/最大值.

    返回 (t, delta), 其中 delta = sqrt(sum_i |dr_i|^2).
    """
    if t_grid is None:
        t_end = min(sim_a.t_end, sim_b.t_end)
        t_grid = np.linspace(0.0, t_end, 2001)
    a = interpolate_states(sim_a, t_grid)
    b = interpolate_states(sim_b, t_grid)
    diff = a[:, :, :2] - b[:, :, :2]
    delta = np.sqrt(np.sum(diff * diff, axis=(1, 2)))
    return t_grid, delta
