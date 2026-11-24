# References

Entries are cited in the text by author and year; the list is alphabetical by first author. Counts of matches, models and tables are not cited — every number in this report traces to a file in the repository, listed in the *Sources* line at the end of each section.

1. **Ali, M. M. (1977).** Probability and utility estimates for racetrack bettors. *Journal of Political Economy*, 85(4), 803–815. — origin of the favourite–longshot bias, the pattern H1 tests.
2. **Cain, M., Law, D., & Peel, D. (2000).** The favourite–longshot bias and market efficiency in UK football betting. *Scottish Journal of Political Economy*, 47(1), 25–36. — the same bias in football rather than racing.
3. **Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008).** Bootstrap-based improvements for inference with clustered errors. *Review of Economics and Statistics*, 90(3), 414–427. — basis for resampling the 48 league–season blocks rather than the 16,733 matches.
4. **Dixon, M. J., & Coles, S. G. (1997).** Modelling association football scores and inefficiencies in the football betting market. *Journal of the Royal Statistical Society: Series C*, 46(2), 265–280. — the specification of B4, including the low-score dependence term τ(ρ) that this report runs at ρ = 0.
5. **Efron, B. (1979).** Bootstrap methods: another look at the jackknife. *Annals of Statistics*, 7(1), 1–26. — the percentile bootstrap used for every interval in the report.
6. **Gneiting, T., & Raftery, A. E. (2007).** Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association*, 102(477), 359–378. — why log loss, Brier and the ranked probability score are the admissible metrics, and why accuracy is not.
7. **Hvattum, L. M., & Arntzen, H. (2010).** Using ELO ratings for match result prediction in association football. *International Journal of Forecasting*, 26(3), 460–470. — the rating engine behind B1 and behind the Elo columns in B2 and B5.
8. **Maher, M. J. (1982).** Modelling association football scores. *Statistica Neerlandica*, 36(3), 109–118. — the independent-Poisson score model of B3.
9. **Murphy, A. H. (1973).** A new vector partition of the probability score. *Journal of Applied Meteorology*, 12(4), 595–600. — the ranked probability score reported as a secondary metric.
10. **Pedregosa, F., et al. (2011).** Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830. — the implementation of the boosted arms B5a/B5b and of the logistic and Poisson fits.
11. **Shin, H. S. (1993).** Measuring the incidence of insider trading in a market for state-contingent claims. *The Economic Journal*, 103(420), 1141–1153. — the second of the three de-vigging methods.
12. **Štrumbelj, E. (2014).** On determining probability forecasts from betting odds. *International Journal of Forecasting*, 30(4), 934–943. — the result that motivates H1: some margin-removal methods remove the favourite–longshot bias and proportional normalisation does not.

## Data

- **football-data.co.uk (2026).** *Free football results and statistics.* https://www.football-data.co.uk — 132 league-season CSV files, seasons 2003/04–2024/25, six leagues, retrieved 26 October 2026 and committed to the repository with SHA-256 checksums (`configs/raw_manifest.csv`). No registration or API key is required, and the archive documents its own column codes on the same site.
