import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from routers import documents, analysis, quiz, search

app = FastAPI(
    title="Advanced RAG Intelligence Platform",
    description="20-Feature AI Document Analysis System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(quiz.router)
app.include_router(search.router)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
frontend_path = os.path.abspath(frontend_path)

print(f"Frontend path: {frontend_path}")
print(f"Frontend exists: {os.path.exists(frontend_path)}")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(frontend_path, "index.html")
    print(f"Serving index from: {index_path}")
    return FileResponse(index_path)

@app.get("/styles.css")
async def serve_css():
    return FileResponse(os.path.join(frontend_path, "styles.css"))

@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(frontend_path, "app.js"))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)