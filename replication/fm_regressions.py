"""Fama-MacBeth tests of H1/H2 from the one-page proposal, plus the robustness checks it promises and the
professor's suggestions, on the cleaned S&P 500 short-interest panel.

Each FINRA publication date is one cross-section (about 430-500 stocks). Every date: OLS (equal-weighted, the main
specification) of the return after the release on short interest and controls, with regressors standardized within
the date (coefficients = basis points of return per 1 standard deviation; interactions = products of the standardized
terms). Reported: the time-series mean of each coefficient and its Newey-West t-statistic (4 lags), which accounts
for time-series dependence as the proposal requires.

Main dependent variable (proposal): FwdRet5_MktAdj, the 5 trading days after the release minus the S&P 500, from the
close of the release day. FwdRet5_MktAdj_skip1 starts one trading day later (robustness).
Professor's suggestions: the bi-weekly return (release to next release, t+1 and t+2) and the 2-week % change in SI.

Run from this folder:  python fm_regressions.py      (reads panel_clean.csv and lseg_output_panel.csv)
Writes: regression_results.md (all tables) and regression_coefs.csv (every coefficient, for the memo/poster).
"""
import sys

import numpy as np
import pandas as pd

CLEAN = sys.argv[1] if len(sys.argv) > 1 else "panel_clean.csv"
RAW = sys.argv[2] if len(sys.argv) > 2 else "lseg_output_panel.csv"
Y = "FwdRet5_MktAdj"
Y2W, Y2W_T2 = "FwdRet2w_MktAdj", "FwdRet2w_t2_MktAdj"
CTRL = ["LogMV", "BM", "LagRet1m", "LagRet6m", "Turnover", "IdioVOL", "PctZero"]   # Boehmer et al. (2022) controls
NO_Z = {"NegBE"}            # dummies stay 0/1
LAGS, MIN_N = 4, 30         # Newey-West lags (about T^(1/4) for 240 dates); minimum stocks per date
SPLIT = "2021-01-01"        # subperiods: the delisted-SI gap is 9-17% of rows a year before, 1-8% after
LABEL = {"SI_float": "SI / float", "dSI_float": "ΔSI (2-week % change)", "SI_shares": "SI / shares out",
         "LogMV": "log market cap", "BM": "book-to-market", "BM_n": "book-to-market (0 if BE ≤ 0)",
         "NegBE": "negative book equity (dummy)", "LagRet1m": "return, past month", "LagRet6m": "return, months -6 to -2",
         "Turnover": "turnover", "IdioVOL": "idiosyncratic volatility", "PctZero": "% zero-return days",
         "AnalystCov": "analyst coverage, ln(1+N)", "SI_float:dSI_float": "SI × ΔSI", "SI_float:LogMV": "SI × size",
         "SI_float:AnalystCov": "SI × analyst coverage", "const": "intercept"}
H1 = ["SI_float"] + CTRL
H2 = ["SI_float", "AnalystCov", "SI_float:AnalystCov"] + CTRL
H2_SIZE = ["SI_float", "SI_float:LogMV"] + CTRL


def load(path):
    df = pd.read_csv(path, parse_dates=["Publication"])
    if "AnalystCov" not in df.columns:
        raise SystemExit(f"{path} looks saved by Excel (semicolons) or is out of date: run lseg_pull.py --build and "
                         f"clean_panel.py again, and close CSVs in Excel without saving")
    df["BM_n"] = df["BM"].where(~(df["BookEquity"] <= 0), 0.0)
    df["NegBE"] = (df["BookEquity"] <= 0).astype(float)
    df["CovRank"] = df.groupby("Publication")["AnalystCov"].rank(pct=True)   # coverage terciles within each date
    return df


