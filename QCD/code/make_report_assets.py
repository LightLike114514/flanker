"""从 results/results.json 生成报告用的 LaTeX 宏与表格。

用法:  python code/make_report_assets.py
输出:  report/numbers.tex, report/tab_*.tex
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
REPORT.mkdir(exist_ok=True)

with open(ROOT / "results" / "results.json", encoding="utf-8") as fh:
    D = json.load(fh)


def sci(x: float, nd: int = 2) -> str:
    """LaTeX 科学计数法 (不含 $)。"""
    if x == 0:
        return "0"
    e = int(math.floor(math.log10(abs(x))))
    m = x / 10**e
    if e == 0:
        return f"{m:.{nd}f}"
    return f"{m:.{nd}f}\\times10^{{{e}}}"


def num(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def pct(x: float, nd: int = 1) -> str:
    return f"{100*x:.{nd}f}\\%"


# ---------------------------------------------------------------------------
# 理论量
# ---------------------------------------------------------------------------
TOL = D["meta"]["tol"]
LN = math.log(1.0 / TOL)


def rho_gs(m: float) -> float:
    return (4.0 / (4.0 + m * m) * math.cos(math.pi / 64)) ** 2


def rho_j(m: float) -> float:
    return 4.0 / (4.0 + m * m) * math.cos(math.pi / 64)


def omega_th(m: float) -> float:
    r = rho_j(m)
    return 2.0 / (1.0 + math.sqrt(1.0 - r * r))


theory = {}
for m in (0.2, 0.5, 1.0):
    rj = rho_j(m)
    rg = rho_gs(m)
    wth = omega_th(m)
    theory[m] = {
        "rhoJ": rj,
        "rhoGS": rg,
        "wth": wth,
        "Ksor_asym": LN / math.log(1.0 / (wth - 1.0)),
        "Kgs_asym": LN / math.log(1.0 / rg),
        "S_asym": (LN / math.log(1.0 / rg)) / (LN / math.log(1.0 / (wth - 1.0))),
    }

# ---------------------------------------------------------------------------
# 宏
# ---------------------------------------------------------------------------
t1 = D["task1"]
t3 = D["task3"]
t4 = D["task4"]
runs = {r["m"]: r for r in D["task2"]["runs"]}
bnd = D["task2"]["boundary"]

M = {}
M["Nmain"] = "31"
M["Nscan"] = "63"
M["Mmain"] = "0.5"
M["Wmain"] = "1.5"
M["Tol"] = "10^{-6}"
M["MaxSweeps"] = "2\\times10^{5}"
M["KtaskI"] = str(t1["K"])
M["RestaskI"] = sci(t1["residual"], 2)
M["UmaxTaskI"] = num(t1["u_max"], 6)
M["SymTaskI"] = sci(t1["symmetry_rel"], 1)
M["ReflTaskI"] = sci(t1["reverse_symmetry"] / t1["u_max"], 1)
M["UMinTaskI"] = sci(t1["u_min"], 1)
M["RatioOne"] = num(t1["profile"][1] / t1["profile"][0], 3)

M["KA"] = str(t4["0.2"]["K_best"])
M["KB"] = str(t4["0.5"]["K_best"])
M["KC"] = str(t4["1.0"]["K_best"])
M["KgsA"] = str(t4["0.2"]["K_GS"])
M["KgsB"] = str(t4["0.5"]["K_GS"])
M["KgsC"] = str(t4["1.0"]["K_GS"])
M["SA"] = num(t4["0.2"]["S"], 2)
M["SB"] = num(t4["0.5"]["S"], 2)
M["SC"] = num(t4["1.0"]["S"], 2)
M["WexpA"] = num(t4["0.2"]["best_omega"], 3)
M["WexpB"] = num(t3["ultra_plateau"]["mid"], 3)
M["WexpC"] = num(t4["1.0"]["best_omega"], 3)
M["WthA"] = num(theory[0.2]["wth"], 4)
M["WthB"] = num(theory[0.5]["wth"], 4)
M["WthC"] = num(theory[1.0]["wth"], 4)
M["PlateauA"] = f"{t4['0.2']['plateau'][0]:.3f}--{t4['0.2']['plateau'][1]:.3f}"
M["PlateauB"] = f"{t4['0.5']['plateau'][0]:.3f}--{t4['0.5']['plateau'][1]:.3f}"
M["PlateauC"] = f"{t4['1.0']['plateau'][0]:.3f}--{t4['1.0']['plateau'][1]:.3f}"

M["XiA"] = num(runs[0.2]["xi"], 2)
M["XiB"] = num(runs[0.5]["xi"], 2)
M["XiC"] = num(runs[1.0]["xi"], 2)
M["ReA"] = str(runs[0.2]["r_e"])
M["ReB"] = str(runs[0.5]["r_e"])
M["ReC"] = str(runs[1.0]["r_e"])
M["RoneA"] = str(runs[0.2]["r_1pct"])
M["RoneB"] = str(runs[0.5]["r_1pct"])
M["RoneC"] = str(runs[1.0]["r_1pct"])
M["XiMA"] = num(0.2 * runs[0.2]["xi"], 2)
M["XiMB"] = num(0.5 * runs[0.5]["xi"], 2)
M["XiMC"] = num(1.0 * runs[1.0]["xi"], 2)

M["Kcoarse"] = str(t3["coarse_best"]["K"])
M["Kfine"] = str(t3["fine_best"]["K"])
M["Wcoarse"] = num(t3["coarse_best"]["omega"], 2)
M["Wfine"] = num(t3["fine_best"]["omega"], 2)
M["PlatLo"] = num(t3["ultra_plateau"]["omega_lo"], 3)
M["PlatHi"] = num(t3["ultra_plateau"]["omega_hi"], 3)
M["PlatMid"] = num(t3["ultra_plateau"]["mid"], 3)
M["RedThree"] = pct(t3["reduction"], 1)
M["Sthree"] = num(t3["speedup"], 2)

M["KgsAsymA"] = num(theory[0.2]["Kgs_asym"], 0)
M["KgsAsymB"] = num(theory[0.5]["Kgs_asym"], 0)
M["KgsAsymC"] = num(theory[1.0]["Kgs_asym"], 0)
M["KsorAsymA"] = num(theory[0.2]["Ksor_asym"], 1)
M["KsorAsymB"] = num(theory[0.5]["Ksor_asym"], 1)
M["KsorAsymC"] = num(theory[1.0]["Ksor_asym"], 1)
M["SthA"] = num(theory[0.2]["S_asym"], 2)
M["SthB"] = num(theory[0.5]["S_asym"], 2)
M["SthC"] = num(theory[1.0]["S_asym"], 2)

M["DxiA"] = num(100 * abs(bnd["0.2"]["xi_127_same_window"] / bnd["0.2"]["xi_63"] - 1), 2)
M["DxiB"] = num(100 * abs(bnd["0.5"]["xi_127_same_window"] / bnd["0.5"]["xi_63"] - 1), 2)
M["DxiC"] = num(100 * abs(bnd["1.0"]["xi_127_same_window"] / bnd["1.0"]["xi_63"] - 1), 2)
M["BndA"] = sci(bnd["0.2"]["max_rel_diff_k_le_20"], 2)
M["BndB"] = sci(bnd["0.5"]["max_rel_diff_k_le_20"], 2)
M["BndC"] = sci(bnd["1.0"]["max_rel_diff_k_le_20"], 2)
M["BndEdgeA"] = sci(bnd["0.2"]["max_rel_diff_k_le_31"], 2)

M["Elapsed"] = num(D["elapsed_seconds"], 1)

lines = ["% 本文件由 code/make_report_assets.py 自动生成, 请勿手工修改。"]
for key, val in M.items():
    lines.append(f"\\newcommand{{\\{key}}}{{{val}}}")
(REPORT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 1: 小网格直接解验证
# ---------------------------------------------------------------------------
rows = []
for r in D["verification"]:
    rows.append(
        " & ".join(
            [
                str(r["N"]),
                f"${sci(r['tol'], 0)}$",
                str(r["K"]),
                f"${sci(r['residual'], 2)}$",
                f"${sci(r['eps_inf'], 2)}$",
                num(r["eps_over_res"], 2),
                num(r["Ainv_inf"], 3),
                f"${sci(r['asymmetry'], 1)}$",
            ]
        )
        + r" \\"
    )
tab = r"""\begin{tabular}{cccccccc}
\toprule
$N$ & 阈值 & $K$ & $\|r\|_\infty$ & $\epsilon_\infty$ & $\epsilon_\infty/\|r\|_\infty$ & $\|A^{-1}\|_\infty$ & 非对称性 \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_verification.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 2: 响应范围指标
# ---------------------------------------------------------------------------
rows = []
for m in (0.2, 0.5, 1.0):
    r = runs[m]
    rows.append(
        " & ".join(
            [
                f"${m}$",
                num(r["u_max"], 4),
                str(r["r_e"]),
                str(r["r_1pct"]),
                num(r["xi"], 2),
                f"{r['xi_fit_range'][0]}--{r['xi_fit_range'][1]}",
                num(r["xi_R2"], 4),
                num(m * r["xi"], 2),
                num(1.0 / m, 2),
            ]
        )
        + r" \\"
    )
