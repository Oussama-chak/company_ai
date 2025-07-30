# shared/mistral_wrapper.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY not found. Please check your .env file.")

def run_mistral(prompt: str) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "system", "content": "You are an expert SQL assistant. You receive requests for data and you only answer with valid SQLite SQL code. Do not provide any text other than the SQL query itself."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0
    }

    try:
        res = requests.post(url, headers=headers, json=body)
        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"]
        return reply.strip()
    except requests.exceptions.HTTPError as e:
        print(f"Mistral API Error: {e.response.text}")
        raise