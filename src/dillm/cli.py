import shutil

import click
import uvicorn


@click.group()
def cli():
    pass


@cli.command()
def hello():
    print("hello")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=7432)
def serve(host, port):
    uvicorn.run("dillm.server:app", host=host, port=port)


@cli.command()
def clean():
    from dillm.db import STORE_PATH

    if STORE_PATH.exists():
        shutil.rmtree(STORE_PATH)
        print(f"Removed {STORE_PATH}")
    else:
        print(f"{STORE_PATH} does not exist")


if __name__ == "__main__":
    cli()
