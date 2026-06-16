import requests
import json
from config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
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
        elif self.provider == "gemini":
            self.url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent"
            self.model = GEMINI_MODEL
            self.headers = {"Content-Type": "application/json"}
        else:
            self.url = f"{OLLAMA_BASE_URL}/api/chat"
            self.model = OLLAMA_MODEL
            self.headers = None

    def _normalize_messages(self, messages):
        if self.provider != "gemini":
            return messages

        gemini_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            gemini_role = "model" if role == "assistant" else "user"
            gemini_messages.append({
                "role": gemini_role,
                "parts": [{"text": content}],
            })
        return gemini_messages

    def _build_payload(self, messages, stream=False, **kwargs):
        if self.provider == "gemini":
            payload = {
                "contents": self._normalize_messages(messages),
            }
            payload.update(kwargs)
            return payload

        payload = {"model": self.model, "messages": self._normalize_messages(messages), "stream": stream}
        payload.update(kwargs)
        return payload

    def _parse_groq_response(self, response):
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _parse_gemini_response(self, response):
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    def _gemini_model_candidates(self):
        # Ordered by preference: configured model first, then fallbacks.
        # gemini-1.5-flash-latest is DEPRECATED (returns 404) — excluded.
        ordered = [
            self.model,
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]
        unique = []
        for name in ordered:
            if name and name not in unique:
                unique.append(name)
        return unique

    def _generate_with_groq_fallback(self, messages, timeout):
        if not GROQ_API_KEY:
            return ""

        payload = {"model": GROQ_MODEL, "messages": messages, "stream": False}
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{GROQ_BASE_URL}/chat/completions"

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return self._parse_groq_response(response)
        except Exception:
            return ""

    def _generate_with_ollama_fallback(self, messages, timeout):
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "num_predict": 256,
            },
        }

        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception:
            return ""

    def generate(self, messages, timeout=120):
        try:
            if self.provider == "groq" and not GROQ_API_KEY:
                return "Error: GROQ_API_KEY is not set."
            if self.provider == "gemini" and not GEMINI_API_KEY:
                return "Error: GEMINI_API_KEY is not set."

            payload = self._build_payload(messages, stream=False)
            if self.provider == "ollama":
                payload["options"] = {
                    "num_ctx": 1024,  # smaller context window -> less RAM
                    "num_predict": 256,  # limit response length
                }

            if self.provider == "gemini":
                last_err = None
                for model_name in self._gemini_model_candidates():
                    request_url = f"{GEMINI_BASE_URL}/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                    response = requests.post(request_url, json=payload, headers=self.headers, timeout=timeout)
                    if response.status_code == 429:
                        groq_text = self._generate_with_groq_fallback(messages, timeout)
                        if groq_text:
                            return groq_text

                        ollama_text = self._generate_with_ollama_fallback(messages, timeout)
                        if ollama_text:
                            return ollama_text

                        last_err = response
                        continue
                    if response.status_code == 404:
                        last_err = response
                        continue
                    response.raise_for_status()
                    self.model = model_name
                    self.url = f"{GEMINI_BASE_URL}/models/{self.model}:generateContent"
                    return self._parse_gemini_response(response)

                if last_err is not None:
                    last_err.raise_for_status()
                return "Error: No supported Gemini model was accepted by the API."

            request_url = self.url
            response = requests.post(request_url, json=payload, headers=self.headers, timeout=timeout)
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
            if self.provider == "gemini" and not GEMINI_API_KEY:
                print("Error: GEMINI_API_KEY is not set.")
                return ""

            if self.provider == "gemini":
                # Fallback to non-streamed Gemini response to keep the existing interface stable.
                full_response = self.generate(messages)
                print(full_response)
                return full_response

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

