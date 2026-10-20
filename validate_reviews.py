"""
Validate Groww reviews in data/reviews_raw.csv.

This script only reads the CSV and writes data/validation_report.txt.
It does not invent, rewrite, or delete reviews, and it does not change
collect_reviews.py or data/reviews_raw.csv.

How to run
----------
From the Milestone 5 folder:

    python validate_reviews.py

Requires pandas (already used by collect_reviews.py).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

CSV_PATH = Path("data") / "reviews_raw.csv"
REPORT_PATH = Path("data") / "validation_report.txt"
REQUIRED_COLUMNS = ["review_id", "date", "rating", "review_text"]
EXPECTED_START = date(2026, 7, 27)
EXPECTED_END = date(2026, 10, 19)
ALLOWED_LATEST = date(2026, 10, 18)


def word_count(text) -> int:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return 0
    return len(str(text).split())


def monday_week_start(series: pd.Series) -> pd.Series:
    """Monday-starting calendar week: Monday=0 through Sunday=6."""
    return (series - pd.to_timedelta(series.dt.dayofweek, unit="D")).dt.date


def format_week_range(week_monday: date) -> str:
    week_sunday = week_monday + timedelta(days=6)
    return f"{week_monday.isoformat()} to {week_sunday.isoformat()}"


def build_report(path: Path) -> str:
    lines: list[str] = []
    add = lines.append

    add("Groww Google Play reviews - validation report")
    add("=" * 52)
    add(f"Source file: {path.as_posix()}")
    add("Mode: read-only. No reviews were invented, rewritten, or deleted.")
    add("")

    if not path.exists():
        add("FAIL: reviews file not found.")
        return "\n".join(lines) + "\n"

    frame = pd.read_csv(path, dtype={"review_id": "string", "review_text": "string"})
    add(f"Row count (as stored in CSV): {len(frame)}")
    add(f"Column names: {', '.join(frame.columns.astype(str))}")
    add("")

    add("1. Required columns")
    add("-" * 52)
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    extra_cols = [col for col in frame.columns if col not in REQUIRED_COLUMNS]
    if missing_cols:
        add(f"FAIL: missing required columns: {', '.join(missing_cols)}")
    else:
        add("PASS: all required columns are present (review_id, date, rating, review_text).")
    if extra_cols:
        add(f"Note: extra columns found: {', '.join(map(str, extra_cols))}")
    else:
        add("No extra columns.")
    add("")

    present = [col for col in REQUIRED_COLUMNS if col in frame.columns]
    add("2. Missing values and duplicate review IDs")
    add("-" * 52)
    if present:
        for col in present:
            if col == "review_id":
                blank_mask = frame[col].isna() | (frame[col].astype(str).str.strip() == "") | (
                    frame[col].astype(str).str.lower() == "nan"
                )
            elif col == "review_text":
                blank_mask = frame[col].isna() | (frame[col].astype(str).str.strip() == "") | (
                    frame[col].astype(str).str.lower() == "<na>"
                )
            else:
                blank_mask = frame[col].isna()
            add(f"  {col}: {int(blank_mask.sum())} missing/blank")
        if "review_id" in frame.columns:
            ids = frame["review_id"].astype(str)
            dup_mask = ids.duplicated(keep=False) & ids.notna() & (ids.str.strip() != "")
            duplicate_rows = int(dup_mask.sum())
            duplicate_id_count = int(ids[dup_mask].nunique()) if duplicate_rows else 0
            extra_copies = int(ids.duplicated().sum())
            add(f"  Duplicate review_id values: {duplicate_id_count}")
            add(f"  Rows involved in those duplicates: {duplicate_rows}")
            add(f"  Extra copies beyond the first occurrence: {extra_copies}")
            if duplicate_id_count:
                add("  FAIL: duplicate review IDs are present.")
            else:
                add("  PASS: no duplicate review IDs.")
    else:
        add("Skipped: required columns are missing.")
    add("")

    add("3. Rating values")
    add("-" * 52)
    if "rating" not in frame.columns:
        add("Skipped: rating column is missing.")
        invalid_rating_count = None
    else:
        rating = pd.to_numeric(frame["rating"], errors="coerce")
        non_numeric = int((frame["rating"].notna() & rating.isna()).sum())
        missing_rating = int(frame["rating"].isna().sum())
        is_integer = rating.notna() & (rating == rating.round())
        in_range = is_integer & rating.between(1, 5)
        invalid_rating = ~in_range
        invalid_rating_count = int(invalid_rating.sum())
        add(f"  Missing ratings: {missing_rating}")
        add(f"  Non-numeric ratings: {non_numeric}")
        add(f"  Integer ratings 1-5: {int(in_range.sum())}")
        add(f"  Invalid ratings (missing, non-integer, or outside 1-5): {invalid_rating_count}")
        if rating.notna().any():
            add(f"  Observed min/max among numeric ratings: {int(rating.min())} / {int(rating.max())}")
            counts = rating[in_range].astype(int).value_counts().sort_index()
            add("  Counts by valid rating:")
            for score, count in counts.items():
                add(f"    {score}: {count}")
        if invalid_rating_count == 0:
            add("  PASS: every rating is an integer from 1 to 5.")
        else:
            add("  FAIL: one or more ratings are not integers from 1 to 5.")
    add("")

    add("4. Date range")
    add("-" * 52)
    parsed_dates = pd.Series(dtype="datetime64[ns]")
    if "date" not in frame.columns:
        add("Skipped: date column is missing.")
        min_day = max_day = None
    else:
        parsed_dates = pd.to_datetime(frame["date"], errors="coerce")
        unparseable = int((frame["date"].notna() & parsed_dates.isna()).sum())
        missing_dates = int(frame["date"].isna().sum())
        valid_dates = parsed_dates.dropna().dt.date
        add(f"  Missing dates: {missing_dates}")
        add(f"  Unparseable dates: {unparseable}")
        if valid_dates.empty:
            add("  FAIL: no valid dates found.")
            min_day = max_day = None
        else:
            min_day = valid_dates.min()
            max_day = valid_dates.max()
            add(f"  Minimum date: {min_day.isoformat()}")
            add(f"  Maximum date: {max_day.isoformat()}")
            add(
                f"  Expected coverage: {EXPECTED_START.isoformat()} through "
                f"{EXPECTED_END.isoformat()} (latest review may be {ALLOWED_LATEST.isoformat()})."
            )

            has_start = (valid_dates == EXPECTED_START).any()
            latest_ok = max_day in {EXPECTED_END, ALLOWED_LATEST}
            starts_ok = min_day == EXPECTED_START
            before_window = int((valid_dates < EXPECTED_START).sum())
            after_window = int((valid_dates > EXPECTED_END).sum())

            add(f"  Reviews on {EXPECTED_START.isoformat()}: {int((valid_dates == EXPECTED_START).sum())}")
            add(f"  Reviews on {ALLOWED_LATEST.isoformat()}: {int((valid_dates == ALLOWED_LATEST).sum())}")
            add(f"  Reviews on {EXPECTED_END.isoformat()}: {int((valid_dates == EXPECTED_END).sum())}")
            add(f"  Reviews before {EXPECTED_START.isoformat()}: {before_window}")
            add(f"  Reviews after {EXPECTED_END.isoformat()}: {after_window}")

            covers = starts_ok and has_start and latest_ok and before_window == 0 and after_window == 0
            if covers:
                if max_day == ALLOWED_LATEST:
                    add(
                        "  PASS: data covers 27 Jul 2026 through the latest available review "
                        "on 18 Oct 2026 (19 Oct 2026 is allowed as the window end; 18 Oct is accepted)."
                    )
                else:
                    add("  PASS: data covers 27 Jul 2026 through 19 Oct 2026.")
            else:
                add("  FAIL: data does not fully cover the expected 27 Jul–19 Oct 2026 window.")
                if not starts_ok:
                    add(f"    Earliest date is {min_day.isoformat()}, not {EXPECTED_START.isoformat()}.")
                if not latest_ok:
                    add(
                        f"    Latest date is {max_day.isoformat()}, not "
                        f"{ALLOWED_LATEST.isoformat()} or {EXPECTED_END.isoformat()}."
                    )
                if not has_start:
                    add(f"    No review dated {EXPECTED_START.isoformat()} was found.")
    add("")

    add("5. Blank reviews and short reviews")
    add("-" * 52)
    if "review_text" not in frame.columns:
        add("Skipped: review_text column is missing.")
    else:
        text = frame["review_text"]
        blank_mask = text.isna() | (text.astype(str).str.strip() == "") | (
            text.astype(str).str.lower().isin(["<na>", "nan"])
        )
        words = text.map(word_count)
        short_mask = (~blank_mask) & (words < 5)
        add(f"  Blank reviews (missing or whitespace-only): {int(blank_mask.sum())}")
        add(f"  Reviews with fewer than 5 words (excluding blanks): {int(short_mask.sum())}")
        add(f"  Reviews with 5 or more words: {int((~blank_mask & (words >= 5)).sum())}")
        add("  These rows were counted only. They were not deleted or rewritten.")
    add("")

    add("6. Review counts by Monday-starting week")
    add("-" * 52)
    add("  Week definition: Monday through Sunday. Week label is the Monday date.")
    if "date" not in frame.columns or parsed_dates.dropna().empty:
        add("  Skipped: no valid dates for weekly grouping.")
    else:
        dated = frame.loc[parsed_dates.notna()].copy()
        dated["_week_start"] = monday_week_start(parsed_dates[parsed_dates.notna()])
        weekly = dated.groupby("_week_start", sort=True).size()
        add(f"  Weeks represented: {len(weekly)}")
        for week_start, count in weekly.items():
            add(f"  {format_week_range(week_start)}: {count}")
        add(f"  Weekly total: {int(weekly.sum())}")
        if int(weekly.sum()) != len(dated):
            add("  FAIL: weekly counts do not sum to the number of dated rows.")
        else:
            add("  PASS: weekly counts sum to the number of rows with valid dates.")
    add("")

    add("7. Integrity")
    add("-" * 52)
    add("  collect_reviews.py was not modified.")
    add("  data/reviews_raw.csv was not modified.")
    add("  No reviews were invented, rewritten, or silently deleted.")
    add("")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report(CSV_PATH)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote validation report to {REPORT_PATH.as_posix()}")
    print(f"Left {CSV_PATH.as_posix()} unchanged.")


if __name__ == "__main__":
    main()
