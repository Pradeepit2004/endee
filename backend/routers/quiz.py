from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
from services.flashcard_service import flashcard_service
from routers.documents import sessions

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class QuizRequest(BaseModel):
    session_id: str
    doc_id: str
    count: Optional[int] = 10


class FlashcardRequest(BaseModel):
    session_id: str
    doc_id: str
    count: Optional[int] = 15


class ExportRequest(BaseModel):
    flashcards: List[dict]


class ScoreRequest(BaseModel):
    quiz: List[dict]
    answers: dict


def _get(session_id: str, doc_id: str) -> dict:
    if session_id not in sessions or doc_id not in sessions[session_id]:
        raise HTTPException(404, "Document not found. Please upload first.")
    return sessions[session_id][doc_id]


@router.post("/generate")
async def generate_quiz(req: QuizRequest):
    doc = _get(req.session_id, req.doc_id)
    questions = flashcard_service.generate_quiz(doc["full_text"], count=req.count)
    return {"success": True, "doc_name": doc["doc_name"],
            "total_questions": len(questions), "quiz": questions}


@router.post("/score")
async def calculate_score(req: ScoreRequest):
    if not req.quiz:
        raise HTTPException(400, "Quiz data is required")
    total = len(req.quiz)
    correct = 0
    results = []
    for i, q in enumerate(req.quiz):
        selected = req.answers.get(str(i))
        right_idx = q.get("correct_index", 0)
        is_correct = (selected == right_idx)
        if is_correct:
            correct += 1
        results.append({
            "question": q.get("question", ""), "selected_index": selected,
            "correct_index": right_idx, "is_correct": is_correct,
            "explanation": q.get("explanation", ""), "options": q.get("options", [])
        })
    pct = round((correct / total) * 100, 1) if total else 0
    grade = "A" if pct >= 90 else "B" if pct >= 80 else "C" if pct >= 70 else "D" if pct >= 60 else "F"
    feedback = ("Excellent work! 🏆" if pct >= 90 else "Great job! 👍" if pct >= 80 else
                "Good effort! 📚" if pct >= 70 else "Keep studying! 💪" if pct >= 60 else "Need more practice! 📖")
    return {"total": total, "correct": correct, "wrong": total - correct,
            "score_pct": pct, "grade": grade, "feedback": feedback, "results": results}


@router.post("/flashcards/generate")
async def generate_flashcards(req: FlashcardRequest):
    doc = _get(req.session_id, req.doc_id)
    cards = flashcard_service.generate_flashcards(doc["full_text"], count=req.count)
    return {"success": True, "doc_name": doc["doc_name"], "count": len(cards), "flashcards": cards}


@router.post("/flashcards/export-csv")
async def export_csv(req: ExportRequest):
    if not req.flashcards:
        raise HTTPException(400, "No flashcards provided")
    csv_content = flashcard_service.export_flashcards_csv(req.flashcards)
    return PlainTextResponse(content=csv_content, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=flashcards.csv"})


@router.post("/flashcards/export-json")
async def export_json(req: ExportRequest):
    if not req.flashcards:
        raise HTTPException(400, "No flashcards provided")
    return {"count": len(req.flashcards), "flashcards": req.flashcards}
