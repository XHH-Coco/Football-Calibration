"""M4 · T4.3 B2 有序 logit（比例优势模型）+ multinomial 稳健性。

内部标签必须 客=0 / 平=1 / 主=2（categories=["A","D","H"]），否则系数符号全反；
落盘前按内部列序重排成 p_home,p_draw,p_away（data_interface.md §1.1 落盘断言）。
特征（M4 卡 T4.3）：Elo 差、主队 Elo、客队 Elo、近 5 场积分差、休息天数差。
验收预估 log loss 0.99–1.02；multinomial 与之差 < 0.01。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from statsmodels.miscmodels.ordinal_model import OrderedModel

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.features import FEATURE_COLS, fit_features, transform_features  # noqa: E402
from src.models._common import load_panel, run_blocks  # noqa: E402

B2_COLS = ["elo_diff", "h_elo", "a_elo"]
CATEGORIES = ["A", "D", "H"]          # 内部有序标签：客=0 / 平=1 / 主=2


def _b2_frame(x: pd.DataFrame) -> pd.DataFrame:
    out = x[B2_COLS].copy()
    out["pts_diff"] = x["h_pts5"] - x["a_pts5"]
    out["rest_diff"] = x["h_rest"] - x["a_rest"]
    return out


def fit(train_df: pd.DataFrame, sample_weight=None):
    """train 内拟合 OrderedModel；另备一份 multinomial 作稳健性对照。"""
    x_train, builder = fit_features(train_df)
    xf = _b2_frame(x_train)
    endog = (train_df["y"].map({0: "H", 1: "D", 2: "A"})
             .astype(pd.CategoricalDtype(categories=CATEGORIES, ordered=True)))
    data = xf.copy()
    data["ycat"] = endog
    formula = "ycat ~ " + " + ".join(xf.columns)
    res = (OrderedModel.from_formula(formula, data=data, distr="logit")
           .fit(method="lbfgs", maxiter=1000, disp=False))
    multi = LogisticRegression(multi_class="multinomial", max_iter=2000)
    multi.fit(xf.to_numpy(), train_df["y"].to_numpy())
    return {"res": res, "multi": multi, "builder": builder}


def predict_proba(test_df: pd.DataFrame, state, x_test: pd.DataFrame | None = None) -> np.ndarray:
    # x_test 允许外部传入：transform_features 会推进 builder 状态，重复调用会污染特征。
    x_test = (transform_features(test_df, state["builder"])
              if x_test is None else x_test)
    xf = _b2_frame(x_test)
    pr = state["res"].predict(exog=xf)          # DataFrame，列序 = categories 顺序
    cols = pr.columns.tolist()
    order = [cols.index(k) for k in CATEGORIES] if set(cols) == set(CATEGORIES) \
        else [cols.index(k) for k in range(3)]
    internal = [CATEGORIES[i] for i in order]
    p_ord = pr.to_numpy()[:, order]             # 内部序 = [A, D, H]
    order_hda = [internal.index(k) for k in ["H", "D", "A"]]
    p = p_ord[:, order_hda]
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-9)

    p_multi = state["multi"].predict_proba(xf.to_numpy())
    internal_m = list(state["multi"].classes_)
    order_m = [internal_m.index(k) for k in [0, 1, 2]]
    p_multi = p_multi[:, order_m]
    from src.models._common import log_loss
    y = test_df["y"].to_numpy()
    diff = log_loss(y, p) - log_loss(y, p_multi)
    print(f"      [B2] {test_df['league'].iloc[0]}|{test_df['season'].iloc[0]} "
          f"ordinal={log_loss(y, p):.5f} multinomial={log_loss(y, p_multi):.5f} "
          f"diff={diff:+.5f}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.3 B2 有序 logit")
    ap.add_argument("--out", default=str(ROOT / "results" / "preds" / "preds_B2.csv"))
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    panel = load_panel()
    summary = run_blocks("B2", fit, predict_proba, args.out,
                         panel=panel, log_path=args.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
