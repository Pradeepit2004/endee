import pdfplumber
import PyPDF2
import re
import textstat
from typing import List, Dict, Any

class PDFProcessor:
    @staticmethod
    def extract_text_with_pages(file_path: str) -> List[Dict[str, Any]]:
        pages = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables() or []
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                        "tables": tables,
                        "char_count": len(text)
                    })
        except Exception:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                        "tables": [],
                        "char_count": len(text)
                    })
        return pages

    @staticmethod
    def extract_full_text(file_path: str) -> str:
        pages = PDFProcessor.extract_text_with_pages(file_path)
        return "\n\n".join([p["text"] for p in pages if p["text"].strip()])

    @staticmethod
    def extract_dates(text: str) -> List[Dict[str, str]]:
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b(\d{4})\b',
        ]
        dates_found = []
        seen = set()
        for pattern in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group()
                if date_str in seen:
                    continue
                seen.add(date_str)
                start = max(0, match.start() - 120)
                end = min(len(text), match.end() + 120)
                context = text[start:end].strip()
                dates_found.append({
                    "date": date_str,
                    "context": context,
                    "position": match.start()
                })
        return sorted(dates_found, key=lambda x: x["position"])[:30]

    @staticmethod
    def extract_action_items(text: str) -> List[str]:
        patterns = [
            r'(?:must|should|will|need to|required to|action item[s]?:?|'
            r'todo:?|task:?)\s+([^.!?\n]{10,120}[.!?])',
            r'(?:deadline|due date|by)\s*:?\s*([^.!?\n]{5,100})',
            r'(?:assigned to|responsible:?)\s*([^.!?\n]{5,100})',
        ]
        items = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            items.extend([m.strip() for m in matches])
        return list(dict.fromkeys(items))[:20]

    @staticmethod
    def reading_difficulty(text: str) -> Dict[str, Any]:
        score = textstat.flesch_reading_ease(text)
        grade = textstat.flesch_kincaid_grade(text)
        words = textstat.lexicon_count(text)
        sentences = textstat.sentence_count(text)
        if score >= 70:
            level = "Beginner"
            color = "green"
        elif score >= 50:
            level = "Intermediate"
            color = "orange"
        else:
            level = "Expert"
            color = "red"
        return {
            "score": round(score, 1),
            "grade_level": round(grade, 1),
            "level": level,
            "color": color,
            "word_count": words,
            "sentence_count": sentences,
            "avg_words_per_sentence": round(words / max(sentences, 1), 1)
        }

pdf_processor = PDFProcessor()
