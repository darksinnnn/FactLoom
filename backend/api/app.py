"""
FactLoom FastAPI Application
REST endpoints for documents, facts, relationships, and queries.
"""

import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.store.db import init_db, get_connection
from backend.ingest.service import IngestionService
from backend.ingest.parser import PDFParser

app = FastAPI(
    title="FactLoom API",
    description="Fact reconciliation engine: durable, versioned, evidence-grounded facts.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.environ.get("FACTLOOM_UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingestion_service = IngestionService()

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "FactLoom"}

@app.post("/documents")
async def upload_document(
    file: Optional[UploadFile] = File(None),
    file_path: Optional[str] = Form(None),
    doc_type_guess: Optional[str] = Form(None)
):
    """
    Accepts either an uploaded file or a local file path, parses pages with bboxes,
    and stores them into the documents and pages tables.
    """
    target_path = ""
    if file:
        filename = file.filename
        target_path = os.path.join(UPLOAD_DIR, filename)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif file_path:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail=f"Path not found: {file_path}")
        target_path = file_path
    else:
        raise HTTPException(status_code=400, detail="Must provide either file or file_path")

    try:
        result = ingestion_service.ingest_document(target_path, doc_type_guess=doc_type_guess)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.get("/documents")
def list_documents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.id, d.filename, d.doc_type_guess, d.uploaded_at, d.page_count,
               COUNT(p.id) as parsed_pages
        FROM documents d
        LEFT JOIN pages p ON d.id = p.document_id
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/documents/{document_id}")
def get_document(document_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    
    cursor.execute("SELECT id, page_number, width, height, has_text_layer, is_scanned FROM pages WHERE document_id = ? ORDER BY page_number ASC", (document_id,))
    pages = cursor.fetchall()
    conn.close()
    return {
        "document": dict(doc),
        "pages": [dict(p) for p in pages]
    }

@app.get("/documents/{document_id}/pages/{page_number}")
def get_page(document_id: str, page_number: int):
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pages WHERE document_id = ? AND page_number = ?", (document_id, page_number))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    
    res = dict(row)
    res["text_blocks"] = json.loads(res["text_blocks"])
    if res.get("table_blocks"):
        res["table_blocks"] = json.loads(res["table_blocks"])
    if res.get("bbox_data"):
        res["bbox_data"] = json.loads(res["bbox_data"])
    return res
