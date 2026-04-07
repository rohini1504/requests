import os
import requests
import time

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

class LLMError(Exception):
    pass


def call_llm(prompt, system_prompt=None, model="llama-3.1-8b-instant", max_retries=3):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise LLMError("Missing GROQ_API_KEY")

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    for attempt in range(max_retries):
        try:
            response = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3
                },
                timeout=15
            )

            if response.status_code != 200:
                raise LLMError(f"HTTP {response.status_code}: {response.text}")

            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise LLMError(f"Invalid response: {data}")

            return data["choices"][0]["message"]["content"]

        except Exception as e:
            if attempt == max_retries - 1:
                return f"LLM ERROR: {str(e)}"

            time.sleep(2 ** attempt)  # exponential backoff
