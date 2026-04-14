import requests
import json
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class LLMClient:
    def __init__(self):
        self.url = f"{OLLAMA_BASE_URL}/api/chat"
        self.model = OLLAMA_MODEL

    def _build_payload(self, messages, stream=False, **kwargs):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        payload.update(kwargs)
        return payload

    def generate(self, messages, timeout=120):
        try:
            payload = self._build_payload(messages, stream=False)
            payload['options'] = {
                'num_ctx': 1024, # smaller context window -> less RAM
                'num_predict': 256 # limit reponse length
            }
            response = requests.post(
                self.url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
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
            payload = self._build_payload(messages, stream=True)
            response = requests.post(
                self.url,
                json=payload,
                stream=True
            )
            response.raise_for_status()

            full_response = ""

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
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

