"""练习 1.7：放射性衰变的面向对象实现与误差分析

物理模型（教材 1.1–1.5 节）
---------------------------
一阶衰变方程 (1.1)::

    dN_U/dt = -N_U / tau

解析解 (1.2)::

    N(t) = N0 * exp(-t/tau)

显式 Euler 格式 (1.3)-(1.4)::

    N_{k+1} = N_k - N_k * dt/tau = N_k * (1 - dt/tau)
    t_k     = k * dt,   k = 0, 1, ..., n

由于每一步的乘子 ``1 - dt/tau`` 是常数，数值解也可以写成闭式
``N0 * (1 - dt/tau)**k``；本实现仍按递推逐步计算，以便真正调用
``Decay.euler_step``，也便于以后替换成更复杂的模型。

程序结构
--------
::

    Decay               封装参数、校验属性、Euler 数值解与解析解
    error_sweep()       固定参数、扫描多个步长，得到最大绝对误差
    plot_decay()        1x3 面板图（解、误差、log-log 收敛）
    self_check()        按作业自查表逐项核对
    main()              运行并保存 decay_oop.png

运行::

    python decay_oop.py

分析题
------
1. ``error`` 恒为负：x=dt/tau>0 时 1-x <= exp(-x)，故 (1-dt/tau)^n <=
   exp(-t/tau)，等号只在 t=0；Euler 每步多扣，数值解系统性偏低（dt>tau
   时乘子变负，符号才交替）。
2. 斜率≈1：全局误差 ∝ dt（每步截断 O(dt^2)，n ∝ 1/dt 步累积），Euler 是
   一阶方法。改用精确递推 N_{k+1}=N_k*exp(-dt/tau) 后每步无截断误差，只剩
   ~1e-14 的浮点舍入，max_abs_error 与 dt 无关，右图变为水平线，斜率≈0。
3. dt=2.5 s > 2*tau：乘子 1-2.5=-1.5，|乘子|>1，每步放大 1.5 倍并变号，
   t=25 s 时 N=100*(-1.5)^10≈5.8e3，振荡发散、出现负核数；稳定边界为
   |1-dt/tau|<1 即 dt<2*tau（dt=2*tau 时临界等幅振荡）。
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

# 作业规定的固定参数（SI 单位：核数无量纲，时间 s）
N0_DEFAULT = 100.0
TAU_DEFAULT = 1.0
DT_DEFAULT = 0.2
T_MAX_DEFAULT = 5.0

# 右图扫描用的步长
DT_SWEEP = (0.5, 0.25, 0.2, 0.1, 0.05, 0.025)


def _check_positive(name: str, value: float) -> float:
    """把 value 转成 float，并要求它是有限正数，否则抛 ValueError。"""
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} 必须是有限正数，收到 {value!r}")
    return number


class Decay:
    """放射性衰变的 Euler 数值解与解析解。

    参数
    ----
    N0 : float
        初始核数（必须 > 0）。
    tau : float
        平均寿命，s（必须 > 0）。
    dt : float
        Euler 步长，s（必须 > 0）。
    t_max : float
        模拟总时长，s（必须 > 0）。

    所有计算属性都"现算"、不做缓存：修改 ``N0`` / ``tau`` / ``dt`` 之后，
    ``numerical``、``error``、``max_abs_error`` 会自动跟着更新。
    """

    def __init__(self, N0: float, tau: float, dt: float, t_max: float) -> None:
        # 走 setter，构造时也执行同一套校验
        self.N0 = N0
        self.tau = tau
        self.dt = dt
        self.t_max = t_max

    def __repr__(self) -> str:
        return (
            f"Decay(N0={self.N0:g}, tau={self.tau:g}, "
            f"dt={self.dt:g}, t_max={self.t_max:g})"
        )

    # ------------------------------------------------------------------
    # 参数：property + setter 校验
    # ------------------------------------------------------------------
    @property
    def N0(self) -> float:
        """初始核数。"""
        return self._N0

    @N0.setter
    def N0(self, value: float) -> None:
        self._N0 = _check_positive("N0", value)

    @property
    def tau(self) -> float:
        """平均寿命 tau，s。"""
        return self._tau

    @tau.setter
    def tau(self, value: float) -> None:
        self._tau = _check_positive("tau", value)

    @property
    def dt(self) -> float:
        """Euler 步长，s。"""
        return self._dt

    @dt.setter
    def dt(self, value: float) -> None:
        self._dt = _check_positive("dt", value)

    @property
    def t_max(self) -> float:
        """模拟总时长，s。"""
        return self._t_max

    @t_max.setter
    def t_max(self, value: float) -> None:
        self._t_max = _check_positive("t_max", value)

    # ------------------------------------------------------------------
    # 网格与解：全部现算
    # ------------------------------------------------------------------
    @property
    def n_steps(self) -> int:
        """完整步数 n = floor(t_max/dt)，保证 t_n <= t_max。"""
        # 加 1e-9 吸收 5/0.2 = 24.999... 这类二进制浮点误差
        return int(np.floor(self._t_max / self._dt + 1e-9))

    @property
    def t(self) -> np.ndarray:
        """Euler 取值点 t_k = k*dt（k = 0..n），与 numerical 一一对应。"""
        return np.arange(self.n_steps + 1, dtype=float) * self._dt

    @property
    def numerical(self) -> np.ndarray:
        """Euler 数值解 (1.4)。

        预先分配 ndarray 再逐步填值，而不是在循环里 list.append 后转换：
        长度已知时预分配更省内存、也不会在转换时多复制一份。
        """
        values = np.empty(self.n_steps + 1, dtype=float)
        values[0] = self._N0
        for k in range(self.n_steps):
            values[k + 1] = self.euler_step(values[k], self._dt, self._tau)
        return values

    @property
    def exact(self) -> np.ndarray:
        """解析解 (1.2) N0*exp(-t/tau)，取样点与 t 完全相同。"""
        return self._N0 * np.exp(-self.t / self._tau)

    @property
    def error(self) -> np.ndarray:
        """带符号的逐点误差 numerical - exact。"""
        return self.numerical - self.exact

    @property
    def max_abs_error(self) -> float:
        """最大绝对误差 max|numerical - exact|。"""
        return float(np.max(np.abs(self.error)))

    @property
    def half_life(self) -> float:
        """半衰期 t_1/2 = tau*ln(2)，s。"""
        return self._tau * math.log(2.0)

    # ------------------------------------------------------------------
    # 单步格式与备用构造函数
    # ------------------------------------------------------------------
    @staticmethod
    def euler_step(n: float, dt: float, tau: float) -> float:
        """单步 Euler：n - n*dt/tau = n*(1 - dt/tau)。"""
        return n - n * dt / tau

    @classmethod
    def from_half_life(
        cls, N0: float, t_half: float, dt: float, t_max: float
    ) -> "Decay":
        """用半衰期构造：tau = t_half / ln(2)。"""
        t_half = _check_positive("t_half", t_half)
        return cls(N0, t_half / math.log(2.0), dt, t_max)


def error_sweep(
    dts: tuple[float, ...] = DT_SWEEP,
    N0: float = N0_DEFAULT,
    tau: float = TAU_DEFAULT,
    t_max: float = T_MAX_DEFAULT,
) -> tuple[np.ndarray, np.ndarray]:
    """扫描一组步长，返回 (dts, 各自的最大绝对误差)。

    只构造一个 Decay 对象，反复改 ``dt``：这既是最省事的写法，也顺带
    验证了"属性现算、修改参数后结果自动更新"这一要求。
    """
    probe = Decay(N0, tau, dts[0], t_max)
    errors = []
    for dt in dts:
        probe.dt = dt
        errors.append(probe.max_abs_error)
    return np.asarray(dts, dtype=float), np.asarray(errors, dtype=float)


def plot_decay(
    path: str | Path = "decay_oop.png",
    *,
    N0: float = N0_DEFAULT,
    tau: float = TAU_DEFAULT,
    dt: float = DT_DEFAULT,
    t_max: float = T_MAX_DEFAULT,
    dts: tuple[float, ...] = DT_SWEEP,
) -> Path:
    """绘制 1x3 面板图并保存，返回图片路径。"""
    import matplotlib

    matplotlib.use("Agg")  # 无显示器环境也能存图
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Source Han Sans SC", "Noto Sans SC",
        "Noto Sans CJK SC", "PingFang SC", "Heiti SC", "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, (ax_t, ax_e, ax_c) = plt.subplots(
        1, 3, figsize=(15, 4.2), constrained_layout=True
    )

    d = Decay(N0, tau, dt, t_max)

    # ---- 左：解析解曲线 + Euler 散点 ----
    ax_t.plot(d.t, d.exact, "-", color="#1f77b4", lw=2.0,
              label="解析解 $N_0e^{-t/\\tau}$")
    ax_t.plot(d.t, d.numerical, "o", ms=5.5, mfc="white", mec="#d62728",
              mew=1.4, label=f"Euler 数值解（$\\Delta t={dt:g}$ s）")
    ax_t.set_xlabel("时间 $t$ / s")
    ax_t.set_ylabel("剩余核数 $N$")
    ax_t.set_title("解析解与 Euler 数值解")
    ax_t.grid(True, ls=":", alpha=0.6)
    ax_t.legend(loc="upper right", fontsize=9)

    # ---- 中：带符号误差 ----
    ax_e.axhline(0.0, color="0.35", lw=1.0, ls="--", label="零参考线")
    ax_e.plot(d.t, d.error, "o-", ms=3.6, lw=1.4, color="#d62728",
              label="$N_{\\mathrm{num}}-N_{\\mathrm{exact}}$")
    ax_e.fill_between(d.t, d.error, 0.0, color="#d62728", alpha=0.15)
    ax_e.set_xlabel("时间 $t$ / s")
    ax_e.set_ylabel("误差 $N_{\\mathrm{num}}-N_{\\mathrm{exact}}$")
    ax_e.set_title(
        f"逐点误差恒为负（$\\Delta t={dt:g}$ s，"
        f"最大绝对误差 {d.max_abs_error:.4f}）"
    )
    ax_e.grid(True, ls=":", alpha=0.6)
    ax_e.legend(loc="lower left", fontsize=9)

    # ---- 右：log-log 误差收敛 ----
    dts_arr, errs = error_sweep(dts, N0, tau, t_max)
    slope = float(np.polyfit(np.log(dts_arr), np.log(errs), 1)[0])

    ax_c.loglog(dts_arr, errs, "o-", color="#2ca02c", lw=1.8, ms=6,
                label="Euler 最大绝对误差")

    # 过第一个数据点、斜率严格为 1 的参考线，便于目测偏离程度
    reference = errs[0] * (dts_arr / dts_arr[0])
    ax_c.loglog(dts_arr, reference, "--", color="0.45", lw=1.3,
                label="斜率 1 参考线（$\\propto\\Delta t$）")

    ax_c.set_xlabel("步长 $\\Delta t$ / s")
    ax_c.set_ylabel("最大绝对误差 $\\max|N_{\\mathrm{num}}-N_{\\mathrm{exact}}|$")
    ax_c.set_title(f"误差随步长的收敛（拟合斜率 {slope:.2f}）")
    ax_c.grid(True, which="major", ls=":", alpha=0.6)
    ax_c.grid(True, which="minor", ls=":", alpha=0.25)

    # log 轴：1-2-5 主刻度（0.02/0.05/0.1/0.2/0.5 与 0.5/1/2/5/10），
    # 其余次刻度只画网格线不标字，避免挤成一团
    for axis in (ax_c.xaxis, ax_c.yaxis):
        axis.set_major_locator(LogLocator(base=10.0, subs=(1.0, 2.0, 5.0),
                                          numticks=24))
        axis.set_minor_locator(LogLocator(base=10.0,
                                          subs=(3.0, 4.0, 6.0, 7.0, 8.0, 9.0),
                                          numticks=24))
        axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        axis.set_minor_formatter(NullFormatter())

    ax_c.set_xlim(0.018, 0.68)
    ax_c.set_ylim(0.32, 18.0)
    ax_c.legend(loc="upper left", fontsize=8.5)

    path = Path(path)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------
# 自查表
# ----------------------------------------------------------------------
EXPECTED = {
    "half_life": 0.6931,
    "N5_dt02": 0.3778,
    "exact5": 0.6738,
    "maxerr_dt02": 4.0199,
    "maxerr_dt005": 0.9394,
    "ratio_05_025": 2.29,
    "ratio_005_0025": 2.02,
    "slope": 1.0,
}


def _relative_gap(value: float, expected: float) -> float:
    return abs(value - expected) / abs(expected)


def self_check(verbose: bool = True) -> list[str]:
    """按作业自查表逐项核对，返回不通过的条目（空列表表示全部通过）。"""
    failures: list[str] = []
    rows: list[tuple[str, str, str, bool]] = []

    def record(name: str, expected: str, actual: str, ok: bool) -> None:
        rows.append((name, expected, actual, ok))
        if not ok:
            failures.append(name)

    tol = 5e-3  # 作业给定 ±0.5%

    d = Decay(100.0, 1.0, 0.2, 5.0)
    dts_arr, errs = error_sweep()

    record("半衰期 / s", "0.6931",
           f"{d.half_life:.4f}",
           _relative_gap(d.half_life, EXPECTED["half_life"]) < tol)
    record("N(5)，dt=0.2", "0.3778",
           f"{d.numerical[-1]:.4f}",
           _relative_gap(d.numerical[-1], EXPECTED["N5_dt02"]) < tol)
    record("解析解 N(5)", "0.6738",
           f"{d.exact[-1]:.4f}",
           _relative_gap(d.exact[-1], EXPECTED["exact5"]) < tol)
    record("max_abs_error，dt=0.2", "4.0199",
           f"{d.max_abs_error:.4f}",
           _relative_gap(d.max_abs_error, EXPECTED["maxerr_dt02"]) < tol)
    record("max_abs_error，dt=0.05", "0.9394",
           f"{errs[list(dts_arr).index(0.05)]:.4f}",
           _relative_gap(errs[list(dts_arr).index(0.05)],
                         EXPECTED["maxerr_dt005"]) < tol)
    record("误差比 0.5→0.25", "2.29",
           f"{errs[0] / errs[1]:.2f}",
           _relative_gap(errs[0] / errs[1], EXPECTED["ratio_05_025"]) < 2e-2)
    record("误差比 0.05→0.025", "2.02",
           f"{errs[-2] / errs[-1]:.2f}",
           _relative_gap(errs[-2] / errs[-1], EXPECTED["ratio_005_0025"]) < 2e-2)

    slope = float(np.polyfit(np.log(dts_arr), np.log(errs), 1)[0])
    record("log-log 拟合斜率", "1.0 ± 0.1", f"{slope:.3f}", abs(slope - 1.0) <= 0.1)

    unstable = Decay(100.0, 1.0, 2.5, 25.0)
    record("dt=2.5, t=25 时 |N|", "> 1e3",
           f"{abs(unstable.numerical[-1]):.1f}",
           abs(unstable.numerical[-1]) > 1e3)

    # 校验：非法参数必须抛 ValueError
    bad_cases = 0
    for call in (lambda: Decay(100, -1.0, 0.2, 5),
                 lambda: setattr(Decay(100, 1.0, 0.2, 5), "dt", 0.0)):
        try:
            call()
        except ValueError:
            bad_cases += 1
    record("非法参数抛 ValueError", "2/2", f"{bad_cases}/2", bad_cases == 2)

    # 现算：改 dt 后 max_abs_error 立刻更新，无需手动重算
    live = Decay(100.0, 1.0, 0.2, 5.0)
    before = live.max_abs_error
    live.dt = 0.05
    after = live.max_abs_error
    record("d.dt=0.05 后自动更新", "4.0199→0.9394",
           f"{before:.4f}→{after:.4f}",
           _relative_gap(before, EXPECTED["maxerr_dt02"]) < tol
           and _relative_gap(after, EXPECTED["maxerr_dt005"]) < tol)

    # @classmethod：半衰期构造与 tau=1 的差异只来自 0.6931 的四舍五入
    via_half = Decay.from_half_life(100.0, 0.6931, 0.2, 5.0)
    gap = abs(via_half.max_abs_error - d.max_abs_error) / d.max_abs_error
    record("from_half_life 相对差", "< 1e-3", f"{gap:.1e}", gap < 1e-3)

    if verbose:
        print("\n自查表（N0=100, tau=1 s, t_max=5 s）")
        print("-" * 72)
        print(f"{'检查项':<26}{'期望值':<16}{'实测值':<18}{'结果'}")
        for name, expected, actual, ok in rows:
            mark = "通过" if ok else "失败"
            print(f"{name:<26}{expected:<16}{actual:<18}{mark}")
        print("-" * 72)
        if failures:
            print("未通过: " + "、".join(failures))
        else:
            print("全部通过。")

    return failures


def main() -> None:
    print("=" * 72)
    print("练习 1.7  放射性衰变：Euler 数值解、误差与稳定性")
    print("=" * 72)
    print(f"模型: dN/dt = -N/tau,  N0={N0_DEFAULT:g}, tau={TAU_DEFAULT:g} s, "
          f"t_max={T_MAX_DEFAULT:g} s")

    d = Decay(N0_DEFAULT, TAU_DEFAULT, DT_DEFAULT, T_MAX_DEFAULT)
    print(f"半衰期 t_1/2 = tau*ln2 = {d.half_life:.4f} s")
    print(f"dt=0.2 s: N(5) = {d.numerical[-1]:.4f}，解析值 "
          f"{d.exact[-1]:.4f}，max_abs_error = {d.max_abs_error:.4f}")

    failures = self_check()

    # 稳定性实验：dt > 2*tau 时解振荡发散
    print("\n稳定性实验（dt = 2.5 s > 2*tau）")
    for t_stop in (2.5, 5.0, 10.0, 25.0):
        u = Decay(100.0, 1.0, 2.5, t_stop)
        print(f"  t={t_stop:5.1f} s: N = {u.numerical[-1]:>10.1f} "
              f"(|1-dt/tau| = {abs(1 - 2.5):.2f}，每步放大 1.5 倍且变号)")

    out = plot_decay(Path(__file__).with_name("decay_oop.png"))
    print(f"\n三面板图已保存: {out}")
    print("图注：左=数值解 vs 解析解；中=误差恒为负；右=log-log 斜率≈1。")

    print("\n分析题要点")
    print("1. (1-dt/tau)^n <= exp(-t/tau)，Euler 每步多扣，数值解系统性偏低，"
          "故 error 恒为负。")
    print("2. 斜率≈1 表明全局误差 ∝ dt，Euler 为一阶方法；若用精确递推"
          " N_{k+1}=N_k exp(-dt/tau)，误差只剩浮点舍入，右图变水平线（斜率≈0）。")
    print("3. |1-dt/tau| > 1（dt > 2*tau）时误差每步放大并变号，解振荡发散；"
          "稳定边界为 dt < 2*tau。")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
