
from pathlib import Path
import pandas as pd

# --------------------------------------------------
# 1. File paths
# --------------------------------------------------
BASE = Path(__file__).parent

RAW_FILE = BASE / "data" / "reviews_raw.csv"
CLASSIFIED_FILE = BASE / "data" / "analysis" / "classified_reviews.csv"
FEE_FILE = BASE / "data" / "analysis" / "fee_review_categories.csv"
OUTPUT_DIR = BASE / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    # --------------------------------------------------
    # 2. Check input files
    # --------------------------------------------------
    for file_path in [RAW_FILE, CLASSIFIED_FILE, FEE_FILE]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file not found: {file_path}"
            )

    raw = pd.read_csv(RAW_FILE)
    classified = pd.read_csv(CLASSIFIED_FILE)
    fees = pd.read_csv(FEE_FILE)

    required_raw = {"review_id", "date", "rating", "review_text"}
    required_classified = {"review_id", "theme"}
    required_fees = {"candidate_category"}

    if not required_raw.issubset(raw.columns):
        raise ValueError(
            f"Raw CSV must contain columns: {required_raw}"
        )

    if not required_classified.issubset(classified.columns):
        raise ValueError(
            f"Classified CSV must contain columns: {required_classified}"
        )

    if not required_fees.issubset(fees.columns):
        raise ValueError(
            f"Fee CSV must contain columns: {required_fees}"
        )

    # --------------------------------------------------
    # 3. Join classifications with original reviews
    # --------------------------------------------------
    reviews = classified.merge(
        raw[["review_id", "date", "rating", "review_text"]],
        on="review_id",
        how="inner",
        validate="one_to_one",
    )

    reviews["rating"] = pd.to_numeric(
        reviews["rating"], errors="coerce"
    )

    reviews["review_text"] = (
        reviews["review_text"].fillna("").astype(str)
    )

    total_raw = len(raw)
    total_classified = len(reviews)

    coverage = (
        total_classified / total_raw * 100
        if total_raw > 0
        else 0
    )

    # --------------------------------------------------
    # 4. Calculate theme counts
    # --------------------------------------------------
    counts = (
        reviews.groupby("theme")
        .agg(
            review_count=("review_id", "count"),
            low_rated=("rating", lambda s: (s <= 2).sum()),
        )
        .sort_values(
            ["low_rated", "review_count"],
            ascending=[False, False],
        )
    )

    # Exclude Other when selecting the three product themes.
    product_themes = counts.drop(
        index="Other", errors="ignore"
    ).head(3)

    # --------------------------------------------------
    # 5. Select three exact quotes from distinct themes
    # --------------------------------------------------
    quotes = reviews[
        (reviews["theme"] != "Other")
        & (
            reviews["review_text"]
            .str.split()
            .str.len()
            .ge(8)
        )
    ].copy()

    quotes = quotes.sort_values(
        ["rating", "date"],
        ascending=[True, False],
    )

    selected_quotes = []
    used_themes = set()

    # Prefer quotes from the top three themes.
    preferred_themes = list(product_themes.index)

    for theme in preferred_themes:
        theme_quotes = quotes[quotes["theme"] == theme]

        if not theme_quotes.empty:
            selected_quotes.append(theme_quotes.iloc[0])
            used_themes.add(theme)

        if len(selected_quotes) == 3:
            break

    # If needed, fill remaining slots from other product themes.
    if len(selected_quotes) < 3:
        for _, row in quotes.iterrows():
            if row["theme"] not in used_themes:
                selected_quotes.append(row)
                used_themes.add(row["theme"])

            if len(selected_quotes) == 3:
                break

    # --------------------------------------------------
    # 6. Fee candidate counts
    # --------------------------------------------------
    fee_counts = fees["candidate_category"].value_counts()

    # --------------------------------------------------
    # 7. Print the results
    # --------------------------------------------------
    print("\n=== CLASSIFICATION COVERAGE ===")
    print(f"Original reviews: {total_raw}")
    print(f"Classified reviews: {total_classified}")
    print(f"Coverage: {coverage:.2f}%")

    print("\n=== THEME COUNTS ===")
    print(counts.to_string())

    print("\n=== TOP 3 PRODUCT THEMES ===")
    if product_themes.empty:
        print("No product themes available.")
    else:
        print(product_themes.to_string())

    print("\n=== THREE CUSTOMER QUOTE CANDIDATES ===")

    if not selected_quotes:
        print("No suitable quotes found.")
    else:
        for row in selected_quotes:
            print(f"\nTheme: {row['theme']}")
            print(f"Rating: {row['rating']}")
            print(f"Date: {row['date']}")
            print(f"Review ID: {row['review_id']}")
            print(f"Exact quote: {row['review_text']}")

    print("\n=== FEE CANDIDATE COUNTS ===")
    print(fee_counts.to_string())

    # --------------------------------------------------
    # 8. Build Markdown report without tabulate
    # --------------------------------------------------
    report_lines = [
        "# Groww Review Analysis",
        "",
        "## Dataset coverage",
        "",
        f"- Original reviews collected: {total_raw}",
        f"- Reviews classified: {total_classified}",
        f"- Classification coverage: {coverage:.2f}%",
        "",
        "**Limitation:** Theme counts describe only the classified "
        "subset. They should not be interpreted as representative "
        "of all collected reviews.",
        "",
        "## Theme counts",
        "",
        "| Theme | Review count | Ratings 1–2 |",
        "|---|---:|---:|",
    ]

    for theme, row in counts.iterrows():
        report_lines.append(
            f"| {theme} | {int(row['review_count'])} "
            f"| {int(row['low_rated'])} |"
        )

    report_lines.extend([
        "",
        "## Top 3 product themes in the classified subset",
        "",
    ])

    for theme, row in product_themes.iterrows():
        report_lines.append(
            f"- **{theme}:** {int(row['review_count'])} classified "
            f"reviews; {int(row['low_rated'])} have ratings of 1–2."
        )

    report_lines.extend([
        "",
        "## Exact customer quote candidates",
        "",
        "Quotes below are copied from the original review text. "
        "Customer allegations are not independently verified.",
        "",
    ])

    for row in selected_quotes:
        report_lines.extend([
            f"### {row['theme']}",
            "",
            f"- Rating: {row['rating']}",
            f"- Date: {row['date']}",
            f"- Review ID: `{row['review_id']}`",
            f"- Exact quote: {row['review_text']}",
            "",
        ])

    report_lines.extend([
        "## Fee-related candidate categories",
        "",
        "| Candidate category | Count |",
        "|---|---:|",
    ])

    for category, count in fee_counts.items():
        report_lines.append(f"| {category} | {int(count)} |")

    report_lines.extend([
        "",
        "**Fee-analysis limitation:** These categories are generated "
        "by keyword-based rules. They are candidates for manual review, "
        "not confirmed counts of fee confusion or billing errors.",
        "",
    ])

    output_file = OUTPUT_DIR / "analysis_summary.md"
    output_file.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print(f"\nSaved report: {output_file}")


if __name__ == "__main__":
    main()
