import requests
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
        # fallback if city is empty or current
        if not city or city.lower() == "current":
            city = ""  # wttr.in auto-detects location

        url = f"https://wttr.in/{city}?format=j1"

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        current = data['current_condition'][0]

        # structured output
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
    description="Search the web for latest information. Call when user asks for current news, latest updates, or real-time info.",
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

    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        limit = 5

    limit = max(1, min(limit, 10))

    try:
        output = []
        with DDGS() as ddgs:
            for row in ddgs.text(query, max_results=limit):
                output.append({
                    "title": row.get("title", ""),
                    "url": row.get("href", ""),
                    "snippet": row.get("body", "")
                })

        return {
            "query": query,
            "results": output
        }
    except Exception as e:
        return {"error": f"Web search failed: {e}"}
