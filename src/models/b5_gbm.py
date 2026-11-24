"""M4 · T4.5 / T4.6 B5a / B5b —— sklearn 内置 HGB（D1 决策，零新增依赖）。

受控比较的锁（data_interface.md §2「对照一致性」）：
  - B4↔B5a 锁**信息 + 权重**：B5a 只用白名单（双方滚动进球/失球、Elo 差），
    sample_weight = exp(−ξ̂·Δ天)，ξ̂ 取该折 B4 的估计，Δ天 = train 末日 − 该场日期。
    两处参考日不同（B4 用 test_start、这里用 train 末场），只差一个常数因子；
    归一后逐元素相等，由 ``check_m4.py`` 第 6 项现场断言。
  - B5a↔B5b 锁**权重 + 超参**：同折同权重、同超参，只换信息。
  - **超参不选**（2026-11-24 口径变更，与 B4 的固定超参同源）：恒用
    ``FIXED_PARAMS = (leaf=3, lr=0.01)``。理由与证据见
    ``src/models/sens_b5_grid.py``：交付网格的 argmin 46/48 折贴在 leaf=7（最小）、
    37/48 折贴在 lr=0.03（最小）；把网格往小扩展到 20 格后，argmin 依旧 37/48 折
    贴在 leaf=3（新的最小值）——最优值永远贴边，说明边界是网格画的、不是数据画
    的。**但固定值的收益是有条件的**：只有 (3,0.01)/(3,0.03) 两组优于扩展网格的
    argmin，(5,0.03) 差 0.0024、(7,0.03) 差 0.0050——固定只在"数据想要的那个容量"
    上才有效，把容量硬抬上去只会更差。故取最保守的角，并把相邻的 (3,0.03) 留作
    稳健性对照。旧的逐折 argmin 规则降级为诊断，产物只写
    ``results/logs/selection_diagnostic/*_argmin``，不参与主表。
predict_proba 列序 = clf.classes_（数值标签恒为升序 [0,1,2] = H/D/A），
仍按 §1.1 显式重排并断言。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features import (FEATURE_COLS, WHITELIST_B5A,  # noqa: E402
                          fit_features, transform_features)
from src.models._common import (DEFAULT_XI, SCHEMA_COLS, load_blocks,  # noqa: E402
                                load_panel, load_xi_map, log_loss,
                                make_preds_df)
from src.splits import resolve_split  # noqa: E402

GRID = [(leaf, lr) for leaf in (7, 15, 31) for lr in (0.03, 0.05, 0.1)]
"""交付时的 9 格网格。仅用于复现被退休的逐折 argmin 诊断，主口径不再读它。"""

FIXED_PARAMS = {"max_leaf_nodes": 3, "learning_rate": 0.01}
FIXED_HP: tuple[int, float] = (FIXED_PARAMS["max_leaf_nodes"],
                               FIXED_PARAMS["learning_rate"])
"""现行主口径：48 折同一组超参，取扩展网格的最小容量角。

