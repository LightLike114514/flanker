"""计算物理作业：含二次空气阻力的最佳发射参数

题目
----
炮弹从原点以初速度 v0、发射角 theta 射出，目标位于 (x_t, y_t) = (1000 m, 100 m)。
空气密度随高度按绝热模型变化::

    rho(y) = rho0 * (1 - a*y/T0)**alpha        (1 - a*y/T0 > 0)
    rho(y) = 0                                  (1 - a*y/T0 <= 0)

阻力为二次阻力，阻力系数按密度修正::

    B_2^*(y) = B_2 * rho(y)/rho0
    a_x = -(B_2^*(y)/m) * v * v_x
    a_y = -g - (B_2^*(y)/m) * v * v_y

用欧拉法积分弹道，在 10° <= theta <= 80°、100 m/s <= v0 <= 1000 m/s 内
寻找命中目标所需的最小初速度及对应发射角；若有多解，取发射角较小者。

程序结构
--------
::

    Projectile                  基类：公共参数 + 欧拉积分（理想无阻力弹道）
    └── AdiabaticDragProjectile 子类：绝热密度模型 + 高度相关二次阻力

主程序只调用 ``simulate()``，不重复编写欧拉迭代过程。

运行
----
    python projectile.py

结果输出到终端，弹道图保存为同目录下的 ``trajectory.png``。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# 题目给定的物理参数（SI 单位）
# ---------------------------------------------------------------------------
G = 9.8                    # 重力加速度, m/s^2
MASS = 10.0                # 炮弹质量, kg
DT = 0.01                  # 欧拉法时间步长, s
B2_OVER_M = 4.0e-5         # B_2/m, m^-1
A_LAPSE = 6.5e-3           # 绝热模型参数 a, K/m
T0 = 300.0                 # 地面温度, K
ALPHA = 2.5                # 绝热指数 alpha

TARGET = (1000.0, 100.0)   # 目标位置 (x_t, y_t), m
HIT_RADIUS = 2.0           # 命中判据: 与目标距离 < 2 m

ANGLE_RANGE = (10.0, 80.0)     # 发射角搜索范围, deg
SPEED_RANGE = (100.0, 1000.0)  # 初速度搜索范围, m/s


@dataclass
class Trajectory:
    """欧拉积分得到的弹道，各数组等长。"""

    t: np.ndarray
    x: np.ndarray
    y: np.ndarray
    vx: np.ndarray
    vy: np.ndarray

    @property
    def speed(self) -> np.ndarray:
        """速率 v = sqrt(vx^2 + vy^2)。"""
        return np.hypot(self.vx, self.vy)

    @property
    def max_height(self) -> float:
        """弹道最高点高度, m。"""
        return float(np.max(self.y))

    @property
    def landing_point(self) -> tuple[float, float]:
        """落地点 (x, y=0)，在最后两个时间步之间线性插值。"""
        if len(self.y) < 2 or self.y[-1] >= 0.0:
            return float(self.x[-1]), float(self.y[-1])
        frac = -self.y[-2] / (self.y[-1] - self.y[-2])
        return (
            float(self.x[-2] + frac * (self.x[-1] - self.x[-2])),
            0.0,
        )

    @property
    def flight_time(self) -> float:
        """落地总飞行时间, s。"""
        if len(self.t) < 2 or self.y[-1] >= 0.0:
            return float(self.t[-1])
        frac = -self.y[-2] / (self.y[-1] - self.y[-2])
        return float(self.t[-2] + frac * (self.t[-1] - self.t[-2]))

    @property
    def range(self) -> float:
        """射程（落地点水平距离）, m。"""
        return self.landing_point[0]

    def closest_approach(self, point: tuple[float, float] = TARGET) -> float:
        """弹道折线到给定点的最短距离, m。

        逐段做点到线段的投影，比只检查离散节点更精确，避免因 dt 较大而
        漏掉两次采样之间的最近点。
        """
        if len(self.x) == 1:
            return math.hypot(self.x[0] - point[0], self.y[0] - point[1])

        px = self.x - point[0]
        py = self.y - point[1]
        ax, ay = px[:-1], py[:-1]
        dx, dy = px[1:] - ax, py[1:] - ay
        denom = dx * dx + dy * dy
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(denom > 0.0, -(ax * dx + ay * dy) / denom, 0.0)
        t = np.clip(t, 0.0, 1.0)
        cx = ax + t * dx
        cy = ay + t * dy
        return float(np.min(np.hypot(cx, cy)))

    def hits(self, point: tuple[float, float] = TARGET,
             radius: float = HIT_RADIUS) -> bool:
        """是否命中目标（最近距离小于命中半径）。"""
        return self.closest_approach(point) < radius

    def time_at_x(self, x_value: float) -> float:
        """弹道经过给定水平位置的时间, s（线性插值）。"""
        return float(np.interp(x_value, self.x, self.t))


class Projectile:
    """基类：公共参数与欧拉法积分过程（默认无阻力）。

    参数
    ----
    v0 : float
        初速度大小, m/s。
    angle_deg : float
        发射角, 度。
    dt : float
        欧拉法时间步长, s。
    mass : float
        炮弹质量, kg。
    """

    def __init__(self, v0: float, angle_deg: float,
                 dt: float = DT, mass: float = MASS) -> None:
        if v0 <= 0.0:
            raise ValueError("v0 必须为正数")
        if not 0.0 < angle_deg < 90.0:
            raise ValueError("发射角必须在 (0, 90) 度之间")
        self.v0 = float(v0)
        self.angle_deg = float(angle_deg)
        self.dt = float(dt)
        self.mass = float(mass)

        theta = math.radians(self.angle_deg)
        self.vx0 = self.v0 * math.cos(theta)
        self.vy0 = self.v0 * math.sin(theta)

    # -- 物理模型：子类通过重写下面的方法加入新物理 ------------------------
    def acceleration(self, vx: float, vy: float, y: float) -> tuple[float, float]:
        """返回 (a_x, a_y)。

        基类只考虑重力，作为无阻力对照；子类必须重写本方法以加入空气阻力。
        """
        return 0.0, -G

    # -- 欧拉法积分：整个继承体系中只在这里实现一次 ------------------------
    def simulate(self, x_stop: float | None = None,
                 max_time: float = 200.0) -> Trajectory:
        """用显式欧拉法积分弹道。

        欧拉格式（与题目一致）::

            x_{i+1} = x_i + v_x,i * dt
            y_{i+1} = y_i + v_y,i * dt
            v_x,i+1 = v_x,i + a_x,i * dt
            v_y,i+1 = v_y,i + a_y,i * dt

        参数
        ----
        x_stop : float, optional
            当 x 达到该值时提前停止（用于快速求给定水平位置处的高度）。
        max_time : float
            最长模拟时间, s。
        """
        dt = self.dt
        x = y = 0.0
        vx, vy = self.vx0, self.vy0

        ts = [0.0]
        xs = [x]
        ys = [y]
        vxs = [vx]
        vys = [vy]

        for _ in range(int(max_time / dt)):
            # 当前状态下的加速度
            ax, ay = self.acceleration(vx, vy, y)

            # 欧拉更新：位置用旧速度，速度用当前加速度
            x_new = x + vx * dt
            y_new = y + vy * dt
            vx_new = vx + ax * dt
            vy_new = vy + ay * dt

            x, y, vx, vy = x_new, y_new, vx_new, vy_new
            ts.append(ts[-1] + dt)
            xs.append(x)
            ys.append(y)
            vxs.append(vx)
            vys.append(vy)

            if y < 0.0:          # 落地
                break
            if x_stop is not None and x >= x_stop:  # 到达指定水平位置
                break

        return Trajectory(
            t=np.asarray(ts),
            x=np.asarray(xs),
            y=np.asarray(ys),
            vx=np.asarray(vxs),
            vy=np.asarray(vys),
        )


class AdiabaticDragProjectile(Projectile):
    """绝热空气密度模型 + 高度相关二次阻力。"""

    def density_ratio(self, y: float) -> float:
        """rho(y)/rho0 = (1 - a*y/T0)**alpha，括号内 <= 0 时取 0。"""
        factor = 1.0 - A_LAPSE * y / T0
        if factor <= 0.0:
            return 0.0
        return factor ** ALPHA

    def acceleration(self, vx: float, vy: float, y: float) -> tuple[float, float]:
        """重写基类的加速度：重力 + 高度相关二次阻力。

            B_2^*(y) = B_2 * rho(y)/rho0
            a_x = -(B_2^*(y)/m) * v * v_x
            a_y = -g - (B_2^*(y)/m) * v * v_y
        """
        k = B2_OVER_M * self.density_ratio(y)   # B_2^*(y)/m
        v = math.hypot(vx, vy)
        return -k * v * vx, -G - k * v * vy


@dataclass
class LaunchSolution:
    """一个可行发射方案。"""

    angle_deg: float
    speed: float
    trajectory: Trajectory

    @property
    def miss_distance(self) -> float:
        """与目标的最近距离, m。"""
        return self.trajectory.closest_approach(TARGET)


def _vertical_miss(projectile_cls: type[Projectile], speed: float,
                   angle_deg: float, target: tuple[float, float],
                   dt: float) -> float:
    """弹道在 x = x_t 处的高度与目标高度之差。

    落点够不到目标时返回 -inf；该函数关于 speed 单调递增，可用于二分。
    """
    traj = projectile_cls(speed, angle_deg, dt=dt).simulate(x_stop=target[0])
    if traj.x[-1] < target[0]:
        return -math.inf
    return float(np.interp(target[0], traj.x, traj.y)) - target[1]


def minimum_speed_for_angle(
    angle_deg: float,
    projectile_cls: type[Projectile] = AdiabaticDragProjectile,
    target: tuple[float, float] = TARGET,
    dt: float = DT,
    speed_range: tuple[float, float] = SPEED_RANGE,
    hit_radius: float = HIT_RADIUS,
    iterations: int = 32,
) -> LaunchSolution | None:
    """固定发射角，二分搜索能命中目标的最小初速度。

    对固定角度，弹道在 x_t 处的高度随 v0 单调上升，因此可对
    ``y(x_t) - y_t`` 的符号做二分。收敛后再用完整弹道检查最近距离。
    """
    lo, hi = speed_range

    if _vertical_miss(projectile_cls, lo, angle_deg, target, dt) > 0.0:
        return None  # 最小速度已经越过目标（本题参数下不会出现）
    if _vertical_miss(projectile_cls, hi, angle_deg, target, dt) < 0.0:
        return None  # 最大速度仍打不到

    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if _vertical_miss(projectile_cls, mid, angle_deg, target, dt) < 0.0:
            lo = mid
        else:
            hi = mid

    speed = 0.5 * (lo + hi)
    trajectory = projectile_cls(speed, angle_deg, dt=dt).simulate()
    if not trajectory.hits(target, hit_radius):
        return None
    return LaunchSolution(angle_deg, speed, trajectory)


def search_best_launch(
    target: tuple[float, float] = TARGET,
    angle_range: tuple[float, float] = ANGLE_RANGE,
    coarse_step: float = 0.5,
    fine_step: float = 0.05,
    dt: float = DT,
    projectile_cls: type[Projectile] = AdiabaticDragProjectile,
) -> tuple[LaunchSolution, list[tuple[float, float]]]:
    """在角度范围内搜索最小初速度方案。

    返回最优方案，以及 (角度, 该角度所需最小初速度) 的粗扫描曲线。
    多个角度速度相同时取发射角较小者（升序扫描 + 严格小于比较）。
    """
    curve: list[tuple[float, float]] = []
    best: LaunchSolution | None = None

    for angle in np.arange(angle_range[0], angle_range[1] + 1e-9, coarse_step):
        solution = minimum_speed_for_angle(
            float(angle), projectile_cls=projectile_cls, target=target,
            dt=dt, iterations=24,
        )
        if solution is None:
            continue
        curve.append((float(angle), solution.speed))
        if best is None or solution.speed < best.speed - 1e-9:
            best = solution

    if best is None:
        raise RuntimeError("搜索范围内没有可行方案")

    # 在粗扫描最优点附近做精细搜索，确定最优角度
    center = best.angle_deg
    lo = max(angle_range[0], center - coarse_step)
    hi = min(angle_range[1], center + coarse_step)
    for angle in np.arange(lo, hi + 1e-9, fine_step):
        solution = minimum_speed_for_angle(
            float(angle), projectile_cls=projectile_cls, target=target, dt=dt,
        )
        if solution is not None and solution.speed < best.speed - 1e-9:
            best = solution

    return best, curve


def analyse(solution: LaunchSolution, vacuum: LaunchSolution) -> list[str]:
    """生成结果分析文字（空气密度随高度降低的影响）。"""
    traj = solution.trajectory
    apex = traj.max_height
    rho_apex = AdiabaticDragProjectile(solution.speed, solution.angle_deg).density_ratio(apex)

    v_launch = solution.speed
    drag_launch = B2_OVER_M * v_launch ** 2
    v_apex = float(np.hypot(traj.vx[int(np.argmax(traj.y))],
                            traj.vy[int(np.argmax(traj.y))]))
    drag_apex = B2_OVER_M * rho_apex * v_apex ** 2

    lines = [
        "空气密度随高度降低的影响：",
        f"  - 最高点 y = {apex:.1f} m 处，rho/rho0 = {rho_apex:.4f}，"
        f"空气密度仅比地面低 {(1 - rho_apex) * 100:.2f}%。",
        f"  - 出射时阻力加速度 {drag_launch:.3f} m/s^2（约 {drag_launch / G * 100:.1f}% g）；"
        f"最高点处 {drag_apex:.3f} m/s^2（约 {drag_apex / G * 100:.1f}% g）。",
        f"  - 与无阻力理想弹道相比，最小初速度由 {vacuum.speed:.2f} m/s 增至 "
        f"{solution.speed:.2f} m/s（+{(solution.speed / vacuum.speed - 1) * 100:.2f}%），",
        f"    最佳发射角由 {vacuum.angle_deg:.2f}° 变为 {solution.angle_deg:.2f}°。",
        "  - 由于密度随高度降低，高处阻力小于地面值，弹道被“削短”的程度减弱；",
        f"    本题最大高度约 {apex:.0f} m，密度仍有地面的 {rho_apex * 100:.1f}% 以上，"
        "故阻力影响较小，",
        "    结果接近真空弹道，但仍需略大的初速度和略小的发射角。",
    ]
    return lines


def plot_solution(solution: LaunchSolution,
                  curve: list[tuple[float, float]],
                  vacuum: LaunchSolution | None = None,
                  path: str | Path = "trajectory.png") -> Path:
    """绘制弹道、目标位置以及“最小初速度-发射角”曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    traj = solution.trajectory
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 5.0),
                                    constrained_layout=True)

    # ---- 左图：弹道 ----
    ax1.plot(traj.x, traj.y, color="tab:blue", lw=2.0, label="含空气阻力弹道")
    ax1.plot(0.0, 0.0, "o", color="tab:green", ms=7, label="发射点")
    ax1.plot(*TARGET, "o", mfc="none", mec="tab:red", mew=2.0, ms=10,
             label="目标 (1000, 100) m")
    ax1.set_xlabel("水平距离 x / m")
    ax1.set_ylabel("高度 y / m")
    ax1.set_title("炮弹弹道与目标位置")
    ax1.grid(True, ls=":", alpha=0.6)
    ax1.set_aspect("equal", adjustable="box")
    ax1.set_xlim(-10, 1120)
    ax1.set_ylim(-10, 330)
    ax1.legend(loc="upper left", fontsize=9)

    info = (
        f"$\\theta$ = {solution.angle_deg:.2f}°    "
        f"$v_0$ = {solution.speed:.2f} m/s\n"
        f"命中点最近距离 = {solution.miss_distance:.3f} m    "
        f"最高点 h = {traj.max_height:.1f} m    "
        f"射程 R = {traj.range:.1f} m"
    )
    ax1.text(0.5, -0.20, info, transform=ax1.transAxes, ha="center", va="top",
             fontsize=9.5,
             bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.9))

    # 目标附近放大，显示 2 m 命中半径
    inset = ax1.inset_axes([0.48, 0.10, 0.34, 0.26])
    inset.plot(traj.x, traj.y, color="tab:blue", lw=1.6)
    inset.plot(*TARGET, "o", mfc="none", mec="tab:red", mew=1.6, ms=7)
    inset.add_patch(plt.Circle(TARGET, HIT_RADIUS, fill=False,
                               ls="--", ec="tab:orange", lw=1.2))
    inset.set_xlim(TARGET[0] - 6, TARGET[0] + 6)
    inset.set_ylim(TARGET[1] - 6, TARGET[1] + 6)
    inset.tick_params(labelsize=7)
    inset.set_title("目标附近放大（虚线圆 R = 2 m）", fontsize=8)
    inset.grid(True, ls=":", alpha=0.5)

    # ---- 右图：最小初速度随发射角的变化 ----
    angles = np.array([a for a, _ in curve])
    speeds = np.array([v for _, v in curve])
    ax2.plot(angles, speeds, color="tab:purple", lw=1.8,
             label="数值搜索：各角度所需最小 $v_0$")
    ax2.plot(solution.angle_deg, solution.speed, "*", color="tab:red", ms=14,
             label=f"最优解 ({solution.angle_deg:.2f}°, {solution.speed:.2f} m/s)")

    if vacuum is not None:
        ax2.axhline(vacuum.speed, color="0.4", ls="--", lw=1.2,
                    label=f"无阻力最小初速度 {vacuum.speed:.2f} m/s")

    ax2.set_xlabel("发射角 $\\theta$ / (°)")
    ax2.set_ylabel("最小初速度 $v_0$ / (m/s)")
    ax2.set_title("最小初速度随发射角的变化")
    ax2.grid(True, ls=":", alpha=0.6)
    ax2.legend(loc="upper center", fontsize=8)

    path = Path(path)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    # 1) 含绝热二次阻力的最优发射方案
    best, curve = search_best_launch()
    traj = best.trajectory

    # 2) 理想无阻力弹道作为对照（复用同一个搜索与 simulate，体现继承的意义）
    vacuum, _ = search_best_launch(projectile_cls=Projectile)

    t_hit = traj.time_at_x(TARGET[0])

    print("=" * 62)
    print("含二次空气阻力的最佳发射参数")
    print("=" * 62)
    # 作业要求规定的四项输出
    print(f"最佳发射角度：{best.angle_deg:.2f} °")
    print(f"最小初速度：{best.speed:.2f} m/s")
    print(f"飞行时间：{t_hit:.2f} s")
    print(f"最高高度：{traj.max_height:.2f} m")
    print("-" * 62)
    print(f"说明：飞行时间按“发射到命中目标”计；若继续积分至落地，总飞行时间 "
          f"{traj.flight_time:.2f} s。")
    print(f"命中目标时弹道与目标的最近距离 {best.miss_distance:.3f} m（判据 < {HIT_RADIUS:.1f} m），"
          f"落地射程 {traj.range:.2f} m。")
    print(f"对照：无阻力时 v0 = {vacuum.speed:.2f} m/s，θ = {vacuum.angle_deg:.2f} °")
    print()
    for line in analyse(best, vacuum):
        print(line)

    out = plot_solution(best, curve, vacuum,
                        path=Path(__file__).with_name("trajectory.png"))
    print(f"\n弹道图已保存: {out}")


if __name__ == "__main__":
    main()
