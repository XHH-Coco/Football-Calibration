"""M2 / T2.7–T2.13：H1–H4 / C1 预注册判定规则（**跑数前冻结**）。

阈值集中在顶部常量区，函数体内不允许出现裸数字。每个 ``*_verdict`` 返回

    {"decision": str, "reason": str, "interval": [lo, hi] | None, "n_paired": int | None}

后两项是 v1.4 补上的结构化倒查字段（规范 §7.7 原本就要求「用到的区间与 n_paired」，
旧实现只把区间写进 reason 文本，M5 无法自动核对）。需要多个区间的判定另带
``interval_95``（H2 判据 a）或 ``intervals``（H3 两个系数）。所有字段恒存在，
不适用的值为 ``None``，便于直接落成 CSV。

依据：``Team-32-Proposal_v3.0.md`` §2 / §5、``docs/plans/m2_harness_spec.md`` §7。
"""

from __future__ import annotations

# —— 唯一来源的阈值（改动须 M2 主签 + M5 会签）——
EQUIV_MARGIN = 0.02       # nats / match，全项目唯一等价边际
CI_MAIN = 0.90            # 主区间置信水平
CI_H2A = 0.95             # H2 判据 (a) 置信水平
H4_REL_THRESHOLD = 0.25   # H4 相对变化 25%
H4_MIN_DENOM = 0.01       # nats，分母过小护栏


def _envelope(decision: str, reason: str, interval=None,
              n_paired: int | None = None, **extra) -> dict:
    """统一的返回信封：判定 + 理由 + 用到的区间 + 配对场数（+ 判定专属附加字段）。"""
    out = {
        "decision": decision,
        "reason": reason,
        "interval": None if interval is None else [float(interval[0]), float(interval[1])],
        "n_paired": None if n_paired is None else int(n_paired),
    }
    out.update(extra)
    return out


def _branch(point: float, lo: float, hi: float,
            margin: float = EQUIV_MARGIN) -> str:
    """四分支：完全在 (+margin) 之上 / (−margin) 之下 / 完全落在等价带内 / 跨边界。"""
    if lo > margin:
        return "above"
    if hi < -margin:
        return "below"
    if lo >= -margin and hi <= margin:
        return "equivalent"
    return "indeterminate"


def controlled_verdict(before: str, after: str, delta: float, lo: float,
                       hi: float, n_paired: int | None = None) -> dict:
    """受控比较四分支（C1/C2 通用）：``Δ = LL(after) − LL(before)``，正 = before 更好。"""
    b = _branch(delta, lo, hi)
    if b == "equivalent":
        decision, reason = "实际等价", "90% 区间完全落在 ±0.02 内"
    elif b == "above":
        decision, reason = f"{before} 更好", "90% 区间完全在 +0.02 之上"
    elif b == "below":
        decision, reason = f"{after} 更好", "90% 区间完全在 −0.02 之下"
    elif lo > 0.0 or hi < 0.0:
        # 区间不含 0 = 差异可分，只是跨过 ±0.02 这条**实用**边界：两件事不能混为一谈
        decision = "跨边界，不下结论"
        reason = ("90% 区间不含 0（差异可分），但整体跨过 ±0.02 等价边际 → "
                  "只报点估计与区间，不作实用性宣称")
    else:
        decision = "分辨率不足，不下结论"
        reason = "90% 区间跨 0（或宽于 0.04），测不出方向"
    return _envelope(decision, reason, interval=(lo, hi), n_paired=n_paired)


def c1_verdict(delta: float, lo: float, hi: float,
               n_paired: int | None = None) -> dict:
    """C1（模型类，B4 → B5a）：``Δ = LL(B5a) − LL(B4)``（正 = B4 更好）。"""
    return controlled_verdict("B4", "B5a", delta, lo, hi, n_paired=n_paired)


def c2_verdict(delta: float, lo: float, hi: float,
               n_paired: int | None = None) -> dict:
    """C2（信息集，B5a → B5b）：``Δ = LL(B5b) − LL(B5a)``（正 = B5a 更好）。"""
    return controlled_verdict("B5a", "B5b", delta, lo, hi, n_paired=n_paired)