tab = r"""\begin{tabular}{ccccccccc}
\toprule
$m$ & $u_{\max}$ & $r_{1/e}$ & $r_{1\%}$ & $\xi$ & 拟合区间 & $R^2$ & $m\xi$ & $1/m$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_task2.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 3: 边界条件影响
# ---------------------------------------------------------------------------
rows = []
for m in ("0.2", "0.5", "1.0"):
    b = bnd[m]
    rows.append(
        " & ".join(
            [
                f"${m}$",
                num(b["xi_63"], 3),
                num(b["xi_127_same_window"], 3),
                f"${sci(b['max_rel_diff_k_le_20'], 2)}$",
                f"${sci(b['max_rel_diff_k_le_31'], 2)}$",
            ]
        )
        + r" \\"
    )
tab = r"""\begin{tabular}{ccccc}
\toprule
$m$ & $\xi_{63}$ & $\xi_{127}$ & $\max_{k\le20}|\Delta u|/u_0$ & $\max_{k\le31}|\Delta u|/u_0$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_boundary.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 4: 任务 3 粗扫
# ---------------------------------------------------------------------------
rows = []
for r in t3["coarse"]:
    rows.append(
        f"${r['omega']:.2f}$ & {r['K']} & ${sci(r['residual'], 2)}$" + r" \\"
    )