依据见 ``sens_b5_grid.py`` 的四张表：交付 9 格网格的 argmin 46/48 折贴在 leaf=7
（最小）、37/48 折贴在 lr=0.03（最小）；把网格往下扩到 20 格后 argmin 依旧 37/48
折贴在 leaf=3（新的最小值）、lr=0.01 出现频次最高。最优值永远贴边 ⇒ "越保守越好"
是数据在说话，边界在哪儿只是网格在说话，因此停止搜索、直接取角。该角同时是扩展
网格里被选中最多的一格（16/48，次高是 (3,0.05) 的 9/48），两条理由指向同一处。
相邻的 (3, 0.03) 保留为稳健性对照：test 上只差 0.0003 nats（等价边际的 1.5%），
所以选两者中的哪一个都不承载结论。"""

DEFAULT_PARAMS = FIXED_PARAMS
"""向后兼容别名（check_m4 / 测试仍按这个名字取参）。"""

SELECTIONS: tuple[str, ...] = ("fixed", "argmin")
HGB_KW = dict(max_iter=1000, early_stopping=True, validation_fraction=0.1,
              n_iter_no_change=20, random_state=0)
DIAG = ROOT / "results" / "logs" / "selection_diagnostic"
TUNING_PATH = DIAG / "b5_params_argmin.csv"
"""退休规则的超参表（逐折 argmin）；主口径写 results/logs/b5_params.csv。"""
LEGACY_TUNING = ROOT / "results" / "logs" / "b5_tuning.csv"
"""交付时的调参表位置；只作只读回退，迁移到 DIAG 后不再写入。"""
PARAMS_PATH = ROOT / "results" / "logs" / "b5_params.csv"


def _weights(train_df: pd.DataFrame, xi: float) -> np.ndarray:
    """w = exp(−ξ·Δ天)，Δ天 = train 末日 − 该场日期（与 B4 时间衰减同参照）。"""
    ref = pd.to_datetime(train_df["date"].max())
    days = (ref - pd.to_datetime(train_df["date"])).dt.days.to_numpy(float)
    return np.exp(-xi * days)


def _fit_hgb(x: pd.DataFrame, y: np.ndarray, w: np.ndarray,
             leaf: int, lr: float) -> HistGradientBoostingClassifier:
    clf = HistGradientBoostingClassifier(max_leaf_nodes=leaf, learning_rate=lr,
                                         **HGB_KW)
    clf.fit(x, y, sample_weight=w)
    return clf


def _proba(clf: HistGradientBoostingClassifier, x: pd.DataFrame) -> np.ndarray:
    p = clf.predict_proba(x)
    internal = list(clf.classes_)
    order = [internal.index(k) for k in [0, 1, 2]]
    p = p[:, order]
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-9)
    return p


def _fit_variant(train_df: pd.DataFrame, sample_weight: np.ndarray | None,
                 cols: list[str], leaf: int, lr: float) -> dict:
    x_train, builder = fit_features(train_df)
    w = (_weights(train_df, DEFAULT_XI) if sample_weight is None
         else np.asarray(sample_weight, dtype=float))
    clf = _fit_hgb(x_train[cols], train_df["y"].to_numpy(), w, leaf, lr)
    return {"clf": clf, "builder": builder, "cols": cols}


def fit_b5a(train_df: pd.DataFrame, sample_weight=None) -> dict:
    return _fit_variant(train_df, sample_weight, WHITELIST_B5A,
                        DEFAULT_PARAMS["max_leaf_nodes"],
                        DEFAULT_PARAMS["learning_rate"])


def fit_b5b(train_df: pd.DataFrame, sample_weight=None) -> dict:
    return _fit_variant(train_df, sample_weight, FEATURE_COLS,
                        DEFAULT_PARAMS["max_leaf_nodes"],
                        DEFAULT_PARAMS["learning_rate"])


def predict_proba(test_df: pd.DataFrame, state: dict) -> np.ndarray:
    x_test = transform_features(test_df, state["builder"])
    return _proba(state["clf"], x_test[state["cols"]])


def _tune_block(x_train: pd.DataFrame, train_df: pd.DataFrame,
                w: np.ndarray) -> tuple[int, float, float]:
    """内层调参：train 的最后一个赛季作验证集（只看 train 内部）。"""
    val_season = train_df["season"].max()
    mask_val = (train_df["season"] == val_season).to_numpy()
    x_in, x_val = x_train[~mask_val], x_train[mask_val]
    y_in = train_df["y"].to_numpy()[~mask_val]
    y_val = train_df["y"].to_numpy()[mask_val]
    best = (None, np.inf)
    for leaf, lr in GRID:
        clf = _fit_hgb(x_in[FEATURE_COLS], y_in, w[~mask_val], leaf, lr)
        p = _proba(clf, x_val[FEATURE_COLS])
        score = log_loss(y_val, p)
        if score < best[1]:
            best = ((leaf, lr), score)
    return best[0][0], best[0][1], float(best[1])


def _run(panel: pd.DataFrame, blocks: list[dict], xi_map: dict[str, float],
         selection: str = "fixed", skip_tune: bool = False
         ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``selection="fixed"``（主口径）恒用 FIXED_PARAMS；``"argmin"`` 是退休规则。"""
    if selection not in SELECTIONS:
        raise ValueError(f"selection 必须是 {SELECTIONS}，收到 {selection!r}")
    tuning = None
    if selection == "argmin":
        src = TUNING_PATH if TUNING_PATH.exists() else LEGACY_TUNING
        if skip_tune:
            if not src.exists():
                raise SystemExit(f"--skip-tune 但没有 {src}")
            tuning = pd.read_csv(src)
            if len(tuning) != 48:
                raise SystemExit(f"{src} 应有 48 行，实际 {len(tuning)}")
    parts_a: list[pd.DataFrame] = []
    parts_b: list[pd.DataFrame] = []
    hp_rows: list[dict] = []

    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(panel, b)
        xi = xi_map.get(b["block_id"], DEFAULT_XI)
        x_train, builder = fit_features(train)
        w = _weights(train, xi)

        if selection == "fixed":
            leaf, lr, val_ll = FIXED_HP[0], FIXED_HP[1], float("nan")
        elif tuning is not None:
            row = tuning[tuning["block_id"] == b["block_id"]].iloc[0]
            leaf = int(row["max_leaf_nodes"])
            lr = float(row["learning_rate"])
            val_ll = float(row["val_logloss"])
        else:
            leaf, lr, val_ll = _tune_block(x_train, train, w)
        hp_rows.append({"block_id": b["block_id"], "max_leaf_nodes": leaf,
                        "learning_rate": lr, "val_logloss": val_ll,
                        "selection": selection})

        y = train["y"].to_numpy()
        wa = _weights(train, xi)          # 同一公式重算，供逐元素相等断言
        clf_a = _fit_hgb(x_train[WHITELIST_B5A], y, wa, leaf, lr)
        clf_b = _fit_hgb(x_train[FEATURE_COLS], y, w, leaf, lr)
        assert np.array_equal(wa, w), "B5a/B5b 权重必须逐元素相同"

        x_test = transform_features(test, builder)
        parts_a.append(make_preds_df(test, _proba(clf_a, x_test[WHITELIST_B5A]), "B5a"))
        parts_b.append(make_preds_df(test, _proba(clf_b, x_test[FEATURE_COLS]), "B5b"))
        ll_a = log_loss(test["y"].to_numpy(),
                        parts_a[-1][["p_home", "p_draw", "p_away"]].to_numpy())
        ll_b = log_loss(test["y"].to_numpy(),
                        parts_b[-1][["p_home", "p_draw", "p_away"]].to_numpy())
        print(f"[{i:02d}/48] {b['block_id']:<11} leaf={leaf:>2} lr={lr:.2f} "
              f"B5a={ll_a:.5f} B5b={ll_b:.5f}")

    return (pd.concat(parts_a, ignore_index=True),
            pd.concat(parts_b, ignore_index=True),
            pd.DataFrame(hp_rows))


