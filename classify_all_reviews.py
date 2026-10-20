
import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# ---------- Configuration ----------
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

INPUT_FILE = "data/reviews_raw.csv"
THEMES_FILE = "data/analysis/discovered_themes.json"
OUTPUT_FILE = "data/analysis/classified_reviews.csv"

BATCH_SIZE = 20
MAX_RETRIES = 3

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

client = Groq(api_key=API_KEY)


def classify_batch(batch, themes, allowed_labels):
    """Ask Groq to classify one small batch of reviews."""

    review_payload = [
        {
            "review_id": str(row["review_id"]),
            "rating": int(row["rating"]),
            "review_text": str(row["review_text"])[:350],
        }
        for _, row in batch.iterrows()
    ]

    prompt = f"""
Classify every Groww app review into exactly one category.

Available categories:
{json.dumps(allowed_labels, ensure_ascii=False)}

Theme descriptions:
{json.dumps(themes, ensure_ascii=False)}

Rules:
- Understand English, Hindi, Hinglish, and transliterated Indian languages.
- Classify by the actual meaning of the review.
- Choose the primary problem if multiple problems are mentioned.
- Use Customer Support Issues for complaints mainly about delayed or
  unhelpful support.
- Use Bugs & Crashes for clearly described technical malfunctions.
- Use Missing Features & Functionality for requested or unavailable features.
- Use High Fees & Charges only for reviews discussing costs or charges.
- Use Other for praise, unclear text, or issues outside these categories.
- Do not assume allegations are verified facts.
- Do not invent details or rewrite review IDs.
- Return valid JSON only, with this exact structure:
{{
  "classifications": [
    {{"review_id": "original ID", "theme": "category"}}
  ]
}}

Reviews:
{json.dumps(review_payload, ensure_ascii=False)}
"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "Classify reviews using the categories provided. "
                "Return one valid JSON object with a "
                "'classifications' array. Each item must contain "
                "'review_id' and 'theme'. Do not include markdown."
            ),
        },
        {"role": "user", "content": prompt},
    ],
    temperature=0,
    max_tokens=2000,
)

            result = json.loads(
                response.choices[0].message.content
            )
            classifications = result.get("classifications")

            if not isinstance(classifications, list):
                raise ValueError("Missing classifications list.")

            expected_ids = {
                str(value) for value in batch["review_id"].tolist()
            }
            returned_ids = [
                str(item.get("review_id", ""))
                for item in classifications
            ]

            if (
                len(returned_ids) != len(expected_ids)
                or len(set(returned_ids)) != len(returned_ids)
                or set(returned_ids) != expected_ids
            ):
                raise ValueError("Classification IDs are missing or duplicated.")

            for item in classifications:
                if item.get("theme") not in allowed_labels:
                    raise ValueError(
                        f"Unexpected theme: {item.get('theme')}"
                    )

            return classifications

        except Exception as error:
            print(
                f"Batch attempt {attempt}/{MAX_RETRIES} failed: "
                f"{type(error).__name__}: {str(error)[:250]}"
            )
            if attempt == MAX_RETRIES:
                raise
            time.sleep(attempt * 15)


def main():
    os.makedirs("data/analysis", exist_ok=True)

    reviews = pd.read_csv(INPUT_FILE)
    reviews["review_id"] = reviews["review_id"].astype(str)
    reviews["review_text"] = (
        reviews["review_text"].fillna("").astype(str).str.strip()
    )

    with open(THEMES_FILE, "r", encoding="utf-8") as file:
        theme_data = json.load(file)

    themes = theme_data["themes"]
    theme_names = [theme["theme"] for theme in themes]
    allowed_labels = theme_names + ["Other"]

    # Resume from successful batches already saved.
    if os.path.exists(OUTPUT_FILE):
        saved = pd.read_csv(OUTPUT_FILE, dtype={"review_id": str})
        completed_ids = set(saved["review_id"].astype(str))
        print(f"Previously classified: {len(completed_ids)}")
    else:
        saved = pd.DataFrame(
            columns=["review_id", "theme"]
        )
        completed_ids = set()

    remaining = reviews[
        ~reviews["review_id"].isin(completed_ids)
    ].copy()

    total_remaining = len(remaining)
    print("Total reviews:", len(reviews))
    print("Already classified:", len(completed_ids))
    print("Remaining:", total_remaining)

    if total_remaining == 0:
        print("All reviews are already classified.")
        return

    for start in range(0, total_remaining, BATCH_SIZE):
        batch = remaining.iloc[start:start + BATCH_SIZE]

        classifications = classify_batch(
            batch, themes, allowed_labels
        )

        new_rows = pd.DataFrame(classifications)
        new_rows["review_id"] = new_rows["review_id"].astype(str)

        # Append only after a whole batch passes validation.
        write_header = not os.path.exists(OUTPUT_FILE)
        new_rows.to_csv(
            OUTPUT_FILE,
            mode="a",
            header=write_header,
            index=False,
            encoding="utf-8-sig" if write_header else "utf-8",
        )

        processed = min(start + len(batch), total_remaining)
        print(
            f"Saved batch: {processed}/{total_remaining} remaining reviews"
        )

        # Brief pause between requests.
        time.sleep(2)

    print("\nClassification processing finished.")
    print("Output:", OUTPUT_FILE)

    # Report counts from the saved classifications.
    final_results = pd.read_csv(
        OUTPUT_FILE, dtype={"review_id": str}
    )
    print("\nTheme counts:")
    print(final_results["theme"].value_counts().to_string())


if __name__ == "__main__":
    main()
