
import pandas as pd

reviews = pd.read_csv("data/reviews_raw.csv")
classified = pd.read_csv(
    "data/analysis/classified_reviews.csv",
    dtype={"review_id": str}
)

reviews["review_id"] = reviews["review_id"].astype(str)

other_ids = set(
    classified.loc[classified["theme"] == "Other", "review_id"]
)

other_reviews = reviews[reviews["review_id"].isin(other_ids)]

print("Total classified as Other:", len(other_reviews))
print("\nSample of 30 reviews labelled Other:\n")

sample = other_reviews.sample(
    n=min(30, len(other_reviews)),
    random_state=42
)

for _, row in sample.iterrows():
    print(f"Rating: {row['rating']} | {row['review_text']}\n")
