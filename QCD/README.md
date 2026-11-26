# 二维格点点源模型中的 SOR 方法

计算物理研究型作业。完成必做任务 1–4，并选做提高任务 5（理论对照）。

> 说明：本题是一个**标量**的格点点源模型，借用“在格点上求解方程、研究源响应”的计算思想，
> **不是格点 QCD 模拟**；报告第 1 节与第 8.2 节对此有明确说明。

## 提交文件

| 文件 | 内容 |
|---|---|
| `二维格点点源模型中的SOR方法_报告.pdf` | 最终报告（封面 + 16 页正文，6 图 10 表） |
| `code/sor2d.py` | 求解器：逐点 SOR（反对角线向量化）、朴素实现、直接解、理论量 |
| `code/experiments.py` | 全部数值实验，输出 `results/results.json` 与 CSV |
| `code/plot_figures.py` | 生成 `figures/fig1`–`fig6` |
| `code/make_report_assets.py` | 从 JSON 生成报告的 LaTeX 宏与表格 |
| `report/main.tex` | 报告 LaTeX 源文件（XeLaTeX） |
| `results/` | 可复核的数值结果 |
| `figures/` | 报告插图（320 dpi PNG） |

## 复现

```powershell
python code/experiments.py        # 约 2 分钟，生成 results/results.json
python code/plot_figures.py       # 生成 figures/*.png
python code/make_report_assets.py # 生成 report/numbers.tex 与 report/tab_*.tex
cd report
xelatex main.tex
xelatex main.tex
```

环境：Python 3.14.7、NumPy 2.5.3、Matplotlib 3.11.2；LaTeX 使用 XeLaTeX（ctexart）。
程序不含随机数，所有参数、网格、初值和扫描顺序均在代码中固定。

## 主要结果

- 验证：`N=7,9` 与稠密直接解对照，阈值 `1e-4 → 1e-10` 时
  `ε∞ = 2.3e-5 → 1.1e-11`，满足 `ε∞ ≤ ||A⁻¹||∞ ||r||∞`；
  向量化实现与朴素逐点实现逐位相同（最大差为 0）。
- 基准：`N=31, m=0.5, ω=1.5`，`K=33`，`||r||∞=3.89e-7`，
  `u_max=0.376855`（源点），转置对称性达机器精度。
- 响应范围：`N=63`，`m=0.2, 0.5, 1.0` 的尾段衰减长度
  `ξ = 4.26, 1.74, 0.90` 格距，`mξ ≈ 0.85–0.90`，支持 `ξ ∝ 1/m`。
- `ω` 扫描：`N=63, m=0.5` 时最优平台约 `1.41–1.43`，`K=30`；
  Gauss–Seidel `K=68`，减少 `55.9%`（`S=2.27`）。
- 理论对照：`ω_exp = 1.684, 1.418, 1.174` 低于
  `ω_th = 1.741, 1.491, 1.249`；把阈值从 `1e-6` 收紧到 `1e-12`，
  经验最优从 `1.41` 移到 `1.47`，说明差异来自有限阈值下的瞬态/前因子效应。
