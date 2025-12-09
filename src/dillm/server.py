import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

_db = None

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    def load_model():
        global _db
        from dillm import db

        db.get_model()
        _db = db

    thread = threading.Thread(target=load_model, daemon=True)
    thread.start()
    yield


app = FastAPI(lifespan=lifespan)


def get_db():
    global _db
    if _db is None:
        from dillm import db

        _db = db
    return _db


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search", response_class=HTMLResponse)
async def search(request: Request, q: str = ""):
    if not q.strip():
        return templates.TemplateResponse(
            "results.html", {"request": request, "results": [], "query": q}
        )
    db = get_db()
    if q.strip() == "*":
        results = db.get_all()
    else:
        results = db.search(q, limit=5)
    return templates.TemplateResponse(
        "results.html", {"request": request, "results": results, "query": q}
    )


@app.post("/api/ingest_file", response_class=HTMLResponse)
async def ingest_file(request: Request, file: UploadFile = File(...)):
    db = get_db()
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        ids = db.ingest_file(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "ingested_file": file.filename,
            "ingested_count": len(ids),
        },
    )
