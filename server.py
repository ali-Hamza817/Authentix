"""Authentix web service.

    python server.py            # http://127.0.0.1:8000
    uvicorn server:app --reload

Serves the UI and exposes POST /api/analyze.

UI resolution order:
  1. frontend/dist   — the built React app (run `npm --prefix frontend run build`)
  2. web/            — the no-build fallback UI
During React development, run `npm --prefix frontend run dev` (Vite on :5173,
which proxies /api here).
"""
from __future__ import annotations

import os
import pathlib

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from authentix import __version__
from authentix.analyzer import analyze_bytes

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "frontend" / "dist"
LEGACY = ROOT / "web"
MAX_BYTES = 30 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"}

app = FastAPI(title="Authentix", version=__version__, docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    ui = "react" if DIST.is_dir() else ("legacy" if LEGACY.is_dir() else "none")
    return {"status": "ok", "product": "Authentix", "version": __version__, "ui": ui}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)) -> JSONResponse:
    name = file.filename or "document"
    ext = os.path.splitext(name)[1].lower()
    if ext and ext not in ALLOWED_EXT:
        raise HTTPException(415, f"Unsupported file type '{ext}'. Upload a PDF or Office file (.docx/.xlsx/.pptx).")
    data = await file.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"File is {len(data) // 1024 // 1024} MB; the limit is {MAX_BYTES // 1024 // 1024} MB.")
    try:
        report = analyze_bytes(data, name)
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(500, f"Analysis failed: {type(e).__name__}: {e}")
    return JSONResponse(report)


# ---- UI (registered last so /api/* wins) --------------------------------- #
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="site")
elif LEGACY.is_dir():
    app.mount("/static", StaticFiles(directory=str(LEGACY)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(LEGACY / "index.html"))


def run() -> None:
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
