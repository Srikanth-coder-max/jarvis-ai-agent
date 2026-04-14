import requests
import json
from config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)


class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        if self.provider == "groq":
            self.url = f"{GROQ_BASE_URL}/chat/completions"
            self.model = GROQ_MODEL
            self.headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
        else:
            self.url = f"{OLLAMA_BASE_URL}/api/chat"
            self.model = OLLAMA_MODEL
            self.headers = None

    def _normalize_messages(self, messages):
        return messages

    def _build_payload(self, messages, stream=False, **kwargs):
        payload = {"model": self.model, "messages": self._normalize_messages(messages), "stream": stream}
        payload.update(kwargs)
        return payload

    def _parse_groq_response(self, response):
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def generate(self, messages, timeout=120):
        try:
            if self.provider == "groq" and not GROQ_API_KEY:
                return "Error: GROQ_API_KEY is not set."

            payload = self._build_payload(messages, stream=False)
            if self.provider == "ollama":
                payload["options"] = {
                    "num_ctx": 1024,  # smaller context window -> less RAM
                    "num_predict": 256,  # limit response length
                }

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=timeout)
            response.raise_for_status()

            if self.provider == "groq":
                return self._parse_groq_response(response)

            data = response.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.Timeout:
            return "Error: The request timed out."
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to the server. Is it running?"
        except requests.exceptions.HTTPError as err:
            return f"Error: HTTP error occured: {err}"
        except Exception as e:
            return f"An unexpected error occured: {e}"

    def stream(self, messages):
        try:
            if self.provider == "groq" and not GROQ_API_KEY:
                print("Error: GROQ_API_KEY is not set.")
                return ""

            payload = self._build_payload(messages, stream=True)
            if self.provider == "groq":
                payload["stream"] = True

            response = requests.post(self.url, json=payload, headers=self.headers, stream=True)
            response.raise_for_status()

            full_response = ""

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if self.provider == "groq":
                        if decoded.startswith("data: "):
                            decoded = decoded.removeprefix("data: ").strip()
                        if decoded == "[DONE]":
                            break
                        chunk = json.loads(decoded)
                        token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    else:
                        chunk = json.loads(decoded)
                        token = chunk.get("message", {}).get("content", "")
                    print(token, end="", flush=True)
                    full_response += token
            print()
            return full_response
        except Exception as e:
            print(f"\nStreaming error:{e}")
            return ""


if __name__ == "__main__":
    client = LLMClient()

