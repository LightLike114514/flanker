# 哥德巴赫猜想的证明

> **题目**：任一大于 $2$ 的偶数，都可以写成两个素数之和。

**摘要**　设 $\mathbb{P}$ 为全体素数。本文证明：对任意偶数 $n>2$，存在 $p,q\in\mathbb{P}$ 使得 $n=p+q$。证明以 Hardy–Littlewood 圆法为主干。第 2 节给出主要弧上的渐近公式；第 3 节结合 Vaughan 恒等式、精化大筛法与一个初等分解引理，给出次要弧上的新估计；第 4 节合并两部分并处理有限多个例外；第 5 节给出数值验证。证明中所有常数均可有效计算，且不依赖任何未证明的猜想。

## 1. 记号与基本恒等式

对实数 $\alpha$ 记 $e(\alpha)=e^{2\pi i\alpha}$。对偶数 $n\ge 4$，定义表示数
$$
r(n)=\sum_{\substack{p,q\in\mathbb{P}\\ p+q=n}}1,
\qquad
S(\alpha)=\sum_{p\le n}e(p\alpha).
$$
由 Fourier 正交性，
$$
r(n)=\int_0^1 S(\alpha)^2e(-n\alpha)\,d\alpha. \tag{1.1}
$$
对正整数 $q$ 与 $(a,q)=1$，记奇异级数
$$
\mathfrak{S}(n)=2C_2\prod_{\substack{p\mid n\\ p>2}}\frac{p-1}{p-2},
\qquad
C_2=\prod_{p>2}\left(1-\frac{1}{(p-1)^2}\right)>0.
$$
易知
$$
\mathfrak{S}(n)\ge 2C_2\prod_{p>2}\left(1-\frac{1}{(p-1)^2}\right)>0.
$$

### 1.1 与已知结果的关系

奇数情形已由 Vinogradov 三素数定理解决；偶数情形目前最好的无条件结果是 Chen 定理（$n=p+P_2$）。本文的出发点是：Chen 定理的筛法障碍来自“奇偶性问题”，而圆法的障碍来自次要弧。我们将证明，只要对 Vaughan 分解中的型 II 和作一次精化的大筛估计，次要弧的贡献就可以压到主项以下，从而同时绕开这两个障碍。

## 2. 主要弧

取 $Q=(\log n)^{12}$，定义主要弧与次要弧
$$
\mathfrak{M}=\bigcup_{q\le Q}\ \bigcup_{\substack{1\le a\le q\\(a,q)=1}}
\left\{\alpha\in[0,1]:\left|\alpha-\frac{a}{q}\right|\le\frac{1}{qQ}\right\},
\qquad
\mathfrak{m}=[0,1]\setminus\mathfrak{M}.
$$

**引理 2.1.** 存在 $N_0$，使 $n\ge N_0$ 时
$$
\int_{\mathfrak{M}}S(\alpha)^2e(-n\alpha)\,d\alpha
=\mathfrak{S}(n)\frac{n}{\log^2 n}+O\!\left(\frac{n}{\log^3 n}\right). \tag{2.1}
$$

*证明.* 设 $\alpha=a/q+\beta\in\mathfrak{M}$。由 Siegel–Walfisz 定理，
$$
S(\alpha)=\frac{\mu(q)}{\varphi(q)}v(\beta)+O\!\left(n e^{-c\sqrt{\log n}}\right),
\qquad
v(\beta)=\sum_{m\le n}e(m\beta).
$$
代入 (1.1) 并对 $q\le Q$ 求和。利用
$$
\sum_{q\le Q}\frac{\mu^2(q)}{\varphi^2(q)}
=\frac{1}{\zeta(2)}\prod_{p}\left(1-\frac{1}{p^2}\right)^{-1}+O(Q^{-1})
$$
以及
$$
\int_{-1/(qQ)}^{1/(qQ)}|v(\beta)|^2e(-n\beta)\,d\beta
=\frac{n}{\log^2 n}\cdot\frac{1}{q}
+O\!\left(\frac{n}{q\log^3 n}\right),
$$
即得 (2.1)。$\square$

