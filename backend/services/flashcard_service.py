import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from config import config

class FlashcardService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.4
        )

    def generate_flashcards(self, text: str, count: int = 15) -> List[Dict[str, str]]:
        prompt = f"""Create {count} study flashcards from this document.
Document: {text[:4000]}
Return ONLY valid JSON array:
[{{"question": "Q1?", "answer": "A1", "topic": "topic category"}}]
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)[:count]
        except Exception:
            return [{"question": "What is the main topic?", "answer": "See document", "topic": "General"}]

    def generate_quiz(self, text: str, count: int = 10) -> List[Dict[str, Any]]:
        prompt = f"""Create {count} multiple choice questions from this document.
Each question must have exactly 4 options with one correct answer.
Document: {text[:4000]}
Return ONLY valid JSON array:
[{{"question": "Question?", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "Why correct"}}]
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)[:count]
        except Exception:
            return []

    def export_flashcards_csv(self, flashcards: List[Dict]) -> str:
        lines = ["Question,Answer,Topic"]
        for card in flashcards:
            q = card.get("question", "").replace(",", ";").replace('"', "'")
            a = card.get("answer", "").replace(",", ";").replace('"', "'")
            t = card.get("topic", "").replace(",", ";")
            lines.append(f'"{q}","{a}","{t}"')
        return "\n".join(lines)

flashcard_service = FlashcardService()
