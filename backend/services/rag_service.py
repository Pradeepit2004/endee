import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from config import config
from utils.embeddings import embedding_manager


class RAGService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.CHAT_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.3
        )
        self.memories: Dict[str, List] = {}

    def get_memory(self, session_id: str) -> List:
        if session_id not in self.memories:
            self.memories[session_id] = []
        return self.memories[session_id]

    def answer_question(self, session_id: str, doc_id: str,
                        question: str, doc_name: str = "") -> Dict[str, Any]:
        retriever = embedding_manager.get_collection(session_id, doc_id)
        relevant_docs = retriever.get_relevant_documents(question, k=5)
        context = "\n\n".join([d.page_content for d in relevant_docs])

        memory = self.get_memory(session_id)
        chat_history = "\n".join([f"Q: {m['q']}\nA: {m['a']}" for m in memory[-3:]])

        prompt = f"""You are an expert document analyst.
Answer the question based ONLY on the provided context.
If the answer is not in the context, start your answer with NOT_IN_DOCUMENT.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Provide a detailed, accurate answer.
End your answer with one line: CONFIDENCE: HIGH or CONFIDENCE: MEDIUM or CONFIDENCE: LOW
"""
        answer = self.llm.predict(prompt)

        confidence = "MEDIUM"
        for level in ["HIGH", "MEDIUM", "LOW"]:
            tag = f"CONFIDENCE: {level}"
            if tag in answer:
                confidence = level
                answer = answer.replace(tag, "").strip()
                break

        memory.append({"q": question, "a": answer[:200]})

        sources = []
        for doc in relevant_docs:
            sources.append({
                "text": doc.page_content[:400],
                "page": doc.metadata.get("page", 1),
                "doc_name": doc.metadata.get("doc_name", doc_name)
            })

        in_document = "NOT_IN_DOCUMENT" not in answer

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "context": context,
            "in_document": in_document
        }

    def suggest_questions(self, doc_text: str, doc_name: str) -> List[str]:
        prompt = f"""Based on this document, suggest 5 highly specific,
insightful questions a reader would want to ask.

Document excerpt:
{doc_text[:3000]}

Return ONLY a valid JSON array of 5 strings. No extra text.
Example: ["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"]
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)[:5]
        except Exception:
            return [
                "What is the main argument of this document?",
                "What evidence supports the key claims?",
                "What are the major conclusions?",
                "What limitations are mentioned?",
                "What recommendations are provided?"
            ]

    def generate_followup(self, question: str, answer: str) -> List[str]:
        prompt = f"""Given this Q&A exchange, generate exactly 3 smart follow-up questions.

Question: {question}
Answer: {answer[:600]}

Return ONLY a valid JSON array of 3 strings. No extra text.
"""
        try:
            response = self.llm.predict(prompt).strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)[:3]
        except Exception:
            return [
                "Can you elaborate on this further?",
                "What are the implications of this?",
                "How does this compare to other approaches?"
            ]

    def tutor_mode(self, session_id: str, doc_id: str,
                   user_input: str) -> Dict[str, Any]:
        retriever = embedding_manager.get_collection(session_id, doc_id)
        relevant_docs = retriever.get_relevant_documents(user_input, k=4)
        context = "\n\n".join([d.page_content for d in relevant_docs])

        prompt = f"""You are a Socratic tutor. Use the document context below.
- Explain concepts step by step
- Ask the student a question back to test understanding
- Be encouraging and clear
- Use simple language

Context:
{context}

Student says: {user_input}

Respond as a tutor:"""

        response = self.llm.predict(prompt)
        return {"tutor_response": response, "context_used": context[:500]}

    def answer_multi_doc(self, session_id: str, doc_ids: List[str],
                         doc_map: Dict[str, str], question: str) -> Dict[str, Any]:
        results = embedding_manager.multi_doc_search(
            session_id, doc_ids, question, k=4
        )

        context_parts = []
        for r in results:
            name = doc_map.get(r["doc_id"], r["doc_id"])
            context_parts.append(f"[From: {name}]\n{r['content']}")
        context = "\n\n".join(context_parts)

        prompt = f"""Answer the question using the context from multiple documents.
For each point, indicate which document it came from.

Context:
{context}

Question: {question}

Answer with document references:"""

        answer = self.llm.predict(prompt)

        doc_scores: Dict[str, float] = {}
        for r in results:
            name = doc_map.get(r["doc_id"], r["doc_id"])
            if name not in doc_scores:
                doc_scores[name] = 0
            doc_scores[name] += 1.0 / (r["score"] + 0.001)

        best_doc = max(doc_scores, key=doc_scores.get) if doc_scores else ""

        return {
            "answer": answer,
            "best_document": best_doc,
            "doc_scores": doc_scores,
            "sources": results[:6]
        }


rag_service = RAGService()