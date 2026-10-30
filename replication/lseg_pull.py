"""Every LSEG input for the short-interest panel, then the panel itself (one row per stock and publication date).

Run in LSEG Workspace CodeBook (in a notebook cell, from the folder holding this file):
  %run lseg_pull.py --test   # 13 stocks on one date (2020-12-24), a few minutes -> lseg_test_*.csv
  %run lseg_pull.py          # full run, about 2-4 hours, resumable: run again after any stop -> lseg_output_*.csv
  python lseg_pull.py --build  # no LSEG needed: rebuild panel.csv from the saved lseg_output_* files (any PC)
CodeBook blocks some standard modules (os among them), so this file imports only argparse, hashlib, re, time,
numpy and pandas, and writes flat files instead of folders.

Needs in the same folder:
  finra_dates.csv                       Settlement, Publication (from finra_dates.py)
  F-F_Research_Data_Factors_daily.csv   Kenneth French daily 3 factors, for IdioVOL (without it IdioVOL stays empty)

Outputs (prefix lseg_output_ or lseg_test_):
  membership.csv          Date (publication), RIC, Name: S&P 500 members on each publication date
  ric_map.csv             index RIC -> DataRIC (used for data) and DailyRIC (close and consolidated volume), Months of prices
  daily.csv.gz            RIC, Date, Close, Volume (both split-adjusted)
  snapshots.csv           RIC, Date, ShortInterest, FloatShares, SharesOut, MktCap, Analysts, AnalystsFY2 on settlement and publication dates
  equity.csv              RIC, BookEquity, PeriodEnd, Announced (quarterly common equity)
  corporate_actions.csv   RIC, ExDate, AdjFactor, AdjType: splits and spin-offs, used to put SI and volume in each date's units
  panel.csv               all regression variables
  errors.csv              requests LSEG refused after retries; running again retries only those
  cache_<stage>_<fields>.csv  every finished request, so a rerun skips them (delete to pull fresh); one file per
                          field list, so a version of this script that asks for other fields never reuses these rows
"""
import argparse
import hashlib
import re
import time

import numpy as np
import pandas as pd

try:
    import lseg.data as ld
except Exception:  # older CodeBook images ship the same library under its previous name
    try:
        import refinitiv.data as ld
    except Exception:   # --build only reads saved files and needs neither
        ld = None

INDEX = ".SPX"
DAILY_START, DAILY_END = "2016-01-01", "2026-09-30"   # 6+ months before the first date, 5+ days after the last
HOLD = 5    # forward returns start at the close of the release day (proposal: the 5 trading days after disclosure);
            # FwdRet5_MktAdj_skip1 starts one day later as a robustness check
FF_FILE = "F-F_Research_Data_Factors_daily.csv"
TEST_DATE = "2020-12-24"   # Tesla just joined; Tiffany and Twitter are still members
# GOOGL/GOOG and BRKb: two share classes; FDX and L (Loews): analyst counts that came back blank in the first pull
TEST_TICKERS = {"AAPL", "IBM", "JPM", "BRKb", "GOOGL", "GOOG", "TSLA", "TWTR", "TIF", "QRVO", "A", "FDX", "L"}

SNAP_FIELDS = {   # pulled on every settlement and publication date
    "ShortInterest": "TR.ShortInterest",                # split-adjusted to today's units
    "FloatShares": "TR.SharesFreeFloat",                # as reported
    "SharesOut": "TR.SharesOutstanding",                # as reported
    "MktCap": "TR.CompanyMarketCap",                    # as reported, all share classes
    "Analysts": "TR.EPSNumIncEstimates(Period=FY1)",
    "AnalystsFY2": "TR.EPSNumIncEstimates(Period=FY2)",   # fallback where FY1 is blank (FedEx, Loews, ...)
}
PAUSE, RETRIES = 0.5, 3
ERRORS = []
STOP_AFTER, STREAK = 5, [0]   # refused requests in a row before the run stops; the running count
OUT = None    # file prefix, set in main()
CACHE = {}    # stage -> {batch key: frame}, loaded from OUT_cache_<stage>.csv


