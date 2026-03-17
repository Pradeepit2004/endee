import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from config import config
from utils.pdf_processor import pdf_processor
from utils.embeddings import embedding_manager
from services.rag_service import rag_service
from services.hallucination_service import hallucination_detector
from services.web_search_service import web_search_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])

sessions: dict = {}


class QuestionRequest(BaseModel):
    session_id: str
    doc_id: str
    question: str
    doc_name: str = ""
    use_web: bool = False
    tutor_mode: bool = False


class MultiDocQuestionRequest(BaseModel):
    session_id: str
    doc_ids: List[str]
    question: str


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), session_id: str = Form(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    doc_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}_{file.filename}")

    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    pages = pdf_processor.extract_text_with_pages(file_path)
    full_text = "\n\n".join([p["text"] for p in pages if p["text"].strip()])

    if not full_text.strip():
        raise HTTPException(400, "Could not extract text from PDF")

    try:
        embedding_manager.create_collection(session_id, pages, doc_id, file.filename)
        suggested_questions = rag_service.suggest_questions(full_text, file.filename)
    except Exception as e:
        # If vector DB or LLM fails (usually API key issue), we still save the doc but note the failure
        print(f"Error during document processing: {str(e)}")
        # If it's an authentication error from OpenAI, make it clear
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(401, f"Invalid OpenAI API Key. Please check your .env file. Error: {error_msg}")
        raise HTTPException(500, f"Failed to process document: {error_msg}")

    difficulty = pdf_processor.reading_difficulty(full_text)

    if session_id not in sessions:
        sessions[session_id] = {}
    sessions[session_id][doc_id] = {
        "doc_id": doc_id,
        "doc_name": file.filename,
        "file_path": file_path,
        "pages": pages,
        "full_text": full_text,
        "total_pages": len(pages),
        "word_count": len(full_text.split())
    }

    return {
        "success": True,
        "doc_id": doc_id,
        "doc_name": file.filename,
        "total_pages": len(pages),
        "word_count": len(full_text.split()),
        "suggested_questions": suggested_questions,
        "difficulty": difficulty
    }


@router.post("/ask")
async def ask_question(req: QuestionRequest):
    if req.session_id not in sessions or req.doc_id not in sessions[req.session_id]:
        raise HTTPException(404, "Document not found. Please upload first.")

    doc_data = sessions[req.session_id][req.doc_id]

    if req.tutor_mode:
        result = rag_service.tutor_mode(req.session_id, req.doc_id, req.question)
        return {"answer": result["tutor_response"], "tutor_mode": True, "sources": [],
                "hallucination_check": None, "followup_questions": []}

    result = rag_service.answer_question(
        req.session_id, req.doc_id, req.question, doc_data["doc_name"]
    )
    hall_check = hallucination_detector.check(result["answer"], result["context"])
    followups = rag_service.generate_followup(req.question, result["answer"])

    hybrid_data = None
    if req.use_web:
        hybrid_data = web_search_service.hybrid_answer(
            req.question, result["answer"], result["context"]
        )

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result["confidence"],
        "in_document": result["in_document"],
        "hallucination_check": hall_check,
        "followup_questions": followups,
        "hybrid_data": hybrid_data,
        "tutor_mode": False
    }


@router.post("/ask-multi")
async def ask_multi_doc(req: MultiDocQuestionRequest):
    if req.session_id not in sessions:
        raise HTTPException(404, "Session not found")

    doc_map = {}
    for doc_id in req.doc_ids:
        if doc_id in sessions.get(req.session_id, {}):
            doc_map[doc_id] = sessions[req.session_id][doc_id]["doc_name"]

    if not doc_map:
        raise HTTPException(404, "No valid documents found")

    result = rag_service.answer_multi_doc(
        req.session_id, list(doc_map.keys()), doc_map, req.question
    )
    followups = rag_service.generate_followup(req.question, result["answer"])
    result["followup_questions"] = followups
    return result


@router.get("/session/{session_id}")
async def get_session_docs(session_id: str):
    docs = sessions.get(session_id, {})
    return {
        "session_id": session_id,
        "documents": [
            {"doc_id": d["doc_id"], "doc_name": d["doc_name"],
             "total_pages": d["total_pages"], "word_count": d["word_count"]}
            for d in docs.values()
        ]
    }


@router.delete("/{session_id}/{doc_id}")
async def delete_document(session_id: str, doc_id: str):
    if session_id in sessions and doc_id in sessions[session_id]:
        doc_data = sessions[session_id][doc_id]
        try:
            os.remove(doc_data["file_path"])
        except Exception:
            pass
        del sessions[session_id][doc_id]
        return {"success": True, "message": "Document deleted"}
    raise HTTPException(404, "Document not found")
