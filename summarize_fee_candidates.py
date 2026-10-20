
import pandas as pd

INPUT = "data/analysis/fee_review_categories.csv"

df = pd.read_csv(INPUT)

print("Total fee candidates:", len(df))
print("\nCandidate categories:")
print(df["candidate_category"].value_counts().to_string())

print("\nLow-rated fee confusion candidates:")
confusion = df[
    (df["candidate_category"] == "Possible fee confusion")
    & (df["rating"] <= 3)
]

for _, row in confusion.iterrows():
    print(f"\nReview ID: {row['review_id']}")
    print(f"Rating: {row['rating']}")
    print(row["review_text"])

print("\nLow-rated possible billing disputes:")
disputes = df[
    (df["candidate_category"] == "Possible billing dispute")
    & (df["rating"] <= 3)
]

for _, row in disputes.iterrows():
    print(f"\nReview ID: {row['review_id']}")
    print(f"Rating: {row['rating']}")
    print(row["review_text"])
