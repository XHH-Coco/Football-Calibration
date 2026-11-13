"""M4 · Elo 引擎（B1 / B2 / B5 特征共用，全组唯一实现，禁止各写一份）。

规格（M4 分工卡 T4.2，Hvattum & Arntzen 2010 简化版）：
  初始 1500；K=20；主场加成 75（卡给 60~100）；赛季间向均值回归 1/3；
  每队主、客各存一分（ratings[team] = [home, away]）；
  严格按日期逐场更新——逐场顺序是防泄漏红线（M4 卡 §7 坑 2）。
"""

from __future__ import annotations


class EloLeague:
    """单联赛的逐场 Elo 状态。"""

    K = 20.0
    HOME_ADV = 75.0
    MEAN = 1500.0
    REGRESS = 1.0 / 3.0

    def __init__(self) -> None:
        self.ratings: dict[str, list[float]] = {}
        self.last_season: str | None = None

    def _touch(self, team: str) -> None:
        if team not in self.ratings:
            self.ratings[team] = [self.MEAN, self.MEAN]

    def maybe_regress(self, season: str) -> None:
        """赛季边界：该联赛所有已见队伍向 1500 回归 1/3。"""
        if self.last_season is not None and season != self.last_season:
            for r in self.ratings.values():
                r[0] += (self.MEAN - r[0]) * self.REGRESS
                r[1] += (self.MEAN - r[1]) * self.REGRESS
        self.last_season = season

    def blended(self, team: str) -> float:
        self._touch(team)
        h, a = self.ratings[team]
        return (h + a) / 2.0

    def home_rating(self, team: str) -> float:
        self._touch(team)
        return self.ratings[team][0]

    def away_rating(self, team: str) -> float:
        self._touch(team)
        return self.ratings[team][1]

    def update(self, home: str, away: str, y: int) -> None:
        """y: 0=主胜 / 1=平 / 2=客胜。主队动 home 分，客队动 away 分。"""
        self._touch(home)
        self._touch(away)
        s_home = 1.0 if y == 0 else (0.5 if y == 1 else 0.0)
        h_eff = self.ratings[home][0] + self.HOME_ADV
        a_eff = self.ratings[away][1]
        e_home = 1.0 / (1.0 + 10.0 ** ((a_eff - h_eff) / 400.0))
        self.ratings[home][0] += self.K * (s_home - e_home)
        self.ratings[away][1] += self.K * ((1.0 - s_home) - (1.0 - e_home))
