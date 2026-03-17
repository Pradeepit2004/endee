import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from config import config
from typing import List, Dict, Any
import os

class EmbeddingManager:
    def __init__(self):
        os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIR
        )

    def _collection_name(self, session_id: str, doc_id: str) -> str:
        return f"s{session_id[:20]}d{doc_id[:20]}"

    def create_collection(self, session_id: str, pages: List[Dict[str, Any]],
                          doc_id: str, doc_name: str) -> Chroma:
        documents = []
        for page in pages:
            if page["text"].strip():
                chunks = self.text_splitter.split_text(page["text"])
                for chunk in chunks:
                    documents.append(Document(
                        page_content=chunk,
                        metadata={
                            "page": page["page_number"],
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "session_id": session_id
                        }
                    ))
        name = self._collection_name(session_id, doc_id)
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            client=self.client,
            collection_name=name
        )
        return vectorstore

    def get_collection(self, session_id: str, doc_id: str) -> Chroma:
        name = self._collection_name(session_id, doc_id)
        return Chroma(
            client=self.client,
            collection_name=name,
            embedding_function=self.embeddings
        )

    def multi_doc_search(self, session_id: str, doc_ids: List[str],
                         query: str, k: int = 5) -> List[Dict]:
        all_results = []
        for doc_id in doc_ids:
            try:
                vs = self.get_collection(session_id, doc_id)
                results = vs.similarity_search_with_score(query, k=k)
                for doc, score in results:
                    all_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": float(score),
                        "doc_id": doc_id
                    })
            except Exception:
                continue
        all_results.sort(key=lambda x: x["score"])
        return all_results[:k * 2]

embedding_manager = EmbeddingManager()