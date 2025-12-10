import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import dillm
from dillm import db

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    def load_model():
        db.get_model()

    thread = threading.Thread(target=load_model, daemon=True)
    thread.start()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/search/symbol", response_class=HTMLResponse)
async def search_symbol(
    request: Request,
    name: str = "",
    project: str = "default",
    version: str = "0.0.0",
):
    """Look up a symbol by exact name within project/version."""
    if not name.strip():
        return templates.TemplateResponse(
            "results.html", {"request": request, "results": [], "query": name}
        )
    results = dillm.find_symbol(name, project=project, version=version)
    return templates.TemplateResponse(
        "results.html", {"request": request, "results": results, "query": name}
    )


@app.get("/api/search/similarity", response_class=HTMLResponse)
async def search_similarity(
    request: Request,
    q: str = "",
    project: str | None = None,
    version: str | None = None,
):
    """Similarity search. If project/version provided, filter to matching metadata. Otherwise search all."""
    if not q.strip():
        return templates.TemplateResponse(
            "results.html", {"request": request, "results": [], "query": q}
        )
    if q.strip() == "*":
        results = db.get_all()
    else:
        results = dillm.match(q, project=project, version=version)
    return templates.TemplateResponse(
        "results.html", {"request": request, "results": results, "query": q}
    )


@app.post("/api/ingest_file", response_class=HTMLResponse)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    project: str = Form("default"),
    version: str = Form("0.0.0"),
):
    original_filename = file.filename or "unknown"
    suffix = Path(original_filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        ids, duplicates = db.ingest_file(
            tmp_path, original_filename, project=project, version=version
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "ingested_file": original_filename,
            "ingested_count": len(ids),
            "duplicates": duplicates,
        },
    )
