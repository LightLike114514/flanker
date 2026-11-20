"""Generate the Chinese DOCX report from results/summary.json.

用法:
    python make_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
FIGURES = BASE / "figures"
REPORT = BASE / "report"
REPORT.mkdir(exist_ok=True)

with (RESULTS / "summary.json").open(encoding="utf-8") as f:
    S = json.load(f)

MODES = S["modes"]
LAG = S["lagrange"]


# ---------------------------------------------------------------------------
# 格式化工具
# ---------------------------------------------------------------------------
def f(x: float, n: int = 4) -> str:
    return f"{x:.{n}f}"


def sci(x: float, n: int = 2) -> str:
    if x == 0:
        return "0"
    return f"{x:.{n}e}"


def set_run(run, size=11, bold=False, italic=False, color=None, cn="宋体", en="Times New Roman"):
    run.font.name = en
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), cn)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def add_rich(paragraph, text, size=11, color=None, cn="宋体", en="Times New Roman"):
    """支持 **粗体** 的简易富文本."""
    parts = text.split("**")
    for k, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        set_run(run, size=size, bold=(k % 2 == 1), color=color, cn=cn, en=en)


def shade_cell(cell, fill="D9E2F3"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell_text(cell, text, size=8.5, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    lines = str(text).split("\n")
    for k, line in enumerate(lines):
        if k:
            p.add_run().add_break()
        run = p.add_run(line)
        set_run(run, size=size, bold=bold, cn="宋体")


class Report:
    def __init__(self):
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_height = Cm(29.7)
        section.page_width = Cm(21.0)
        section.top_margin = Cm(2.4)
        section.bottom_margin = Cm(2.3)
        section.left_margin = Cm(2.7)
        section.right_margin = Cm(2.5)

        style = self.doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(11)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_after = Pt(5)

        # 页眉页脚
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run("计算物理作业 · 三体问题")
        set_run(hr, size=9, color=(0x66, 0x66, 0x66))
        self._add_page_number(section)

    @staticmethod
    def _add_page_number(section):
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        fld1 = OxmlElement("w:fldChar")
        fld1.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        fld2 = OxmlElement("w:fldChar")
        fld2.set(qn("w:fldCharType"), "end")
        run._r.append(fld1)
        run._r.append(instr)
        run._r.append(fld2)
        set_run(run, size=9, color=(0x66, 0x66, 0x66))

    def h1(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        set_run(run, size=15, bold=True, cn="微软雅黑", en="Arial")
        # 下边框
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "2")
        bottom.set(qn("w:color"), "1F4E79")
        pBdr.append(bottom)
        pPr.append(pBdr)

    def h2(self, text):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        set_run(run, size=12.5, bold=True, cn="微软雅黑", en="Arial")

    def p(self, text, indent=True, size=11, align=None, space_after=5):
        p = self.doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(space_after)
        if indent:
            p.paragraph_format.first_line_indent = Pt(22)
        if align is not None:
            p.alignment = align
        add_rich(p, text, size=size)

    def bullet(self, text, size=11):
        p = self.doc.add_paragraph(style="List Bullet")
        p.paragraph_format.line_spacing = 1.4
        p.paragraph_format.space_after = Pt(2)
        add_rich(p, text, size=size)

    def eq(self, text, number=None):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        set_run(run, size=11, italic=False, cn="宋体", en="Cambria Math")
        if number:
            run2 = p.add_run("    " + number)
            set_run(run2, size=10.5, cn="宋体")
        return p

    def caption(self, text):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(text)
        set_run(run, size=9, color=(0x55, 0x55, 0x55))

    def figure(self, filename, caption, width=15.4):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run()
        run.add_picture(str(FIGURES / filename), width=Cm(width))
        self.caption(caption)

    def table(self, headers, rows, widths=None, caption=None, font_size=8.5, header_fill="D9E2F3"):
        if caption:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(caption)
            set_run(run, size=9, color=(0x55, 0x55, 0x55))

        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        hdr = table.rows[0]
        trPr = hdr._tr.get_or_add_trPr()
        tblHeader = OxmlElement("w:tblHeader")
        tblHeader.set(qn("w:val"), "true")
        trPr.append(tblHeader)
        for j, htext in enumerate(headers):
            cell = hdr.cells[j]
            if widths:
                cell.width = Cm(widths[j])
            set_cell_text(cell, htext, size=font_size, bold=True)
            shade_cell(cell, header_fill)

        for row in rows:
            cells = table.add_row().cells
            for j, val in enumerate(row):
                if widths:
                    cells[j].width = Cm(widths[j])
                set_cell_text(cells[j], val, size=font_size)

        # 禁止单行跨页；并尽量让整张表保持在同一页
        for row in table.rows:
            trPr = row._tr.get_or_add_trPr()
            cantSplit = OxmlElement("w:cantSplit")
            trPr.append(cantSplit)
        for row in table.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True

        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def page_break(self):
        self.doc.add_page_break()

    def save(self, path):
        self.doc.save(str(path))


# ---------------------------------------------------------------------------
# 正文
# ---------------------------------------------------------------------------
def build():
    r = Report()

    # ---------------- 封面 ----------------
    for _ in range(4):
        r.doc.add_paragraph()
    p = r.doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("计算物理作业")
    set_run(run, size=26, bold=True, cn="微软雅黑", en="Arial")

    p = r.doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    run = p.add_run("《三体》中的稳定运动模式")
    set_run(run, size=22, bold=True, cn="微软雅黑", en="Arial")

    p = r.doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("—— 平面等质量三体问题的有界运动与扰动稳定性")
    set_run(run, size=12, cn="楷体", en="Times New Roman", color=(0x44, 0x44, 0x44))

    for _ in range(6):
        r.doc.add_paragraph()
    for line in [
        "姓　　名：____________________",
        "学　　号：____________________",
        "专　　业：____________________",
        "日　　期：2026 年 11 月",
    ]:
        p = r.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(line)
        set_run(run, size=12, cn="宋体")
    r.page_break()

    # ---------------- 摘要 ----------------
    r.h1("摘要")
    r.p(
        "本文用四阶 Runge–Kutta（RK4）与自适应 Dormand–Prince（DP45）方法数值研究平面等质量三体问题，"
        "在 0≤t≤50 内检验了四种有界运动模式：Lagrange 等边三角形、8 字形、飞蛾 I 和层级三体"
        "（紧密双星 + 远方第三体）。模式 A 有解析解，三对距离恒为 1，但线性稳定性分析给出增长率 "
        "λ=1.2247：10⁻⁴ 的速度扰动在 t≈8 后使三角形瓦解，t≈15.55 触发 0.05 的近距离预警；"
        "双精度数值积分也会因舍入误差在 t≈30 后偏离解析解。模式 B 的 8 字形在 50 时间内保持有界，"
        "扰动分离仅 6.3×10⁻³。模式 C 的飞蛾轨道最小距离 0.0794，扰动后有界但接近阈值；"
        "模式 D 的层级三体最小距离 0.399，扰动分离 4.7×10⁻⁴，表现出时间尺度分离带来的鲁棒性。"
        "步长检验表明：8 字形的 RK4 能量误差从 6.6×10⁻¹² 降到 3.1×10⁻¹⁴，"
        "而飞蛾模式在近距离交会处对步长敏感——Δt=0.002 与 0.001 的最大位置差为 0.042、"
        "最小距离差 0.029，因此扰动实验必须使用高精度自适应积分。结果说明：有限时间有界不等于对扰动稳定，"
        "周期轨道也不自动稳定；能量守恒不能代替轨迹精度。",
        indent=True,
    )
    r.p("关键词：三体问题；周期轨道；Lagrange 三角形；8 字形；扰动稳定性；能量误差", indent=False)

    # ---------------- 1 问题与模型 ----------------
    r.h1("一、问题与物理模型")
    r.p(
        "题目要求寻找三颗等质量恒星在有限时间 0≤t≤50 内保持有界的运动模式，并比较它们对初始扰动的响应。"
        "取 G=1、m₁=m₂=m₃=1，恒星在同一平面内运动，只受相互牛顿引力作用。位置 r_i=(x_i,y_i)，"
        "运动方程为"
    )
    r.eq("d²r_i/dt² = Σ_{j≠i} (r_j − r_i) / |r_j − r_i|³ ,   i=1,2,3.", "(1)")
    r.p(
        "总能量、总角动量和质心分别为"
    )
    r.eq("E = ½ Σ_i |v_i|² − Σ_{i<j} 1/|r_i − r_j| ,   L = Σ_i (x_i v_{iy} − y_i v_{ix}).", "(2)")
    r.eq("R_cm = (1/3) Σ_i r_i ,   V_cm = (1/3) Σ_i v_i.", "(3)")
    r.p(
        "所有初始条件均取质心在原点、总动量为零。数值预警条件为：任意两星距离 d_ij<0.05 时停止该组计算并记录时间；"
        "一个模式要计入“有界模式”，还要求整个 0≤t≤50 内 0.05≤d_ij<10。"
        "本文共检验四种模式：A、B 为题目给定，C、D 为本文新找到/构造的模式；"
        "每个模式都给出完整初始条件、轨迹、距离曲线和模拟时长。"
    )
    r.p(
        "需要强调，题目所说的“稳定”是有限时间意义下的有界性，而不是 Lyapunov 意义或永久稳定性。"
        "后文会看到：模式 A 是严格周期解，却对微小扰动指数不稳定；模式 B 在 50 时间内对扰动有界，"
        "但这也不构成永久稳定的证明。"
    )

    # ---------------- 2 数值方法 ----------------
    r.h1("二、数值方法与检验")
    r.h2("2.1 状态量与积分器")
    r.p(
        "把三颗星的位置和速度拼成 12 维状态向量 y=(r₁,r₂,r₃,v₁,v₂,v₃)，方程 (1) 写成一阶系统 dy/dt=f(y)。"
        "本文使用两种积分器："
    )
    r.bullet("**固定步长 RK4**：用于步长—能量误差对比。每步 4 次右端函数计算，局部误差 O(Δt⁵)，全局误差 O(Δt⁴)。")
    r.bullet(
        "**自适应 Dormand–Prince 5(4)**：用于轨迹、扰动和步长基准。采用比例型步长控制（带安全因子），"
        "本文高精度运行取 rtol=10⁻¹³、atol=10⁻¹⁵、最大步长 0.005；在近距离交会时步长会自动缩小。"
    )
    r.p(
        "右端函数直接用 numpy 向量化计算：对每对 (i,j) 计算 d=r_j−r_i、r=|d|，累加 d/r³。"
        "每步都检查最小距离，若小于 0.05 立即停止；同时记录最大半径，防止逃逸轨道无限积分。"
        "为排除“插值造成的假误差”，步长对比时两条轨道在严格相同的时间网格上逐点比较，不做状态插值。"
    )

    r.h2("2.2 诊断量与检验")
    r.p(
        "对每条轨道记录：三对距离 d₁₂、d₁₃、d₂₃ 的时间序列；最小/最大距离；总能量 E(t)；"
        "总角动量 L；停止时间与停止原因；以及扰动轨道相对未扰动轨道的分离"
    )
    r.eq("δ(t) = √( Σ_i |Δr_i(t)|² ),   Δr_i = r_i(pert) − r_i(unpert).", "(4)")
    r.p("程序正确性做了以下独立检验：")
    r.bullet(
        f"在 Lagrange 初值处，数值加速度与 −ω²r 的最大偏差为 {sci(LAG['force_residual_max'], 1)}；"
        "解析解代入方程 (1) 的残差为 1.1×10⁻¹⁵，说明引力公式与初值一致。"
    )
    r.bullet(
        "对 8 字形等长轨道，能量相对漂移在 10⁻¹² 量级（高精度运行），总动量保持为零；"
        "RK4 步长减半时能量误差按预期下降。"
    )
    r.bullet(
        "用解析 Lagrange 解逐点对比数值解：在误差尚未被不稳定模式放大前（t≲15），"
        "偏差从 10⁻¹² 量级开始增长，斜率与线性稳定性分析的 λ=1.2247 一致。"
    )
    r.bullet("附录 A 提供了可复现命令与文件清单；仓库中还包含 8 个断言测试。")

    # ---------------- 3 模式 A ----------------
    r.h1("三、模式 A：等边三角形旋转（Lagrange 解）")
    r.h2("3.1 角速度推导")
    r.p(
        "取等边三角形边长 a=1。三个顶点到中心的距离（外接圆半径）为 R=a/√3=1/√3。"
        "对其中一颗星，另外两颗星对它的引力大小均为 Gm²/a²=1，两力夹角为 60°，"
        "因此合力指向中心，大小为"
    )
    r.eq("F = 2·(Gm²/a²)·cos30° = √3 Gm²/a².", "(5)")
    r.p("刚性旋转所需的向心力为 mω²R=mω²a/√3。令 F=mω²R，得")
    r.eq("ω² = 3Gm/a³ = 3  ⇒  ω = √3 ≈ 1.732051.", "(6)")
    r.p(
        f"周期 T=2π/ω={f(LAG['period'], 6)}。初始位置和速度按题目给出："
        "r_i 位于半径 1/√3 的圆上，v_i=ω(−y_i,x_i)。代入可得总能量 E=−1.5、总角动量 L=√3，"
        "与解析计算一致。"
    )
    r.p("初始条件为")
    r.eq("r₁=(1/√3, 0),  r₂=(−1/(2√3), 1/2),  r₃=(−1/(2√3), −1/2),", "(7)")
    r.eq("v₁=(0, √3),  v₂=(−√3/2, −1/2),  v₃=(√3/2, −1/2).", "(8)")

    r.h2("3.2 解析轨道与有界性")
    r.p(
        "该模式的解析解为整个三角形以角速度 ω 刚性旋转：r_i(t)=R(ωt)r_i(0)，v_i(t)=R(ωt)v_i(0)。"
        "因此三对距离严格恒为 1，最小距离和最大距离都为 1，0.05≤d_ij<10 对全部 t 成立。"
        "图 1(a) 用不同时刻的三角形快照显示这一刚性旋转；图 2(a) 的三条距离曲线重合为 d=1。"
        "从“有限时间有界”的判据看，模式 A 是严格满足的。"
    )

    r.h2("3.3 线性稳定性：周期不等于稳定")
    r.p(
        "在随三角形一起旋转的参考系中，Lagrange 构型是一个平衡点。设 ρ_i 为旋转系坐标，"
        "线性化方程为"
    )
    r.eq("δρ_i″ = −Σ_j H_ij δρ_j − 2ω J δρ_i′ + ω² δρ_i ,   J=[[0,−1],[1,0]].", "(9)")
    r.p(
        "其中 H 是势能 U=−Σ_{i<j}1/r_ij 的 Hessian。把 12 维线性系统写成矩阵并求特征值，"
        f"得到一对实部为正的复特征值 λ={f(LAG['growth_rate'], 6)}±i·1.732051；"
        f"实部即最大增长率，e 折时间 1/λ≈{f(1/LAG['growth_rate'], 3)}。"
        "这意味着任何微小扰动都会以 exp(λt) 增长：模式 A 虽严格周期，却是线性不稳定的。"
        "这一结论与“等边三角形解对等质量三体不稳定”的经典结果一致。"
    )

    r.h2("3.4 双精度能否模拟到 t=50？")
    r.p(
        "既然 λ≈1.2247，初始误差 ε 增长到 O(1) 所需时间约为 ln(1/ε)/λ。"
        "双精度舍入/截断误差约 10⁻¹²–10⁻¹⁶，对应 t≈20–30；要在 t=50 内保持 O(1) 以下，需要 ε<exp(−61)≈10⁻²⁷，"
        "即约 27 位十进制有效数字。普通双精度无法满足。表 1 给出了三组未扰动数值积分与解析解的偏差："
    )
    rows = []
    for tag, name in [("rk4_dt002", "RK4, Δt=0.002"), ("rk4_dt001", "RK4, Δt=0.001"), ("dp45", "DP45, rtol=10⁻¹³")]:
        d = MODES["A"]["numerical_precision"][tag]
        dev = d["dev_at"]
        rows.append(
            [
                name,
                f"{d['t_end']:.2f}",
                "近距离" if d["stopped"] else "完成",
                sci(d["energy_max_rel_error"], 2),
                sci(dev.get("20", float("nan")), 2),
                sci(dev.get("30", float("nan")), 2),
            ]
        )
    r.table(
        ["数值方案", "t_end", "停止原因", "max|ΔE|/|E₀|", "t=20 偏差", "t=30 偏差"],
        rows,
        widths=[3.9, 1.7, 2.1, 3.0, 2.5, 2.5],
        caption="表 1  模式 A 未扰动数值积分与解析解的偏差",
    )
    r.p(
        "可以看到：三种方案的偏差都在 t≈20 后迅速增大，t=30 时已到 O(0.4–2)。"
        "RK4 Δt=0.001 恰好在 t=50 前没有触发 0.05 预警（d_min=0.064），但它在 t=30 时已偏离解析解 2.09，"
        "轨迹早已不是原来的旋转三角形。这说明“没有触发预警”不能证明模拟正确；"
        "能量误差也只有 3.9×10⁻⁶，同样不能保证轨迹精度。"
    )
    r.p(
        "因此，**模式 A 的轨迹、距离和有界性数据采用解析解**；数值积分只用于研究不稳定性和数值精度，"
        "不用于声称“数值上模拟了 50 时间的三角形”。图 5(b) 把数值误差包络与 10⁻⁴ 的物理扰动画在一起："
        "两者斜率都接近 exp(1.2247t)，只是起点不同（数值误差 10⁻¹²–10⁻⁶，物理扰动 10⁻⁴）。"
        "这正是“同一不稳定模式被不同初始误差触发”的直接证据。"
    )
    # ---------------- 4 模式 B ----------------
    r.h1("四、模式 B：8 字形运动")
    r.p(
        "题目给出的 8 字形初值为"
    )
    r.eq("r₁=(0.97000436, −0.24308753),  r₂=−r₁,  r₃=0,", "(10)")
    r.eq("v₁=v₂=(0.46620369, 0.43236573),  v₃=−2v₁.", "(11)")
    r.p(
        "这组初值经过四舍五入，严格说只是近似周期轨道；文献中的周期为 T≈6.3259。"
        f"直接积分得 E₀={f(MODES['B']['energy0'], 6)}、L=0（机器精度），"
        f"在 0≤t≤50 内（约 7.9 个周期）d_min={f(MODES['B']['dmin'])}、d_max={f(MODES['B']['dmax'])}，"
        "未触发 0.05 预警，也未逃逸。图 1(b) 显示三颗星共用同一条 8 字曲线，只是相位不同；"
        "图 2(b) 显示三对距离在 0.69–2.0 之间周期振荡。"
    )
    r.p(
        "8 字形的运动结构是“舞蹈型”（choreography）：三颗星依次沿同一条闭合曲线运动，"
        "在任意时刻它们位于曲线的不同段上。它与模式 A 的刚性三角形有本质区别：A 是三体保持固定形状整体旋转，"
        "B 是三体沿同一条轨道追逐，形状不断变化。"
    )
    r.p(
        "已有理论结果表明，等质量 8 字形轨道是线性稳定的（Simó 等）。本文的扰动实验（§6）与之相符："
        "10⁻⁴ 的扰动只产生 6.3×10⁻³ 的分离，50 时间内没有失稳。但要注意，给定初值只有 8 位有效数字，"
        "实际数值轨道是严格周期轨道附近的准周期轨道；50 时间内的有界性不能外推为永久稳定。"
    )

    # ---------------- 5 其他模式 ----------------
    r.h1("五、其他有界模式：飞蛾 I 与层级三体")
    r.h2("5.1 搜索策略与候选筛选")
    r.p(
        "为了寻找题目要求的新模式，本文采用两类策略。第一类是零角动量对称族：取 "
        "r₁=(−1,0)、r₂=(1,0)、r₃=0，v₁=v₂=(v_x,v_y)、v₃=−2(v₁)，"
        "这样质心在原点、总动量为零、总角动量为零。Šuvakov 与 Dmitrašinović 在这一族中给出了一批"
        "平面周期轨道（butterfly、moth、goggles、yarn、yin-yang 等），其初值和周期可查。"
        "本文把这些初值当作候选，用自己的积分器独立检验，而不是直接相信文献。"
    )
    r.p(
        "筛选标准严格按题意：在 0≤t≤50 内（周期短于 50 的积分一个周期）d_min≥0.05 且 d_max<10。"
        "图 3 把所有候选画在 (d_min,d_max) 平面上；表 4 列出具体数值。结果非常清楚："
        "**15 个已发表候选里只有 moth I（飞蛾 I）通过**，其余的最小距离都远小于 0.05"
        "（butterfly I 为 0.0110，butterfly II 为 0.0041，goggles 为 0.0185，yarn 为 0.0050，"
        "butterfly IV 甚至只有 2.9×10⁻⁵）。这些轨道在数学上是漂亮周期解，但在题目给定的 0.05 阈值下不合格。"
    )
    r.p(
        "需要说明：如果把某个紧致轨道整体放大，d_min 会随之增大，可能满足 0.05；但题目明确规定"
        "“仅对同一轨道做尺度变换不算找到新模式”，所以本文不把缩放后的同一轨道当作新模式。"
        "本文保留的第二个新模式是自行构造的层级三体，它与对称族的舞蹈型轨道在运动结构上完全不同。"
    )

    r.h2("5.2 模式 C：飞蛾 I（moth I）")
    r.p(
        "飞蛾 I 的初值为 r₁=(−1,0)、r₂=(1,0)、r₃=0，v₁=v₂=(0.46444,0.39606)、"
        "v₃=(−0.92888,−0.79212)。文献周期 T≈14.8939。"
        f"直接积分得 E₀={f(MODES['C']['energy0'], 6)}、L=0；"
        f"在 0≤t≤50 内 d_min={f(MODES['C']['dmin'])}、d_max={f(MODES['C']['dmax'])}，"
        "未触发预警。图 1(c) 是它的轨迹：三条曲线相互穿插，形成一个类似飞蛾翅膀的图案，"
        "与 8 字形的单一闭合曲线明显不同；图 2(c) 显示 d₁₃/d₂₃ 会周期性地下探到 0.08 左右，"
        "最近一次出现在 t≈24.6，之后在 t≈47 附近还有一次。"
    )
    r.p(
        "飞蛾 I 的最小距离只比 0.05 大 0.029，属于“边缘合格”。这不是一个很安全的模式："
        "任何额外的扰动或数值误差都可能把某次交会推到阈值以下。后文的扰动实验会看到，"
        "10⁻⁴ 的扰动虽然没有触发预警，但分离可达 1.2×10⁻²，最小距离降到 0.0793，"
        "已经非常接近边界。"
    )

    r.h2("5.3 模式 D：层级三体（紧密双星 + 远方第三体）")
    r.p(
        "第二个新模式由两个时间尺度相差很大的子系统组成：恒星 1、2 组成间距 d=0.4 的紧密圆双星，"
        "恒星 3 在半径约 2.67 的宽轨道上绕整个系统的质心运动。构造如下。"
        "双星内部每颗星到双星质心的距离为 d/2，圆运动速度为"
    )
    r.eq("v_int = √(1/(2d)) = √1.25 ≈ 1.118034.", "(12)")
    r.p(
        "把双星看成一个总质量 2 的质点，它与星 3 的相对圆轨道半径取 R=4，相对速度为"
    )
    r.eq("v_rel = √(3/R) = √0.75 ≈ 0.866025.", "(13)")
    r.p(
        "为保证质心静止，双星质心位于 −R/3、星 3 位于 2R/3；速度按质量反比分配："
        "双星质心速度 −v_rel/3，星 3 速度 2v_rel/3。把双星内部速度叠加到 1、2 号星上，得到"
    )
    r.eq("r₁=(−1.533333,0), r₂=(−1.133333,0), r₃=(2.666667,0),", "(14)")
    r.eq("v₁=(0,0.829359), v₂=(0,−1.406709), v₃=(0,0.577350).", "(15)")
    r.p(
        "代入得 E₀≈−1.501253、L≈1.862187，质心位置和速度均为零（数值上到 10⁻¹⁶）。"
        "该构型的时间尺度为：双星内部周期 T_in=πd/v_int≈1.12，外层轨道周期 T_out=2πR/v_rel≈29.0，"
        "两者相差约 26 倍。双星的 Hill 半径约为 R(2/3)^(1/3)≈3.5，远大于 d=0.4，"
        "所以第三体不会轻易撕开双星。"
    )
    r.p(
        f"数值积分到 t=50 得 d_min={f(MODES['D']['dmin'])}、d_max={f(MODES['D']['dmax'])}，"
        "未触发预警，也未逃逸。图 1(d) 显示双星的两个小环在一个大圆内运动，插图是 1–2 的相对轨道；"
        "图 2(d) 显示双星间距在 0.399–0.401 之间小幅振荡（第三体的潮汐扰动），"
        "而 d₁₃/d₂₃ 在 3.78–4.20 之间变化。"
    )
    r.p(
        "模式 D 的运动结构与 A、B、C 都不同：它不是三体对称的舞蹈型轨道，而是“双星 + 第三体”的层级结构，"
        "两个子系统的时间尺度分离是它保持有界的主要原因。它也不是严格周期轨道，"
        "但在 50 时间内表现出很好的规则性和鲁棒性。"
    )

    r.h2("5.4 模式汇总与结构比较")
    r.figure(
        "fig1_trajectories.png",
        "图 1  四种模式的轨迹。(a) 等边三角形：不同时刻的三角形快照；(b) 8 字形：三颗星共用同一条曲线；"
        "(c) 飞蛾 I；(d) 层级三体，插图为 1–2 的相对轨道。",
        width=14.8,
    )
    r.p(
        "四种模式的结构差异可以概括为：**A** 是三体保持等边形状的整体刚性旋转，三对距离恒定；"
        "**B** 是三体沿同一条 8 字曲线依次追逐的舞蹈型轨道，零角动量；"
        "**C** 是同一对称族中另一种舞蹈型轨道，轨迹呈飞蛾状、有更近的双星式交会，周期和最小距离都不同；"
        "**D** 是层级结构，一个紧密双星加一个远距离第三体，两个时间尺度分离。"
        "它们不是彼此的整体旋转、平移、速度方向旋转或尺度变换，因此按题目规则应计为不同模式。"
    )
    rows = []
    for key in ["A", "B", "C", "D"]:
        m = MODES[key]
        stopped = "否" if m["stop_reason"] in ("completed", "exact") else "是"
        t_end = "50（解析）" if key == "A" else f"{m['t_end']:.2f}"
        rows.append(
            [
                key,
                m["short"],
                t_end,
                stopped,
                f(m["dmin"]),
                f(m["dmax"]),
                f(m["energy0"], 6),
                "0" if key == "A" else sci(m["energy_max_rel_error"], 2),
            ]
        )
    r.figure(
        "fig2_distances.png",
        "图 2  四种模式的恒星间距离。红虚线为 0.05 预警阈值，灰色点线为 10 的上界；纵轴为对数坐标。",
        width=14.8,
    )
    r.table(
        ["模式", "名称", "t_end", "提前停止", "d_min", "d_max", "E₀", "max|ΔE|/|E₀|"],
        rows,
        widths=[1.1, 3.5, 1.9, 1.5, 1.6, 1.6, 2.1, 2.6],
        caption="表 2  四种有界模式的汇总（0≤t≤50；模式 A 为解析解）",
    )
    r.table(
        ["模式", "r₁", "r₂", "r₃", "v₁", "v₂", "v₃"],
        [
            [
                "A",
                "(0.577350, 0.000000)",
                "(−0.288675, 0.500000)",
                "(−0.288675, −0.500000)",
                "(0.000000, 1.732051)",
                "(−0.866025, −0.500000)",
                "(0.866025, −0.500000)",
            ],
            [
                "B",
                "(0.970004, −0.243088)",
                "(−0.970004, 0.243088)",
                "(0.000000, 0.000000)",
                "(0.466204, 0.432366)",
                "(0.466204, 0.432366)",
                "(−0.932407, −0.864731)",
            ],
            [
                "C",
                "(−1.000000, 0.000000)",
                "(1.000000, 0.000000)",
                "(0.000000, 0.000000)",
                "(0.464440, 0.396060)",
                "(0.464440, 0.396060)",
                "(−0.928880, −0.792120)",
            ],
            [
                "D",
                "(−1.533333, 0.000000)",
                "(−1.133333, 0.000000)",
                "(2.666667, 0.000000)",
                "(0.000000, 0.829359)",
                "(0.000000, −1.406709)",
                "(0.000000, 0.577350)",
            ],
        ],
        widths=[1.1, 2.55, 2.55, 2.55, 2.35, 2.35, 2.35],
        caption="表 3  四种模式的完整初始条件（G=m=1；质心在原点，总动量为零）",
        font_size=7.6,
    )

    # 表 4 候选筛选
    rows = []
    for cand in S["screening"]:
        rows.append(
            [
                cand["name"],
                f"{cand['vx']:.5f}",
                f"{cand['vy']:.5f}",
                f"{cand['period']:.4f}",
                sci(cand["dmin"], 3),
                f"{cand['dmax']:.4f}",
                "是" if cand["valid"] else "否",
            ]
        )
    r.table(
        ["候选", "v_x", "v_y", "T", "d_min", "d_max", "有效？"],
        rows,
        widths=[3.2, 2.0, 2.0, 2.0, 2.4, 2.1, 1.8],
        caption="表 4  已发表对称族候选轨道的筛选（周期短于 50 的积分一个周期，否则积分到 t=50）",
        font_size=7.8,
    )
    r.figure(
        "fig7_screening.png",
        "图 3  候选轨道的 (d_min,d_max) 分布。绿色区域为 0.05≤d_min 且 d_max<10；"
        "只有 moth I 落在区域内，A–D 为本文四种模式。",
        width=12.5,
    )
    r.p(
        "表 4 和图 3 说明：在 0.05 这个阈值下，“已知漂亮周期轨道”远不等于“本题合格模式”。"
        "很多轨道的最小距离只有 10⁻³–10⁻²，在真实恒星系统中会经历极强的近距离交会；"
        "题目用 0.05 作为数值预警是合理的。"
    )

    # ---------------- 6 扰动实验 ----------------
    r.h1("六、扰动实验：有限时间有界 ≠ 对扰动稳定")
    r.h2("6.1 扰动方案")
    r.p(
        "按题目要求，对每个模式把恒星 1 的初始 v_x 增加 10⁻⁴，然后统一减去三颗星的质心速度，"
        "使总动量重新为零。被扰动的初始速度为"
    )
    r.eq("v₁ ← v₁ + (10⁻⁴, 0),   v_i ← v_i − V_cm  (i=1,2,3).", "(16)")
    r.p(
        "扰动后的轨道与未扰动轨道用同一高精度积分器计算（DP45，rtol=10⁻¹³）。"
        "模式 A 的未扰动参考用解析解；B、C、D 用各自的未扰动数值轨道。"
        "为隔离数值误差，扰动实验不使用 RK4 Δt=0.002；后文会说明原因。"
    )

    r.h2("6.2 结果")
    r.figure(
        "fig3_perturbation.png",
        "图 4  扰动前后的轨迹对比。灰色为未扰动，红色为扰动后；B、C、D 的插图为恒星 1 的扰动位移 Δr₁。",
        width=14.8,
    )
    r.p(
        "四种模式的结构差异可以概括为：**A** 是三体保持等边形状的整体刚性旋转，三对距离恒定；"
        "**B** 是三体沿同一条 8 字曲线依次追逐的舞蹈型轨道，零角动量；"
        "**C** 是同一对称族中另一种舞蹈型轨道，轨迹呈飞蛾状、有更近的双星式交会，周期和最小距离都不同；"
        "**D** 是层级结构，一个紧密双星加一个远距离第三体，两个时间尺度分离。"
        "它们不是彼此的整体旋转、平移、速度方向旋转或尺度变换，因此按题目规则应计为不同模式。"
    )
    rows = []
    verdict = {
        "A": "指数失稳",
        "B": "有界，缓慢分离",
        "C": "有界，边缘",
        "D": "有界，鲁棒",
    }
    for key in ["A", "B", "C", "D"]:
        m = MODES[key]
        p = m["pert"]
        rows.append(
            [
                key,
                f(m["dmin"]),
                f(p["dmin"]),
                f(m["dmax"]),
                f(p["dmax"]),
                sci(p["delta_end"], 2),
                f"{p['t_end']:.2f} / {'近距离' if p['stopped'] else '完成'}",
                verdict[key],
            ]
        )
    r.table(
        ["模式", "d_min（未）", "d_min（扰）", "d_max（未）", "d_max（扰）", "δ_end", "t_end / 停止", "判定"],
        rows,
        widths=[1.2, 1.9, 1.9, 1.9, 1.9, 1.9, 3.0, 2.5],
        caption="表 5  10⁻⁴ 速度扰动前后的最小/最大距离与末端分离",
    )

    r.p(
        "**模式 A：** δ(t) 从 10⁻⁴ 开始，以接近 exp(1.2247t) 的斜率增长，t≈8 时达到 O(1)，"
        "三角形已经瓦解；t=15.55 时某两颗星的距离降到 0.05 以下，计算停止（d_min=0.0499，d_max=2.47）。"
        "对 δ(t) 在 t=1–6 做指数拟合得 λ≈1.17，略低于线性值 1.2247；这是因为初始扰动包含多个本征模式，"
        "且后期出现非线性饱和。图 5(a) 中紫色曲线与黑色虚线（拟合）几乎重合。"
        "这个结果说明：模式 A 的“周期”只在精确的数学解中存在，任何 10⁻⁴ 的扰动都会在十几个时间单位内摧毁它。"
    )
    r.p(
        "**模式 B：** 扰动后 δ 缓慢增长到 6.3×10⁻³，d_min 从 0.69053 降到 0.69036，d_max 从 2.0 增到 2.00019，"
        "50 时间内没有触发预警。δ 的增长远慢于指数（拟合 λ≈0.26，且不是直线），"
        "与 8 字形已知的线性稳定性一致。但“50 时间内有界”仍不是永久稳定的证明；"
        "更严格的结论需要 Floquet 分析或长期积分。"
    )
    r.p(
        "**模式 C：** 扰动后 δ 最大 1.19×10⁻²，末端 4.76×10⁻³；d_min 从 0.07940 降到 0.07933，"
        "d_max 从 2.16006 增到 2.16018，仍未触发预警。它是有界的，但最小距离只比阈值大 0.029，"
        "扰动已经把某次交会推得更近；这是一个“边缘稳定”的案例，不能据此声称长期稳定。"
    )
    r.p(
        "**模式 D：** 扰动后 δ 最大 7.6×10⁻⁴，末端 4.7×10⁻⁴；d_min、d_max 在四位小数内几乎不变。"
        "双星的内部运动很快（周期 1.12），第三体的外轨道很慢（周期 29），扰动主要在双星内部相位上，"
        "不会立即破坏层级结构。这是四种模式中对 10⁻⁴ 扰动最鲁棒的一个。"
    )
    r.figure(
        "fig4_separation.png",
        "图 5  (a) 四种模式的扰动分离 δ(t)；(b) 模式 A 的数值误差包络与 10⁻⁴ 物理扰动对比，"
        "黑点线为 exp(1.2247t) 参考。",
    )

    r.h2("6.3 如何理解“稳定”")
    r.p(
        "把四个结果放在一起，可以得到三个层次的区别："
    )
    r.bullet(
        "**有限时间有界**：只要求 0≤t≤50 内 0.05≤d_ij<10。四种模式都满足（A 由解析解，B/C/D 由数值积分）。"
    )
    r.bullet(
        "**对扰动有界（Lyapunov 意义下的有限时间稳定）**：给 10⁻⁴ 扰动后仍不触发预警、仍保持有界。"
        "B、C、D 满足；A 不满足。"
    )
    r.bullet(
        "**永久稳定**：对所有时间、所有足够小的扰动都有界。本文没有证明任何一种模式永久稳定；"
        "B 有已知的线性稳定性结果，C、D 只有 50 时间的数值证据。"
    )
    r.p(
        "因此，题目中“在 t≤50 内没有失稳不等于永久稳定；未扰动轨道周期重复，也不自动意味着对扰动稳定”"
        "在模式 A 上体现得最清楚：它是严格周期解，却指数不稳定；而模式 B 的周期轨道在 50 时间内对扰动有界，"
        "但也不能仅凭这一点断言永久稳定。"
    )

    # ---------------- 7 步长与能量 ----------------
    r.h1("七、步长、能量误差与数值局限")
    r.h2("7.1 实验设置")
    r.p(
        "对 8 字形和飞蛾 I，用固定步长 RK4 分别取 Δt=0.002、0.001、0.0005，积分到 t=50。"
        "定义相对能量误差"
    )
    r.eq("ε_E(t) = |E(t) − E(0)| / |E(0)|,", "(17)")
    r.p(
        "记录全程最大值；同时记录 d_min、d_max，并以 Δt=0.002 的严格相同时间网格为基准，"
        "比较位置、速度和最小距离的差异（不做插值）。"
    )

    rows = []
    for key, label in [("B", "B（8 字形）"), ("C", "C（飞蛾 I）")]:
        for entry in S["stepsize"][key]:
            rows.append(
                [
                    label,
                    f"{entry['dt']:g}",
                    sci(entry["energy_max_rel"], 2),
                    f"{entry['dmin']:.6f}",
                    f"{entry['dmax']:.6f}",
                    "—" if entry["tag"] == "dt002" else sci(entry["traj_diff_max"], 2),
                    "—" if entry["tag"] == "dt002" else sci(entry.get("vel_diff_max", float("nan")), 2),
                    "—" if entry["tag"] == "dt002" else sci(entry["dmin_diff_max"], 2),
                ]
            )
    r.table(
        ["模式", "Δt", "max ε_E", "d_min", "d_max", "最大位置差", "最大速度差", "最大 d_min 差"],
        rows,
        widths=[1.9, 1.2, 2.3, 1.9, 1.9, 2.2, 2.2, 2.2],
        caption="表 6  RK4 步长对能量误差和距离的影响（差异均相对 Δt=0.002）",
        font_size=7.9,
    )
    r.figure(
        "fig5_energy_stepsize.png",
        "图 6  RK4 能量误差随时间的变化；图例中给出全程最大相对误差。",
        width=14.8,
    )
    r.figure(
        "fig6_distance_stepsize.png",
        "图 7  最小恒星间距离对步长的敏感性；插图为飞蛾模式在 t≈9.7 附近的近距离交会。",
        width=14.8,
    )

    r.h2("7.2 结果与解释")
    r.p(
        "**8 字形：** 能量误差从 Δt=0.002 的 6.6×10⁻¹² 降到 0.001 的 2.0×10⁻¹³、0.0005 的 3.1×10⁻¹⁴；"
        "d_min、d_max 在 6 位小数内不变；位置差最大 1.2×10⁻⁹，速度差 2.3×10⁻⁹，d_min 差 7.6×10⁻¹⁰。"
        "这是一条“数值友好”的轨道：没有强近距离交会，RK4 的四阶收敛表现得很干净，"
        "继续减小步长后误差接近双精度舍入平台（10⁻¹⁴）。"
    )
    r.p(
        "**飞蛾 I：** 能量误差从 2.46×10⁻⁴ 降到 7.72×10⁻⁶、2.42×10⁻⁷，相邻步长之间约缩小 32 倍；"
        "d_min 从 0.079388 变到 0.079422、0.079405，d_max 从 2.159999 变到 2.160056、2.160061。"
        "但轨迹并不随步长单调收敛：Δt=0.002 与 0.001 的最大位置差为 0.042，"
        "速度差可达 1.82，d_min 差 0.029；继续把步长减到 0.0005，位置差仍为 0.043，没有明显下降。"
        "原因不是能量不守恒，而是飞蛾轨道在 t≈24.6、47 附近的近距离交会对相位极其敏感："
        "步长改变一点，交会时刻就移动，位置和速度在交会附近被放大，但能量仍然守恒得很好。"
        "这是“能量误差小 ≠ 轨迹准确”的典型例子。"
    )
    r.p(
        "能量误差的下降倍数约为 32，接近 2⁵。RK4 的全局误差名义上是 O(Δt⁴)，"
        "但这里的最大能量误差主要来自近距离交会附近的局部误差，局部误差按 Δt⁵ 缩放；"
        "因此观测到的比值更接近五阶局域标度，不能简单用单一阶数概括。"
        "对 8 字形，误差已经接近舍入平台，不能再用单一幂次拟合。"
    )
    r.p(
        "**模式 A 的教训：** 它的能量误差可以很小（RK4 Δt=0.001 为 3.9×10⁻⁶），"
        "但轨迹在 t=30 时已偏离解析解 2.09。原因是能量守恒只约束一个标量，"
        "而不稳定模式会把微小的相位误差指数放大。对不稳定轨道，必须同时检查能量、"
        "与解析解/高精度参考的偏差，以及不同步长/容差下的收敛性。"
    )

    r.h2("7.3 数值建议")
    r.bullet("对普通有界轨道，RK4 Δt=0.001 已能给出 10⁻¹² 量级的能量误差；但不要只看能量，要看轨迹收敛。")
    r.bullet(
        "对含近距离交会的轨道（如飞蛾 I），固定步长 RK4 的相位误差可能远大于扰动信号；"
        "本文的扰动实验改用 DP45（rtol=10⁻¹³），并用两种容差复核。"
    )
    r.bullet(
        "对不稳定平衡/周期轨道（如模式 A），双精度不足以维持 t=50；应使用解析解、"
        "更高精度算术（约 27 位有效数字）或把有限时间缩短到误差增长可接受的范围。"
    )
    r.bullet("所有长时间积分都应监控 d_min、d_max 和能量；0.05 的预警阈值应作为事件检测，而不是事后检查。")

    # ---------------- 8 稳定性总结 ----------------
    r.h1("八、有限时间稳定性的综合讨论")
    rows = []
    stability = {
        "A": ("是（解析）", "0.95", "指数增长，t≈15.5 瓦解", "λ=1.2247（线性不稳定）", "不稳定"),
        "B": ("是", "0.64", "δ≤6.3×10⁻³，有界", "已知线性稳定", "有限时间稳定"),
        "C": ("是", "0.029", "δ≤1.2×10⁻²，有界但敏感", "未证明", "边缘"),
        "D": ("是", "0.35", "δ≤7.6×10⁻⁴", "未证明；时间尺度分离", "鲁棒"),
    }
    for key in ["A", "B", "C", "D"]:
        m = MODES[key]
        rows.append(
            [
                key,
                stability[key][0],
                stability[key][1],
                stability[key][2],
                stability[key][3],
                stability[key][4],
            ]
        )
    r.table(
        ["模式", "0≤t≤50 有界", "d_min−0.05", "对 10⁻⁴ 扰动", "线性稳定性", "结论"],
        rows,
        widths=[1.1, 2.5, 2.1, 4.6, 3.8, 1.9],
        caption="表 7  四种模式的有限时间稳定性对比",
    )
    r.p(
        "模式 A 是唯一一个“未扰动严格周期、但对扰动不稳定”的例子。它的不稳定性来自等边三角形构型的鞍点性质，"
        "而不是数值误差；数值误差只是提前触发了它。模式 B 是已知的线性稳定周期轨道，"
        "本文的 50 时间扰动实验与之一致。模式 C 的最小距离只有 0.079，"
        "裕量只有 0.029，属于边缘案例；模式 D 依靠时间尺度分离获得鲁棒性，"
        "但严格地说，层级三体在极长时间下仍可能出现混沌或逃逸，本文没有证明永久稳定。"
    )
    r.p(
        "题目提醒“在 t≤50 内没有失稳不等于永久稳定；未扰动轨道周期重复，也不自动意味着对扰动稳定”。"
        "本文的四个模式正好覆盖了这句话的几种情形：A 周期但不稳定，B 周期且（有限时间）稳定，"
        "C 有界但边缘，D 非周期但鲁棒。判断一个模式是否“稳定”，必须明确时间尺度、扰动幅度和稳定性的定义。"
    )

    # ---------------- 9 AI 使用 ----------------
    r.h1("九、AI 使用记录与核验")
    r.p(
        "本作业允许 AI 辅助编程和查找思路。本文使用 DeepSeek Harness 的编码助手（deepseek-flash）"
        "完成以下工作：生成 RK4/DP45 积分器与绘图脚本的初稿；检索零角动量对称族的三体周期轨道初值；"
        "帮助组织报告结构。所有数值结果均由本地程序重新计算，AI 给出的候选轨道和结论都做了独立检验。"
        "下面记录三次具体使用及其核验过程。"
    )
    r.table(
        ["AI 的输出/建议", "核验方法", "结果"],
        [
            [
                "生成三体右端函数、RK4 和 DP45 积分器，并建议用解析 Lagrange 解检验。",
                "手算 t=0 的加速度并与 −ω²r 比较；把解析解代入方程检查残差；检查能量和动量守恒；"
                "用两种步长比较能量误差。",
                "残差 1.1×10⁻¹⁵；能量误差随步长下降；代码用于全部计算。",
            ],
            [
                "检索 Šuvakov–Dmitrašinović 的对称族初值，并推荐 butterfly I 作为“新模式”。",
                "用本文积分器独立积分一个周期，检查 0.05≤d_ij<10；不直接采用文献结论。",
                "butterfly I 的 d_min=0.0110<0.05，不合格，剔除；moth I 的 d_min=0.0794，保留。",
            ],
            [
                "建议直接用双精度数值积分把模式 A 模拟到 t=50，并报告“有界”。",
                "与解析解逐点比较；对旋转系做线性化，求最大特征值；检查不同积分器的偏差。",
                "数值解在 t≈30 偏离解析解 O(1)；线性 λ=1.2247，确认是物理不稳定被舍入误差触发。"
                "改用解析解呈现模式 A，并单列数值精度实验。",
            ],
        ],
        widths=[5.4, 5.8, 4.4],
        caption="表 8  AI 使用与核验记录",
        font_size=8.0,
    )
    r.p(
        "一个具体的“AI 错误”例子是 butterfly I：AI 只根据文献说它是已知周期轨道，"
        "但它在题目给定的 0.05 阈值下最小距离只有 0.0110，不满足有界模式的定义。"
        "如果直接相信 AI 的推荐，就会把一个不合格的轨道写进结果表。"
        "这说明 AI 适合提供思路和初稿，但物理判据必须由程序独立复核。"
    )
    r.p(
        "另一个例子是模式 A 的“双精度能算到 50”这一直觉。AI 最初建议直接数值积分并报告有界；"
        "但解析解对比显示 t≈30 后偏差已达 O(1)，而能量误差仍只有 10⁻⁶。"
        "进一步做线性稳定性分析得到 λ=1.2247，才解释清楚这是物理不稳定而非程序 bug。"
        "最终报告中模式 A 的数据来自解析解，数值积分只作为“数值精度”的反面教材。"
    )

    # ---------------- 10 结论 ----------------
    r.h1("十、结论")
    r.p(
        "本文在 0≤t≤50 内检验了四种平面等质量三体有界模式：Lagrange 等边三角形、8 字形、飞蛾 I 和层级三体。"
        "模式 A、B 为题目给定；模式 C、D 为本文新找到/构造的模式，均给出完整初始条件、轨迹、距离和模拟时长。"
        "四种模式都满足 0.05≤d_ij<10（A 由解析解，B/C/D 由数值积分），其中 C、D 是新模式。"
    )
    r.p(
        "主要结论如下："
    )
    r.bullet(
        "模式 A 是严格周期解（ω=√3，T=3.6276，d≡1），但线性增长率 λ=1.2247；10⁻⁴ 扰动在 t≈8 后使三角形瓦解，"
        "t≈15.55 触发预警。双精度数值积分也会在 t≈30 后偏离解析解，需约 27 位有效数字才能维持到 t=50。"
    )
    r.bullet(
        "模式 B 的 8 字形在 50 时间内保持有界，扰动分离仅 6.3×10⁻³；与已知的线性稳定性一致。"
    )
    r.bullet(
        "模式 C 的飞蛾 I 最小距离 0.0794，扰动后有界（δ≤1.2×10⁻²），但裕量仅 0.029，属于边缘稳定。"
    )
    r.bullet(
        "模式 D 的层级三体最小距离 0.399，扰动分离 4.7×10⁻⁴；时间尺度分离（1.12 对 29.0）带来鲁棒性。"
    )
    r.bullet(
        "步长检验：8 字形的 RK4 能量误差 6.6×10⁻¹²→3.1×10⁻¹⁴；飞蛾 I 的能量误差 2.46×10⁻⁴→2.42×10⁻⁷，"
        "但近距离交会处的位置差可达 0.042、d_min 差 0.029，轨迹不随步长单调收敛。"
        "扰动实验必须用高精度自适应积分，不能只用固定步长 RK4。"
    )
    r.p(
        "最终的回答是：特殊初始条件确实可以让三颗恒星在有限时间内做有规律的运动；"
        "但“有规律”不等于“稳定”。等边三角形是周期解却不稳定，8 字形在有限时间内稳定，"
        "飞蛾 I 处于边缘，层级三体靠时间尺度分离获得鲁棒性。"
        "判断稳定性必须同时说明时间尺度、扰动幅度和数值精度，并区分有限时间有界与永久稳定。"
    )

    # ---------------- 附录 ----------------
    r.h1("附录 A  程序结构与复现")
    r.p("本作业的全部代码和数据都在 3body 目录下，结构如下：")
    r.bullet("three_body.py：物理模型、初始条件、RK4/DP45 积分器、能量/距离/分离等诊断函数。")
    r.bullet("run_experiments.py：跑全部模式、扰动实验、步长对比和候选筛选，输出 results/。")
    r.bullet("make_figures.py：从 results/ 生成 figures/ 下的 7 张图。")
    r.bullet("make_report.py：从 results/summary.json 生成本报告 DOCX。")
    r.bullet("test_three_body.py：8 个断言测试（力平衡、能量守恒、解析解、扰动质心等），可直接运行，也可用 pytest 运行。")
    r.bullet("results/：trajectories.npz、summary.json、summary.csv、screening.csv。")
    r.p("复现命令（Windows，Python 3.12+）：")
    r.eq("python run_experiments.py", None)
    r.eq("python make_figures.py", None)
    r.eq("python make_report.py", None)
    r.eq("python test_three_body.py", None)
    r.p(
        "依赖：numpy、matplotlib、python-docx；测试脚本无需 pytest。所有随机性均无（初值固定），"
        "结果对平台差异只会有 10⁻¹² 量级的数值差别。"
    )

    r.h1("参考文献")
    refs = [
        "[1] Chenciner A., Montgomery R. A remarkable periodic solution of the three-body problem in the case of equal masses. "
        "Annals of Mathematics, 2000, 152(3): 881–901.",
        "[2] Šuvakov M., Dmitrašinović V. Three classes of Newtonian three-body planar periodic orbits. "
        "Physical Review Letters, 2013, 110: 114301. arXiv:1303.0181.",
        "[3] Simó C. Dynamical analysis of the Chenciner–Montgomery orbit. In: Hamiltonian Systems and Celestial Mechanics, 2002.",
        "[4] Hairer E., Nørsett S. P., Wanner G. Solving Ordinary Differential Equations I. Springer, 1993. "
        "（Dormand–Prince 5(4) 方法）",
        "[5] Giordano N. J., Nakanishi H. Computational Physics. 2nd ed. Pearson, 2006.",
        "[6] NEMO data file: planar 3body initial conditions [Šuvakov & Dmitrašinović (2013)]. "
        "https://gitlab.astro.rug.nl/teuben/nemo/-/blob/master/data/3body.tab",
    ]
    for ref in refs:
        p = r.doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.first_line_indent = Pt(-18)
        run = p.add_run(ref)
        set_run(run, size=9.5)

    r.save(REPORT / "三体问题作业报告.docx")
    print("Saved", REPORT / "三体问题作业报告.docx")


if __name__ == "__main__":
    build()
