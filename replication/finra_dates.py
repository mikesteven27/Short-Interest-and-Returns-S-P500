"""FINRA short-interest settlement and publication dates, Sep 2016 - Aug 2026.

FINRA rule: settlement dates are the 15th and the last business day of each month
(rolled back to the previous settlement day), and data is published 7 business days later.
"Business day" means a stock-market trading day: bank-only holidays (Columbus Day, Veterans Day, Juneteenth 2021,
New Year's observed on Friday 2021-12-31) count, as Nasdaq's dated releases show (checks below).
FINRA only posts the current schedule, so the dates are rebuilt from that rule and checked against the 2025-26 rows
FINRA publishes and against Nasdaq's short-interest press releases for the dates a bank-holiday calendar gets wrong.

Output: finra_dates.csv  (Settlement, Publication)
"""
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr,
                                    USMemorialDay, USPresidentsDay, USThanksgivingDay, nearest_workday, sunday_to_monday)
from pandas.tseries.offsets import CustomBusinessDay


class TradingCalendar(AbstractHolidayCalendar):
    """NYSE holidays 2016-2027: no Columbus or Veterans Day, Juneteenth from 2022, and a Saturday New Year's Day is
    not moved back to Friday."""
    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
        Holiday("Bush mourning", year=2018, month=12, day=5),
        Holiday("Carter mourning", year=2025, month=1, day=9),
    ]


BD = CustomBusinessDay(calendar=TradingCalendar())


def schedule(first_month, last_month):
    rows = []
    for m in pd.period_range(first_month, last_month, freq="M"):
        for anchor in (pd.Timestamp(m.year, m.month, 15), m.to_timestamp(how="end").normalize()):
            settle = BD.rollback(anchor)
            rows.append({"Settlement": settle, "Publication": settle + 7 * BD})
    return pd.DataFrame(rows)


# FINRA's published schedule (finra.org/filing-reporting/short-interest-reporting, read 2026-10-19)
FINRA_PUBLISHED = [
    ("2025-11-14", "2025-11-25"), ("2025-11-28", "2025-12-09"), ("2025-12-15", "2025-12-24"), ("2025-12-31", "2026-01-12"),
    ("2026-01-15", "2026-01-27"), ("2026-01-30", "2026-02-10"), ("2026-02-13", "2026-02-25"), ("2026-02-27", "2026-03-10"),
    ("2026-03-13", "2026-03-24"), ("2026-03-31", "2026-04-10"), ("2026-04-15", "2026-04-24"), ("2026-04-30", "2026-05-11"),
    ("2026-05-15", "2026-05-27"), ("2026-05-29", "2026-06-09"), ("2026-06-15", "2026-06-25"), ("2026-06-30", "2026-07-10"),
    ("2026-07-15", "2026-07-24"), ("2026-07-31", "2026-08-11"), ("2026-08-14", "2026-08-25"), ("2026-08-31", "2026-09-10"),
    ("2026-09-15", "2026-09-24"), ("2026-09-30", "2026-10-09"), ("2026-10-15", "2026-10-26"), ("2026-10-30", "2026-11-10"),
    ("2026-11-13", "2026-11-24"), ("2026-11-30", "2026-12-09"), ("2026-12-15", "2026-12-24"), ("2026-12-31", "2027-01-12"),
]
# Nasdaq's short-interest press releases (issued on the publication date), for dates where bank holidays matter
NASDAQ_RELEASES = [
    ("2021-06-15", "2021-06-24"),   # Juneteenth observed Fri 2021-06-18 by banks only
    ("2023-09-29", "2023-10-10"),   # Columbus Day 2023-10-09
    ("2023-10-13", "2023-10-24"), ("2024-09-30", "2024-10-09"),   # no holiday: plain 7-day count
    ("2024-10-31", "2024-11-11"), ("2025-10-31", "2025-11-11"),   # Veterans Day
]

if __name__ == "__main__":
    check = schedule("2025-11", "2026-12")
    got = list(zip(check["Settlement"].dt.strftime("%Y-%m-%d"), check["Publication"].dt.strftime("%Y-%m-%d")))
    assert got == FINRA_PUBLISHED, [(g, f) for g, f in zip(got, FINRA_PUBLISHED) if g != f]
    allrows = schedule("2016-01", "2026-12")
    pub = dict(zip(allrows["Settlement"].dt.strftime("%Y-%m-%d"), allrows["Publication"].dt.strftime("%Y-%m-%d")))
    for s, p in NASDAQ_RELEASES:
        assert pub.get(s) == p, f"settlement {s}: computed {pub.get(s)}, Nasdaq published {p}"
    assert "2021-12-31" in pub and pub["2021-12-31"] == "2022-01-11"   # LSEG's SI changes on Dec 31, not Dec 30

    d = schedule("2016-09", "2026-08")
    assert len(d) == 240 and d["Settlement"].is_monotonic_increasing
    out = Path(__file__).with_name("finra_dates.csv")
    d.to_csv(out, index=False, date_format="%Y-%m-%d")
    print(f"{len(d)} dates, {d['Settlement'].iloc[0]:%Y-%m-%d} to {d['Settlement'].iloc[-1]:%Y-%m-%d}; matches FINRA's "
          f"{len(FINRA_PUBLISHED)} published rows and {len(NASDAQ_RELEASES)} Nasdaq release dates -> {out.name}")
