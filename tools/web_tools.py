import requests
import re
from tools.registry import tool

@tool(
    name="get_weather",
    description="Call when user asks about weather in a city.",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Name of the city"
            }
        },
        "required": ["city"]
    }
)
def get_weather(city):
    try:
        if not city or city.lower() == "current":
            city = ""

        url = f"https://wttr.in/{city}?format=j1"

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        current = data['current_condition'][0]

        return {
            "city": city if city else "current location",
            "temperature_c": current["temp_C"],
            "feels_like_c": current["FeelsLikeC"],
            "description": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
            "wind_kmph": current["windspeedKmph"]
        }

    except requests.exceptions.RequestException:
        return {"error": "Unable to fetch weather data."}
    except (KeyError, IndexError):
        return {"error": "Unexpected response format."}



@tool(
    name="search_web",
    description="Search the web for latest information.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1-10)"
            }
        },
        "required": ["query"]
    }
)
def search_web(query, max_results=5):
    if not query or not str(query).strip():
        return {"error": "Query cannot be empty."}

    try:
        from ddgs import DDGS
    except ImportError:
        return {"error": "ddgs is not installed. Run: pip install ddgs"}

    def _score_result(query, text):
        q_words = set(query.lower().split())
        t_words = set(text.lower().split())  # ✅ FIXED
        return len(q_words & t_words)

    try:
        results = []

        with DDGS() as ddgs:
            for row in ddgs.text(query, max_results=max_results):
                title = row.get("title", "")
                snippet = row.get("body", "")
                url = row.get("href", "")

                combined = f"{title} {snippet}"
                score = _score_result(query, combined)

                if len(snippet) > 30:
                    results.append({
                        "score": score,
                        "title": title,
                        "snippet": snippet,
                        "url": url
                    })

        if not results:
            return {
                "query": query,
                "answer": None,
                "raw": []
            }

        results.sort(key=lambda x: x["score"], reverse=True)

        raw_results = results[:5]

        # 🔥 Extract answer
        answer = extract_answer(query, raw_results)

        return {
            "query": query,
            "answer": answer,
            "raw": raw_results[:3]
        }

    except Exception as e:
        return {"error": f"Web search failed: {e}"}

def extract_answer(query, results):
    query_lower = query.lower()

    priority_patterns = [
        r"\bwas\b",
        r"\bis\b",
        r"\bwon\b",
        r"\bwinner\b"
    ]

    candidates = []

    for r in results:
        snippet = r.get("snippet", "")
        sentences = re.split(r'(?<=[.!?])\s+', snippet)

        for s in sentences:
            s_lower = s.lower()

            # ❌ skip bad sentences
            if s.strip().endswith("?"):
                continue

            if "is awarded" in s_lower or "is handed" in s_lower:
                continue

            score = 0

            # boost answer patterns
            for p in priority_patterns:
                if re.search(p, s_lower):
                    score += 3

            # keyword match
            score += sum(1 for word in query_lower.split() if word in s_lower)

            # boost names
            if re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", s):
                score += 2

            # boost correct year
            if "2025" in s_lower:
                score += 2

            candidates.append((score, s.strip()))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)

    best = candidates[0][1]

    # clean date prefix
    best = re.sub(r'^[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\s+·\s+', '', best)

    return best

if __name__ == "__main__":
    print(search_web("what is the name of the player, who wins the orange cap in IPL 2018?"))