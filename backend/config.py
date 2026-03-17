import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    
    CHROMA_PERSIST_DIR = "./chroma_db"
    EMBEDDING_MODEL = "text-embedding-3-small"
    CHAT_MODEL = "gpt-4o"
    
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    MAX_FILE_SIZE = 50 * 1024 * 1024
    UPLOAD_DIR = "./uploads"
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

config = Config()
