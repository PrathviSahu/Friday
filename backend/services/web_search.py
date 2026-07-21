"""
FRIDAY Web Search Service
Performs quick instant answer & web snippet searches via DuckDuckGo HTML/Lite without external API keys.
"""
import urllib.request
import urllib.parse
import re
from html import unescape


def search_web_instant(query: str) -> dict:
    """Search DuckDuckGo and return top 3 instant snippet results."""
    q = query.strip()
    if not q:
        return {"query": "", "results": []}

    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract snippets from DuckDuckGo HTML results
        snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles = re.findall(r'<a class="result__url[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)

        results = []
        for i in range(min(4, len(snippets))):
            clean_snip = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            clean_title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "Result"
            clean_snip = unescape(clean_snip)
            clean_title = unescape(clean_title)
            if clean_snip:
                results.append({"title": clean_title, "snippet": clean_snip})

        return {"query": q, "results": results}
    except Exception as e:
        print(f"[WebSearch] Search failed for '{q}': {e}")
        return {
            "query": q,
            "results": [
                {
                    "title": "Search Query",
                    "snippet": f"Could not fetch live search results for '{q}'. Please check network connection."
                }
            ]
        }