def nw_tstat(b, lags=LAGS):
    """t-statistic of the mean of a coefficient series, Newey-West (Bartlett) standard error."""
    e, T = b - b.mean(), len(b)
    s = e @ e / T + 2 * sum((1 - l / (lags + 1)) * (e[l:] @ e[:-l]) / T for l in range(1, lags + 1))
    return b.mean() / np.sqrt(s / T)


def fm(df, y, terms, z=True, weight=None):
    """Fama-MacBeth: one cross-sectional regression per date, OLS or WLS with weight (a column, e.g. MktCap).
    terms may hold interactions 'a:b'."""
    base = sorted({t for term in terms for t in term.split(":")})
    d = df[["Publication", y] + base + ([weight] if weight else [])].dropna()
    rows = []
    for date, g in d.groupby("Publication"):
        if len(g) < MIN_N:
            continue
        x = g[base].astype(float)
        if z:
            zc = [c for c in base if c not in NO_Z]
            x[zc] = (x[zc] - x[zc].mean()) / x[zc].std()
        X = np.column_stack([np.ones(len(g))] + [np.prod([x[t] for t in term.split(":")], axis=0) for term in terms])
        yy = g[y].to_numpy(float) * 1e4                           # basis points
        sw = np.sqrt(g[weight].to_numpy(float)) if weight else np.ones(len(g))
        b, *_ = np.linalg.lstsq(X * sw[:, None], yy * sw, rcond=None)
        resid, dev = (yy - X @ b) * sw, (yy - np.average(yy, weights=sw ** 2)) * sw
        r2 = 1 - resid @ resid / (dev @ dev)
        k = X.shape[1] - 1
        rows.append([date, len(g), 1 - (1 - r2) * (len(g) - 1) / (len(g) - k - 1), *b])
    B = pd.DataFrame(rows, columns=["date", "n", "adjR2", "const"] + terms)
    coefs = {t: (B[t].mean(), nw_tstat(B[t].to_numpy())) for t in ["const"] + terms}
    return {"coefs": coefs, "dates": len(B), "avg_n": B["n"].mean(), "adjR2": B["adjR2"].mean(), "series": B}


def table(results, title, note=""):
    """Markdown table: rows = variables, columns = models, cells = coefficient (t)."""
    order = []
    for r in results.values():
        order += [t for t in r["coefs"] if t not in order and t != "const"]
    lines = [f"### {title}", "", "| | " + " | ".join(results) + " |", "|---" * (len(results) + 1) + "|"]
    for t in order + ["const"]:
        cells = [f"{r['coefs'][t][0]:.2f} ({r['coefs'][t][1]:.2f}){stars(r['coefs'][t][1])}" if t in r["coefs"] else ""
                 for r in results.values()]
        lines.append(f"| {LABEL.get(t, t)} | " + " | ".join(cells) + " |")
    for name, key, fmt in [("dates", "dates", "{:.0f}"), ("avg. stocks per date", "avg_n", "{:.0f}"),
                           ("avg. adj. R²", "adjR2", "{:.3f}")]:
        lines.append(f"| {name} | " + " | ".join(fmt.format(r[key]) for r in results.values()) + " |")
    return "\n".join(lines + ["", note, ""] if note else lines + [""])


def stars(t):
    return "***" if abs(t) >= 2.58 else "**" if abs(t) >= 1.96 else "*" if abs(t) >= 1.645 else ""


