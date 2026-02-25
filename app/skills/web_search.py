"""ArcHillx — Web Search Skill (DuckDuckGo)"""
from __future__ import annotations


def run(inputs: dict) -> dict:
    query = inputs.get("query") or inputs.get("command", "")
    if not query:
        return {"error": "query required", "results": []}
    max_results = int(inputs.get("max_results", 5))
    results = []
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {"error": "Install ddgs: pip install ddgs", "results": []}
    try:
        with DDGS() as d:
            for r in d.text(query, max_results=max_results):
                results.append({"title": r.get("title", ""),
                                 "url": r.get("href", ""),
                                 "snippet": r.get("body", "")})
    except Exception as e:
        return {"error": str(e), "results": []}
    return {"results": results, "count": len(results), "query": query}
