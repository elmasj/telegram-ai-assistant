import os
from tavily import TavilyClient

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return _client


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web and return a list of results with title, url, content."""
    client = _get_client()
    response = client.search(query, max_results=max_results, include_raw_content=False)
    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        })
    return results


def read_url(url: str) -> str:
    """Fetch and return the readable text content of a webpage."""
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (compatible; PersonalAssistant/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Trim to ~8000 chars to stay within context limits
        return text[:8000]
    except Exception as e:
        return f"Error fetching URL: {e}"
