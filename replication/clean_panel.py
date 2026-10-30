"""Cleaning before the regressions: lseg_output_panel.csv -> panel_clean.csv (the raw panel is left untouched).

1. Drop Viatris (VTRS.OQ) before the Mylan-Upjohn merger closed on 2020-11-16: LSEG's history for it is broken
   (market cap about $0.5B, turnover 37% a day, SI/float above 100%).
2. BM <= 0 (negative book equity, e.g. McDonald's, AutoZone) -> missing.
3. One share class per company and date (GOOG/GOOGL, FOX/FOXA, NWS/NWSA, UA/UAA, DISCK/WBD, TFCF/TFCFA). Classes
   share the company-level market cap and book equity; keep the class with the higher share turnover.
4. Winsorize the continuous variables at the 1st/99th percentile within each date, then recompute the interactions
   (SI x analyst coverage [ln(1 + analysts), as in the proposal], SI x size, and SI x bi-weekly change in SI,
   which the professor suggested for short covering).

Run from this folder:  python clean_panel.py
"""
import pandas as pd

WINSOR = ["FwdRet2w", "FwdRet2w_MktAdj", "FwdRet2w_t2_MktAdj", "FwdRet5", "FwdRet5_MktAdj", "FwdRet5_MktAdj_skip1",
          "SI_float", "SI_shares",
          "dSI_float", "LogMV", "BM", "LagRet1m", "LagRet6m", "Turnover", "IdioVOL"]
SAME_FIRM = ["Publication", "MktCap", "BookEquity"]

p = pd.read_csv("lseg_output_panel.csv", parse_dates=["Publication", "Settlement", "BookPeriodEnd"])
n0 = len(p)

viatris = (p["DataRIC"] == "VTRS.OQ") & (p["Publication"] < "2020-11-16")
p = p[~viatris]

neg_bm = int((p["BM"] <= 0).sum())
p["BM"] = p["BM"].where(p["BM"] > 0)

# both values must match: two different companies can share a rounded market cap on a date (MCK and USB, 2024-04-09)
pair = p["MktCap"].notna() & p["BookEquity"].notna() & p.duplicated(SAME_FIRM, keep=False)
keep = p[pair].sort_values("Turnover", ascending=False).drop_duplicates(SAME_FIRM).index   # NaN turnover sorts last
p = p[~pair | p.index.isin(keep)]

g = p.groupby("Publication")[WINSOR]
lo, hi = g.transform(lambda x: x.quantile(0.01)), g.transform(lambda x: x.quantile(0.99))
p[WINSOR] = p[WINSOR].clip(lower=lo, upper=hi)
p["SI_x_Analysts"] = p["SI_float"] * p["AnalystCov"]
p["SI_x_LogMV"] = p["SI_float"] * p["LogMV"]
p["SI_x_dSI"] = p["SI_float"] * p["dSI_float"]

# self-checks
assert not ((p["DataRIC"] == "VTRS.OQ") & (p["Publication"] < "2020-11-16")).any()
assert not (p["BM"] <= 0).any()
assert not (p["MktCap"].notna() & p["BookEquity"].notna() & p.duplicated(SAME_FIRM, keep=False)).any()
assert not ((p[WINSOR] > hi) | (p[WINSOR] < lo)).any().any()
# split correction: LSEG's SI is in today's units, float as reported; if it breaks, SI/float jumps by the split ratio
# (NVDA 10:1 split 2024-06-10; GE 1:8 reverse split 2021-08-02, where LSEG's float was also wrong before), so the two
# dates on either side must stay within 2x
for ric, split in [("NVDA.OQ", "2024-06-10"), ("GE.N", "2021-08-02")]:
    s = p[p["DataRIC"] == ric].set_index("Publication")["SI_float"].sort_index()
    jump = s[s.index > split].iloc[:2].median() / s[s.index < split].iloc[-2:].median()
    assert 0.5 < jump < 2, f"SI/float jumps {jump:.1f}x across {ric}'s {split} split: check the split correction in lseg_pull.py"

p.to_csv("panel_clean.csv", index=False, date_format="%Y-%m-%d")
print(f"{n0:,} rows -> {len(p):,}: dropped {int(viatris.sum())} pre-merger Viatris rows and {int(pair.sum()) - len(keep)} "
      f"second share-class rows; set BM missing in {neg_bm:,} rows with BM <= 0; winsorized {len(WINSOR)} variables "
      f"at 1%/99% per date -> panel_clean.csv")