tab = r"""\begin{tabular}{ccc}
\toprule
$\omega$ & $K$ & $\|r\|_\infty$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_task3.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 5: 任务 4
# ---------------------------------------------------------------------------
rows = []
for m in ("0.2", "0.5", "1.0"):
    t = t4[m]
    rows.append(
        " & ".join(
            [
                f"${m}$",
                num(t3["ultra_plateau"]["mid"], 3) if m == "0.5" else num(t["best_omega"], 3),
                str(t["K_best"]),
                str(t["K_GS"]),
                num(t["S"], 2),
                num(theory[float(m)]["wth"], 4),
                f"{t['plateau'][0]:.3f}--{t['plateau'][1]:.3f}",
            ]
        )
        + r" \\"
    )
tab = r"""\begin{tabular}{ccccccc}
\toprule
$m$ & 实验最优 $\omega$ & $K_{\rm SOR}$ & $K_{\rm GS}$ & $S=K_{\rm GS}/K_{\rm SOR}$ & 理论 $\omega_{\rm th}$ & 最优平台 \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_task4.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 6: 谱半径核对
# ---------------------------------------------------------------------------
rows = []
for r in D["theory"]["rho_num"]:
    w = r["omega"]
    rj = D["theory"]["rho_J"]
    wth = D["theory"]["omega_th"]
    disc = max(0.0, w * w * rj * rj - 4.0 * (w - 1.0))
    rho = (w * rj + math.sqrt(disc)) ** 2 / 4.0 if w <= wth else w - 1.0
    rows.append(
        f"${w:.2f}$ & {r['rho_num']:.6f} & {rho:.6f} & ${sci(abs(r['rho_num']-rho), 1)}$"
        + r" \\"
    )
