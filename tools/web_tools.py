import requests
import re
import os
from datetime import date
from urllib.parse import quote
from bs4 import BeautifulSoup
from tools.registry import tool
from config import WEATHER_DEFAULT_CITY
from todoist_api_python.api import TodoistAPI
from dotenv import load_dotenv

load_dotenv()

# Stopwords to exclude from relevance scoring
_STOPWORDS = {
    "what", "is", "the", "a", "an", "are", "was", "were", "which", "who",
    "how", "when", "where", "now", "in", "at", "on", "for", "of", "to",
    "and", "or", "my", "me", "i", "it", "this", "that", "do", "did", "will",
    "about", "with", "by", "from", "as", "be", "been", "have", "has",
}

# Keywords that indicate the query needs today's date injected.
# ONLY explicit time-reference words trigger this — NOT topic words like
# 'ipl', 'cricket', 'score' (those cause false injections for general queries).
_DATE_INJECT_KEYWORDS = [
    "today", "tonight", "this week", "this month", "right now",
    "latest", "current", "live", "schedule", "fixture", "upcoming",
    "yesterday", "tomorrow", "now",
]

# Domains to SKIP when fetching page content (evergreen, generic, JS-heavy)
_SKIP_FETCH_DOMAINS = {
    "wikipedia.org", "youtube.com", "youtu.be", "reddit.com",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "google.com", "bing.com", "amazon.com",
}

# JS-heavy / API-rendered sites where the DDG snippet is more reliable than
# a raw page fetch. We use the snippet directly for these domains.
_USE_SNIPPET_DOMAINS = {
    # Cricket
    "cricbuzz.com", "espncricinfo.com", "iplt20.com", "bcci.tv",
    # Sports
    "espn.com", "sports.ndtv.com", "skysports.com",
    # Finance
    "coinmarketcap.com", "finance.yahoo.com", "investing.com",
    # News
    "reuters.com", "bbc.com", "apnews.com",
    # Tech
    "techcrunch.com", "theverge.com", "wired.com",
}

