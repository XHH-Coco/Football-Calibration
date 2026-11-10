"""M2 / T2.7–T2.13：H1–H4 / C1 预注册判定规则（**跑数前冻结**）。

阈值集中在顶部常量区，函数体内不允许出现裸数字。每个 ``*_verdict`` 返回
``{"decision": str, "reason": str}``，报告 §5 可据此逐条倒查；区间一律来自
``src.eval.bootstrap`` 的 48 块簇 bootstrap。

依据：``Team-32-Proposal_v3.0.md`` §2 / §5、``docs/plans/m2_harness_spec.md`` §7。
"""

from __future__ import annotations

# —— 唯一来源的阈值（改动须 M2 主签 + M5 会签）——
EQUIV_MARGIN = 0.02       # nats / match，全项目唯一等价边际
CI_MAIN = 0.90            # 主区间置信水平
CI_H2A = 0.95             # H2 判据 (a) 置信水平
H4_REL_THRESHOLD = 0.25   # H4 相对变化 25%
H4_MIN_DENOM = 0.01       # nats，分母过小护栏


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


def c1_verdict(delta: float, lo: float, hi: float) -> dict[str, str]:
    """C1 受控比较（模型类，B5a vs B4）：``Δ = LL(B5a) − LL(B4)``（正 = B4 更好）。"""
    b = _branch(delta, lo, hi)
    if b == "equivalent":
        decision, reason = "实际等价", "90% 区间完全落在 ±0.02 内"
    elif b == "above":
        decision, reason = "B4 更好", "90% 区间完全在 +0.02 之上"
    elif b == "below":
        decision, reason = "B5a 更好", "90% 区间完全在 −0.02 之下"
    else:
        decision, reason = "分辨率不足，不下结论", "区间跨边界或宽于 0.04"
    return {"decision": decision, "reason": reason}


def h1_verdict(slope_prop: float, lo: float, hi: float) -> dict[str, str]:
    """H1 主判据：比例法去抽水下 B6 的重校准斜率。斜率 ≤ 1 即证伪。"""
    if hi <= 1.0:
        return {"decision": "证伪", "reason": "比例法斜率区间上界 ≤ 1（未 under-dispersed）"}
    if lo > 1.0:
        return {"decision": "支持", "reason": "比例法斜率区间下界 > 1（under-dispersed）"}
    return {"decision": "不确定", "reason": "斜率区间跨 1，分辨率不足以判定"}


def h1_ordering_verdict(diff: float, lo: float, hi: float) -> dict[str, str]:
    """H1 次判据：``|slope−1|_proportional − |slope−1|_Shin``。下界 > 0 才宣称「比例法最大」。"""
    if lo > 0.0:
        return {"decision": "支持排序", "reason": "差值的 90% 区间下界 > 0，比例法偏差最大"}
    return {"decision": "不作排序宣称", "reason": "区间下界 ≤ 0，三法只作描述性对照"}


def h2_verdict(delta_46: float, lo95: float, hi95: float,
               lo90: float, hi90: float) -> dict[str, str]:
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
    return {"decision": f"判据(a)：{a}；判据(b)：{bd}",
            "reason": f"Δ_46 = {delta_46:.4f}，95% CI [{lo95:.4f}, {hi95:.4f}]，"
                      f"90% CI [{lo90:.4f}, {hi90:.4f}]"}


def h3_verdict(b1: float, lo1: float, hi1: float,
               b2: float, lo2: float, hi2: float) -> dict[str, str]:
    """H3 联合判据：两个系数都正且各自 90% 区间下界 > 0 才支持；任一跨 0 只描述。"""
    if b1 > 0 and b2 > 0 and lo1 > 0 and lo2 > 0:
        return {"decision": "支持", "reason": "两系数均正且各自区间下界 > 0"}
    return {"decision": "只作描述", "reason": "至少一个系数跨 0，不宣称成立或证伪"}


def h4_verdict(rel: float, lo: float, hi: float,
               denom_gap: float) -> dict[str, str]:
    """H4：重校准前后 gap 的相对变化。上界 < 25% 支持、下界 > 25% 证伪；分母过小改绝对差。"""
    if denom_gap < H4_MIN_DENOM:
        return {"decision": "改报绝对差", "reason": f"分母 gap {denom_gap:.4f} < 0.01 nats，比值不稳"}
    if hi < H4_REL_THRESHOLD:
        return {"decision": "支持", "reason": f"相对变化 90% 区间上界 {hi:.3f} < 0.25"}
    if lo > H4_REL_THRESHOLD:
        return {"decision": "证伪", "reason": f"相对变化 90% 区间下界 {lo:.3f} > 0.25"}
    return {"decision": "分辨率不足", "reason": "相对变化区间跨 25%，不下判定"}