# ---------------- LSEG helpers ----------------
def call(universe, fields, params=None):
    last = None
    for attempt in range(RETRIES):
        try:
            df = ld.get_data(universe=universe, fields=fields, parameters=params or {})
            time.sleep(PAUSE)
            return df
        except Exception as e:  # LSEG raises several error classes
            last = e
            time.sleep(2 ** (attempt + 1))
    raise last


def year_chunks(start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    for y in range(s.year, e.year + 1):
        a = max(s, pd.Timestamp(f"{y}-01-01"))
        b = min(e, pd.Timestamp(f"{y}-12-31"))
        out.append((a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")))
    return out


def day(x):
    """Dates as YYYY-MM-DD from LSEG's mixed formats ('2021-07-20', '2020-04-09 00:00:00', with or without a time
    zone): pandas guesses one format from the first value and turns the rest into blanks otherwise."""
    return pd.to_datetime(pd.Series(x).astype(str).str[:10], errors="coerce").to_numpy()


_d = day(["2021-07-20", "2020-04-09 00:00:00", "2020-04-09T00:00:00+00:00", None])
assert (_d[:3] == np.array(["2021-07-20", "2020-04-09", "2020-04-09"], dtype="datetime64[D]")).all() and np.isnat(_d[3])


def tidy(df, cols):
    df = df.iloc[:, :len(cols)].copy()
    df.columns = cols   # fails loudly (and gets logged) if LSEG dropped a field
    return df


def cached(stage):
    """{tag: rows already pulled}, read once from OUT_cache_<stage>.csv."""
    if stage not in CACHE:
        try:
            # two runs writing at once can garble a line; skip it (with a warning) and its RIC is re-pulled if needed
            df = pd.read_csv(f"{OUT}_cache_{stage}.csv", on_bad_lines="warn")
            tags = df.pop("_key").str.rsplit("_", n=1).str[0]   # older cache files keyed batches as <tag>_<hash>
            CACHE[stage] = {t: g for t, g in df.groupby(tags, sort=False)}
        except FileNotFoundError:
            CACHE[stage] = {}
    return CACHE[stage]


def pull(tag, rics, fields, params, cols, size, retry_empty=False):
    """get_data in batches of `size` RICs. Rows are appended to one cache file per stage (tag without its trailing
    digits); a rerun only requests the RICs this tag has no rows for, so a changed RIC list never redoes the rest.
    retry_empty also re-requests RICs whose saved rows are all blank (LSEG sometimes answers a batch with blanks)."""
    # the field list is part of the file name: rows saved by a version asking for other fields are never mixed in
    stage = re.sub(r"\d+$", "", tag) + "_" + hashlib.md5(" ".join(fields).encode()).hexdigest()[:6]
    done = cached(stage)
    have = done.get(tag, pd.DataFrame(columns=cols))
    have = have[have.iloc[:, 0].isin(rics)]           # first column is the requested instrument
    filled = have[have.iloc[:, 1:].notna().any(axis=1)] if retry_empty else have
    todo = [r for r in rics if r not in set(filled.iloc[:, 0])]
    have = have[~have.iloc[:, 0].isin(todo)]
    frames, failed = ([have] if len(have) else []), 0
    for i in range(0, len(todo), size):
        group = todo[i:i + size]
        try:
            df = tidy(call(group, fields, params), cols)
            text = df.assign(_key=tag).to_csv(index=False, header=not done)
            with open(f"{OUT}_cache_{stage}.csv", "a", encoding="utf-8", newline="") as f:
                f.write(text)   # one write, so stopping the run can't leave half a batch in the cache
            done.setdefault(tag, have)   # the file has a header now
            frames.append(df)
            STREAK[0] = 0
        except Exception as e:
            ERRORS.append({"request": tag, "rics": " ".join(group), "error": str(e)[:300]})
            failed += len(group)
            STREAK[0] += 1
            if STREAK[0] >= STOP_AFTER:   # session expired or a limit was hit: stop instead of failing for hours
                raise RuntimeError(f"LSEG refused {STOP_AFTER} requests in a row, so the run stopped. Everything "
                                   f"finished so far is saved; run again later. Last error: {e}") from e
        print(f"\r{tag}: {min(i + size, len(todo))}/{len(todo)} new RICs", end="", flush=True)
    print(f"\r{tag}: done ({len(rics) - len(todo)} saved, {len(todo) - failed} new"
          f"{f', {failed} FAILED' if failed else ''}){' ' * 20}")
    return pd.concat(frames, ignore_index=True).drop_duplicates() if frames else pd.DataFrame(columns=cols)


# ---------------- RICs ----------------
def ticker(ric):
    return re.match(r"[A-Za-z]*", ric).group()


def consolidated(ric):
    """RIC with consolidated volume: Nasdaq .OQ -> .O; NYSE .N -> no suffix for 1-3 letter tickers, else .K."""
    m = re.fullmatch(r"([A-Z]+)([a-z]?)\.(OQ|N)(\^\w+)?", ric)
    if not m:
        return ric
    t, cls, ex, tail = m.groups(default="")
    return t + cls + (".O" if ex == "OQ" else "" if len(t) <= 3 else ".K") + tail


for _ric, _want in [("AAPL.OQ", "AAPL.O"), ("IBM.N", "IBM"), ("ABBV.N", "ABBV.K"), ("BRKb.N", "BRKb"),
                    ("TWTR.N^J22", "TWTR.K^J22"), ("TIF.N^A21", "TIF^A21"), ("CBOE.Z", "CBOE.Z")]:
    assert consolidated(_ric) == _want, (_ric, consolidated(_ric))


def company_names(tag, rics):
    df = pull(tag, rics, ["TR.CommonName"], {}, ["RIC", "CoName"], 200)
    return df.dropna().drop_duplicates("RIC").set_index("RIC")["CoName"]


def month_ends(tag, rics):
    """{RIC: dates with a month-end close}, to see which RICs really have prices, and when."""
    df = pull(tag, rics, ["TR.PriceClose.date", "TR.PriceClose"], {"SDate": DAILY_START, "EDate": DAILY_END, "Frq": "M"},
              ["RIC", "Date", "Close"], 50)
    df["Date"] = day(df["Date"])
    return {r: g["Date"] for r, g in df.dropna(subset=["Date", "Close"]).groupby("RIC")}


def ric_map(mem):
    """For each index RIC, the RIC to pull data with, chosen by which one actually has prices while it was a member:
    - the index RIC, or the RIC without ^... when the index RIC has none (QRVO.OQ^I26 -> QRVO.OQ)
    - for a listing that moved exchange (KMB.N -> KMB.OQ, same ticker and company), the latest RIC when it has
      at least as many months of prices, since LSEG keeps short interest on the current listing
    Daily data use the consolidated-volume RIC only when it is the same company with at least as many months."""
    win = mem.groupby("RIC")["Date"].agg(["min", "max"])
    m = pd.DataFrame({"RIC": win.index})
    m["Base"] = m["RIC"].str.split("^").str[0]
    names = company_names("names", list(m["RIC"]))
    live = m.loc[~m["RIC"].str.contains("^", regex=False), "RIC"]
    live = pd.DataFrame({"RIC": live, "Tk": live.map(ticker), "Co": live.map(names), "Last": live.map(win["max"])})
    latest = live.dropna(subset=["Co"]).sort_values("Last").groupby(["Tk", "Co"])["RIC"].last()
    m["Moved"] = [r if "^" in r else latest.get((ticker(r), names.get(r)), r) for r in m["RIC"]]

    px = month_ends("probe", sorted(set(m["RIC"]) | set(m["Base"]) | set(m["Moved"])))

    def months(c, r):   # months with a close for RIC c while index RIC r was a member (and 250 days before)
        d = px.get(c)
        return 0 if d is None else int(d.between(win.loc[r, "min"] - pd.Timedelta(days=250), win.loc[r, "max"]).sum())

    def pick(r, base, moved):
        d = base if months(r, r) == 0 and months(base, r) > 0 else r
        return moved if moved != r and months(moved, r) >= max(months(d, r), 1) else d

    m["DataRIC"] = [pick(*t) for t in zip(m["RIC"], m["Base"], m["Moved"])]
    m["Cons"] = m["DataRIC"].map(consolidated)
    extra = sorted((set(m["Base"]) | set(m["Cons"])) - set(names.index))
    names = pd.concat([names, company_names("names2", extra)]) if extra else names
    px.update(month_ends("probe2", sorted(set(m["Cons"]) - set(px))))
    m["Name"], m["DataName"] = m["RIC"].map(names), m["DataRIC"].map(names)
    m["Months"] = [months(d, r) for r, d in zip(m["RIC"], m["DataRIC"])]
    m["ConsolidatedVolume"] = [c != d and pd.notna(names.get(d)) and names.get(c) == names.get(d)
                               and months(c, r) >= max(months(d, r), 1) for r, d, c in zip(m["RIC"], m["DataRIC"], m["Cons"])]
    m["DailyRIC"] = m["Cons"].where(m["ConsolidatedVolume"], m["DataRIC"])
    return m[["RIC", "DataRIC", "DailyRIC", "ConsolidatedVolume", "Months", "Name", "DataName"]]


# ---------------- pulls ----------------
def membership(pub_dates):
    frames = []
    for d in pub_dates:
        df = pull(f"members{d:%Y%m%d}", [INDEX], ["TR.IndexConstituentRIC", "TR.IndexConstituentName"],
                  {"SDate": f"{d:%Y-%m-%d}"}, ["Index", "RIC", "Name"], 1)
        frames.append(df.drop(columns="Index").assign(Date=d))
    mem = pd.concat(frames, ignore_index=True)
    mem = mem[mem["RIC"].notna() & ~mem["RIC"].isin(["NULL", ""])]
    return mem.drop_duplicates(["Date", "RIC"])[["Date", "RIC", "Name"]]   # a re-pulled date must not double a stock


def daily(rmap, mem):
    """Daily close and volume. Each year only asks for RICs whose membership (plus 250 days before for the lagged
    returns, 45 after for the forward returns up to t+2) touches that year, so blank answers are worth asking again."""
    w = mem.merge(rmap[["RIC", "DailyRIC"]], on="RIC").groupby("DailyRIC")["Date"].agg(["min", "max"])
    lo, hi = w["min"] - pd.Timedelta(days=250), w["max"] + pd.Timedelta(days=45)
    frames = []
    for a, b in year_chunks(DAILY_START, DAILY_END):
        rics = sorted(w.index[(lo <= pd.Timestamp(b)) & (hi >= pd.Timestamp(a))]) + [INDEX]
        frames.append(pull(f"daily{a[:4]}", rics, ["TR.PriceClose.date", "TR.PriceClose", "TR.Volume"],
                           {"SDate": a, "EDate": b, "Frq": "D"}, ["RIC", "Date", "Close", "Volume"], 10, retry_empty=True))
    d = pd.concat(frames, ignore_index=True)
    d["Date"] = day(d["Date"])
    d["RIC"] = d["RIC"].map(dict(zip(rmap["DailyRIC"], rmap["DataRIC"]))).fillna(d["RIC"])
    return d.dropna(subset=["Date", "Close"]).drop_duplicates(["RIC", "Date"]).sort_values(["RIC", "Date"])


def snapshots(obs):
    pairs = pd.concat([obs[["Settlement", "DataRIC"]].set_axis(["Date", "RIC"], axis=1),
                       obs[["Publication", "DataRIC"]].set_axis(["Date", "RIC"], axis=1)]).drop_duplicates()
    frames = []
    for d, g in pairs.groupby("Date"):
        df = pull(f"snap{d:%Y%m%d}", sorted(g["RIC"]), list(SNAP_FIELDS.values()), {"SDate": f"{d:%Y-%m-%d}"},
                  ["RIC"] + list(SNAP_FIELDS), 300)
        frames.append(df.assign(Date=d))
    return pd.concat(frames, ignore_index=True).drop_duplicates(["RIC", "Date"])


def equity(rics):
    """Quarterly common equity (excludes preferred) with the date the figure was first announced."""
    return pull("equity", rics, ["TR.F.ComEqTot", "TR.F.PeriodEndDate", "TR.F.OriginalAnnouncementDate"],
                {"SDate": "0", "EDate": "-45", "Period": "FQ0", "Frq": "FQ"},
                ["RIC", "BookEquity", "PeriodEnd", "Announced"], 10)


def corporate_actions(rics):
    """Splits ('Capital Change Type') and spin-offs ('LSEG Pricing Only') with LSEG's price adjustment factor, up to
    today: LSEG adjusts past prices and short interest to the day of the pull, so every later event is needed."""
    return pull("ca", rics, ["TR.CAExDate", "TR.CAAdjustmentFactor", "TR.CAAdjustmentType"],
                {"SDate": DAILY_START, "EDate": pd.Timestamp.today().strftime("%Y-%m-%d")},
                ["RIC", "ExDate", "AdjFactor", "AdjType"], 50)


def read_ff(path):
    try:
        with open(path, encoding="latin-1") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"WARNING: {path} not found, IdioVOL will be empty")
        return None
    rows = [line.split(",") for line in lines if re.match(r"\s*\d{8},", line)]
    idx = pd.to_datetime([r[0].strip() for r in rows], format="%Y%m%d")
    return pd.DataFrame([[float(x) for x in r[1:5]] for r in rows], index=idx, columns=["MktRF", "SMB", "HML", "RF"]) / 100


# ---------------- variables ----------------
WINDOW_COLS = ["FwdRet5", "FwdRet5_MktAdj", "FwdRet5_MktAdj_skip1", "FwdRet2w", "FwdRet2w_MktAdj", "FwdRet2w_t2_MktAdj",
               "LagRet1m", "LagRet6m", "AvgVolume21", "PctZero", "IdioVOL"]


def window_vars(obs, dly, ff):
    """Return-window variables. k = the release day; backward windows end at its close, forward windows start there.
    FwdRet5 = the 5 trading days after the release. Bi-weekly returns run from one release's close to the next
    release's close (t+1) and on to the one after (t+2), so consecutive windows tile time like FINRA's releases."""
    px = dly.pivot(index="Date", columns="RIC", values="Close").sort_index()
    # trading days = days most stocks have a close; LSEG's .SPX repeats its last value on some holidays
    # (10 of them in Sep 2021 - Sep 2022), which would otherwise blank every window that touches them
    n_px = px.drop(columns=INDEX).notna().sum(axis=1)
    px = px[n_px >= n_px.median() / 2]
    p, v =px.to_numpy(float), dly.pivot(index="Date", columns="RIC", values="Volume").reindex(px.index).to_numpy(float)
    ret = p / np.vstack([np.full((1, p.shape[1]), np.nan), p[:-1]]) - 1
    col = {r: i for i, r in enumerate(px.columns)}
    m, n = col[INDEX], len(px)
    if ff is not None:
        f = ff.reindex(px.index)
        X = np.column_stack([np.ones(n), f[["MktRF", "SMB", "HML"]].to_numpy()])
        rf = f["RF"].to_numpy()
    pubs = pd.DatetimeIndex(sorted(obs["Publication"].unique()))
    missing = pubs[~pubs.isin(px.index)]
    assert missing.empty, f"release days with no trading: {list(missing.date)}; forward returns would start too early"
    kp = list(px.index.searchsorted(pubs, side="right") - 1) + [None, None]   # shortcut: no t+1 for the last date
    ret_mkt = lambda j, a, b: (p[b, j] / p[a, j] - 1, p[b, j] / p[a, j] - p[b, m] / p[a, m])
    out = []
    for ric, i, k in zip(obs["DataRIC"], pubs.get_indexer(obs["Publication"]),
                         px.index.searchsorted(obs["Publication"], side="right") - 1):
        j, r = col.get(ric), {}
        if j is not None and k >= 126:
            if k + HOLD < n:
                r["FwdRet5"], r["FwdRet5_MktAdj"] = ret_mkt(j, k, k + HOLD)
            if k + 1 + HOLD < n:
                r["FwdRet5_MktAdj_skip1"] = ret_mkt(j, k + 1, k + 1 + HOLD)[1]
            k1, k2 = kp[i + 1], kp[i + 2]
            if k1 is not None:
                r["FwdRet2w"], r["FwdRet2w_MktAdj"] = ret_mkt(j, k, k1)
                if k2 is not None:
                    r["FwdRet2w_t2_MktAdj"] = ret_mkt(j, k1, k2)[1]
            r["LagRet1m"] = p[k, j] / p[k - 21, j] - 1
            r["LagRet6m"] = p[k - 21, j] / p[k - 126, j] - 1
            v21, r21 = v[k - 20:k + 1, j], ret[k - 20:k + 1, j]
            v21, r21 = v21[~np.isnan(v21)], r21[~np.isnan(r21)]
            r["AvgVolume21"] = v21.mean() if len(v21) else np.nan
            r["PctZero"] = (r21 == 0).mean() if len(r21) else np.nan
            if ff is not None:
                y, x = ret[k - 62:k + 1, j] - rf[k - 62:k + 1], X[k - 62:k + 1]
                ok = ~np.isnan(y) & ~np.isnan(x).any(axis=1)
                if ok.sum() >= 50:   # shortcut: needs 50 of 63 days; French data lags 1-2 months, so the last dates may miss
                    e = y[ok] - x[ok] @ np.linalg.lstsq(x[ok], y[ok], rcond=None)[0]
                    r["IdioVOL"] = e.std(ddof=4)
        out.append(r)
    return pd.DataFrame(out, index=obs.index, columns=WINDOW_COLS)


SPLITS = ["Capital Change Type"]               # splits, reverse splits: adjust prices, volume and short interest
ALL_EVENTS = SPLITS + ["LSEG Pricing Only"]     # spin-offs: adjust prices and short interest, not volume


def later_factor(ca, rics, dates, types):
    """For each (stock, date): product of LSEG's price adjustment factors for that stock's events after the date
    (a 4:1 split has factor 0.25). Multiplying today's adjusted figure by it gives the figure in that date's units."""
    x = pd.DataFrame({"RIC": rics.to_numpy(), "Date": dates.to_numpy()}).reset_index()
    x = x.merge(ca[ca["AdjType"].isin(types)], on="RIC")
    f = x[x["ExDate"] > x["Date"]].groupby("index")["AdjFactor"].prod()
    out = np.ones(len(rics))
    out[f.index.to_numpy()] = f.to_numpy()
    return out


def build(obs, dly, snaps, eq, ca, ff):
    ns ="datetime64[ns]"   # one date resolution everywhere, or lookups and merge_asof silently miss
    obs = obs.astype({"Settlement": ns, "Publication": ns})
    dly = dly.assign(Date=pd.to_datetime(dly["Date"]).astype(ns))
    ff = ff.set_axis(ff.index.astype(ns)) if ff is not None else None
    s = snaps.assign(Date=pd.to_datetime(snaps["Date"]).astype(ns)).set_index(["RIC", "Date"])
    at_settle = s.reindex(pd.MultiIndex.from_arrays([obs["DataRIC"], obs["Settlement"]])).set_index(obs.index)
    at_pub = s.reindex(pd.MultiIndex.from_arrays([obs["DataRIC"], obs["Publication"]])).set_index(obs.index)
    both = at_settle["ShortInterest"].notna() & at_pub["ShortInterest"].notna()
    same = pd.Series(np.isclose(at_settle["ShortInterest"], at_pub["ShortInterest"]), index=obs.index)[both]
    stale = same.groupby(obs.loc[both, "Publication"]).mean().loc[lambda x: x < 0.9]
    assert stale.empty, f"SI on the settlement date is not the published figure for {list(stale.index.date)}: check finra_dates.csv"

    c = ca.assign(ExDate=pd.to_datetime(day(ca["ExDate"])).astype(ns),
                  AdjFactor=pd.to_numeric(ca["AdjFactor"], errors="coerce")).dropna(subset=["ExDate", "AdjFactor"])
    c = c[c["AdjFactor"] != 1].drop_duplicates(["RIC", "ExDate", "AdjFactor"])
    # a float above 1.5x shares outstanding is impossible (GE 2019-21: LSEG's float is 7.7x the 8.7B shares out);
    # use shares outstanding as the float there (61 settlement rows, 50 of them GE)
    floats = lambda a: a["FloatShares"].where(~(a["FloatShares"] > 1.5 * a["SharesOut"]), a["SharesOut"])

    p = obs[["Publication", "Settlement", "RIC", "DataRIC", "Name"]].copy()
    # LSEG states SI in today's units, adjusted for every later split and spin-off, while float and shares are as
    # reported for one share class; the later factors put SI back into that date's units for the same class
    si_raw = at_settle["ShortInterest"] * later_factor(c, obs["DataRIC"], obs["Settlement"], ALL_EVENTS)
    p["SI_float"] = si_raw / floats(at_settle)
    p["SI_shares"] = si_raw / at_settle["SharesOut"]
    cls = p[p["DataRIC"].isin(["GOOGL.OQ", "GOOG.OQ"])].groupby("DataRIC")["SI_float"].median()
    assert len(cls) < 2 or 0.5 < cls.iloc[0] / cls.iloc[1] < 2, f"Alphabet's share classes disagree on SI/float: {cls.to_dict()}"
    # bi-weekly % change in SI/float, only between consecutive FINRA dates of the same stock (short covering)
    t = pd.Series(pd.DatetimeIndex(sorted(p["Publication"].unique())).get_indexer(p["Publication"]), index=p.index)
    q = p.assign(t=t).sort_values(["DataRIC", "t"])
    prev = q.groupby("DataRIC")[["SI_float", "t"]].shift()
    p["dSI_float"] = (q["SI_float"] / prev["SI_float"] - 1).where(q["t"] - prev["t"] == 1).replace([np.inf, -np.inf], np.nan)
    p["MktCap"] = at_pub["MktCap"]
    p["LogMV"] = np.log(at_pub["MktCap"].where(at_pub["MktCap"] > 0))
    fy2 = at_pub["AnalystsFY2"] if "AnalystsFY2" in at_pub else np.nan   # first-pull files have no FY2 column
    p["Analysts"] = at_pub["Analysts"].fillna(fy2)
    p["AnalystCov"] = np.log1p(p["Analysts"])   # proposal: ln(1 + analysts with active forecasts) at disclosure

    e = eq.assign(Announced=day(eq["Announced"]), PeriodEnd=day(eq["PeriodEnd"]),
                  BookEquity=pd.to_numeric(eq["BookEquity"], errors="coerce"))
    e["Available"] = e["Announced"].fillna(e["PeriodEnd"] + pd.Timedelta(days=90)).astype(ns)   # no announcement date: 90-day lag
    e = e.dropna(subset=["Available", "BookEquity"]).sort_values("Available")
    be = pd.merge_asof(p[["Publication", "DataRIC"]].reset_index().sort_values("Publication"),
                       e[["RIC", "Available", "BookEquity", "PeriodEnd"]].rename(columns={"RIC": "DataRIC"}),
                       left_on="Publication", right_on="Available", by="DataRIC").set_index("index")
    p["BookEquity"], p["BookPeriodEnd"] = be["BookEquity"], be["PeriodEnd"]
    p["BM"] = p["BookEquity"] / p["MktCap"]

    w = window_vars(obs, dly, ff)
    p = p.join(w)
    # volume is in today's units for later splits only; spin-offs adjust prices, not volume
    p["Turnover"] = p.pop("AvgVolume21") * later_factor(c, obs["DataRIC"], obs["Publication"], SPLITS) / at_pub["SharesOut"]
    med = p.groupby("DataRIC")["Turnover"].agg(["median", "size"])
    low = med[(med["size"] >= 20) & (med["median"] < 0.1 * p["Turnover"].median())]
    assert low.empty, f"turnover below 10% of the panel median for {list(low.index)}: check volume and share units"
    p["SI_x_Analysts"] = p["SI_float"] * p["AnalystCov"]
    p["SI_x_LogMV"] = p["SI_float"] * p["LogMV"]
    return p.sort_values(["Publication", "RIC"])


# ---------------- main ----------------
def main(test, build_only=False):
    global OUT
    OUT = "lseg_test" if test else "lseg_output"

    def save(df, name, **kw):
        df.to_csv(f"{OUT}_{name}", index=False, date_format="%Y-%m-%d", **kw)

    dates = pd.read_csv("finra_dates.csv", parse_dates=["Settlement", "Publication"])
    if test:
        dates = dates[dates["Publication"] == TEST_DATE]
    if build_only:
        mem = pd.read_csv(f"{OUT}_membership.csv", parse_dates=["Date"])
        rmap = pd.read_csv(f"{OUT}_ric_map.csv")
    else:
        mem = membership(dates["Publication"])
        if test:
            mem = mem[mem["RIC"].map(ticker).isin(TEST_TICKERS)]
        save(mem, "membership.csv")
        rmap = ric_map(mem)
        save(rmap, "ric_map.csv")
    obs = mem.merge(rmap[["RIC", "DataRIC"]], on="RIC").merge(dates, left_on="Date", right_on="Publication")
    # two index RICs of one listing on the same date (HST.N and HST.OQ) count once, keeping the one that is the DataRIC
    obs = (obs.assign(_other=obs["RIC"].ne(obs["DataRIC"])).sort_values("_other")
              .drop_duplicates(["Publication", "DataRIC"]).drop(columns=["Date", "_other"]).reset_index(drop=True))
    rics = sorted(rmap["DataRIC"].unique())

    if not build_only:
        save(daily(rmap, mem), "daily.csv.gz")
        save(snapshots(obs), "snapshots.csv")
        save(equity(rics), "equity.csv")
        save(corporate_actions(rics), "corporate_actions.csv")

    # build from the saved files so fresh and cached pulls have the same column types
    panel = build(obs, pd.read_csv(f"{OUT}_daily.csv.gz"), pd.read_csv(f"{OUT}_snapshots.csv"),
                  pd.read_csv(f"{OUT}_equity.csv"), pd.read_csv(f"{OUT}_corporate_actions.csv"), read_ff(FF_FILE))
    save(panel, "panel.csv")
    if not build_only:
        save(pd.DataFrame(ERRORS, columns=["request", "rics", "error"]), "errors.csv")

    print(f"\n{len(dates)} dates | {len(rics)} stocks | {len(panel):,} panel rows | "
          f"consolidated volume for {rmap['ConsolidatedVolume'].sum()}/{len(rmap)} | failed requests: {len(ERRORS)}")
    print("Share of panel rows with a value:\n" + panel.notna().mean().round(3).to_string())
    if test:
        with pd.option_context("display.width", 250, "display.max_columns", 50):
            print("\n" + rmap.to_string() + "\n\n" + panel.drop(columns=["Name"]).to_string())
    if ERRORS:
        print(f"Some requests failed (see {OUT}_errors.csv). Run the same command again to retry them.")
    print(f"Saved {OUT}_*.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="10 stocks on one date, to check every field first")
    ap.add_argument("--build", action="store_true", help="rebuild panel.csv from the saved files, without LSEG")
    args = ap.parse_args()
    if args.build:
        raise SystemExit(main(args.test, build_only=True))
    ld.open_session()
    try:
        main(args.test)
    finally:
        ld.close_session()
