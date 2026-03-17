import json
from langchain_openai import ChatOpenAI
from config import config
from typing import Dict, Any

class HallucinationDetector:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0
        )

    def check(self, answer: str, context: str) -> Dict[str, Any]:
        prompt = f"""You are a fact-checker. 
Determine if the ANSWER is fully supported by the CONTEXT provided.
CONTEXT:
{context[:3000]}
ANSWER:
{answer[:1000]}
Respond in this exact JSON format:
{{
  "verdict": "VERIFIED" or "HALLUCINATION" or "PARTIAL",
  "confidence_score": 0-100,
  "explanation": "brief explanation",
  "supported_parts": ["part of answer that IS in context"],
  "unsupported_parts": ["part of answer NOT in context"]
}}
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            answer_words = set(answer.lower().split())
            context_words = set(context.lower().split())
            overlap = len(answer_words & context_words) / max(len(answer_words), 1)
            verdict = "VERIFIED" if overlap > 0.4 else "PARTIAL" if overlap > 0.2 else "HALLUCINATION"
            return {
                "verdict": verdict,
                "confidence_score": int(overlap * 100),
                "explanation": f"Word overlap analysis: {overlap:.0%}",
                "supported_parts": [],
                "unsupported_parts": []
            }

hallucination_detector = HallucinationDetector()
