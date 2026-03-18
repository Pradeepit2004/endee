import requests
import json
import uuid
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from config import config
from typing import List, Dict, Any
import os

ENDEE_URL = "http://localhost:8080/api/v1"

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
        self.headers = {"Content-Type": "application/json"}
        self.dimension = 1536
        self.chunks_store: Dict[str, List[Dict]] = {}
        print("✅ EmbeddingManager initialized with Endee Vector DB")

    def _index_name(self, session_id: str, doc_id: str) -> str:
        name = f"s{session_id[:15]}d{doc_id[:15]}"
        return name.lower().replace("-", "").replace("_", "")

    def _endee_available(self) -> bool:
        try:
            r = requests.get(f"http://localhost:8080", timeout=3)
            return True
        except:
            return False

    def _create_endee_index(self, index_name: str):
        try:
            payload = {
                "name": index_name,
                "dimension": self.dimension,
                "metric": "cosine"
            }
            r = requests.post(
                f"{ENDEE_URL}/index/create",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            print(f"Endee index created: {index_name} → {r.status_code}")
            return True
        except Exception as e:
            print(f"Endee create index error: {e}")
            return False

    def _upsert_endee_vectors(self, index_name: str, vectors: List[Dict]):
        try:
            payload = {
                "index": index_name,
                "vectors": vectors
            }
            r = requests.post(
                f"{ENDEE_URL}/vector/upsert",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            print(f"Endee upsert: {r.status_code}")
            return True
        except Exception as e:
            print(f"Endee upsert error: {e}")
            return False

    def _search_endee(self, index_name: str, query_vector: List[float], k: int = 5):
        try:
            payload = {
                "index": index_name,
                "vector": query_vector,
                "top_k": k
            }
            r = requests.post(
                f"{ENDEE_URL}/vector/search",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            return r.json()
        except Exception as e:
            print(f"Endee search error: {e}")
            return None

    def create_collection(self, session_id: str, pages: List[Dict[str, Any]],
                          doc_id: str, doc_name: str):
        # Split documents into chunks
        documents = []
        for page in pages:
            if page["text"].strip():
                chunks = self.text_splitter.split_text(page["text"])
                for chunk in chunks:
                    documents.append({
                        "content": chunk,
                        "page": page["page_number"],
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "session_id": session_id
                    })

        # Get embeddings from OpenAI
        texts = [d["content"] for d in documents]
        print(f"Getting embeddings for {len(texts)} chunks...")
        embedding_vectors = self.embeddings.embed_documents(texts)

        index_name = self._index_name(session_id, doc_id)

        if self._endee_available():
            print("✅ Using Endee Vector Database")
            # Create index in Endee
            self._create_endee_index(index_name)

            # Prepare vectors for Endee
            vectors = []
            for i, (doc, vec) in enumerate(zip(documents, embedding_vectors)):
                vectors.append({
                    "id": str(i),
                    "vector": vec,
                    "metadata": {
                        "content": doc["content"],
                        "page": doc["page"],
                        "doc_name": doc["doc_name"],
                        "doc_id": doc["doc_id"]
                    }
                })

            # Store in Endee
            self._upsert_endee_vectors(index_name, vectors)
        else:
            print("⚠️ Endee not available, using local store")

        # Always keep local copy for retrieval
        self.chunks_store[index_name] = [
            {
                "content": doc["content"],
                "embedding": vec,
                "metadata": {
                    "page": doc["page"],
                    "doc_name": doc["doc_name"],
                    "doc_id": doc["doc_id"],
                    "session_id": doc["session_id"]
                }
            }
            for doc, vec in zip(documents, embedding_vectors)
        ]
        print(f"✅ Stored {len(documents)} chunks in Endee")
        return index_name

    def get_collection(self, session_id: str, doc_id: str):
        index_name = self._index_name(session_id, doc_id)
        return EndeeRetriever(
            index_name=index_name,
            embedding_manager=self,
            embeddings=self.embeddings
        )

    def multi_doc_search(self, session_id: str, doc_ids: List[str],
                         query: str, k: int = 5) -> List[Dict]:
        all_results = []
        query_vector = self.embeddings.embed_query(query)

        for doc_id in doc_ids:
            index_name = self._index_name(session_id, doc_id)
            results = self._similarity_search(index_name, query_vector, k=k)
            for r in results:
                r["doc_id"] = doc_id
                all_results.append(r)

        all_results.sort(key=lambda x: x["score"])
        return all_results[:k * 2]

    def _similarity_search(self, index_name: str, query_vector: List[float], k: int = 5):
        chunks = self.chunks_store.get(index_name, [])
        if not chunks:
            return []

        # Calculate cosine similarity
        import numpy as np
        query_vec = np.array(query_vector)
        results = []

        for chunk in chunks:
            chunk_vec = np.array(chunk["embedding"])
            # Cosine similarity
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-10
            )
            score = 1 - similarity  # Convert to distance
            results.append({
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "score": float(score)
            })

        results.sort(key=lambda x: x["score"])
        return results[:k]


class EndeeRetriever:
    """Retriever that works with Endee Vector DB"""

    def __init__(self, index_name: str, embedding_manager: EmbeddingManager,
                 embeddings: OpenAIEmbeddings):
        self.index_name = index_name
        self.em = embedding_manager
        self.embeddings = embeddings

    def as_retriever(self, search_type="similarity", search_kwargs={"k": 5}):
        return self

    def get_relevant_documents(self, query: str, k: int = 5):
        query_vector = self.embeddings.embed_query(query)
        results = self.em._similarity_search(self.index_name, query_vector, k=k)

        docs = []
        for r in results:
            doc = Document(
                page_content=r["content"],
                metadata=r["metadata"]
            )
            docs.append(doc)
        return docs

    def similarity_search_with_score(self, query: str, k: int = 5):
        query_vector = self.embeddings.embed_query(query)
        results = self.em._similarity_search(self.index_name, query_vector, k=k)

        docs_with_scores = []
        for r in results:
            doc = Document(
                page_content=r["content"],
                metadata=r["metadata"]
            )
            docs_with_scores.append((doc, r["score"]))
        return docs_with_scores


embedding_manager = EmbeddingManager()