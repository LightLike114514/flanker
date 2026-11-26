"""二维格点点源模型的 SOR 求解器。

模型
----
在 (N+2) x (N+2) 的格点上取内部 N x N 个未知量, 四周一圈 Dirichlet 边界 u=0,
格距 h=1。中心格点放单位点源, 求解

    (4 + m^2) u_{i,j} - u_{i+1,j} - u_{i-1,j} - u_{i,j+1} - u_{i,j-1} = s_{i,j}

逐点 SOR 扫描顺序为 i 递增、j 递增 (lexicographic)。相邻的反对角线 i+j=k
之间互不依赖, 因此按反对角线整条更新与逐点扫描在数学上完全等价, 但可以向量化。
本模块同时提供逐点实现, 用于核对向量化实现的正确性。

约定
----
* 数组 u, s 的形状为 (N+2, N+2), 内部格点为 u[1:N+1, 1:N+1];
* 源点 (i0, j0) 使用内部 0-based 指标, 0 <= i0, j0 < N;
* 迭代次数按“完整扫描次数”计。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# 网格、源项与残差
# ---------------------------------------------------------------------------
def make_system(
    N: int, m: float, source: Optional[Tuple[int, int]] = None
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """返回源项数组 s 和内部 0-based 源点坐标 (i0, j0)。

    默认源点在几何中心。source 可指定偏离中心的源点, 供拓展实验使用。
    """
    if N < 3:
        raise ValueError("N 必须 >= 3")
    s = np.zeros((N + 2, N + 2), dtype=float)
    if source is None:
        i0 = j0 = (N - 1) // 2
    else:
        i0, j0 = source
        if not (0 <= i0 < N and 0 <= j0 < N):
            raise ValueError("源点必须位于内部格点")
    s[i0 + 1, j0 + 1] = 1.0
    return s, (i0, j0)


def residual(u: np.ndarray, s: np.ndarray, m: float) -> float:
    """最大绝对残差 ||r||_inf, r = s - A u。"""
    m2 = m * m
    r = s[1:-1, 1:-1] - (
        (4.0 + m2) * u[1:-1, 1:-1]
        - u[:-2, 1:-1]
        - u[2:, 1:-1]
        - u[1:-1, :-2]
        - u[1:-1, 2:]
    )
    return float(np.max(np.abs(r)))


def _anti_diagonals(N: int) -> List[Tuple[np.ndarray, np.ndarray]]:
    """预先计算内部格点的反对角线 i+j=k 的索引数组。"""
    diags: List[Tuple[np.ndarray, np.ndarray]] = []
    for k in range(2, 2 * N + 1):
        i = np.arange(max(1, k - N), min(N, k - 1) + 1)
        j = k - i
        diags.append((i, j))
    return diags


# ---------------------------------------------------------------------------
# SOR 求解
# ---------------------------------------------------------------------------
@dataclass
class SORResult:
    u: np.ndarray
    sweeps: int
    residual: float
    converged: bool
    history: np.ndarray = field(default_factory=lambda: np.empty(0))
    i0: int = 0
    j0: int = 0

    @property
    def u_max(self) -> float:
        return float(self.u[self.i0 + 1, self.j0 + 1])


def solve_sor(
    N: int,
    m: float,
    omega: float,
    tol: float = 1e-6,
    max_sweeps: int = 200_000,
    record_history: bool = False,
    source: Optional[Tuple[int, int]] = None,
) -> SORResult:
    """逐点 (lexicographic) SOR, 按反对角线向量化实现。

    停止准则: 一次完整扫描后 ||r||_inf < tol。
    """
    if not (0.0 < omega < 2.0):
        raise ValueError("SOR 要求 0 < omega < 2")
    s, (i0, j0) = make_system(N, m, source)
    u = np.zeros_like(s)
    m2 = m * m
    diags = _anti_diagonals(N)
    hist: List[float] = []
    converged = False
    sweeps = 0

    if record_history:
        hist.append(residual(u, s, m))

    for k in range(1, max_sweeps + 1):
        for i, j in diags:
            gs = (
                s[i, j]
                + u[i - 1, j]
                + u[i + 1, j]
                + u[i, j - 1]
                + u[i, j + 1]
            ) / (4.0 + m2)
            u[i, j] = (1.0 - omega) * u[i, j] + omega * gs
        res = residual(u, s, m)
        sweeps = k
        if record_history:
            hist.append(res)
        if res < tol:
            converged = True
            break

    return SORResult(
        u=u,
        sweeps=sweeps,
        residual=res,
        converged=converged,
        history=np.asarray(hist),
        i0=i0,
        j0=j0,
    )


def solve_sor_naive(
    N: int,
    m: float,
    omega: float,
    tol: float = 1e-6,
    max_sweeps: int = 200_000,
    source: Optional[Tuple[int, int]] = None,
) -> SORResult:
    """最朴素的逐点双层循环实现, 仅用于与向量化版本对照。"""
    s, (i0, j0) = make_system(N, m, source)
    u = np.zeros_like(s)
    m2 = m * m
    converged = False
    sweeps = 0
    res = np.inf
    for k in range(1, max_sweeps + 1):
        for i in range(1, N + 1):
            for j in range(1, N + 1):
                gs = (
                    s[i, j]
                    + u[i - 1, j]
                    + u[i + 1, j]
                    + u[i, j - 1]
                    + u[i, j + 1]
                ) / (4.0 + m2)
                u[i, j] = (1.0 - omega) * u[i, j] + omega * gs
        res = residual(u, s, m)
        sweeps = k
        if res < tol:
            converged = True
            break
    return SORResult(u, sweeps, res, converged, np.empty(0), i0, j0)


# ---------------------------------------------------------------------------
# 参考解: 直接线性求解
# ---------------------------------------------------------------------------
def build_dense_matrix(N: int, m: float) -> np.ndarray:
    """按行优先 (i 外层, j 内层) 排列未知量, 构造 A。"""
    S = np.zeros((N, N))
    idx = np.arange(N - 1)
    S[idx, idx + 1] = 1.0
    S[idx + 1, idx] = 1.0
    I = np.eye(N)
    return (4.0 + m * m) * np.eye(N * N) - np.kron(S, I) - np.kron(I, S)


def solve_direct(N: int, m: float, source: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """返回内部格点上的直接解, 形状 (N, N)。"""
    A = build_dense_matrix(N, m)
    s, (i0, j0) = make_system(N, m, source)
    b = s[1:-1, 1:-1].reshape(-1)
    x = np.linalg.solve(A, b)
    return x.reshape(N, N)


def infinity_norm_inverse(N: int, m: float) -> float:
    """||A^{-1}||_inf, 用于把残差上界换算成解误差上界。"""
    A = build_dense_matrix(N, m)
    Ainv = np.linalg.inv(A)
    return float(np.max(np.sum(np.abs(Ainv), axis=1)))


# ---------------------------------------------------------------------------
# 理论参考量
# ---------------------------------------------------------------------------
def jacobi_spectral_radius(N: int, m: float) -> float:
    """标准方形网格上 Jacobi 迭代的谱半径。"""
    return 4.0 / (4.0 + m * m) * np.cos(np.pi / (N + 1))


def optimal_omega(N: int, m: float) -> float:
    """由 rho_J 给出的 SOR 最优松弛因子 (理论参考值)。"""
    rho = jacobi_spectral_radius(N, m)
    return 2.0 / (1.0 + np.sqrt(1.0 - rho * rho))
