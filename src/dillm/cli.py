import json
import shutil

import click
import uvicorn


@click.group()
def cli():
    pass


@cli.command()
@click.argument("symbol")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--version", "-v", default=None, help="Filter by version")
def find(symbol, project, version):
    """Look up a symbol by exact name."""
    import dillm
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.text import Text

    results = dillm.find_symbol(symbol, project=project, version=version)
    console = Console()
    if not results:
        console.print(f"No results for '{symbol}'", style="dim")
        return

    for i, r in enumerate(results):
        sym_name = r.get("symbol_name", "unknown")
        sym_type = r.get("symbol_type", "")
        filename = r.get("filename", "")
        start = r.get("start_line", "?")
        end = r.get("end_line", "?")
        content = r.get("content", "")

        header = Text()
        if sym_type == "func":
            header.append(sym_name, style="bright_cyan bold")
        else:
            header.append(sym_name, style="bright_yellow bold")
        header.append(f" ({sym_type}) ", style="dim")
        header.append(f"{filename}:{start}-{end}", style="bright_black")
        console.print(header)

        syntax = Syntax(content, "c", theme="ansi_dark", background_color="default")
        console.print(syntax)

        if i < len(results) - 1:
            console.print()


@cli.command()
@click.option("--text", "-t", default=None, help="Text to match against")
@click.option("--file", "-f", "filepath", default=None, help="File to match against")
@click.option("--project", "-p", default=None, help="Project name (optional)")
@click.option("--version", "-v", default=None, help="Version string (optional)")
@click.option("--limit", "-n", default=5, help="Max results")
def match(text, filepath, project, version, limit):
    """Similarity search against stored embeddings."""
    import dillm
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.text import Text

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

    console = Console()
    if not results:
        console.print("No results", style="dim")
        return

    for i, r in enumerate(results):
        sym_name = r.get("symbol_name", "unknown")
        sym_type = r.get("symbol_type", "")
        filename = r.get("filename", "")
        start = r.get("start_line", "?")
        end = r.get("end_line", "?")
        similarity = r.get("similarity", 0)
        content = r.get("content", "")

        # Header line
        header = Text()
        if sym_type == "func":
            header.append(sym_name, style="bright_cyan bold")
        else:
            header.append(sym_name, style="bright_yellow bold")
        header.append(f" ({sym_type}) ", style="dim")
        header.append(f"{filename}:{start}-{end}", style="bright_black")
        header.append(f" [{similarity:.1%}]", style="green")
        console.print(header)

        # Syntax highlighted code
        syntax = Syntax(content, "c", theme="ansi_dark", background_color="default")
        console.print(syntax)

        if i < len(results) - 1:
            console.print()


@cli.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--project", "-p", default="default", help="Project name")
@click.option("--version", "-v", default="0.0.0", help="Version string")
def ingest(filepath, project, version):
    """Ingest a C/C++ file into the store."""
    from dillm import db

    ids, duplicates = db.ingest_file(filepath, project=project, version=version)
    print(f"Ingested {len(ids)} symbols from {filepath}")
    if duplicates:
        for name, count in duplicates.items():
            print(f"  duplicate: {name} ({count} skipped)")


@cli.command("list")
@click.option("--project", "-p", default=None, help="Filter by project")
@click.option("--version", "-v", default=None, help="Filter by version")
def list_symbols(project, version):
    """List all symbols in the store."""
    from rich.console import Console
    from rich.table import Table
    from dillm import db

    results = db.list_symbols(project=project, version=version)
    if not results:
        print("No symbols found")
        return

    table = Table()
    table.add_column("Symbol", header_style="bright_black")
    table.add_column("Type", header_style="bright_black")
    table.add_column("Project", header_style="bright_black")
    table.add_column("Version", header_style="bright_black")
    table.add_column("File", header_style="bright_black")
    table.add_column("Lines", header_style="bright_black")
    table.add_column("Chars", header_style="bright_black")

    for r in results:
        sym_name = r.get("symbol_name", "unknown")
        sym_type = r.get("symbol_type", "")
        proj = r.get("project", "")
        ver = r.get("version", "")
        filename = r.get("filename", "")
        start = r.get("start_line", "?")
        end = r.get("end_line", "?")
        content = r.get("content", "")

        if sym_type == "func":
            name_styled = f"[bright_cyan]{sym_name}[/bright_cyan]"
        else:  # struct, class
            name_styled = f"[bright_yellow]{sym_name}[/bright_yellow]"

        table.add_row(
            name_styled, sym_type, proj, ver, filename, f"{start}-{end}", str(len(content))
        )

    Console().print(table)


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
