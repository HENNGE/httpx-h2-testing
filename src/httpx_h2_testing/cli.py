import asyncio

import click

from .client import run_client
from .server import run_server


@click.group()
def main():
    pass


@main.command()
@click.option("--min-delay", type=click.FLOAT, default=0.1)
@click.option("--max-delay", type=click.FLOAT, default=2.5)
@click.option("--port", type=click.INT, default=8000)
def server(port, min_delay, max_delay):
    asyncio.run(
        run_server(port, min_delay, max_delay), debug=True,
    )


@main.command()
@click.argument("requests", type=click.INT)
@click.option("--warm/--no-warm", default=False)
@click.option("--port", type=click.INT, default=8000)
def client(requests, port, warm):
    asyncio.run(run_client(port, requests, warm))
