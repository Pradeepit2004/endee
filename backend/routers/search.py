from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from services.rag_service import rag_service
from services.hallucination_service import hallucination_detector
from services.web_search_service import web_search_service
from utils.embeddings import embedding_manager
from routers.documents import sessions

router = APIRouter(prefix="/api/search", tags=["search"])


class SingleSearchRequest(BaseModel):
    session_id: str
    doc_id: str
    query: str
    top_k: Optional[int] = 5


class MultiDocSearchRequest(BaseModel):
    session_id: str
    doc_ids: List[str]
    query: str
    top_k: Optional[int] = 5


class HybridSearchRequest(BaseModel):
    session_id: str
    doc_id: str
    query: str
    use_web: Optional[bool] = True


class EvolutionRequest(BaseModel):
    session_id: str
    doc_ids: List[str]
    doc_names: List[str]
    question: str


class SemanticSearchRequest(BaseModel):
    session_id: str
    doc_id: str
    query: str
    top_k: Optional[int] = 8


def _get(session_id: str, doc_id: str) -> dict:
    if session_id not in sessions or doc_id not in sessions[session_id]:
        raise HTTPException(404, "Document not found. Please upload first.")
    return sessions[session_id][doc_id]


def _get_doc_map(session_id: str, doc_ids: List[str]) -> Dict[str, str]:
    doc_map = {}
    sess = sessions.get(session_id, {})
    for did in doc_ids:
        if did in sess:
            doc_map[did] = sess[did]["doc_name"]
    if not doc_map:
        raise HTTPException(404, "No valid documents found in session")
    return doc_map


def _score_to_relevance(score: float) -> str:
    if score < 0.3: return "Very High"
    elif score < 0.5: return "High"
    elif score < 0.7: return "Medium"
    else: return "Low"


def _extract_key_points(answer: str) -> List[str]:
    sentences = [s.strip() for s in answer.replace('\n', ' ').split('.') if len(s.strip()) > 30]
    return sentences[:3]


def _compare_answers(evolution_data: list, question: str) -> dict:
    answered = [d for d in evolution_data if d.get("in_document")]
    not_answered = [d for d in evolution_data if not d.get("in_document")]
    high_conf = [d["doc_name"] for d in answered if d.get("confidence") == "HIGH"]
    mid_conf = [d["doc_name"] for d in answered if d.get("confidence") == "MEDIUM"]
    low_conf = [d["doc_name"] for d in answered if d.get("confidence") == "LOW"]
    agreement_score = 0
    if len(answered) >= 2:
        word_sets = [set(d["answer"].lower().split()) for d in answered]
        intersect = word_sets[0]
        union = word_sets[0]
        for ws in word_sets[1:]:
            intersect &= ws
            union |= ws
        agreement_score = round(len(intersect) / max(len(union), 1) * 100, 1)
    return {
        "docs_with_answer": len(answered), "docs_without_answer": len(not_answered),
        "high_confidence_docs": high_conf, "medium_confidence_docs": mid_conf,
        "low_confidence_docs": low_conf, "answer_agreement_pct": agreement_score,
        "summary": f"{len(answered)} of {len(evolution_data)} documents contain relevant information. Agreement: {agreement_score}%."
    }


@router.post("/single")
async def search_single_doc(req: SingleSearchRequest):
    _get(req.session_id, req.doc_id)
    try:
        vs = embedding_manager.get_collection(req.session_id, req.doc_id)
        results = vs.similarity_search_with_score(req.query, k=req.top_k)
    except Exception as e:
        raise HTTPException(500, f"Search error: {str(e)}")
    chunks = [{"rank": i + 1, "content": doc.page_content, "page": doc.metadata.get("page", 1),
               "doc_name": doc.metadata.get("doc_name", ""), "score": round(float(score), 4),
               "relevance": _score_to_relevance(float(score))} for i, (doc, score) in enumerate(results)]
    return {"query": req.query, "total_chunks": len(chunks), "chunks": chunks}


