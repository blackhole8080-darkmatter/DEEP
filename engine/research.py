# deep/research.py — Web Research & Lookup (Bible Section 26.3)
"""DuckDuckGo search, webpage fetch, Wikipedia, arXiv, weather, currency,
news. All network features are optional/guarded so the module imports offline."""
from __future__ import annotations

import re


class ResearchEngine:
    def __init__(self, config=None):
        self.config = config

    def web_search(self, query, n_results=8) -> dict:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=n_results))
            results = [{"title": h.get("title"), "url": h.get("href"),
                        "snippet": h.get("body", "")[:200]} for h in hits]
            top = results[0]["title"] if results else "no results"
            return {"results": results, "result": len(results),
                    "verbal": f"Top result for '{query}': {top}, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None,
                    "verbal": f"Web search needs duckduckgo-search + network, sir: {e}"}

    def wikipedia_lookup(self, query, sentences=4) -> dict:
        try:
            import wikipediaapi
            wiki = wikipediaapi.Wikipedia(user_agent="DEEP/3.0", language="en")
            page = wiki.page(query)
            if not page.exists():
                return {"result": None, "verbal": f"No Wikipedia article for '{query}', sir."}
            summary = " ".join(page.summary.split(". ")[:sentences])
            return {"title": page.title, "summary": summary, "url": page.fullurl,
                    "result": summary[:200],
                    "verbal": f"{page.title}: {summary[:200]}"}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Wikipedia lookup needs wikipedia-api, sir: {e}"}

    def arxiv_search(self, query, max_results=5) -> dict:
        try:
            import arxiv
            search = arxiv.Search(query=query, max_results=max_results,
                                  sort_by=arxiv.SortCriterion.Relevance)
            papers = []
            for r in search.results():
                papers.append({"title": r.title, "authors": [a.name for a in r.authors][:3],
                               "pdf_url": r.pdf_url, "date": str(r.published.date())})
            top = papers[0]["title"] if papers else "no papers"
            return {"papers": papers, "result": len(papers),
                    "verbal": f"Found {len(papers)} arXiv papers; top: {top}, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"arXiv search needs the arxiv package, sir: {e}"}

    def weather(self, location, units="metric") -> dict:
        try:
            import requests
            geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                               params={"name": location, "count": 1}, timeout=8).json()
            if not geo.get("results"):
                return {"result": None, "verbal": f"Could not find {location}, sir."}
            lat = geo["results"][0]["latitude"]; lon = geo["results"][0]["longitude"]
            w = requests.get("https://api.open-meteo.com/v1/forecast",
                             params={"latitude": lat, "longitude": lon,
                                     "current_weather": True}, timeout=8).json()
            cw = w.get("current_weather", {})
            return {"current": cw, "result": cw,
                    "verbal": f"{location}: {cw.get('temperature')}°C, "
                              f"wind {cw.get('windspeed')} km/h, sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Weather needs network, sir: {e}"}

    def currency_convert(self, amount, from_ccy, to_ccy) -> dict:
        try:
            import requests
            r = requests.get(f"https://open.er-api.com/v6/latest/{from_ccy.upper()}",
                             timeout=8).json()
            rate = r["rates"][to_ccy.upper()]
            return {"result": amount * rate, "rate": rate,
                    "verbal": f"{amount} {from_ccy.upper()} = "
                              f"{amount*rate:.2f} {to_ccy.upper()} (rate {rate:.4f}), sir."}
        except Exception as e:  # noqa: BLE001
            return {"result": None, "verbal": f"Currency conversion needs network, sir: {e}"}

    def test(self) -> None:
        # offline: methods must return a dict without raising
        assert isinstance(self.web_search("test"), dict)
        assert isinstance(self.arxiv_search("test"), dict)
        print("research.ResearchEngine: OK")


_engine = ResearchEngine()


def search(text: str) -> dict:
    payload = re.sub(r"^.*?(search web|look up|who is|wikipedia)\b[:,]?\s*",
                     "", text, flags=re.I).strip() or text
    if "wikipedia" in text.lower():
        return _engine.wikipedia_lookup(payload)
    return _engine.web_search(payload)


def arxiv(text: str) -> dict:
    payload = re.sub(r"^.*?(arxiv|research paper|scientific paper)\b[:,]?\s*",
                     "", text, flags=re.I).strip() or text
    return _engine.arxiv_search(payload)


def test() -> None:
    ResearchEngine().test()


if __name__ == "__main__":
    test()
