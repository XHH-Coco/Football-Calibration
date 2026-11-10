"""报告 §4.2 / 附录 A 的正文数字必须与成品表逐项一致。

M5 统稿时如果改了表而没改文（或反过来），这里会先亮红灯。报告文件不在时 skip。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.a1_gamma import LEAGUES  # noqa: E402
from src.models.tune_b4 import XI_GRID  # noqa: E402

REPORT = ROOT / "products" / "report"
TABLES = ROOT / "products" / "tables"


def _md_table(text: str, first_cell: str) -> list[list[str]]:
    """抓出表头之后、首个单元格等于 ``first_cell`` 的那张 markdown 表。"""
    rows: list[list[str]] = []
    started = False
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if started and rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not started:
            started = cells[0] == first_cell
            if not started:
                continue
        if set(cells[0]) <= set("-: "):
            continue
        rows.append(cells)
    return rows


def _num(s: str) -> float:
    return float(s.replace(",", "").replace("+", "").replace("−", "-"))


def _flat(s: str) -> str:
    """去掉空白、加粗和两种负号，用于正文子串比对。"""
    return re.sub(r"[\s*]", "", s).replace("−", "-")


def _table(name: str) -> pd.DataFrame:
    p = TABLES / f"{name}.csv"
    if not p.exists():
        pytest.skip(f"{name}.csv 未生成")
    return pd.read_csv(p)


def test_section_4_2_league_table_matches_csv():
    p = REPORT / "section_4_2_model.md"
    if not p.exists():
        pytest.skip("§4.2 初稿不存在")
    rows = _md_table(p.read_text(encoding="utf-8"), "League")
    assert rows and rows[0][0] == "League"
    body = rows[1:]
    t = _table("t4_2_model_fit").set_index("league")
    assert [r[0] for r in body] == ["E0", "SP1", "I1", "D1", "F1", "N1", "**All**"]
    for r in body:
        cells = [c.strip("*") for c in r]
        lg = cells[0]
        row = t.loc["ALL" if lg == "All" else lg]
        assert int(cells[1]) == row["n_folds"]
        assert int(cells[2].replace(",", "")) == row["n_matches"]
        assert _num(cells[3]) == pytest.approx(round(row["logloss_b3"], 4), abs=5e-5)
        assert _num(cells[4]) == pytest.approx(round(row["logloss_b4"], 4), abs=5e-5)
        assert _num(cells[5]) == pytest.approx(round(row["dll"], 4), abs=5e-5)
        assert cells[6] == f"{int(row['n_b4_better'])}/{int(row['n_folds'])}"


def test_section_4_2_hyperparameter_table_matches_csv():
    p = REPORT / "section_4_2_model.md"
    if not p.exists():
        pytest.skip("§4.2 初稿不存在")
    rows = _md_table(p.read_text(encoding="utf-8"), "ξ (day⁻¹)")
    assert rows and rows[0][0] == "ξ (day⁻¹)"
    t = _table("t4_2_hyperparameters")
    xi = t.loc[(t["parameter"] == "xi") & (t["kind"] == "grid")].set_index("label")
    rho = t.loc[(t["parameter"] == "rho") & (t["kind"] == "grid")].set_index("label")
    xi_mid = int(t.loc[(t["parameter"] == "xi") & (t["kind"] == "interior_4_mid"),
                       "n_folds"].iloc[0])
    rho_end = int(t.loc[(t["parameter"] == "rho") & (t["kind"] == "both_ends"),
                        "n_folds"].iloc[0])
    for r in rows[1:]:
        if r[0].startswith("**"):
            assert r[2].strip("*").startswith(f"{xi_mid}/48")
            assert r[5].strip("*").startswith(f"{rho_end}/48")
            continue
        assert int(r[2]) == xi.loc[r[0], "n_folds"]
        if r[3]:
            assert int(r[5]) == rho.loc[r[3], "n_folds"]


def test_section_4_2_prose_matches_tables():
    p = REPORT / "section_4_2_model.md"
    if not p.exists():
        pytest.skip("§4.2 初稿不存在")
    text = p.read_text(encoding="utf-8")
    fit = _table("t4_2_model_fit").set_index("league")
    folds = _table("t4_2_paired_folds")
    summ = _table("t4_2_paired_summary").iloc[0]
    a = fit.loc["ALL"]
    expect = [
        f"{a['logloss_b3']:.4f}", f"{a['logloss_b4']:.4f}", f"{a['dll']:.4f}",
        f"{a['dll_fold_mean']:.4f}", f"{a['dll_fold_sd']:.4f}",
        f"{int(a['n_b4_better'])}/48", f"{int(a['b3_iter_max'])}",
        f"{a['b4_iter_median']:.0f}", f"{int(a['b4_iter_max'])}",
        f"{a['max_grad_norm']:.2f}",
        f"{int(folds['n_candidates_converged'].min())}",
        f"{folds['xi_half_life_years'].median():.2f}",
        f"{folds['xi_half_life_years'].min():.2f}",
        f"{folds['xi_half_life_years'].max():.2f}",
        f"{int(summ['n_sig_vs_neighbour'])} of 48",
        f"{summ['median_abs_dll_vs_neighbour']:.4f}",
        f"{summ['median_se_vs_neighbour']:.4f}",
        f"{summ['median_abs_t_vs_neighbour']:.2f}",
        f"{summ['max_abs_t_vs_best_other']:.2f}",
    ]
    flat = _flat(text)
    missing = [s for s in expect if _flat(s) not in flat]
    assert not missing, f"正文缺少与表一致的数字：{missing}"
    sig = folds.loc[folds["xi_neighbour_significant"]]
    for _, r in sig.iterrows():
        assert _flat(f"t = {abs(r['t_vs_neighbour']):.2f}") in flat, r["block_id"]


def test_appendix_A_numbers_match_csv():
    p = REPORT / "appendix_A.md"
    if not p.exists():
        pytest.skip("附录 A 初稿不存在")
    text = p.read_text(encoding="utf-8")
    tr = _table("tA1_gamma_trend").set_index("scope")
    win = _table("tA1_empty_window")
    ext = _table("tA1_extrapolation").set_index("league")
    inf = _table("tA1_trend_se_inflation")
    pooled = tr.loc["pooled"]
    expect = [
        f"{pooled['slope_per_decade']:.3f}",
        f"{pooled['first']:.3f}", f"{pooled['last']:.3f}",
        f"{pooled['home_boost_first_pct'] * 100:.1f}",
        f"{pooled['home_boost_last_pct'] * 100:.1f}",
        f"{int(pooled['n_matches_first']):,}",
        f"{int(pooled['n_matches_last']):,}",
        f"{pooled['gamma_se_first']:.3f}",
        f"{pooled['gamma_se_last']:.4f}",
    ]
    for scope in tr.index:
        expect.append(f"{tr.loc[scope, 'hi95']:.4f}")
    for _, r in win.loc[win["scope"] == "contrast"].iterrows():
        expect.append(f"{r['diff']:.3f}")
        expect.append(f"{r['z']:.2f}")
    expect.append(f"{ext.loc['ALL', 'dll']:.4f}")
    for _, r in inf.iterrows():
        if r["rho"] in (0.5, 0.9):
            expect.append(f"{r['inflation_ratio']:.1f} times")
    worst = inf.loc[inf["rho"] == 0.9, "inflation_ratio"].iloc[0]
    expect.append(f"{abs(pooled['slope_per_year']) / (pooled['se'] * worst):.1f} standard errors")
    flat = _flat(text)
    missing = [s for s in expect if _flat(s) not in flat]
    assert not missing, f"附录缺少与表一致的数字：{missing}"


def test_appendix_A_direction_claims_match_csv():
    """方向性措辞（几家为正、末季回升、改善几家）必须与表一致，不能凭印象写。"""
    p = REPORT / "appendix_A.md"
    if not p.exists():
        pytest.skip("附录 A 初稿不存在")
    text = _flat(p.read_text(encoding="utf-8"))
    ext = _table("tA1_extrapolation").set_index("league")
    lg = ext.loc[ext["scope"] == "league"]
    up = [x for x in LEAGUES if lg.loc[x, "dgamma"] > 0]
    down = [x for x in LEAGUES if lg.loc[x, "dgamma"] < 0]
    assert (len(up), len(down)) == (3, 3)
    assert _flat("positive in three leagues (" + ", ".join(up) + ")") in text
    assert _flat("negative in three (" + ", ".join(down) + ")") in text
    n_better = int((lg["dll"] > 0).sum())
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    assert _flat(f"improves log loss in {words[n_better]}") in text
    for col, fmt in (("p_home_stale", "{:.1%}"), ("home_share_actual", "{:.1%}"),
                     ("p_home_oracle", "{:.1%}")):
        assert _flat(fmt.format(ext.loc["ALL", col])) in text, col

    g = pd.read_csv(ROOT / "results" / "logs" / "gamma_by_season.csv").set_index("season")
    for season in ("2020/21", "2022/23", "2024/25"):
        assert _flat(f"{g.loc[season, 'gamma_pooled']:.3f}") in text, season
    rise = [c[len("gamma_"):] for c in g.columns if c.startswith("gamma_")
            and c != "gamma_pooled" and g[c].iloc[-1] > g[c].iloc[-2]]
    assert sorted(rise) == ["F1", "N1"], rise
    assert _flat("two leagues (" + ", ".join(rise) + ")") in text


def test_section_4_2_fold_claims_match_xi_rho_log():
    """验收项 11：正文里点名的折与 (ξ, ρ) 必须能在 xi_rho_by_block.csv 找到原值。"""
    p = REPORT / "section_4_2_model.md"
    if not p.exists():
        pytest.skip("§4.2 初稿不存在")
    flat = _flat(p.read_text(encoding="utf-8"))
    folds = _table("t4_2_paired_folds")
    log = pd.read_csv(ROOT / "results" / "logs" / "xi_rho_by_block.csv").set_index("block_id")
    idx = {v: i for i, v in enumerate(XI_GRID)}
    pos = folds["xi"].map(idx)
    nbr = folds["xi_neighbour"].map(idx)
    assert nbr.notna().all(), "每折都应找到同 ρ 的最近 ξ 对手"
    adjacent = (nbr - pos).abs() == 1
    assert int(adjacent.sum()) == 47
    assert _flat(f"{int(adjacent.sum())} of the 48") in flat
    odd = folds.loc[~adjacent]
    assert len(odd) == 1
    row = odd.iloc[0]
    assert row["block_id"] == "F1|2021/22"
    assert _flat(f"ξ = {row['xi_neighbour']:.4f}") in flat
    for col in ("xi", "rho"):
        assert row[col] == log.loc[row["block_id"], col]
    sig = folds.loc[folds["xi_neighbour_significant"]]
    assert (sig["xi"] < sig["xi_neighbour"]).all(), "显著折应全部选更长的记忆（更小的 ξ）"
    assert _flat("prefer longer memory") in flat


def _notebook_text() -> str:
    import json

    p = ROOT / "analysis" / "a1_home_advantage.ipynb"
    if not p.exists():
        pytest.skip("a1 notebook 不存在")
    nb = json.loads(p.read_text(encoding="utf-8"))
    chunks = []
    for c in nb["cells"]:
        for o in c.get("outputs", []):
            chunks.append("".join(o.get("text", [])))
    return "\n".join(chunks)


def test_notebook_outputs_are_not_stale():
    """notebook 的内嵌输出必须与成品表同值；否则重跑 notebook。"""
    txt = _notebook_text()
    if not txt.strip():
        pytest.skip("notebook 没有文本输出")
    tr = _table("tA1_gamma_trend").set_index("scope")
    win = _table("tA1_empty_window")
    ext = _table("tA1_extrapolation").set_index("league")
    expect = [f"{tr.loc[sc, 'slope_per_year']:.5f}" for sc in tr.index]
    expect += [f"{tr.loc[sc, 'slope_per_decade']:.3f}" for sc in ("pooled",)]
    for _, r in win.loc[win["scope"] == "pooled"].iterrows():
        expect += [f"{r['gamma']:.4f}", f"{r['se']:.4f}"]
    for _, r in win.loc[win["scope"] == "contrast"].iterrows():
        expect += [f"{r['diff']:.4f}", f"{r['se']:.4f}"]
    expect += [f"{ext.loc[lg, 'gamma_stale']:.4f}" for lg in ext.index if ext.loc[lg, "scope"] == "league"]
    expect += [f"{ext.loc[lg, 'dll']:.4f}" for lg in ext.index]
    missing = [s for s in expect if s not in txt]
    assert not missing, f"notebook 输出与表不一致（重跑 notebook）：{missing}"