@router.post("/multi")
async def search_multi_doc(req: MultiDocSearchRequest):
    doc_map = _get_doc_map(req.session_id, req.doc_ids)
    raw = embedding_manager.multi_doc_search(req.session_id, list(doc_map.keys()), req.query, k=req.top_k)
    doc_scores: Dict[str, float] = {}
    for r in raw:
        name = doc_map.get(r["doc_id"], r["doc_id"])
        doc_scores[name] = doc_scores.get(name, 0) + 1.0 / (r["score"] + 1e-6)
    best_doc = max(doc_scores, key=doc_scores.get) if doc_scores else ""
    ranked = [{"rank": i + 1, "content": r["content"], "doc_name": doc_map.get(r["doc_id"], r["doc_id"]),
               "doc_id": r["doc_id"], "page": r["metadata"].get("page", 1),
               "score": round(r["score"], 4), "relevance": _score_to_relevance(r["score"])} for i, r in enumerate(raw)]
    return {"query": req.query, "documents_searched": len(doc_map), "best_document": best_doc,
            "doc_scores": {k: round(v, 2) for k, v in doc_scores.items()}, "results": ranked}


@router.post("/hybrid")
async def hybrid_search(req: HybridSearchRequest):
    doc = _get(req.session_id, req.doc_id)
    doc_result = rag_service.answer_question(req.session_id, req.doc_id, req.query, doc["doc_name"])
    hall_check = hallucination_detector.check(doc_result["answer"], doc_result["context"])
    hybrid = None
    if req.use_web:
        hybrid = web_search_service.hybrid_answer(req.query, doc_result["answer"], doc_result["context"])
    return {
        "query": req.query, "doc_answer": doc_result["answer"], "doc_sources": doc_result["sources"],
        "confidence": doc_result["confidence"], "hallucination_check": hall_check,
        "hybrid_answer": hybrid.get("hybrid_answer") if hybrid else None,
        "web_results": hybrid.get("web_results", []) if hybrid else [],
        "has_web_data": hybrid.get("has_web_data", False) if hybrid else False
    }


@router.post("/evolution")
async def answer_evolution(req: EvolutionRequest):
    if len(req.doc_ids) != len(req.doc_names):
        raise HTTPException(400, "doc_ids and doc_names must have same length")
    evolution_data = []
    for doc_id, doc_name in zip(req.doc_ids, req.doc_names):
        if doc_id not in sessions.get(req.session_id, {}):
            evolution_data.append({"doc_id": doc_id, "doc_name": doc_name,
                                   "answer": "Document not found", "confidence": "LOW", "in_document": False, "key_points": []})
            continue
        try:
            result = rag_service.answer_question(req.session_id, doc_id, req.question, doc_name)
            evolution_data.append({"doc_id": doc_id, "doc_name": doc_name, "answer": result["answer"],
                                   "confidence": result["confidence"], "in_document": result["in_document"],
                                   "sources": result["sources"][:2], "key_points": _extract_key_points(result["answer"])})
        except Exception as e:
            evolution_data.append({"doc_id": doc_id, "doc_name": doc_name, "answer": f"Error: {str(e)}",
                                   "confidence": "LOW", "in_document": False, "key_points": []})
    return {"question": req.question, "total_docs": len(req.doc_ids),
            "evolution": evolution_data, "comparison": _compare_answers(evolution_data, req.question)}


@router.post("/semantic")
async def semantic_chunk_search(req: SemanticSearchRequest):
    _get(req.session_id, req.doc_id)
    try:
        vs = embedding_manager.get_collection(req.session_id, req.doc_id)
        results = vs.similarity_search_with_score(req.query, k=req.top_k)
    except Exception as e:
        raise HTTPException(500, f"Semantic search error: {str(e)}")
    chunks = [{"rank": i + 1, "text": doc.page_content, "page": doc.metadata.get("page", 1),
               "relevance_pct": max(0, min(100, int((1 - float(score)) * 100))),
               "relevance_label": _score_to_relevance(float(score)), "raw_score": round(float(score), 6),
               "char_count": len(doc.page_content)} for i, (doc, score) in enumerate(results)]
    return {"query": req.query, "chunks_found": len(chunks), "chunks": chunks}


@router.post("/web")
async def web_only_search(query: str):
    if not query.strip():
        raise HTTPException(400, "Query cannot be empty")
    results = web_search_service.search_web(query)
    if not results:
        return {"query": query, "results": [], "message": "No web results found. Check SERPAPI_KEY in .env"}
    return {"query": query, "total_results": len(results), "results": results}
