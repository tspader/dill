import json
import shutil

import click
import uvicorn


@click.group()
def cli():
    pass


@cli.command()
@click.argument("symbol")
@click.option("--project", "-p", default="default", help="Project name")
@click.option("--version", "-v", default="0.0.0", help="Version string")
def find(symbol, project, version):
    """Look up a symbol by exact name."""
    import dillm

    results = dillm.find_symbol(symbol, project=project, version=version)
    if not results:
        print(f"No results for '{symbol}'")
        return
    for r in results:
        print(
            f"--- {r['symbol_name']} ({r['symbol_type']}) @ {r['filename']}:{r['start_line']}-{r['end_line']}"
        )
        print(r["content"])
        print()


@cli.command()
@click.option("--text", "-t", default=None, help="Text to match against")
@click.option("--file", "-f", "filepath", default=None, help="File to match against")
@click.option("--project", "-p", default=None, help="Project name (optional)")
@click.option("--version", "-v", default=None, help="Version string (optional)")
@click.option("--limit", "-n", default=5, help="Max results")
def match(text, filepath, project, version, limit):
    """Similarity search against stored embeddings."""
    import dillm

    if text is None and filepath is None:
        raise click.UsageError("Must provide --text or --file")
    if text is not None and filepath is not None:
        raise click.UsageError("Cannot provide both --text and --file")

    if filepath:
        results = dillm.match_file(
            filepath, project=project, version=version, limit=limit
        )
    else:
        results = dillm.match(text, project=project, version=version, limit=limit)

    if not results:
        print("No results")
        return
    for r in results:
        sym_name = r.get("symbol_name", "")
        sym_type = r.get("symbol_type", "")
        label = f"{sym_name} ({sym_type})" if sym_name else "unknown"
        print(
            f"--- {label} @ {r['filename']}:{r.get('start_line', '?')}-{r.get('end_line', '?')} [sim={r['similarity']:.3f}]"
        )
        print(r.get("snippet", r.get("content", "")[:200]))
        print()


@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--project", "-p", default="default", help="Project name")
@click.option("--version", "-v", default="0.0.0", help="Version string")
def ingest(filepath, project, version):
    """Ingest a C/C++ file into the store."""
    from dillm import db

    ids = db.ingest_file(filepath, project=project, version=version)
    print(f"Ingested {len(ids)} symbols from {filepath}")


@cli.command("list")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--version", "-v", default=None, help="Filter by version")
def list_symbols(project, version):
    """List all symbols in the store."""
    from dillm import db

    results = db.list_symbols(project=project, version=version)
    if not results:
        print("No symbols found")
        return
    for r in results:
        sym_name = r.get("symbol_name", "unknown")
        sym_type = r.get("symbol_type", "")
        proj = r.get("project", "")
        ver = r.get("version", "")
        filename = r.get("filename", "")
        start = r.get("start_line", "?")
        end = r.get("end_line", "?")
        print(f"{sym_name} ({sym_type}) [{proj}@{ver}] {filename}:{start}-{end}")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=7432)
def serve(host, port):
    """Start the HTTP server."""
    uvicorn.run("dillm.server:app", host=host, port=port)


@cli.command()
def clean():
    """Remove the local store."""
    from dillm.db import STORE_PATH

    if STORE_PATH.exists():
        shutil.rmtree(STORE_PATH)
        print(f"Removed {STORE_PATH}")
    else:
        print(f"{STORE_PATH} does not exist")


if __name__ == "__main__":
    cli()