def _selftest():
    rng = np.random.default_rng(0)
    n, T = 300, 120
    d = pd.DataFrame({"Publication": np.repeat(pd.date_range("2020-01-01", periods=T, freq="14D"), n),
                      "x": rng.normal(size=n * T), "w": 1.0})
    d["y"] = 0.002 * d["x"] + rng.normal(0, 0.05, n * T)          # true effect 20 bps per 1 SD of x
    r = fm(d, "y", ["x"])
    assert abs(r["coefs"]["x"][0] - 20) < 3 and r["coefs"]["x"][1] > 5, r["coefs"]
    assert np.isclose(fm(d, "y", ["x"], weight="w")["coefs"]["x"][0], r["coefs"]["x"][0]), "equal weights = OLS"
    b = r["series"]["x"].to_numpy()
    assert np.isclose(nw_tstat(b, 0), b.mean() / (b.std() / np.sqrt(len(b)))), "NW with 0 lags = plain t"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):   # Windows consoles default to cp1252 (no Δ, ×); Jupyter has no reconfigure
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _selftest()
    p, raw = load(CLEAN), load(RAW)
    out, coef_rows = [], []

    def keep(name, res):
        for t, (c, tt) in res["coefs"].items():
            coef_rows.append({"model": name, "term": t, "coef_bps": c, "t_NW": tt, "dates": res["dates"],
                              "avg_n": res["avg_n"], "adjR2": res["adjR2"]})
        return res

    main = {
        "(1) SI only": keep("(1)", fm(p, Y, ["SI_float"])),
        "(2) H1": keep("(2)", fm(p, Y, H1)),
        "(3) H2: SI × coverage": keep("(3)", fm(p, Y, H2)),
        "(4) H2 robustness: SI × size": keep("(4)", fm(p, Y, H2_SIZE)),
    }
    out.append(table(main, "Table 1. H1 and H2: next 5-trading-day market-adjusted return (bps per 1 SD), Fama-MacBeth",
                     "t-statistics (Newey-West, 4 lags) in brackets; * 10%, ** 5%, *** 1%. H1 predicts a positive SI "
                     "coefficient; H2 predicts a negative SI × coverage (and SI × size) coefficient. The 5-day return "
                     "runs from the close of the release day to the close 5 trading days later."))

    terc = {
        "(2) low coverage (bottom third)": keep("(2) low coverage", fm(p[p["CovRank"] <= 1 / 3], Y, H1)),
        "(2) high coverage (top third)": keep("(2) high coverage", fm(p[p["CovRank"] > 2 / 3], Y, H1)),
    }
    out.append(table(terc, "Table 2. H2 check: model (2) within analyst-coverage terciles",
                     "The proposal says H2 fails if the SI coefficient is not positive among low-coverage firms. "
                     "Terciles are formed within each date from ln(1 + analysts)."))

    rob = {
        "(2) baseline": main["(2) H1"],
        "(2) value-weighted": keep("(2) value-weighted", fm(p, Y, H1, weight="MktCap")),
        "(3) value-weighted": keep("(3) value-weighted", fm(p, Y, H2, weight="MktCap")),
        "(2) raw panel (no cleaning)": keep("(2) raw panel", fm(raw, Y, H1)),
        "(2) keep BE ≤ 0 (dummy)": keep("(2) neg BE dummy", fm(p, Y, ["SI_float"] + [c if c != "BM" else "BM_n" for c in CTRL]
                                                          + ["NegBE"])),
        "(2) SI / shares out": keep("(2) SI/shares", fm(p, Y, ["SI_shares"] + CTRL)),
        "(2) skip a day": keep("(2) skip1", fm(p, "FwdRet5_MktAdj_skip1", H1)),
    }
    out.append(table(rob, "Table 3. Robustness (value-weighted = WLS by market cap, as the proposal specifies)"))

    horizons = {
        "(2) 5 days (main)": main["(2) H1"],
        "(2) 2 weeks, t+1": keep("(2) 2w t+1", fm(p, Y2W, H1)),
        "(2) 2 weeks, t+2": keep("(2) 2w t+2", fm(p, Y2W_T2, H1)),
        "(3) 2 weeks, t+1": keep("(3) 2w t+1", fm(p, Y2W, H2)),
    }
    out.append(table(horizons, "Table 4. Bi-weekly horizons (professor): return from one release to the next (t+1) "
                               "and the one after (t+2)",
                     "The bi-weekly return runs from the close of release t to the close of release t+1, "
                     "so consecutive returns tile time exactly like FINRA's twice-monthly releases."))

    cover = {
        "5 days: + ΔSI": keep("ΔSI 5d", fm(p, Y, ["SI_float", "dSI_float"] + CTRL)),
        "5 days: SI × ΔSI": keep("SI×ΔSI 5d", fm(p, Y, ["SI_float", "dSI_float", "SI_float:dSI_float"] + CTRL)),
        "2 weeks: + ΔSI": keep("ΔSI 2w", fm(p, Y2W, ["SI_float", "dSI_float"] + CTRL)),
        "2 weeks: SI × ΔSI": keep("SI×ΔSI 2w", fm(p, Y2W, ["SI_float", "dSI_float", "SI_float:dSI_float"] + CTRL)),
    }
    out.append(table(cover, "Table 5. Short covering (professor): the 2-week % change in short interest",
                     "A falling SI (negative ΔSI) is evidence of short covering, which the professor expected to "
                     "push prices up, i.e. a negative ΔSI coefficient."))

    early, late = p[p["Publication"] < SPLIT], p[p["Publication"] >= SPLIT]
    sub = {f"{m} {tag}": keep(f"{m} {tag}", fm(d, Y, terms))
           for tag, d in [("2016-2020", early), ("2021-2026", late)] for m, terms in [("(2)", H1), ("(3)", H2)]}
    out.append(table(sub, "Table 6. Subperiods (delisted-firm SI gap: 9-17% of rows a year in 2016-2020, 1-8% in 2021-2026)"))

    # are the firms without SI (delisted, LSEG keeps no SI) different from the firms in the regressions?
    p["group"] = np.where(p["SI_float"].notna(), "in regressions", np.where(p["RIC"].str.contains("^", regex=False),
                          "delisted, no SI", "other, no SI"))
    comp_vars = [Y, "LogMV", "BM", "LagRet1m", "LagRet6m", "Turnover", "IdioVOL"]
    m = p[p["group"] != "other, no SI"].groupby(["Publication", "group"])[comp_vars].mean().unstack("group")
    lines = ["### Table 7. Delisted firms without SI vs firms in the regressions (per-date means, averaged)", "",
             "| variable | in regressions | delisted, no SI | difference (t) |", "|---|---|---|---|"]
    for v in comp_vars:
        diff = (m[(v, "delisted, no SI")] - m[(v, "in regressions")]).dropna().to_numpy()
        scale = 1e4 if v == Y else 1
        lines.append(f"| {LABEL.get(v, v) if v != Y else 'next 5-day adj. return (bps)'} | "
                     f"{m[(v, 'in regressions')].mean() * scale:.4f} | {m[(v, 'delisted, no SI')].mean() * scale:.4f} | "
                     f"{diff.mean() * scale:.4f} ({nw_tstat(diff):.2f}){stars(nw_tstat(diff))} |")
    out.append("\n".join(lines + ["", "Difference t-statistics are Newey-West over dates.", ""]))

    ctrl = {"all firms": keep("controls only, all firms", fm(p, Y, CTRL)),
            "firms with SI only": keep("controls only, firms with SI", fm(p[p["SI_float"].notna()], Y, CTRL))}
    out.append(table(ctrl, "Table 8. Controls-only model with and without the firms lacking SI",
                     "If the coefficients barely move, leaving out the delisted firms does not distort the cross-section."))

    head = (f"# Fama-MacBeth results\n\nPanel: {CLEAN} ({len(p):,} rows, {p['Publication'].nunique()} FINRA dates, "
            f"{p['DataRIC'].nunique()} stocks). Dependent variable unless noted: {Y} (the proposal's main specification).\n")
    with open("regression_results.md", "w", encoding="utf-8") as f:
        f.write(head + "\n" + "\n".join(out))
    pd.DataFrame(coef_rows).to_csv("regression_coefs.csv", index=False)
    print(head + "\n" + "\n".join(out))
