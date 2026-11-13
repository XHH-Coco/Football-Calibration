"""M4 · T4.5 / T4.6 B5a / B5b —— sklearn 内置 HGB（D1 决策，零新增依赖）。

受控比较的锁（data_interface.md §2「对照一致性」）：
  - B4↔B5a 锁**信息 + 权重**：B5a 只用白名单（双方滚动进球/失球、Elo 差），
    sample_weight = exp(−ξ̂·Δ天)，ξ̂ 取该折 B4 的估计（M3 交付前兜底 0.0019），
    Δ天 = train 末日 − 该场日期；
  - B5a↔B5b 锁**权重 + 超参**：同折同权重（np.array_equal 断言）、同超参
    （超参在 B5b 的内层验证集上选，两臂共用），只换信息；
  - 内层验证 = train 的最后一个赛季（倒数第二个赛季作验证，见 M2 卡 T2.3），
    调参只看 train 内部，绝不看目标赛季。
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
DEFAULT_PARAMS = {"max_leaf_nodes": 15, "learning_rate": 0.05}
HGB_KW = dict(max_iter=1000, early_stopping=True, validation_fraction=0.1,
              n_iter_no_change=20, random_state=0)
TUNING_PATH = ROOT / "results" / "logs" / "b5_tuning.csv"


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
         skip_tune: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    tuning = pd.read_csv(TUNING_PATH) if skip_tune and TUNING_PATH.exists() else None
    if skip_tune and tuning is None:
        raise SystemExit("--skip-tune 但没有 results/logs/b5_tuning.csv")
    parts_a: list[pd.DataFrame] = []
    parts_b: list[pd.DataFrame] = []
    tune_rows: list[dict] = []

    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(panel, b)
        xi = xi_map.get(b["block_id"], DEFAULT_XI)
        x_train, builder = fit_features(train)
        w = _weights(train, xi)

        if skip_tune:
            row = tuning[tuning["block_id"] == b["block_id"]].iloc[0]
            leaf, lr = int(row["max_leaf_nodes"]), float(row["learning_rate"])
        else:
            leaf, lr, val_ll = _tune_block(x_train, train, w)
            tune_rows.append({"block_id": b["block_id"],
                              "max_leaf_nodes": leaf, "learning_rate": lr,
                              "val_logloss": val_ll})

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

    if tune_rows:
        pd.DataFrame(tune_rows).to_csv(TUNING_PATH, index=False, encoding="utf-8")
    return pd.concat(parts_a, ignore_index=True), pd.concat(parts_b, ignore_index=True)


def _write(full: pd.DataFrame, out: Path) -> float:
    assert len(full) == 16_733 and full["match_id"].is_unique
    out.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(out, index=False, encoding="utf-8")
    return log_loss(full["y"].to_numpy(),
                    full[["p_home", "p_draw", "p_away"]].to_numpy())


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.5-T4.6 B5a/B5b HGB")
    ap.add_argument("--skip-tune", action="store_true",
                    help="复用 results/logs/b5_tuning.csv，不再跑 48×9 网格")
    args = ap.parse_args()
    panel = load_panel()
    blocks = load_blocks()
    xi_map = load_xi_map()
    if xi_map:
        print(f"已加载 M3 ξ 表：{len(xi_map)} 块")
    else:
        print(f"未找到 xi_rho_by_block.csv，ξ 兜底 {DEFAULT_XI}（待 M3 交付）")
    full_a, full_b = _run(panel, blocks, xi_map, args.skip_tune)
    ll_a = _write(full_a, ROOT / "results" / "preds" / "preds_B5a.csv")
    ll_b = _write(full_b, ROOT / "results" / "preds" / "preds_B5b.csv")
    print(f"[B5] 整体 B5a={ll_a:.5f}  B5b={ll_b:.5f}  已写入 preds_B5a/B5b.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
