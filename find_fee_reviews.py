
import pandas as pd
import re

INPUT_FILE = "data/reviews_raw.csv"
OUTPUT_FILE = "data/analysis/fee_candidate_reviews.csv"

df = pd.read_csv(INPUT_FILE)
df["review_text"] = df["review_text"].fillna("").astype(str)

# Find possible fee-related reviews in the original dataset.
fee_pattern = re.compile(
    r"\b("
    r"brokerage|charges?|charged|charging|"
    r"fees?|deduct(?:ed|ion|ions)?|"
    r"hidden charges?|transaction charge|"
    r"extra amount|money deducted|"
    r"broker fee|platform fee"
    r")\b",
    flags=re.IGNORECASE,
)

matches = df[df["review_text"].apply(
    lambda text: bool(fee_pattern.search(text))
)].copy()

# Keep original reviews and identifiers unchanged.
matches.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("Total original reviews:", len(df))
print("Potential fee-related reviews:", len(matches))
print("Saved to:", OUTPUT_FILE)

print("\nSample of up to 40 candidate reviews:\n")

for _, row in matches.head(40).iterrows():
    print(
        f"ID: {row['review_id']} | Rating: {row['rating']}\n"
        f"{row['review_text']}\n"
    )
