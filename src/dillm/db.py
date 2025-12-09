import logging
import uuid
from pathlib import Path

import chromadb
import torch
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)

STORE_PATH = Path("./store")
MODEL_NAME = "microsoft/unixcoder-base"

_model = None
_tokenizer = None
_device = None


def get_device():
    global _device
    if _device is None:
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
        device = get_device()
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.to(device)
        _model.eval()
    return _model, _tokenizer


def embed(text: str) -> list[float]:
    model, tokenizer = get_model()
    device = get_device()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
    return embedding.tolist()


def get_client():
    STORE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(STORE_PATH))


def get_collection():
    client = get_client()
    return client.get_or_create_collection(name="documents")


def ingest(content: str) -> str:
    collection = get_collection()
    embedding = embed(content)
    doc_id = str(uuid.uuid4())
    collection.add(ids=[doc_id], embeddings=[embedding], documents=[content])
    return doc_id


def search(query: str, limit: int = 5) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    embedding = embed(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=limit,
        include=["documents", "distances"],
    )
    out = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        content = results["documents"][0][i]
        similarity = 1 / (1 + distance)
        snippet = content[:200] + "..." if len(content) > 200 else content
        out.append(
            {
                "id": doc_id,
                "content": content,
                "snippet": snippet,
                "distance": distance,
                "similarity": similarity,
            }
        )
    return out
