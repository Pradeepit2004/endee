import requests
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from config import config

class WebSearchService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.3
        )

    def search_web(self, query: str) -> List[Dict[str, str]]:
        if not config.SERPAPI_KEY:
            return []
        try:
            params = {"q": query, "api_key": config.SERPAPI_KEY, "num": 5, "engine": "google"}
            response = requests.get("https://serpapi.com/search", params=params, timeout=10)
            data = response.json()
            results = []
            for r in data.get("organic_results", [])[:5]:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "link": r.get("link", "")
                })
            return results
        except Exception:
            return []

    def hybrid_answer(self, question: str, doc_answer: str, doc_context: str) -> Dict[str, Any]:
        web_results = self.search_web(question)
        web_context = ""
        for r in web_results:
            web_context += f"\n[Web: {r['title']}]\n{r['snippet']}\n"

        if not web_context:
            return {"hybrid_answer": doc_answer, "web_results": [], "has_web_data": False}

        prompt = f"""Combine document knowledge with web search results.
Document Answer: {doc_answer}
Web Search Results: {web_context}
Question: {question}
Label document info as [From Document] and web info as [From Web].
"""
        combined = self.llm.predict(prompt)
        return {"hybrid_answer": combined, "web_results": web_results, "has_web_data": True}

web_search_service = WebSearchService()