def h1_verdict(slope_prop: float, lo: float, hi: float,
               n_paired: int | None = None) -> dict:
    """H1 主判据：比例法去抽水下 B6 的重校准斜率。斜率 ≤ 1 即证伪。"""
    if hi <= 1.0:
        return _envelope("证伪", "比例法斜率区间上界 ≤ 1（未 under-dispersed）",
                         (lo, hi), n_paired)
    if lo > 1.0:
        return _envelope("支持", "比例法斜率区间下界 > 1（under-dispersed）",
                         (lo, hi), n_paired)
    return _envelope("不确定", "斜率区间跨 1，分辨率不足以判定", (lo, hi), n_paired)


def h1_ordering_verdict(diff: float, lo: float, hi: float,
                        n_paired: int | None = None) -> dict:
    """H1 次判据：``|slope−1|_proportional − |slope−1|_Shin``。下界 > 0 才宣称「比例法最大」。"""
    if lo > 0.0:
        return _envelope("支持排序", "差值的 90% 区间下界 > 0，比例法偏差最大",
                         (lo, hi), n_paired)
    return _envelope("不作排序宣称", "区间下界 ≤ 0，三法只作描述性对照", (lo, hi), n_paired)


def h2_verdict(delta_46: float, lo95: float, hi95: float,
               lo90: float, hi90: float, n_paired: int | None = None) -> dict:
    """H2 双判据，``Δ_46 = LL(B4) − LL(B6)``（正 = 模型更差）。"""
    # 判据 (a)：95% 区间
    if hi95 < 0.0:
        a = "证伪(a)：B4 明确优于 B6 —— 先查泄漏"
    elif lo95 > 0.0:
        a = "支持(a)：B4 未追上 B6"
    else:
        a = "未测出差异，也不排除等价"
    # 判据 (b)：90% 区间 vs ±0.02
    b = _branch(delta_46, lo90, hi90)
    if b == "equivalent":
        bd = "证伪(b)：差距落在 ±0.02 内（实际等价）"
    elif b == "above":
        bd = "支持(b)：差距实际非零（区间整体高于 +0.02）"
    elif b == "below":
        bd = "支持(b)方向异常：模型反而更优 —— 先查泄漏"
    else:
        bd = "分辨率不足，不做判定"
    return _envelope(
        f"判据(a)：{a}；判据(b)：{bd}",
        f"Δ_46 = {delta_46:.4f}，95% CI [{lo95:.4f}, {hi95:.4f}]，"
        f"90% CI [{lo90:.4f}, {hi90:.4f}]",
        interval=(lo90, hi90), n_paired=n_paired,
        interval_95=[float(lo95), float(hi95)], point=float(delta_46),
    )


def h3_verdict(b1: float, lo1: float, hi1: float,
               b2: float, lo2: float, hi2: float,
               n_paired: int | None = None) -> dict:
    """H3 联合判据：两个系数都正且各自 90% 区间下界 > 0 才支持；任一跨 0 只描述。"""
    intervals = {"promoted": [float(lo1), float(hi1)],
                 "early": [float(lo2), float(hi2)]}
    if b1 > 0 and b2 > 0 and lo1 > 0 and lo2 > 0:
        return _envelope("支持", "两系数均正且各自区间下界 > 0",
                         n_paired=n_paired, intervals=intervals,
                         point={"promoted": float(b1), "early": float(b2)})
    return _envelope("只作描述", "至少一个系数跨 0，不宣称成立或证伪",
                     n_paired=n_paired, intervals=intervals,
                     point={"promoted": float(b1), "early": float(b2)})


def h4_verdict(rel: float, lo: float, hi: float,
               denom_gap: float, n_paired: int | None = None) -> dict:
    """H4：重校准前后 gap 的相对变化。上界 < 25% 支持、下界 > 25% 证伪；分母过小改绝对差。"""
    if denom_gap < H4_MIN_DENOM:
        return _envelope("改报绝对差",
                         f"分母 gap {denom_gap:.4f} < 0.01 nats，比值不稳",
                         (lo, hi), n_paired, denom_gap=float(denom_gap))
    if hi < H4_REL_THRESHOLD:
        return _envelope("支持", f"相对变化 90% 区间上界 {hi:.3f} < 0.25",
                         (lo, hi), n_paired, denom_gap=float(denom_gap))
    if lo > H4_REL_THRESHOLD:
        return _envelope("证伪", f"相对变化 90% 区间下界 {lo:.3f} > 0.25",
                         (lo, hi), n_paired, denom_gap=float(denom_gap))
    return _envelope("分辨率不足", "相对变化区间跨 25%，不下判定",
                     (lo, hi), n_paired, denom_gap=float(denom_gap))