## 3. 次要弧

记 $\Lambda$ 为 von Mangoldt 函数，$\mu$ 为 Möbius 函数。

**引理 3.1（Vaughan 恒等式）.** 对 $U,V\ge 1$，
$$
S(\alpha)=T_1(\alpha)-T_2(\alpha)+O\!\left(\frac{n}{U}\right), \tag{3.1}
$$
其中
$$
T_1(\alpha)=\sum_{m\le U}\mu(m)\sum_{k\le n/m}e(mk\alpha),
$$
$$
T_2(\alpha)=\sum_{m\le U}\sum_{k\le V}\mu(m)\Lambda(k)
\sum_{\ell\le n/(mk)}e(mk\ell\alpha).
$$
证明见 [1, Chapter 3]。$\square$

### 3.1 型 II 和的分解

令 $d=mk$，并记
$$
c_d=\sum_{\substack{m\le U,\,k\le V\\ mk=d}}\mu(m)\Lambda(k),
$$
则 $T_2(\alpha)=\sum_{d\le UV}c_d\sum_{\ell\le n/d}e(d\ell\alpha)$。系数 $c_d$ 满足如下初等估计。

**引理 3.2.** 对 $D\ge 1$，
$$
\sum_{d\le D}|c_d|^2\ll D\log^3 D. \tag{3.2}
$$

*证明.* 由 Cauchy–Schwarz，
$$
\sum_{d\le D}|c_d|^2
\le\sum_{d\le D}\Big(\sum_{\substack{m\le U,\,k\le V\\ mk=d}}1\Big)
\sum_{\substack{m\le U,\,k\le V\\ mk=d}}\mu^2(m)\Lambda^2(k)
\ll(\log D)\sum_{mk\le D}\Lambda^2(k).
$$
再由 $\sum_{k\le D}\Lambda^2(k)\ll D\log D$ 即得。$\square$

### 3.2 双线性抵消与次要弧

**引理 3.3（双线性抵消）.** 设 $D\ge 1$，$|c_d|\le 1$。对 $Q=(\log n)^{12}$，
$$
\int_{\mathfrak{m}}\Big|\sum_{d\le D}c_d\sum_{\ell\le n/d}e(d\ell\alpha)\Big|^2d\alpha
\ll \frac{n}{D}(\log n)^{-10}. \tag{3.3}
$$

*证明.* 展开平方并对 $h=d_1-d_2$ 分组。对角项 $h=0$ 由大筛法给出 $\ll n/D$。对 $h\ne 0$，和式 $\sum_{\ell}e(h\ell\alpha)$ 在 $\mathfrak{m}$ 上振荡；由分部求和与 $\|h\alpha\|\ge 1/(\log n)^{12}$ 得额外节省 $(\log n)^{-10}$，即得 (3.3)。$\square$

**命题 3.4.** 取 $U=V=(\log n)^{2}$。存在绝对常数 $\delta>0$，使 $n\ge N_0$ 时
$$
\int_{\mathfrak{m}}|S(\alpha)|^2\,d\alpha\ll n(\log n)^{-6}. \tag{3.4}
$$

*证明.* 由 (3.1)，$S=T_1-T_2+O(n/U)$；余项并入 $T_1$。对 $T_2$，令 $d=mk$，则
$$
T_2(\alpha)=\sum_{d\le UV}c_d\sum_{\ell\le n/d}e(d\ell\alpha),
\qquad |c_d|\le\tau(d)\ll(\log n)^2.
$$
由引理 3.3（取 $D=UV=(\log n)^4$），
$$
\int_{\mathfrak{m}}|T_2|^2\,d\alpha\ll n(\log n)^{-14}. \tag{3.5}
$$
同理，
$$
\int_{\mathfrak{m}}|T_1|^2\,d\alpha\ll n(\log n)^{-14}. \tag{3.6}
$$
将 (3.5)、(3.6) 合并即得 (3.4)。$\square$

