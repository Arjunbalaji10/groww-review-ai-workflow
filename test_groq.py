
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not api_key:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

try:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Reply with exactly: Groq connection successful"}
        ],
        temperature=0,
        max_tokens=30,
    )

    print("Connection successful!")
    print("Model:", model)
    print("Response:", response.choices[0].message.content)

except Exception as error:
    print("Groq connection failed.")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error)[:500])
