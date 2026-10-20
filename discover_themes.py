
import os
import json
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# 1. Load configuration
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

# 2. Load reviews
df = pd.read_csv("data/reviews_raw.csv")
df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()

# 3. Remove low-information reviews for theme discovery only.
# Keep the original CSV unchanged.
generic_reviews = {
    "good", "good app", "nice", "nice app", "excellent",
    "outstanding", "super", "best app", "very good",
    "ok", "okay", "worst", "bad", "good 😊👍"
}

candidates = df[
    (df["review_text"].str.split().str.len() >= 4)
    & (~df["review_text"].str.lower().isin(generic_reviews))
].copy()

if len(candidates) < 20:
    raise ValueError("Not enough informative reviews for theme discovery.")

# 4. Select a reproducible sample, balancing ratings.
# This helps avoid discovering themes only from 5-star reviews.
sample_parts = []

for rating, group in candidates.groupby("rating"):
    sample_parts.append(
        group.sample(n=min(30, len(group)), random_state=42)
    )

sample = pd.concat(sample_parts).sample(frac=1, random_state=42)
sample = sample.head(60)

# 5. Ask Groq to discover up to five themes.
review_lines = []
for _, row in sample.iterrows():
    review_lines.append(
        f"ID: {row['review_id']} | Rating: {row['rating']} | "
        f"Review: {row['review_text'][:250]}"
    )

prompt = f"""
You are analysing customer reviews of the Groww investment app.

Discover at most five recurring product-feedback themes from the
reviews below.

Rules:
- Use only themes supported by these reviews.
- Give each theme a short, distinct name.
- Explain what customer problem or experience it represents.
- Do not invent counts, quotes, or causes.
- Do not treat generic praise such as "good app" as a useful theme.
- If a theme has little evidence, omit it.
- Return valid JSON only, using this structure:
{{
  "themes": [
    {{
      "theme": "Short name",
      "description": "What these reviews indicate",
      "keywords": ["keyword1", "keyword2"]
    }}
  ]
}}

Reviews:
{chr(10).join(review_lines)}
"""

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
    max_tokens=1500,
)

content = response.choices[0].message.content

# 6. Parse and validate the AI response.
# If parsing fails, print the response so we can debug it.
try:
    result = json.loads(content)
except json.JSONDecodeError:
    print("Groq did not return valid JSON. Raw response:")
    print(content)
    raise

themes = result.get("themes", [])

if not isinstance(themes, list) or len(themes) > 5:
    raise ValueError("Expected a list containing at most five themes.")

os.makedirs("data/analysis", exist_ok=True)

with open("data/analysis/discovered_themes.json", "w", encoding="utf-8") as file:
    json.dump(result, file, indent=2, ensure_ascii=False)

print("Theme discovery completed.")
print("Candidate reviews:", len(candidates))
print("Sample reviewed by AI:", len(sample))
print("Themes discovered:", len(themes))

for index, theme in enumerate(themes, start=1):
    print(f"\n{index}. {theme['theme']}")
    print(theme["description"])
    print("Keywords:", ", ".join(theme.get("keywords", [])))

print("\nSaved to data/analysis/discovered_themes.json")
