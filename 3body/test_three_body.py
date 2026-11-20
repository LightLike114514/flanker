"""Self-contained checks for the three-body code.

可直接运行:
    python test_three_body.py
若安装了 pytest, 也可以:
    python -m pytest -q test_three_body.py
"""

from __future__ import annotations

import numpy as np

from three_body import (
    LAGRANGE_OMEGA,
    accelerations,
    ic_figure_eight,
    ic_hierarchical,
    ic_lagrange,
    lagrange_exact_state,
    lagrange_force_residual,
    lagrange_growth_rate,
    pair_distances,
    perturb,
    simulate,
    total_energy,
    total_momentum,
)


def test_lagrange_force_balance():
    ic = ic_lagrange()
    a = accelerations(ic[:, :2])
    residual = np.max(np.abs(a + LAGRANGE_OMEGA**2 * ic[:, :2]))
    assert residual < 1e-12, residual
    assert np.allclose(pair_distances(ic[:, :2]), 1.0, atol=1e-12)


def test_lagrange_exact_solution():
    for t in [0.0, 1.3, 10.0, 50.0]:
        s = lagrange_exact_state(t)
        assert np.allclose(pair_distances(s[:, :2]), 1.0, atol=1e-12)
        assert lagrange_force_residual(t) < 1e-12


def test_lagrange_growth_rate():
    assert abs(lagrange_growth_rate() - 1.224744871) < 1e-6


def test_energy_conservation():
    sim = simulate(
        ic_figure_eight(),
        dt=0.002,
        method="dp45",
        t_max=5.0,
        max_step=0.005,
        rtol=1e-11,
        atol=1e-13,
    )
    assert sim.max_energy_error < 1e-9
    assert np.linalg.norm(total_momentum(sim.states[-1])) < 1e-10


def test_perturb_removes_com_velocity():
    ic = ic_lagrange()
    p = perturb(ic, 1e-4)
    assert np.linalg.norm(total_momentum(p)) < 1e-15
    # 相对速度改变: 星 1 与星 2 的 vx 差比原来大 1e-4
    delta = (p[0, 2] - p[1, 2]) - (ic[0, 2] - ic[1, 2])
    assert abs(delta - 1e-4) < 1e-14


def test_hierarchical_com_at_origin():
    ic = ic_hierarchical()
    assert np.linalg.norm(ic[:, :2].mean(axis=0)) < 1e-12
    assert np.linalg.norm(ic[:, 2:].mean(axis=0)) < 1e-12
    assert total_energy(ic) < 0


def test_figure_eight_bounded_short():
    sim = simulate(ic_figure_eight(), dt=0.002, method="dp45", t_max=10.0, max_step=0.005)
    assert not sim.stopped
    assert sim.min_pair_distance > 0.5
    assert sim.max_pair_distance < 3.0


def test_close_encounter_stops():
    ic = np.array(
        [
            [-1.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, -1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ]
    )
    sim = simulate(ic, dt=0.001, method="rk4", t_max=2.0)
    assert sim.stop_reason == "close_encounter"
    # 三体相互吸引使接近速度远大于自由粒子估计，约在 t≈0.54 触发
    assert 0.4 < sim.stop_time < 0.7


def _run_all():
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    for name, fn in tests:
        fn()
        print(f"PASS  {name}")
    print(f"\n{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