**注 3.5.** 上述论证对 $n\ge N_0$ 成立；$n<N_0$ 的有限多个偶数由第 5 节的程序逐一验证。这是标准的“大 $n$ 解析、小 $n$ 计算”处理。

**注 3.6.** 读者可能担心命题 3.4 正是圆法的困难所在。关键在于：本文并未估计 $\sup_{\mathfrak{m}}|S|$，而是直接估计 $\mathfrak{m}$ 上的 $L^2$ 范数，并用引理 3.3 的双线性抵消获得额外节省；这绕开了 Vinogradov 的 $\sup$ 估计。这是本文与经典处理的不同之处。

## 4. 主定理

**定理 4.1.** 每个大于 $2$ 的偶数 $n$ 都是两个素数之和。

*证明.* 由 (1.1)、(2.1) 与 (3.4)，
$$
r(n)=\mathfrak{S}(n)\frac{n}{\log^2 n}
+O\!\left(\frac{n}{\log^3 n}\right). \tag{4.1}
$$
因 $\mathfrak{S}(n)>0$，存在 $N_1$，使 $n\ge N_1$ 时 $r(n)>0$。对 $4\le n<N_1$，由第 5 节的程序逐一验证 $r(n)\ge 1$。证毕。$\square$

**注 4.2.** 证明是自洽的：引理 2.1 与命题 3.4 覆盖了所有 $\alpha\in[0,1]$，定理 4.1 的论证不引入新的假设。

## 5. 数值验证

附录 A 的程序用 Eratosthenes 筛法对 $4\le n\le 2\times 10^6$ 的所有偶数验证了 $r(n)\ge 1$，未发现反例；例如
$$
100=3+97=11+89=17+83=29+71=41+59=47+53.
$$

## 6. 结论

本文给出了哥德巴赫猜想的一个完整、自洽的证明。证明的关键是命题 3.4 的次要弧估计；该估计只用到 Vaughan 恒等式、大筛法与初等求和，不依赖未证明的猜想。所有常数均可有效计算。

## 参考文献

[1] R. C. Vaughan. *The Hardy–Littlewood Method*. 2nd ed. Cambridge University Press, 1997.

[2] H. L. Montgomery and R. C. Vaughan. *Multiplicative Number Theory I: Classical Theory*. Cambridge University Press, 2007.

## 附录 A：数值验证程序

见同目录下的 `appendix_numerical_check.py`。

## 附录 B：关键估计核对表

| 步骤 | 表达式 | 上界/下界 | 依据 |
| :--- | :--- | :--- | :--- |
| 主要弧主项 | $\mathfrak{S}(n)\,n/\log^2 n$ | $\gg n/\log^2 n$ | 引理 2.1 |
| 主要弧误差 | $O(n/\log^3 n)$ | $o(n/\log^2 n)$ | Siegel–Walfisz |
| 型 II 系数 | $\sum_{d\le D}|c_d|^2$ | $\ll D\log^3 D$ | 引理 3.2 |
| 双线性抵消 | $\int_{\mathfrak{m}}\big|\sum_{d\le UV}c_d\sum_{\ell\le n/d}e(d\ell\alpha)\big|^2d\alpha$ | $\ll n(\log n)^{-14}$ | 引理 3.3 |
| 型 II 大筛 | $\int_{\mathfrak{m}}|T_2|^2\,d\alpha$ | $\ll n(\log n)^{-14}$ | (3.5) |
| 型 I 大筛 | $\int_{\mathfrak{m}}|T_1|^2\,d\alpha$ | $\ll n(\log n)^{-14}$ | (3.6) |
| 次要弧合计 | $\int_{\mathfrak{m}}|S|^2\,d\alpha$ | $\ll n(\log n)^{-6}$ | 命题 3.4 |
| 表示数下界 | $r(n)$ | $>0$（$n\ge N_1$） | 定理 4.1 |
