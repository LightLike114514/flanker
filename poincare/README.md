# 第六周作业：受迫阻尼非线性摆的庞加莱截面

本目录是《计算物理》第六周作业的完整提交。**计算与绘图源码只有一个文件**
`pendulum_poincare.py`，运行一次即可生成报告中全部 5 幅图与数值结果。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `pendulum_poincare.py` | 唯一计算源码：模型、Euler–Cromer 积分、截面采样、Lyapunov 指数、盒计数与全部图件 |
| `第六周作业报告.docx` | 计算报告正文（公式、图表、讨论、选做盒计数） |
| `第六周作业报告.pdf` | 同一报告的 PDF 版本 |
| `figures/` | 报告用图（fig1–fig5 及三级放大单独图）与公式图片 |
| `data/summary.json` | 全部数值指标（重叠度、λ_max、D_B、D_KY 等） |
| `data/poincare_*.npz` | 高分辨率截面数据，可直接复现局部放大图 |
| `report_builder/` | 可选的 Word 排版工具（`build_report.py`、`make_equations.py`），不属于计算源码 |
| `新建 文本文档.txt` | 原始作业要求 |

## 运行

```powershell
python pendulum_poincare.py          # 完整计算，约 2.5 分钟
python pendulum_poincare.py --quick  # 快速自检，约 5 秒（点数少，盒维数无意义）
```

`--quick` 的结果写到 `figures_quick/` 和 `data/summary_quick.json`，不会覆盖正式图件和数据。
依赖：Python 3.10+、NumPy、Matplotlib。完整运行后生成/覆盖
`figures/` 与 `data/` 中的文件，并在终端打印全部指标。

主要输出：

- `figures/fig1_poincare_ic.png`：三组初值的截面与叠加；
- `figures/fig2_timestep.png`：Δt = 0.04 / 0.02 / 0.01 对比；
- `figures/fig3_zoom.png`：全局截面 + 三级局部放大（另有 `fig3_zoom1..3.png`）；
- `figures/fig4_boxcount.png`：盒计数 log N–log(1/ε) 与局部斜率；
- `figures/fig5_dt_zoom.png`：局部“发卡”结构随步长的变化；
- `data/summary.json`、`data/poincare_hr.npz`、`data/poincare_dt0.02.npz`、`data/poincare_dt0.04.npz`。

## 主要结果

- 三组初值（0.2,0）、(0.8,0)、(−1.0,0.5) 舍弃 300T_D 暂态后落在同一细丝状吸引子上，
  截面粗粒化重叠度 0.92–0.94。
- 最大 Lyapunov 指数 λ_max ≈ 0.137 s⁻¹（切空间变分方程复核 0.136）。
- Kaplan–Yorke 维数 D_KY ≈ 1.22；盒计数给出 D_B ≈ 1.07（局部斜率随尺度缓慢上升）。
- Δt = 0.04 / 0.02 / 0.01 的整体轮廓与统计量一致；最细丝位置存在 O(Δt) 漂移
  （Δt = 0.04 与 0.01 之间最近邻中位数约 3.7×10⁻³）。
- θ > 2 区域三级放大（线性尺度缩小约 47 倍）仍保留“丝束—裂隙”结构，且该结构
  在三种步长下可重复，不是采样或数值假象。

## 数值方法要点

- Euler–Cromer：先更新角速度，再用新角速度推进角度；每步把 θ 约化到 [−π, π]。
- 每个驱动周期分成 `N = int(T_D/Δt)` 个整步加一个长度 `h = T_D − NΔt` 的尾步，
  使采样严格发生在 `t_n = nT_D`，避免插值平滑掉细丝。
- 主截面每组 2000 点；放大与盒计数使用单条轨道 6×10⁵ 点（Δt = 0.01）。

## 可选：重新生成 Word 报告

报告排版与公式图片的生成脚本单独放在 `report_builder/`，只在需要修改报告文字时使用，
需要装有 `python-docx` 的环境：

```powershell
python report_builder/make_equations.py   # 公式 PNG（通常无需重跑）
python report_builder/build_report.py     # 读取 data/summary.json 与 figures/ 生成 docx
```
