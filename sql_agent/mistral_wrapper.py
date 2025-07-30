import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")

def run_mistral(prompt: str) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "mistral-large-latest",  # change if using another
        "messages": [
            {"role": "system", "content": "You are an expert SQL assistant.You recieve requests for data and You only answer with valid SQL code."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    res = requests.post(url, headers=headers, json=body)
    res.raise_for_status()
    reply = res.json()["choices"][0]["message"]["content"]
    return reply.strip()
