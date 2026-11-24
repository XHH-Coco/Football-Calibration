"""M4 · B5 超参网格敏感性分析（2026-11-24 复盘 P0-1 的仓库证据）。

交付时的网格是 ``leaf ∈ {7,15,31} × lr ∈ {0.03,0.05,0.1}``，逐折在 1 季验证集上取
argmin。事后看，这个 argmin **贴在网格最保守的那个角上**：leaf=7（最小）占 46/48
折、lr=0.03（最小）占 37/48 折。最优值反复落在边界，说明"越保守越好"是数据在
说话，而"边界在哪儿"只是网格在说话——只要边界还在那儿，argmin 就永远是同一个角。

本脚本把这件事变成可复现的四张表：

  表 A 选中分布：原网格 48 折的 leaf/lr 频次；扩展网格（leaf 往小补到 3、
       lr 往小补到 0.01，共 20 格）48 折的频次。若扩展后 argmin 仍贴边，
       说明再加网格也是同一个结论，不是网格没给够。
  表 B 验证集对照：原网格 argmin、扩展网格 argmin、四组固定超参的 48 折验证均值。
  表 C test 对照：20 格全部重训两臂的池化 test log loss，以及"固定 vs 两种 argmin"
       的配对差（48 块簇 bootstrap，10,000 次，与 M2 同一估计量）。
  表 D C1/C2 在六种口径下的判定，用来确认换口径没有改变 H2 的结论。

口径说明：表 C 的存在是为了回答"固定是不是碰巧挑对了"。若四组固定的池化损失
都优于两种 argmin，"固定优于逐折选参"就是结构性的，不是单点运气；若只有某一组
好，报告必须如实写出来，不能只说好听的那一组。

实测结果（2026-11-24）：答案是"部分"。扩展网格的 argmin **仍然贴在新边界上**
（leaf=3 占 37/48、lr=0.01 占 22/48），所以缺陷不是"网格差一格"而是"不该搜"；
只有 (3,0.01)/(3,0.03) 两组固定优于扩展 argmin，(5,0.03)/(7,0.03) 反而更差。
两者拆开算：把网格放宽值 0.0067，在放宽后改用固定值再省 0.0037。

用法：
  python -m src.models.sens_b5_grid            # 有缓存则直接出表（秒级）
  python -m src.models.sens_b5_grid --rebuild  # 重算两张缓存（约 17 分钟）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.bootstrap import BlockDeltas, cluster_bootstrap  # noqa: E402
from src.features import (FEATURE_COLS, WHITELIST_B5A,  # noqa: E402
                          fit_features, transform_features)
from src.models._common import (load_blocks, load_panel, load_xi_map,  # noqa: E402
                                log_loss)
from src.models.b5_gbm import FIXED_HP  # noqa: E402

LOGS = ROOT / "results" / "logs"
PREDS = ROOT / "results" / "preds"
DIAG = LOGS / "selection_diagnostic"
CACHE_TEST = LOGS / "sens_b5_grid_test.csv"
CACHE_VAL = LOGS / "sens_b5_grid_val.csv"

GRID_ORIG = [(leaf, lr) for leaf in (7, 15, 31) for lr in (0.03, 0.05, 0.1)]
GRID_EXT = [(leaf, lr) for leaf in (3, 5, 7, 15, 31)
            for lr in (0.01, 0.03, 0.05, 0.1)]
# 候选固定点：最保守角 (3,0.01)=主口径、往上三格看单调性。
CONFIGS = [(3, 0.01), (3, 0.03), (5, 0.03), (7, 0.03)]
# 主口径直接从 b5_gbm 取，不在这里复制一份——本文件第一次落地时就因为手抄成
# (3,0.03) 而让表 C 的「← 主口径」标记指错了行（数字不受影响，只有标记错）。
FIXED = FIXED_HP
EQ_MARGIN = 0.02
B = 10_000


def _cell(leaf: int, lr: float) -> str:
    return f"{leaf}_{lr}"


def build_test_cache() -> pd.DataFrame:
    """一块一算特征、20 格共用一张 X_test。

    注意：``fit_features(train)`` 返回的 builder 有状态，``transform_features`` 会
    逐场推进它。因此 test 特征**每块只能算一次**，用同一份 X_test 跑 20 格。早期
    版本每格各调一次 ``fit_features``（每格都是全新状态，数字正确），白算 20 次
    特征——48 块要多花约 55 分钟，是本文件第一次运行耗时 75 分钟的原因。
    """
    from src.models.b5_gbm import _fit_hgb, _proba, _weights
    from src.splits import resolve_split
    panel, blocks = load_panel(), load_blocks()
    xi_map = load_xi_map()
    rows: list[dict] = []
    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(panel, b)
        xi = xi_map.get(b["block_id"], 0.0019)
        x_tr, builder = fit_features(train)
        x_te = transform_features(test, builder)
        w = _weights(train, xi)
        y, y_te = train["y"].to_numpy(), test["y"].to_numpy()
        rec = {"block_id": b["block_id"], "n_test": len(test)}
        for leaf, lr in GRID_EXT:
            for arm, cols in (("B5a", WHITELIST_B5A), ("B5b", FEATURE_COLS)):
                clf = _fit_hgb(x_tr[cols], y, w, leaf, lr)
                rec[f"{arm}_{_cell(leaf, lr)}"] = log_loss(y_te, _proba(clf, x_te[cols]))
        rows.append(rec)
        print(f"[test {i:02d}/48] {b['block_id']:<11} "
              f"B5b 最好格 {min(v for k, v in rec.items() if k.startswith('B5b_')):.5f}")
    return pd.DataFrame(rows)


def build_val_cache() -> pd.DataFrame:
    """扩展网格 48 折验证损失（内层：train 的最后一个赛季作验证集）。"""
    from src.models.b5_gbm import _fit_hgb, _proba, _weights
    from src.splits import resolve_split
    panel, blocks = load_panel(), load_blocks()
    xi_map = load_xi_map()
    rows: list[dict] = []
    for i, b in enumerate(blocks, 1):
        train, _ = resolve_split(panel, b)
        xi = xi_map.get(b["block_id"], 0.0019)
        x_tr, _ = fit_features(train)
        w = _weights(train, xi)
        y = train["y"].to_numpy()
        mask = (train["season"] == train["season"].max()).to_numpy()
        x_in, x_val = x_tr[FEATURE_COLS][~mask], x_tr[FEATURE_COLS][mask]
        y_in, y_val = y[~mask], y[mask]
        rec = {"block_id": b["block_id"]}
        for leaf, lr in GRID_EXT:
            clf = _fit_hgb(x_in, y_in, w[~mask], leaf, lr)
            rec[_cell(leaf, lr)] = log_loss(y_val, _proba(clf, x_val))
        rows.append(rec)
        print(f"[val {i:02d}/48] {b['block_id']:<11} best="
              f"{min(v for k, v in rec.items() if k != 'block_id'):.5f}")
    return pd.DataFrame(rows)


def _ci(delta: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    """块级配对差 → 簇 bootstrap 区间（复用 M2 估计量）。

    只给 values/weights 是充分的：``cluster_bootstrap`` 只对这两者做加权重采样，
    ``per_match`` 仅供 iid 变体使用，这里给等长占位数组即可。
    """
    blk = BlockDeltas(values=np.asarray(delta, float),
                      weights=np.asarray(weights, float),
                      per_match=np.zeros(int(np.sum(weights))),
                      n_paired=int(np.sum(weights)))
    return cluster_bootstrap(blk, B=B, alpha=0.10)


def _branch(ci: dict[str, float]) -> str:
    """四分支判定（阈值 ±0.02，全项目唯一）。"""
    lo, hi = ci["lo"], ci["hi"]
    if lo > 0 or hi < 0:
        if hi <= EQ_MARGIN and lo >= -EQ_MARGIN:
            return "差异可分但实际等价"
        return "跨边界（差异可分且越过 ±0.02）"
    return "实际等价（区间跨 0）"


def _block_ll(df: pd.DataFrame, block_ids: pd.Series) -> np.ndarray:
    d = df.copy()
    d["block_id"] = d["league"] + "|" + d["season"]
    g = d.groupby("block_id").apply(
        lambda x: log_loss(x["y"].to_numpy(),
                           x[["p_home", "p_draw", "p_away"]].to_numpy()),
        include_groups=False)
    return g.reindex(block_ids).to_numpy()


def _pooled(col: np.ndarray, n: np.ndarray) -> float:
    return float(np.sum(col * n) / n.sum())


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / B5 网格敏感性分析")
    ap.add_argument("--rebuild", action="store_true", help="重算两张缓存")
    args = ap.parse_args()

    if args.rebuild or not CACHE_TEST.exists():
        print("== 重算 test 缓存（48 块 × 20 格 × 2 臂）==")
        build_test_cache().to_csv(CACHE_TEST, index=False, encoding="utf-8")
    if args.rebuild or not CACHE_VAL.exists():
        print("== 重算 val 缓存（48 块 × 20 格）==")
        build_val_cache().to_csv(CACHE_VAL, index=False, encoding="utf-8")

    test = pd.read_csv(CACHE_TEST)
    val = pd.read_csv(CACHE_VAL)
    cells = [_cell(leaf, lr) for leaf, lr in GRID_EXT]
    cells_o = [_cell(leaf, lr) for leaf, lr in GRID_ORIG]
    n = test["n_test"].to_numpy(float)
    blocks = test["block_id"]

    print("\n" + "=" * 96)
    print("表 A · 逐折 argmin 的选中分布（贴边 = 网格画窄了）")
    print("=" * 96)
    tune = DIAG / "b5_params_argmin.csv"
    if not tune.exists():
        tune = LOGS / "b5_tuning.csv"
    if tune.exists():
        t = pd.read_csv(tune)
        print(f"原网格（{len(GRID_ORIG)} 格）   leaf 频次 "
              f"{t['max_leaf_nodes'].value_counts().sort_index().to_dict()}   lr 频次 "
              f"{t['learning_rate'].value_counts().sort_index().to_dict()}   ← {tune.name}")
    else:
        print("原网格选中分布：未找到 b5_tuning(_argmin).csv，跳过")
    best_ext = val[cells].idxmin(axis=1)
    leaf_e = [int(c.split("_")[0]) for c in best_ext]
    lr_e = [float(c.split("_")[1]) for c in best_ext]
    print(f"扩展网格（{len(GRID_EXT)} 格）  leaf 频次 "
          f"{pd.Series(leaf_e).value_counts().sort_index().to_dict()}   lr 频次 "
          f"{pd.Series(lr_e).value_counts().sort_index().to_dict()}")

    print("\n" + "=" * 96)
    print("表 B · 验证集 48 折对照（均值，越低越好）")
    print("=" * 96)
    v_orig = val[cells_o].min(axis=1).mean()
    v_ext = val[cells].min(axis=1).mean()
    print(f"{'原网格 argmin':<16}{v_orig:.6f}")
    print(f"{'扩展网格 argmin':<16}{v_ext:.6f}   比原网格 {v_ext - v_orig:+.6f}")
    for leaf, lr in CONFIGS:
        c = _cell(leaf, lr)
        print(f"{f'固定 ({leaf},{lr})':<16}{val[c].mean():.6f}"
              f"   比扩展 argmin {val[c].mean() - v_ext:+.6f}"
              f"   被 argmin 选中 {int((best_ext == c).sum())}/48 折")

    print("\n" + "=" * 96)
    print("表 C · test 池化 log loss（48 块，按场数加权）")
    print("=" * 96)
    ext_a = np.array([test.loc[i, f"B5a_{best_ext.iloc[i]}"] for i in range(len(test))])
    ext_b = np.array([test.loc[i, f"B5b_{best_ext.iloc[i]}"] for i in range(len(test))])
    rows_c = []
    arch_a = DIAG / "preds_B5a_argmin.csv"
    arch_b = DIAG / "preds_B5b_argmin.csv"
    if arch_a.exists():
        oa = _block_ll(pd.read_csv(arch_a), blocks)
        ob = _block_ll(pd.read_csv(arch_b), blocks)
        rows_c.append(("原网格 argmin（交付）", oa, ob, oa - ext_a))
    rows_c.append(("扩展网格 argmin", ext_a, ext_b, np.zeros(len(test))))
    for leaf, lr in CONFIGS:
        c = _cell(leaf, lr)
        a, bb = test[f"B5a_{c}"].to_numpy(), test[f"B5b_{c}"].to_numpy()
        rows_c.append((f"固定 ({leaf},{lr})", a, bb, a - ext_a))
    print(f"{'口径':<22}{'B5a':>10}{'B5b':>10}"
          f"{'B5a vs 扩展argmin':>20}{'90% 区间':>24}")
    for tag, a, bb, dv in rows_c:
        ci = _ci(dv, n)
        star = "  ← 主口径" if tag == f"固定 ({FIXED[0]},{FIXED[1]})" else ""
        print(f"{tag:<22}{_pooled(a, n):>10.6f}{_pooled(bb, n):>10.6f}"
              f"{(ci['point'] if tag != '扩展网格 argmin' else 0):>+20.5f}"
              f"   [{ci['lo']:+.5f}, {ci['hi']:+.5f}]{star}")

    print("\n" + "=" * 96)
    print("D · C1 / C2 在三种口径下的判定")
    print("C1 = LL(B5a) − LL(B4)（正 = B5a 更差）；C2 = LL(B5b) − LL(B5a)（负 = 加信息有提升）")
    print("=" * 96)
    b4 = _block_ll(pd.read_csv(PREDS / "preds_B4.csv"), blocks)
    cases: list[tuple[str, np.ndarray, np.ndarray]] = []
    if arch_a.exists():
        cases.append(("原网格 argmin", oa - b4, ob - oa))
    cases.append(("扩展网格 argmin", ext_a - b4, ext_b - ext_a))
    for leaf, lr in CONFIGS:
        c = _cell(leaf, lr)
        a, bb = test[f"B5a_{c}"].to_numpy(), test[f"B5b_{c}"].to_numpy()
        cases.append((f"固定 ({leaf},{lr})", a - b4, bb - a))
    print(f"{'口径':<18}{'C1':>10}{'C1 90% 区间':>24}{'判定':<24}"
          f"{'C2':>10}{'C2 90% 区间':>24}{'判定':<24}")
    for tag, c1, c2 in cases:
        r1, r2 = _ci(c1, n), _ci(c2, n)
        print(f"{tag:<18}{r1['point']:>+10.5f}   [{r1['lo']:+.5f}, {r1['hi']:+.5f}]"
              f"{_branch(r1):<24}{r2['point']:>+10.5f}   [{r2['lo']:+.5f}, {r2['hi']:+.5f}]"
              f"{_branch(r2):<24}")

    print(f"\n注：等价边际 ±{EQ_MARGIN} 是项目内唯一阈值。区间不含 0 且整体落在 "
          f"±{EQ_MARGIN} 内 → 「差异可分但实际等价」；区间跨 0 → 「实际等价」；"
          "区间整体越过边界 → 「跨边界」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
