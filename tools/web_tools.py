import requests
import re
import os
from urllib.parse import quote
from tools.registry import tool
from config import WEATHER_DEFAULT_CITY
from todoist_api_python.api import TodoistAPI
from dotenv import load_dotenv

load_dotenv()


def _resolve_weather_city(city):
    text = (city or "").strip()
    lowered = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    lowered = re.sub(r"\s+", " ", lowered).strip()

    if not lowered:
        return WEATHER_DEFAULT_CITY

    generic_tokens = {
        "weather", "current", "now", "today", "what", "is", "the", "in", "at", "for"
    }
    words = [w for w in lowered.split() if w]

    # Generic requests like "what is the current weather" should use configured default city.
    if words and all(w in generic_tokens for w in words):
        return WEATHER_DEFAULT_CITY

    if lowered in {"current", "current weather", "weather now", "weather"}:
        return WEATHER_DEFAULT_CITY

    return text

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
    requested_city = _resolve_weather_city(city)
    candidates = [requested_city]
    if requested_city.lower() != WEATHER_DEFAULT_CITY.lower():
        candidates.append(WEATHER_DEFAULT_CITY)

    for candidate in candidates:
        try:
            city_query = quote(candidate)
            url = f"https://wttr.in/{city_query}?format=j1"

            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            current = data["current_condition"][0]

            return {
                "city": candidate,
                "temperature_c": current["temp_C"],
                "feels_like_c": current["FeelsLikeC"],
                "description": current["weatherDesc"][0]["value"],
                "humidity": current["humidity"],
                "wind_kmph": current["windspeedKmph"],
            }
        except requests.exceptions.RequestException:
            continue
        except (KeyError, IndexError, ValueError):
            continue

    return {"error": "Unable to fetch weather data."}



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
        t_words = set(text.lower().split())  # FIXED
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

        # Extract answer
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

            # skip bad sentences
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


API_KEY = (os.getenv("TODOIST_API_KEY") or "").strip()
api = TodoistAPI(API_KEY) if API_KEY else None


def _get_todoist_client():
    if api is None:
        return None, "TODOIST_API_KEY is not configured in environment."
    return api, None


def _normalize_tasks(raw_tasks):
    tasks = []
    for item in raw_tasks:
        if isinstance(item, list):
            tasks.extend(item)
        else:
            tasks.append(item)
    return tasks


@tool(
    name='add_task',
    description="Add a task to Todoist",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "due_date": {
                "type": "string",
                "description": "Natural language date like 'tomorrow 6pm'"
            }
        },
        "required": ["title"]
    }
)

def add_task(title, due_date=None):
    client, error = _get_todoist_client()
    if client is None:
        return error or "TODOIST_API_KEY is not configured in environment."

    try:
        task = client.add_task(
            content=title,
            due_string=due_date if due_date else None
        )
        return f"Task added: {task.content}"
    except Exception as e:
        return f"Error adding task: {e}"


@tool(
    name="list_task",
    description="List active tasks",
    parameters={"type": "object", "properties": {}}
)
def list_task():
    client, error = _get_todoist_client()
    if client is None:
        return error or "TODOIST_API_KEY is not configured in environment."

    try:
        tasks = _normalize_tasks(client.get_tasks())
        if not tasks:
            return "No tasks found"
        output = []
        for t in tasks[:10]:
            output.append(f"- {t.content}")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing tasks: {e}"
    
@tool(
    name="complete_task",
    description="Mark a task as completed",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"}
        },
        "required": ["title"]
    }
)
def complete_task(title):
    client, error = _get_todoist_client()
    if client is None:
        return error or "TODOIST_API_KEY is not configured in environment."

    try:
        tasks = _normalize_tasks(client.get_tasks())

        for t in tasks:
            if t.content.lower() == title.lower():
                complete_fn = getattr(client, "close_task", None) or getattr(client, "complete_task", None)
                if not callable(complete_fn):
                    return "Error completing task: Todoist client does not support task completion."
                complete_fn(t.id)
                return f"Task completed: {title}"

        return "Task not found."
    except Exception as e:
        return f"Error completing task: {e}"


# if __name__ == "__main__":
#     print(search_web("what is the name of the player, who wins the orange cap in IPL 2018?"))