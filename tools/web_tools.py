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