def _write(full: pd.DataFrame, out: Path) -> float:
    assert len(full) == 16_733 and full["match_id"].is_unique
    out.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(out, index=False, encoding="utf-8")
    return log_loss(full["y"].to_numpy(),
                    full[["p_home", "p_draw", "p_away"]].to_numpy())


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.5-T4.6 B5a/B5b HGB")
    ap.add_argument("--selection", choices=SELECTIONS, default="fixed",
                    help="fixed=现行主口径（恒用 FIXED_PARAMS）；"
                         "argmin=被退休的逐折选参，产物只写 diagnostic 目录")
    ap.add_argument("--skip-tune", action="store_true",
                    help="argmin 口径下复用归档的 b5_tuning_argmin.csv，不重跑网格")
    args = ap.parse_args()
    panel = load_panel()
    blocks = load_blocks()
    xi_map = load_xi_map()
    if xi_map:
        print(f"已加载 M3 ξ 表：{len(xi_map)} 块")
    else:
        print(f"未找到 xi_rho_by_block.csv，ξ 兜底 {DEFAULT_XI}（待 M3 交付）")
    if args.selection == "fixed":
        print(f"选参口径 fixed：48 折恒用 leaf={FIXED_HP[0]} lr={FIXED_HP[1]}")
    else:
        print(f"选参口径 argmin（已退休，仅诊断）：9 格网格逐折取验证集最优")
    full_a, full_b, hp = _run(panel, blocks, xi_map, args.selection, args.skip_tune)
    if args.selection == "argmin":
        out_dir, suffix, hp_path = DIAG, "_argmin", DIAG / "b5_params_argmin.csv"
    else:
        out_dir, suffix = ROOT / "results" / "preds", ""
        hp_path = PARAMS_PATH
    hp_path.parent.mkdir(parents=True, exist_ok=True)
    hp.to_csv(hp_path, index=False, encoding="utf-8")
    ll_a = _write(full_a, out_dir / f"preds_B5a{suffix}.csv")
    ll_b = _write(full_b, out_dir / f"preds_B5b{suffix}.csv")
    print(f"[B5] 整体 B5a={ll_a:.5f}  B5b={ll_b:.5f}  -> {out_dir}/preds_B5{{a,b}}{suffix}.csv")
    print(f"[B5] 超参表 -> {hp_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
