import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

STORE_PATH = Path("./store")
MODEL_NAME = "microsoft/unixcoder-base"

_model = None
_tokenizer = None
_device = None
_torch = None


def _get_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


def get_device():
    global _device
    if _device is None:
        torch = _get_torch()
        if torch.cuda.is_available():
            _device = torch.device("cuda")
            logger.info("Using CUDA")
        else:
            _device = torch.device("cpu")
            logger.warning("CUDA not available, falling back to CPU")
    return _device


def get_model():
    global _model, _tokenizer
    if _model is None:
        from transformers import AutoModel, AutoTokenizer
        device = get_device()
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.to(device)
        _model.eval()
    return _model, _tokenizer


def embed(text: str) -> list[float]:
    torch = _get_torch()
    model, tokenizer = get_model()
    device = get_device()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding.tolist()


def get_client():
    import chromadb
    STORE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(STORE_PATH))


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name="documents", metadata={"hnsw:space": "cosine"}
    )


def ingest(content: str) -> str:
    collection = get_collection()
    embedding = embed(content)
    doc_id = str(uuid.uuid4())
    collection.add(ids=[doc_id], embeddings=[embedding], documents=[content])
    return doc_id


def search(
    query: str,
    limit: int = 5,
    project: str | None = None,
    version: str | None = None,
) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    # Build where filter for project/version if provided
    where = None
    if project is not None and version is not None:
        where = {"$and": [{"project": project}, {"version": version}]}
    elif project is not None:
        where = {"project": project}
    elif version is not None:
        where = {"version": version}

    embedding = embed(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=limit,
        include=["documents", "distances", "metadatas"],
        where=where,
    )
    out = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        content = results["documents"][0][i]
        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        similarity = 1 / (1 + distance)
        snippet = content[:200] + "..." if len(content) > 200 else content
        out.append(
            {
                "id": doc_id,
                "content": content,
                "snippet": snippet,
                "distance": distance,
                "similarity": similarity,
                "filename": metadata.get("filename", ""),
                "start_line": metadata.get("start_line"),
                "end_line": metadata.get("end_line"),
                "symbol_name": metadata.get("symbol_name", ""),
                "symbol_type": metadata.get("symbol_type", ""),
                "project": metadata.get("project", ""),
                "version": metadata.get("version", ""),
            }
        )
    return out


def search_by_symbol(
    symbol_name: str,
    project: str = "default",
    version: str = "0.0.0",
) -> list[dict]:
    """Look up symbols by exact name within a project/version."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    where = {
        "$and": [
            {"symbol_name": symbol_name},
            {"project": project},
            {"version": version},
        ]
    }

    results = collection.get(
        where=where,
        include=["documents", "metadatas"],
    )

    out = []
    for i, doc_id in enumerate(results["ids"]):
        content = results["documents"][i]
        metadata = results["metadatas"][i] if results["metadatas"] else {}
        out.append(
            {
                "id": doc_id,
                "content": content,
                "filename": metadata.get("filename", ""),
                "filepath": metadata.get("filepath", ""),
                "start_line": metadata.get("start_line"),
                "end_line": metadata.get("end_line"),
                "symbol_name": metadata.get("symbol_name", ""),
                "symbol_type": metadata.get("symbol_type", ""),
                "project": metadata.get("project", ""),
                "version": metadata.get("version", ""),
            }
        )
    return out


def ingest_file(
    filepath: str,
    original_filename: str | None = None,
    project: str = "default",
    version: str = "0.0.0",
) -> tuple[list[str], dict[str, int]]:
    """Ingest symbols from a file.
    
    Returns:
        Tuple of (list of ingested IDs, dict of duplicate symbol names -> count)
    """
    from dillm.parser import extract_symbols

    symbols = extract_symbols(filepath, original_filename)
    if not symbols:
        return [], {}

    collection = get_collection()
    ids = []
    seen: dict[str, int] = {}
    duplicates: dict[str, int] = {}

    for sym in symbols:
        name = sym["symbol_name"]
        if name in seen:
            duplicates[name] = duplicates.get(name, 0) + 1
            continue
        seen[name] = 1

        embedding = embed(sym["text"])
        doc_id = str(uuid.uuid4())
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[sym["text"]],
            metadatas=[
                {
                    "filename": sym["filename"],
                    "filepath": sym["filepath"],
                    "start_line": sym["start_line"],
                    "end_line": sym["end_line"],
                    "symbol_name": sym["symbol_name"],
                    "symbol_type": sym["symbol_type"],
                    "project": project,
                    "version": version,
                }
            ],
        )
        ids.append(doc_id)
    return ids, duplicates


def list_symbols(
    project: str | None = None,
    version: str | None = None,
) -> list[dict]:
    """List all symbols, optionally filtered by project/version."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    where = None
    if project is not None and version is not None:
        where = {"$and": [{"project": project}, {"version": version}]}
    elif project is not None:
        where = {"project": project}
    elif version is not None:
        where = {"version": version}

    results = collection.get(where=where, include=["documents", "metadatas"])
    out = []
    for i, doc_id in enumerate(results["ids"]):
        content = results["documents"][i]
        metadata = results["metadatas"][i] if results["metadatas"] else {}
        out.append(
            {
                "id": doc_id,
                "content": content,
                "filename": metadata.get("filename", ""),
                "filepath": metadata.get("filepath", ""),
                "start_line": metadata.get("start_line"),
                "end_line": metadata.get("end_line"),
                "symbol_name": metadata.get("symbol_name", ""),
                "symbol_type": metadata.get("symbol_type", ""),
                "project": metadata.get("project", ""),
                "version": metadata.get("version", ""),
            }
        )
    return out


def get_all() -> list[dict]:
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []
    results = collection.get(include=["documents", "metadatas"])
    out = []
    for i, doc_id in enumerate(results["ids"]):
        content = results["documents"][i]
        metadata = results["metadatas"][i] if results["metadatas"] else {}
        snippet = content[:200] + "..." if len(content) > 200 else content
        out.append(
            {
                "id": doc_id,
                "content": content,
                "snippet": snippet,
                "distance": 0,
                "similarity": 1.0,
                "filename": metadata.get("filename", ""),
                "start_line": metadata.get("start_line"),
                "end_line": metadata.get("end_line"),
            }
        )
    return out
