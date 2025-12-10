"""Programmatic API for dill.

Usage:
    import dillm as dill

    results = dill.find_symbol("my_function", project="myproj", version="1.0.0")
    results = dill.match("some code snippet", project="myproj")
    results = dill.match_file("path/to/file.c", project="myproj")
"""

from pathlib import Path


def find_symbol(
    name: str,
    project: str = "default",
    version: str = "0.0.0",
) -> list[dict]:
    """Look up a symbol by exact name within project/version."""
    from dillm import db
    return db.search_by_symbol(name, project=project, version=version)


def match(
    content: str,
    project: str | None = None,
    version: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Similarity search against stored embeddings.

    If project/version provided, filter to matching metadata.
    Otherwise search all.
    """
    from dillm import db
    return db.search(content, limit=limit, project=project, version=version)


def match_file(
    path: str | Path,
    project: str | None = None,
    version: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Similarity search using file contents."""
    content = Path(path).read_text(encoding="utf-8", errors="replace")
    return match(content, project=project, version=version, limit=limit)