# Domain-based score boost for authoritative / structured sources.
# Kept broad — not cricket-only — so any domain search works well.
_DOMAIN_BOOST = {
    # Cricket
    "cricbuzz.com": 5, "espncricinfo.com": 5, "iplt20.com": 5,
    # General sports
    "espn.com": 4, "skysports.com": 4, "ndtvsports.com": 4,
    # Finance
    "coinmarketcap.com": 4, "investing.com": 3, "reuters.com": 4,
    # News
    "bbc.com": 4, "apnews.com": 4, "theguardian.com": 3,
    "ndtv.com": 3, "thehindu.com": 3, "indiatoday.in": 3,
    # Tech
    "techcrunch.com": 4, "theverge.com": 4, "wired.com": 3,
    # Entertainment
    "variety.com": 3, "hollywoodreporter.com": 3, "deadline.com": 3,
    # Science/Space
    "nasa.gov": 4, "spacex.com": 4, "space.com": 3,
}


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
            },
            "site": {
                "type": "string",
                "description": "Optional site or domain to prefer, such as iplt20.com"
            }
        },
        "required": ["query"]
    }
)
def search_web(query, max_results=5, site=None, **kwargs):
    if not query or not str(query).strip():
        return {"error": "Query cannot be empty."}

    site = (site or kwargs.get("domain") or kwargs.get("url") or "").strip()
    search_query = str(query).strip()

    # Inject today's date for time-sensitive queries so the search engine
    # returns fresh, dated results instead of evergreen/generic pages.
    today_str = date.today().strftime("%B %d %Y")   # e.g. "April 25 2026"
    current_year = str(date.today().year)            # e.g. "2026"
    lower_q = search_query.lower()
    needs_date = any(kw in lower_q for kw in _DATE_INJECT_KEYWORDS)
    # Only inject if the date isn't already in the query (avoid "2026 April 25 2026")
    already_dated = today_str in search_query or current_year in search_query
    if needs_date and not already_dated:
        search_query = f"{search_query} {today_str}"

    if site:
        site = site.replace("https://", "").replace("http://", "").strip("/")
        search_query = f"{search_query} site:{site}"

    try:
        from ddgs import DDGS
    except ImportError:
        return {"error": "ddgs is not installed. Run: pip install ddgs"}

    def _score_result(query, text):
        """Score relevance ignoring stopwords so common English words
        don't accidentally boost wrong results."""
        q_words = {w for w in query.lower().split() if w not in _STOPWORDS}
        t_words = set(text.lower().split())
        return len(q_words & t_words)

    def _clean_text(text):
        return re.sub(r"\s+", " ", text or "").strip()

    def _fetch_page_text(url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "header", "footer", "aside"]):
            tag.decompose()

        title = _clean_text(soup.title.get_text()) if soup.title else ""
        body = soup.find("article") or soup.find("main") or soup.body or soup
        lines = []
        seen = set()

        for raw_line in body.get_text("\n").splitlines():
            line = _clean_text(raw_line)
            if not line or len(line) < 30:
                continue
            if line in seen:
                continue
            seen.add(line)
            lines.append(line)

        content = "\n".join(lines[:80])
        return {
            "title": title,
            "content": content,
            "url": response.url or url,
            "has_content": bool(content.strip()),
        }

    import time

    def _ddgs_search(search_query, max_results):
        """Run DDGS text search with up to 3 retries on transient network errors."""
        last_error = None
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(search_query, max_results=max(max_results, 5)))
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(1.2)   # brief pause before retry
        raise last_error

    try:
        results = []
        raw_rows = _ddgs_search(search_query, max_results)

        for row in raw_rows:
            title = row.get("title", "")
            snippet = row.get("body", "")
            url = row.get("href", "")

            # Score uses the ORIGINAL query keywords (not date suffix)
            # so injected words like "April" don't distort ranking.
            combined = f"{title} {snippet}"
            score = _score_result(query, combined)

            # Boost for authoritative domains across all topics
            for domain, boost in _DOMAIN_BOOST.items():
                if domain in url:
                    score += boost
                    break

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

        # Build enriched results. For JS-heavy sports sites, use the DDG snippet
        # directly since page fetch returns minimal content. For other sites,
        # try fetching the page for richer content.
        fetched = None
        top_result = results[0]  # default

        for candidate in results[:5]:
            url = candidate["url"]
            # Use snippet directly for JS-heavy sports sites
            if any(d in url for d in _USE_SNIPPET_DOMAINS):
                fetched = {
                    "title": candidate.get("title", ""),
                    "content": candidate.get("snippet", ""),
                    "url": url,
                    "has_content": bool(candidate.get("snippet", "").strip()),
                }
                top_result = candidate
                break

            # Skip known bad/evergreen domains
            if any(skip in url for skip in _SKIP_FETCH_DOMAINS):
                continue

            try:
                page = _fetch_page_text(url)
                if page.get("has_content"):
                    fetched = page
                    top_result = candidate
                    break
            except Exception:
                continue

        if fetched is None:
            # All page fetches failed or skipped — fall back to best snippet
            top_result = results[0]
            fetched = {
                "title": top_result.get("title", ""),
                "content": top_result.get("snippet", ""),
                "url": top_result.get("url", ""),
            }

        enriched_results = [{
            "score": top_result["score"],
            "title": fetched.get("title") or top_result.get("title", ""),
            "snippet": fetched.get("content") or top_result.get("snippet", ""),
            "content": fetched.get("content", ""),
            "url": fetched.get("url") or top_result.get("url", ""),
        }]

        # Include remaining snippets so LLM has maximum context
        for r in results:
            if r is top_result:
                continue
            enriched_results.append({
                "score": r["score"],
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "content": r.get("snippet", ""),
                "url": r.get("url", ""),
            })

        # Extract answer
        answer = extract_answer(query, enriched_results)

        return {
            "query": search_query,
            "answer": answer,
            "raw": enriched_results
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
        text = r.get("content") or r.get("snippet", "")
        sentences = re.split(r'(?<=[.!?])\s+', text)

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

            # boost correct year (current year wins)
            current_year = str(date.today().year)
            if current_year in s_lower:
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