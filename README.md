# Does Short Interest Predict Short-Horizon Returns? Evidence from S&P 500 Stocks

Group project for **BMF5324 AI and Statistics for Financial Decision-Making** (NUS), group **S02-10**:
Lo Hao Yu, Michael Steven, Vini Shrivastava, Zhang Licheng.

FINRA publishes every stock's short interest twice a month, free to all investors. We ask whether an S&P 500
manager can use that release to predict returns over the next five trading days, and in which direction:
is a heavily shorted stock a warning (informed short sellers) or fuel for a squeeze (covering pressure)?

## Findings

- **H1 (covering pressure) is not supported; the sign is the opposite.** One standard deviation more short
  interest (% of float) predicts a **6.2 bps lower** five-day market-adjusted return (t = −2.89). The 95%
  confidence interval, −10.4 to −2.0 bps, rules out any squeeze effect.
- From one release to the next the shortfall is **about 11 bps** (t = −3.34), with no reversal afterwards.
- **H2 (a stronger effect for firms with fewer analysts) is not supported as stated**: the short interest ×
  analyst coverage interaction is +1.75 (t = 1.22). The negative effect is concentrated in the index's smaller
  members (short interest × size +5.95, t = 2.94).
- The effect is small, not significant when stocks are weighted by market value, and weaker since 2021, so it
  works as a screen on trades already planned, not as a stand-alone strategy.

## Data and method

- S&P 500 members on each of 240 FINRA release dates, September 2016 – September 2026 (point-in-time
  membership, so firms that left the index stay in for the dates they belonged to it): 103,920 stock-release
  observations, about 433 stocks per release.
- Returns run from the close of each publication day over the next five trading days, minus the S&P 500.
- Fama-MacBeth cross-sectional regressions with the seven firm controls of Boehmer et al. (2021) and
  Newey-West t-statistics (4 lags), plus robustness checks on weighting, horizon, sample period and
  standard-error method.

## Repository

| Path | Contents |
|---|---|
| `docs/memo.pdf` | The strategy memo, with its references and AI Collaboration Appendix |
| `docs/poster.pdf` | The poster |
| `replication/replication.ipynb` | Replication notebook: runs the whole pipeline and checks every figure in the memo against the computed value |
| `replication/replication.pdf` | The executed notebook, with all its outputs |
| `replication/*.py` | Pipeline: FINRA calendar, LSEG download and panel build, cleaning, Fama-MacBeth regressions |
| `replication/regression_results.md`, `regression_coefs.csv` | All regression tables and coefficients |
| `replication/F-F_Research_Data_Factors_daily.csv` | Daily Fama-French three factors from the [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) (CRSP 202608 vintage) |

## Reproducing the results

The LSEG data are **not included**: LSEG's licence does not allow redistributing them. With LSEG Workspace
access you can rebuild them:

1. `cd replication`, then `python finra_dates.py` writes `finra_dates.csv` (the FINRA release calendar).
2. In LSEG Workspace CodeBook, upload `lseg_pull.py`, `finra_dates.csv` and
   `F-F_Research_Data_Factors_daily.csv` to a new folder and run `%run lseg_pull.py` (about 2–4 hours; it
   resumes after any stop).
3. Download the `lseg_output_*.csv` files (and `lseg_output_daily.csv.gz`) into `replication/`.
4. `pip install -r requirements.txt` (tested on Python 3.14.7), open `replication.ipynb` and choose *Run All*
   (about two minutes). Its last cell checks 186 figures against the memo.

Our pull was made on 21 October 2026; a later pull can differ slightly where LSEG revises its history.

## Use of AI

The analysis code, notebook and documents were developed with the help of Claude (Anthropic), used through
Claude Code. The AI Collaboration Appendix at the end of the memo documents how.

## Licence

- **Code** (the Python scripts, the notebook and `requirements.txt`): [MIT](LICENSE).
- **Memo and poster** (`docs/`): [CC BY 4.0](docs/LICENSE.md).
- **Third-party data**: `F-F_Research_Data_Factors_daily.csv` comes from the Kenneth R. French Data Library and
  stays under its own terms; it is not covered by either licence above. LSEG data are not included.
