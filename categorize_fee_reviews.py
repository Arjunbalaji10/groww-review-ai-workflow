
import pandas as pd
import re

INPUT = "data/analysis/fee_candidate_reviews.csv"
OUTPUT = "data/analysis/fee_review_categories.csv"

df = pd.read_csv(INPUT)
text = df["review_text"].fillna("").astype(str).str.lower()

confusion_patterns = [
    r"\bwhy\b.*\b(charge|deduct|money|fee)",
    r"\bnot clear\b",
    r"\bunclear\b",
    r"\bdon't know\b",
    r"\bdo not know\b",
    r"\bwithout (any )?reason\b",
    r"\bcan't explain\b",
    r"\bcannot explain\b",
    r"\bwhat (is|are|was|were)\b.*\b(charge|fee|deduct)",
    r"\bhidden charges?\b",
    r"\bununderstandable\b",
    r"\bnot understand\b",
    r"\bno explanation\b",
]

billing_patterns = [
    r"\bcharged twice\b",
    r"\bdeducted.*\bwithout\b",
    r"\bwrong deduction\b",
    r"\bextra (charge|amount|money)\b",
    r"\bmoney (missing|deducted|gone)\b",
]

def categorize(review):
    if any(re.search(p, review) for p in billing_patterns):
        return "Possible billing dispute"
    if any(re.search(p, review) for p in confusion_patterns):
        return "Possible fee confusion"
    if re.search(
        r"\b(high|too much|expensive|reduce|lower|costly)\b",
        review
    ):
        return "Price dissatisfaction"
    if re.search(
        r"\b(charges|fees|brokerage|deduct|tax)\b",
        review
    ):
        return "Fee mention - needs review"
    return "Unclear"

df["candidate_category"] = text.apply(categorize)

df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

print("Category counts:")
print(df["candidate_category"].value_counts().to_string())

print("\nPossible fee confusion:")
subset = df[df["candidate_category"] == "Possible fee confusion"]

for _, row in subset.head(25).iterrows():
    print(f"\nID: {row['review_id']} | Rating: {row['rating']}")
    print(row["review_text"])

print("\nSaved to:", OUTPUT)