tab = r"""\begin{tabular}{cccc}
\toprule
$\omega$ & 数值 $\rho_{\rm SOR}$ & 公式 $\rho_{\rm SOR}$ & $|\Delta\rho|$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_rho.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 7: 理论对照 (转置)
# ---------------------------------------------------------------------------
def theory_row(label, key, fmt):
    vals = []
    for m in ("0.2", "0.5", "1.0"):
        vals.append(fmt(m))
    return label + " & " + " & ".join(vals) + r" \\"


rows = []
rows.append(theory_row(r"$\rho_J$", "rhoJ", lambda m: num(theory[float(m)]["rhoJ"], 4)))
rows.append(theory_row(r"$\omega_{\rm th}$", "wth", lambda m: num(theory[float(m)]["wth"], 4)))
def wexp(m):
    return t3["ultra_plateau"]["mid"] if m == "0.5" else t4[m]["best_omega"]

rows.append(theory_row(r"$\omega_{\rm exp}$", "wexp", lambda m: num(wexp(m), 3)))
rows.append(
    theory_row(
        r"$\Delta\omega=\omega_{\rm th}-\omega_{\rm exp}$",
        "dw",
        lambda m: num(theory[float(m)]["wth"] - wexp(m), 3),
    )
)
rows.append(theory_row(r"$K_{\rm SOR}$", "ksor", lambda m: str(t4[m]["K_best"])))
rows.append(
    theory_row(
        r"$K_{\rm SOR}^{\rm asym}$",
        "ksora",
        lambda m: num(theory[float(m)]["Ksor_asym"], 1),
    )
)
rows.append(theory_row(r"$K_{\rm GS}$", "kgs", lambda m: str(t4[m]["K_GS"])))
rows.append(
    theory_row(
        r"$K_{\rm GS}^{\rm asym}$",
        "kgsa",
        lambda m: num(theory[float(m)]["Kgs_asym"], 0),
    )
)
rows.append(theory_row(r"$S_{\rm exp}$", "sexp", lambda m: num(t4[m]["S"], 2)))
rows.append(theory_row(r"$S_{\rm th}$", "sth", lambda m: num(theory[float(m)]["S_asym"], 2)))

tab = r"""\begin{tabular}{lccc}
\toprule
量 & $m=0.2$ & $m=0.5$ & $m=1.0$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_theory.tex").write_text(tab, encoding="utf-8")

# ---------------------------------------------------------------------------
# 表 8: 阈值依赖
# ---------------------------------------------------------------------------
rows = []
for r in D["threshold_dependence"]:
    rows.append(
        f"${sci(r['tol'], 0)}$ & ${r['best_omega']:.2f}$ & {r['K']} & {r['K_GS']} & {r['K_GS']/r['K']:.2f}"
        + r" \\"
    )
tab = r"""\begin{tabular}{ccccc}
\toprule
阈值 $\epsilon$ & 经验最优 $\omega$ & $K_{\rm SOR}$ & $K_{\rm GS}$ & $S$ \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
"""
(REPORT / "tab_threshold.tex").write_text(tab, encoding="utf-8")

print("generated:")
for p in sorted(REPORT.glob("*.tex")):
    print(" ", p.name, p.stat().st_size)
print("\nnumbers (selected):")
for key in ("KtaskI", "RestaskI", "UmaxTaskI", "SA", "SB", "SC", "WexpA", "WexpB", "WexpC",
            "KgsAsymB", "KsorAsymB", "SthB", "DxiA", "BndA", "RedThree", "Sthree"):
    print(f"  \\{key} = {M[key]}")
