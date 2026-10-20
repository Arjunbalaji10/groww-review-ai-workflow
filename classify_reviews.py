
import os
import json
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

# Load source reviews and discovered themes
reviews = pd.read_csv("data/reviews_raw.csv")
with open(
    "data/analysis/discovered_themes.json",
    "r",
    encoding="utf-8"
) as file:
    theme_data = json.load(file)

themes = theme_data["themes"]
theme_names = [theme["theme"] for theme in themes]
allowed_labels = theme_names + ["Other"]

# Select 10 informative reviews for the first test
reviews["review_text"] = (
    reviews["review_text"].fillna("").astype(str).str.strip()
)
candidates = reviews[
    reviews["review_text"].str.split().str.len() >= 4
].copy()

test_batch = candidates.sample(
    n=min(10, len(candidates)),
    random_state=42
)

review_payload = [
    {
        "review_id": str(row["review_id"]),
        "rating": int(row["rating"]),
        "review_text": row["review_text"][:400],
    }
    for _, row in test_batch.iterrows()
]

prompt = f"""
Classify each Groww app review into exactly one category.

Available categories:
{json.dumps(allowed_labels, ensure_ascii=False)}

Theme descriptions:
{json.dumps(themes, ensure_ascii=False)}


Rules:
- Understand English, Hindi, Hinglish, and transliterated Indian languages.
- Classify based on actual meaning, not just English keywords.
- If a review describes multiple problems, choose the primary problem.
- Choose Customer Support Issues when delayed or unhelpful support
  is the main complaint.
- Choose Bugs & Crashes only for app malfunctions, errors, or
  unexpected technical behavior.
- Choose Missing Features & Functionality for a clearly requested
  feature or unavailable capability.
- Use Other for generic praise, unclear text, privacy concerns,
  or complaints that do not fit any of the five themes.
- Do not assume allegations in reviews are verified facts.
- Use a theme only when the review supports it.
- Do not rewrite review text or IDs.
- Return valid JSON only in this format:
{{
  "classifications": [
    {{"review_id": "original ID", "theme": "category"}}
  ]
}}

Reviews:
{json.dumps(review_payload, ensure_ascii=False)}
"""

client = Groq(api_key=api_key)
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
    max_tokens=2500,
     response_format={"type": "json_object"},
)

content = response.choices[0].message.content

try:
    result = json.loads(content)
except json.JSONDecodeError:
    print("Invalid JSON returned by Groq:")
    print(content)
    raise

classifications = result.get("classifications", [])

# Validate IDs, labels, and completeness
expected_ids = set(test_batch["review_id"].astype(str))
returned_ids = [str(item.get("review_id", "")) for item in classifications]

if len(returned_ids) != len(expected_ids):
    raise ValueError("Wrong number of classifications returned.")

if set(returned_ids) != expected_ids:
    raise ValueError("Returned review IDs do not match the input batch.")

for item in classifications:
    if item.get("theme") not in allowed_labels:
        raise ValueError(f"Unexpected theme: {item.get('theme')}")

labels = pd.DataFrame(classifications)
labels["review_id"] = labels["review_id"].astype(str)

test_batch["review_id"] = test_batch["review_id"].astype(str)
output = test_batch.merge(
    labels,
    on="review_id",
    how="left",
    validate="one_to_one"
)

os.makedirs("data/analysis", exist_ok=True)
output.to_csv(
    "data/analysis/classification_test.csv",
    index=False,
    encoding="utf-8-sig"
)

print("Classification test completed.")
print("Reviews classified:", len(output))
print("\nTheme counts:")
print(output["theme"].value_counts().to_string())
print("\nSaved to data/analysis/classification_test.csv")
