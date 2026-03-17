from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List
from services.analysis_service import analysis_service
from services.flashcard_service import flashcard_service
from routers.documents import sessions

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class DocRequest(BaseModel):
    session_id: str
    doc_id: str


class DebateRequest(BaseModel):
    session_id: str
    doc_id_1: str
    doc_id_2: str


class FlashcardExportRequest(BaseModel):
    flashcards: List[dict]


def get_doc_data(session_id: str, doc_id: str):
    if session_id not in sessions or doc_id not in sessions[session_id]:
        raise HTTPException(404, "Document not found")
    return sessions[session_id][doc_id]


@router.post("/mindmap")
async def get_mindmap(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return analysis_service.generate_mindmap(data["full_text"], data["doc_name"])


@router.post("/knowledge-graph")
async def get_knowledge_graph(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return analysis_service.generate_knowledge_graph(data["full_text"])


@router.post("/tone")
async def get_tone_analysis(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return analysis_service.analyze_tone(data["full_text"], data["pages"])


@router.post("/contradictions")
async def find_contradictions(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return {"contradictions": analysis_service.find_contradictions(data["full_text"])}


@router.post("/facts-opinions")
async def facts_opinions(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return {"items": analysis_service.separate_facts_opinions(data["full_text"])}


@router.post("/executive-email")
async def executive_email(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return analysis_service.generate_executive_summary_email(data["full_text"], data["doc_name"])


@router.post("/timeline")
async def get_timeline(req: DocRequest):
    from utils.pdf_processor import pdf_processor
    data = get_doc_data(req.session_id, req.doc_id)
    return {"timeline": pdf_processor.extract_dates(data["full_text"])}


@router.post("/action-items")
async def get_action_items(req: DocRequest):
    from utils.pdf_processor import pdf_processor
    data = get_doc_data(req.session_id, req.doc_id)
    return {"action_items": pdf_processor.extract_action_items(data["full_text"])}


@router.post("/debate")
async def debate_documents(req: DebateRequest):
    d1 = get_doc_data(req.session_id, req.doc_id_1)
    d2 = get_doc_data(req.session_id, req.doc_id_2)
    result = analysis_service.debate_documents(
        d1["full_text"], d2["full_text"], d1["doc_name"], d2["doc_name"]
    )
    result["doc1_name"] = d1["doc_name"]
    result["doc2_name"] = d2["doc_name"]
    return result


@router.post("/flashcards")
async def generate_flashcards(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return {"flashcards": flashcard_service.generate_flashcards(data["full_text"])}


@router.post("/flashcards/export-csv")
async def export_flashcards_csv(req: FlashcardExportRequest):
    csv_content = flashcard_service.export_flashcards_csv(req.flashcards)
    return PlainTextResponse(
        content=csv_content, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=flashcards.csv"}
    )


@router.post("/quiz")
async def generate_quiz(req: DocRequest):
    data = get_doc_data(req.session_id, req.doc_id)
    return {"quiz": flashcard_service.generate_quiz(data["full_text"])}
