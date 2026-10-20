"""
Collect Groww Google Play reviews (newest first) until July 27, 2026.

Saves only review ID, date, rating, and review text to data/reviews_raw.csv.
Reviewer names and other personal fields are never written.

How to run
----------
From the Milestone 5 folder, with google-play-scraper and pandas installed:

    python collect_reviews.py

The script talks to Google Play live. It does not invent reviews or dates.
Google Play often returns only a limited recent window of reviews, even when
paginating with continuation tokens. If the oldest review is still after
2026-07-27, that is a source limit, not a bug in this script.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews as fetch_reviews

APP_ID = "com.nextbillion.groww"
LANG = "en"
COUNTRY = "in"
CUTOFF_DATE = date(2026, 7, 27)
BATCH_SIZE = 200
SLEEP_SECONDS = 1.5
MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = 3.0
MAX_PAGES = 500
OUTPUT_PATH = Path("data") / "reviews_raw.csv"
CSV_COLUMNS = ["review_id", "date", "rating", "review_text"]


def _review_date(raw) -> date | None:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return None


def _is_blank_text(text) -> bool:
    return text is None or not str(text).strip()


def fetch_page(continuation_token):
    """Fetch one page, retrying on empty/failed responses that look like errors."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            batch, token_obj = fetch_reviews(
                APP_ID,
                lang=LANG,
                country=COUNTRY,
                sort=Sort.NEWEST,
                count=BATCH_SIZE,
                continuation_token=continuation_token,
            )
        except Exception as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(
                f"Network or scraper error (attempt {attempt}/{MAX_RETRIES}): {exc}. "
                f"Retrying in {wait:.1f}s..."
            )
            time.sleep(wait)
            continue

        token_value = getattr(token_obj, "token", None)
        if batch:
            return batch, token_obj

        # Empty page with no token usually means the source is exhausted.
        # Empty page after a request error inside the library looks the same,
        # so retry a few times before giving up.
        if token_value is None and continuation_token is not None:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(
                f"Empty page with no continuation token (attempt {attempt}/{MAX_RETRIES}). "
                f"Retrying in {wait:.1f}s..."
            )
            time.sleep(wait)
            continue

        return batch, token_obj

    raise RuntimeError(
        f"Failed to fetch reviews after {MAX_RETRIES} retries. Last error: {last_error}"
    )


def collect_reviews() -> pd.DataFrame:
    collected: dict[str, dict] = {}
    continuation_token = None
    reached_cutoff = False
    source_exhausted = False

    print(
        f"Collecting reviews for {APP_ID} "
        f"(country={COUNTRY}, lang={LANG}, sort=NEWEST) "
        f"until {CUTOFF_DATE.isoformat()} inclusive."
    )

    for page in range(1, MAX_PAGES + 1):
        batch, token_obj = fetch_page(continuation_token)
        if not batch:
            source_exhausted = True
            print(f"Page {page}: no more results from Google Play.")
            break

        kept_this_page = 0
        skipped_blank = 0
        skipped_duplicate = 0
        older_than_cutoff = 0

        for item in batch:
            review_id = item.get("reviewId")
            review_day = _review_date(item.get("at"))
            text = item.get("content")
            score = item.get("score")

            if review_day is not None and review_day < CUTOFF_DATE:
                older_than_cutoff += 1
                continue
            if not review_id or _is_blank_text(text):
                skipped_blank += 1
                continue
            if review_id in collected:
                skipped_duplicate += 1
                continue

            collected[review_id] = {
                "review_id": review_id,
                "date": review_day.isoformat() if review_day else "",
                "rating": score,
                "review_text": str(text).strip(),
            }
            kept_this_page += 1

        print(
            f"Page {page}: received {len(batch)}, kept {kept_this_page}, "
            f"blank {skipped_blank}, duplicate {skipped_duplicate}, "
            f"before cutoff {older_than_cutoff}. Running total: {len(collected)}"
        )

        if older_than_cutoff:
            reached_cutoff = True
            print(
                f"Reached reviews older than {CUTOFF_DATE.isoformat()}. "
                "Stopping pagination."
            )
            break

        continuation_token = token_obj
        if getattr(token_obj, "token", None) is None:
            source_exhausted = True
            print("No continuation token returned. Stopping pagination.")
            break

        time.sleep(SLEEP_SECONDS)
    else:
        print(f"Stopped after {MAX_PAGES} pages (safety limit).")

    frame = pd.DataFrame(list(collected.values()), columns=CSV_COLUMNS)
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"])
        frame = frame.sort_values("date", ascending=False).reset_index(drop=True)

    frame.attrs["reached_cutoff"] = reached_cutoff
    frame.attrs["source_exhausted"] = source_exhausted
    return frame


def print_summary(frame: pd.DataFrame) -> None:
    print("\n=== Collection summary ===")
    if frame.empty:
        print("Total reviews: 0")
        print("No reviews were saved. Google Play returned no usable text reviews.")
        return

    earliest = frame["date"].min()
    latest = frame["date"].max()
    print(f"Total reviews: {len(frame)}")
    print(f"Earliest date: {earliest.date().isoformat()}")
    print(f"Latest date:   {latest.date().isoformat()}")

    weekly = (
        frame.assign(week=frame["date"].dt.to_period("W-MON").dt.start_time.dt.date)
        .groupby("week", sort=True)
        .size()
    )
    print("\nCounts by week (week starting Monday):")
    for week_start, count in weekly.items():
        print(f"  {week_start}: {count}")

    if earliest.date() > CUTOFF_DATE:
        print(
            "\nLIMITATION: Google Play did not return reviews as far back as "
            f"{CUTOFF_DATE.isoformat()}. The oldest review in this file is "
            f"{earliest.date().isoformat()}. This script does not fabricate "
            "older reviews. The Play Store API typically exposes only a limited "
            "recent window, even with continuation tokens."
        )
    elif not frame.attrs.get("reached_cutoff") and not frame.attrs.get("source_exhausted"):
        print(
            "\nLIMITATION: Pagination stopped before confirming the cutoff date "
            f"or an empty source page. Oldest review: {earliest.date().isoformat()}."
        )


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = collect_reviews()

    save_frame = frame.copy()
    if not save_frame.empty:
        save_frame["date"] = save_frame["date"].dt.strftime("%Y-%m-%d")
    save_frame.to_csv(OUTPUT_PATH, index=False, columns=CSV_COLUMNS)
    print(f"\nWrote {len(save_frame)} reviews to {OUTPUT_PATH}")
    print("Columns: " + ", ".join(CSV_COLUMNS) + " (reviewer names are not saved).")

    print_summary(frame)


if __name__ == "__main__":
    main()
