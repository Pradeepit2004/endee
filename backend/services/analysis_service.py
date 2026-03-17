import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from config import config


class AnalysisService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.4
        )

    def generate_mindmap(self, text: str, doc_name: str) -> Dict[str, Any]:
        prompt = f"""Analyze this document and create a mind map structure.
Document: {text[:4000]}
Return ONLY valid JSON:
{{
  "center": "{doc_name}",
  "branches": [
    {{"topic": "Main Topic 1", "color": "#4CAF50", "subtopics": ["subtopic1", "subtopic2"]}},
    {{"topic": "Main Topic 2", "color": "#2196F3", "subtopics": ["subtopic1", "subtopic2"]}}
  ]
}}
Create 5-7 branches with 2-4 subtopics each.
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            return {
                "center": doc_name,
                "branches": [
                    {"topic": "Main Concepts", "color": "#4CAF50", "subtopics": ["Key ideas", "Core themes"]},
                    {"topic": "Details", "color": "#2196F3", "subtopics": ["Supporting points", "Examples"]},
                    {"topic": "Conclusions", "color": "#FF9800", "subtopics": ["Summary", "Outcomes"]}
                ]
            }

    def generate_knowledge_graph(self, text: str) -> Dict[str, Any]:
        prompt = f"""Extract entities and relationships from this text for a knowledge graph.
Text: {text[:3000]}
Return ONLY valid JSON:
{{
  "nodes": [{{"id": "1", "label": "Entity Name", "type": "person|concept|place|organization"}}],
  "edges": [{{"from": "1", "to": "2", "label": "relationship verb"}}]
}}
Extract 8-15 nodes and 8-15 edges.
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            return {"nodes": [], "edges": []}

    def analyze_tone(self, text: str, pages: List[Dict]) -> Dict[str, Any]:
        prompt = f"""Analyze the emotional tone and writing style of this document.
Text: {text[:3000]}
Return ONLY valid JSON:
{{
  "overall_tone": "Formal|Informal|Academic|Persuasive|Neutral|Aggressive|Positive|Negative",
  "sentiment_score": -100,
  "formality_score": 0,
  "emotions": {{"joy": 0, "anger": 0, "sadness": 0, "fear": 0, "surprise": 0, "trust": 0}},
  "writing_style": "brief description",
  "tone_summary": "2-3 sentence summary"
}}
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            result = json.loads(response)
        except Exception:
            result = {
                "overall_tone": "Neutral", "sentiment_score": 0, "formality_score": 60,
                "emotions": {"joy": 20, "anger": 10, "sadness": 10, "fear": 10, "surprise": 20, "trust": 50},
                "writing_style": "Standard prose",
                "tone_summary": "The document maintains a neutral tone throughout."
            }

        chapter_tones = []
        for page in pages[:5]:
            if len(page["text"]) > 100:
                p = f"Rate the tone of this text in one word (Positive/Negative/Neutral/Formal/Aggressive):\n{page['text'][:500]}\nReturn ONLY the single tone word."
                try:
                    tone = self.llm.predict(p).strip().split()[0]
                except Exception:
                    tone = "Neutral"
                chapter_tones.append({"page": page["page_number"], "tone": tone})

        result["chapter_tones"] = chapter_tones
        return result

    def find_contradictions(self, text: str) -> List[Dict[str, str]]:
        prompt = f"""Find any contradicting statements in this document.
Text: {text[:4000]}
Return ONLY valid JSON array:
[{{"statement_1": "...", "statement_2": "...", "explanation": "...", "severity": "HIGH|MEDIUM|LOW"}}]
If no contradictions, return [].
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            return []

    def separate_facts_opinions(self, text: str) -> List[Dict[str, str]]:
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 80][:10]
        prompt = f"""Classify each paragraph as FACT or OPINION.
Paragraphs: {json.dumps(paragraphs[:8])}
Return ONLY valid JSON array:
[{{"text": "paragraph text", "type": "FACT|OPINION", "reason": "brief reason"}}]
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            return [{"text": p[:100], "type": "FACT", "reason": "Default"} for p in paragraphs[:5]]

    def generate_executive_summary_email(self, text: str, doc_name: str) -> Dict[str, str]:
        prompt = f"""Write a professional executive summary email for this document.
Document Name: {doc_name}
Content: {text[:3000]}
Return ONLY valid JSON:
{{"subject": "Email subject line", "to": "boss@company.com", "body": "Full professional email body"}}
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except Exception:
            return {
                "subject": f"Summary: {doc_name}",
                "to": "recipient@company.com",
                "body": f"Please find attached the summary of {doc_name}."
            }

    def debate_documents(self, text1: str, text2: str, name1: str, name2: str) -> Dict[str, Any]:
        prompt = f"""Compare these two documents and determine which has a stronger argument.
Document 1 ({name1}): {text1[:2000]}
Document 2 ({name2}): {text2[:2000]}
Return ONLY valid JSON:
{{
  "doc1_arguments": ["arg1", "arg2", "arg3"],
  "doc2_arguments": ["arg1", "arg2", "arg3"],
  "doc1_strengths": ["s1"], "doc2_strengths": ["s1"],
  "doc1_weaknesses": ["w1"], "doc2_weaknesses": ["w1"],
  "winner": "{name1} or {name2} or TIE",
  "winner_reason": "explanation",
  "comparison_summary": "2-3 sentence comparison"
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
            return {
                "doc1_arguments": ["Unable to parse"], "doc2_arguments": ["Unable to parse"],
                "winner": "TIE", "winner_reason": "Analysis failed",
                "comparison_summary": "Could not complete debate analysis."
            }


analysis_service = AnalysisService()
