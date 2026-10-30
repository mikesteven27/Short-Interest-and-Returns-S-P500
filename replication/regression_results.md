# Fama-MacBeth results

Panel: panel_clean.csv (119,879 rows, 240 FINRA dates, 688 stocks). Dependent variable unless noted: FwdRet5_MktAdj (the proposal's main specification).

### Table 1. H1 and H2: next 5-trading-day market-adjusted return (bps per 1 SD), Fama-MacBeth

| | (1) SI only | (2) H1 | (3) H2: SI × coverage | (4) H2 robustness: SI × size |
|---|---|---|---|---|
| SI / float | -3.99 (-1.38) | -6.22 (-2.89)*** | -5.04 (-2.36)** | -0.89 (-0.34) |
| log market cap |  | 3.48 (1.38) | 2.88 (1.15) | 6.75 (2.20)** |
| book-to-market |  | -2.39 (-0.70) | -2.34 (-0.69) | -2.08 (-0.62) |
| return, past month |  | -3.30 (-0.80) | -3.24 (-0.78) | -3.91 (-0.97) |
| return, months -6 to -2 |  | -1.88 (-0.42) | -1.71 (-0.39) | -2.43 (-0.54) |
| turnover |  | 4.13 (1.20) | 3.24 (0.95) | 4.11 (1.18) |
| idiosyncratic volatility |  | 1.87 (0.63) | 1.54 (0.53) | 1.75 (0.59) |
| % zero-return days |  | 0.27 (0.27) | 0.40 (0.39) | 0.40 (0.39) |
| analyst coverage, ln(1+N) |  |  | 2.31 (1.01) |  |
| SI × analyst coverage |  |  | 1.75 (1.22) |  |
| SI × size |  |  |  | 5.95 (2.94)*** |
| intercept | -7.52 (-1.28) | -7.93 (-1.34) | -7.55 (-1.29) | -5.05 (-0.89) |
| dates | 240 | 240 | 240 | 240 |
| avg. stocks per date | 461 | 433 | 429 | 433 |
| avg. adj. R² | 0.018 | 0.135 | 0.142 | 0.137 |

t-statistics (Newey-West, 4 lags) in brackets; * 10%, ** 5%, *** 1%. H1 predicts a positive SI coefficient; H2 predicts a negative SI × coverage (and SI × size) coefficient. The 5-day return runs from the close of the release day to the close 5 trading days later.

### Table 2. H2 check: model (2) within analyst-coverage terciles

| | (2) low coverage (bottom third) | (2) high coverage (top third) |
|---|---|---|
| SI / float | -8.83 (-2.80)*** | -3.71 (-0.99) |
| log market cap | 0.38 (0.16) | 6.43 (1.63) |
| book-to-market | -1.39 (-0.42) | -3.62 (-0.87) |
| return, past month | -3.29 (-0.81) | -3.55 (-0.79) |
| return, months -6 to -2 | -0.96 (-0.21) | -1.46 (-0.26) |
| turnover | 2.12 (0.52) | 4.22 (0.91) |
| idiosyncratic volatility | 1.62 (0.46) | 6.06 (1.50) |
| % zero-return days | 1.29 (0.71) | 0.96 (0.49) |
| intercept | -11.51 (-1.58) | -3.11 (-0.62) |
| dates | 240 | 240 |
| avg. stocks per date | 144 | 140 |
| avg. adj. R² | 0.135 | 0.152 |

The proposal says H2 fails if the SI coefficient is not positive among low-coverage firms. Terciles are formed within each date from ln(1 + analysts).

### Table 3. Robustness (value-weighted = WLS by market cap, as the proposal specifies)

| | (2) baseline | (2) value-weighted | (3) value-weighted | (2) raw panel (no cleaning) | (2) keep BE ≤ 0 (dummy) | (2) SI / shares out | (2) skip a day |
|---|---|---|---|---|---|---|---|
| SI / float | -6.22 (-2.89)*** | -4.80 (-1.35) | -3.27 (-0.95) | -11.02 (-1.72)* | -5.94 (-2.82)*** |  | -4.32 (-1.70)* |
| log market cap | 3.48 (1.38) | 4.80 (1.09) | 4.84 (1.24) | 4.11 (1.56) | 3.12 (1.27) | 3.39 (1.34) | 2.39 (0.83) |
| book-to-market | -2.39 (-0.70) | -3.82 (-0.81) | -4.00 (-0.87) | -7.36 (-1.44) |  | -2.40 (-0.71) | -2.57 (-0.73) |
| return, past month | -3.30 (-0.80) | -6.83 (-1.39) | -7.38 (-1.53) | -2.62 (-0.59) | -3.04 (-0.75) | -3.34 (-0.81) | -1.04 (-0.17) |
| return, months -6 to -2 | -1.88 (-0.42) | -4.42 (-0.80) | -3.20 (-0.59) | -0.08 (-0.02) | -1.65 (-0.37) | -1.84 (-0.41) | -5.27 (-1.17) |
| turnover | 4.13 (1.20) | 9.99 (1.98)** | 9.22 (1.87)* | 20.26 (2.59)*** | 3.73 (1.05) | 4.56 (1.29) | 1.29 (0.33) |
| idiosyncratic volatility | 1.87 (0.63) | -1.12 (-0.22) | -1.60 (-0.31) | 0.81 (0.24) | 1.91 (0.66) | 1.71 (0.58) | 0.95 (0.34) |
| % zero-return days | 0.27 (0.27) | 2.84 (1.22) | 3.08 (1.34) | 0.01 (0.01) | 0.36 (0.38) | 0.27 (0.26) | 1.05 (0.97) |
| analyst coverage, ln(1+N) |  |  | 3.04 (1.19) |  |  |  |  |
| SI × analyst coverage |  |  | 3.79 (1.34) |  |  |  |  |
| book-to-market (0 if BE ≤ 0) |  |  |  |  | -2.38 (-0.69) |  |  |
| negative book equity (dummy) |  |  |  |  | 0.23 (0.04) |  |  |
| SI / shares out |  |  |  |  |  | -6.56 (-2.80)*** |  |
| intercept | -7.93 (-1.34) | -6.77 (-0.98) | -6.52 (-0.96) | -7.32 (-1.25) | -7.60 (-1.33) | -7.93 (-1.34) | -6.42 (-0.91) |
| dates | 240 | 240 | 240 | 240 | 240 | 240 | 240 |
| avg. stocks per date | 433 | 433 | 429 | 464 | 460 | 433 | 433 |
| avg. adj. R² | 0.135 | 0.227 | 0.241 | 0.127 | 0.133 | 0.135 | 0.133 |

### Table 4. Bi-weekly horizons (professor): return from one release to the next (t+1) and the one after (t+2)

| | (2) 5 days (main) | (2) 2 weeks, t+1 | (2) 2 weeks, t+2 | (3) 2 weeks, t+1 |
|---|---|---|---|---|
| SI / float | -6.22 (-2.89)*** | -10.83 (-3.34)*** | -11.09 (-3.47)*** | -9.48 (-2.96)*** |
| log market cap | 3.48 (1.38) | 4.32 (1.12) | 3.50 (0.97) | 2.20 (0.53) |
| book-to-market | -2.39 (-0.70) | -1.66 (-0.29) | -1.85 (-0.33) | -1.76 (-0.30) |
| return, past month | -3.30 (-0.80) | -7.28 (-1.27) | 0.83 (0.16) | -7.37 (-1.30) |
| return, months -6 to -2 | -1.88 (-0.42) | 3.51 (0.66) | 2.54 (0.50) | 3.76 (0.71) |
| turnover | 4.13 (1.20) | 10.69 (2.09)** | 11.03 (2.29)** | 9.30 (1.85)* |
| idiosyncratic volatility | 1.87 (0.63) | 0.76 (0.17) | 1.11 (0.24) | 0.29 (0.06) |
| % zero-return days | 0.27 (0.27) | -0.25 (-0.16) | -1.41 (-0.86) | 0.09 (0.06) |
| analyst coverage, ln(1+N) |  |  |  | 5.35 (1.44) |
| SI × analyst coverage |  |  |  | 1.22 (0.62) |
| intercept | -7.93 (-1.34) | -11.80 (-1.48) | -11.64 (-1.45) | -11.45 (-1.44) |
| dates | 240 | 239 | 238 | 239 |
| avg. stocks per date | 433 | 433 | 433 | 429 |
| avg. adj. R² | 0.135 | 0.132 | 0.132 | 0.139 |

The bi-weekly return runs from the close of release t to the close of release t+1, so consecutive returns tile time exactly like FINRA's twice-monthly releases.

### Table 5. Short covering (professor): the 2-week % change in short interest

| | 5 days: + ΔSI | 5 days: SI × ΔSI | 2 weeks: + ΔSI | 2 weeks: SI × ΔSI |
|---|---|---|---|---|
| SI / float | -6.30 (-2.94)*** | -6.77 (-3.12)*** | -11.17 (-3.43)*** | -11.30 (-3.36)*** |
| ΔSI (2-week % change) | -2.60 (-1.78)* | -2.64 (-1.75)* | -3.10 (-1.53) | -3.29 (-1.58) |
| log market cap | 3.42 (1.34) | 3.16 (1.25) | 4.02 (1.03) | 3.82 (0.98) |
| book-to-market | -2.38 (-0.71) | -2.38 (-0.70) | -2.00 (-0.35) | -2.07 (-0.36) |
| return, past month | -2.93 (-0.71) | -2.62 (-0.64) | -6.52 (-1.14) | -6.17 (-1.08) |
| return, months -6 to -2 | -2.20 (-0.49) | -2.13 (-0.48) | 3.24 (0.62) | 3.04 (0.58) |
| turnover | 4.25 (1.22) | 3.82 (1.08) | 10.64 (2.12)** | 10.48 (2.08)** |
| idiosyncratic volatility | 1.65 (0.55) | 1.83 (0.60) | 0.52 (0.11) | 0.59 (0.13) |
| % zero-return days | 0.41 (0.40) | 0.37 (0.36) | -0.04 (-0.02) | -0.16 (-0.10) |
| SI × ΔSI |  | 2.29 (1.37) |  | 2.06 (1.02) |
| intercept | -7.88 (-1.33) | -8.09 (-1.37) | -11.67 (-1.46) | -11.79 (-1.48) |
| dates | 239 | 239 | 238 | 238 |
| avg. stocks per date | 433 | 433 | 432 | 432 |
| avg. adj. R² | 0.136 | 0.137 | 0.133 | 0.133 |

A falling SI (negative ΔSI) is evidence of short covering, which the professor expected to push prices up, i.e. a negative ΔSI coefficient.

### Table 6. Subperiods (delisted-firm SI gap: 9-17% of rows a year in 2016-2020, 1-8% in 2021-2026)

| | (2) 2016-2020 | (3) 2016-2020 | (2) 2021-2026 | (3) 2021-2026 |
|---|---|---|---|---|
| SI / float | -10.64 (-3.05)*** | -9.43 (-2.90)*** | -2.89 (-1.16) | -1.75 (-0.66) |
| log market cap | 1.78 (0.43) | 1.94 (0.53) | 4.76 (1.54) | 3.59 (1.07) |
| book-to-market | -13.34 (-2.80)*** | -13.13 (-2.74)*** | 5.84 (1.42) | 5.77 (1.40) |
| return, past month | -5.73 (-0.90) | -5.85 (-0.89) | -1.47 (-0.28) | -1.28 (-0.25) |
| return, months -6 to -2 | 2.98 (0.55) | 2.82 (0.53) | -5.53 (-0.83) | -5.12 (-0.79) |
| turnover | 5.13 (1.19) | 4.13 (0.99) | 3.38 (0.66) | 2.57 (0.51) |
| idiosyncratic volatility | -1.63 (-0.50) | -1.91 (-0.59) | 4.50 (1.01) | 4.13 (0.94) |
| % zero-return days | -0.46 (-0.27) | -0.23 (-0.13) | 0.82 (0.67) | 0.87 (0.70) |
| analyst coverage, ln(1+N) |  | 1.25 (0.36) |  | 3.10 (1.03) |
| SI × analyst coverage |  | 3.24 (1.54) |  | 0.63 (0.33) |
| intercept | -12.73 (-1.82)* | -12.19 (-1.77)* | -4.32 (-0.49) | -4.07 (-0.46) |
| dates | 103 | 103 | 137 | 137 |
| avg. stocks per date | 415 | 411 | 446 | 443 |
| avg. adj. R² | 0.119 | 0.128 | 0.147 | 0.153 |

### Table 7. Delisted firms without SI vs firms in the regressions (per-date means, averaged)

| variable | in regressions | delisted, no SI | difference (t) |
|---|---|---|---|
| next 5-day adj. return (bps) | -7.5202 | -11.4809 | -3.9607 (-0.62) |
| log market cap | 24.2523 | 23.6143 | -0.6380 (-28.22)*** |
| book-to-market | 0.3684 | 0.4342 | 0.0658 (7.90)*** |
| return, past month | 0.0101 | 0.0086 | -0.0015 (-0.81) |
| return, months -6 to -2 | 0.0497 | 0.0415 | -0.0082 (-0.98) |
| turnover | 0.0085 | 0.0107 | 0.0022 (11.88)*** |
| idiosyncratic volatility | 0.0146 | 0.0160 | 0.0014 (3.54)*** |

Difference t-statistics are Newey-West over dates.

### Table 8. Controls-only model with and without the firms lacking SI

| | all firms | firms with SI only |
|---|---|---|
| log market cap | 5.42 (2.25)** | 5.45 (2.21)** |
| book-to-market | -1.50 (-0.44) | -1.95 (-0.58) |
| return, past month | -3.53 (-0.82) | -3.85 (-0.92) |
| return, months -6 to -2 | -1.81 (-0.40) | -1.75 (-0.39) |
| turnover | 1.73 (0.54) | 1.66 (0.51) |
| idiosyncratic volatility | 1.17 (0.42) | 1.30 (0.44) |
| % zero-return days | 0.07 (0.07) | 0.32 (0.31) |
| intercept | -8.57 (-1.44) | -7.93 (-1.34) |
| dates | 240 | 240 |
| avg. stocks per date | 470 | 433 |
| avg. adj. R² | 0.128 | 0.130 |

If the coefficients barely move, leaving out the delisted firms does not distort the cross-section.
