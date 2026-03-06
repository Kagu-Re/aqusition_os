"""Blocklist CLI for Acq Engine Operator Console.

Usage examples:

  # Add a 15-minute block for an IP (requires Redis configured on the server):
  python ops/blocklist_cli.py add --base-url http://localhost:8000 --secret <SECRET> --key 1.2.3.4 --ttl 900

  # Remove:
  python ops/blocklist_cli.py remove --base-url http://localhost:8000 --secret <SECRET> --key 1.2.3.4

  # Check TTL:
  python ops/blocklist_cli.py ttl --base-url http://localhost:8000 --secret <SECRET> --key 1.2.3.4
"""

from __future__ import annotations

import typer
import httpx

app = typer.Typer(add_completion=False)

def _headers(secret: str) -> dict[str, str]:
    return {"X-AE-SECRET": secret}

@app.command()
def add(
    base_url: str = typer.Option(..., help="Console base URL, e.g. http://localhost:8000"),
    secret: str = typer.Option(..., help="Console secret (X-Secret)"),
    key: str = typer.Option(..., help="Client key to block (usually IP)"),
    ttl: int = typer.Option(900, help="TTL seconds"),
):
    r = httpx.post(f"{base_url.rstrip('/')}/api/blocklist/add", headers=_headers(secret), params={"key": key, "ttl_s": ttl}, timeout=10.0)
    typer.echo(r.text)
    r.raise_for_status()

@app.command()
def remove(
    base_url: str = typer.Option(...),
    secret: str = typer.Option(...),
    key: str = typer.Option(...),
):
    r = httpx.post(f"{base_url.rstrip('/')}/api/blocklist/remove", headers=_headers(secret), params={"key": key}, timeout=10.0)
    typer.echo(r.text)
    r.raise_for_status()

@app.command()
def ttl(
    base_url: str = typer.Option(...),
    secret: str = typer.Option(...),
    key: str = typer.Option(...),
):
    r = httpx.get(f"{base_url.rstrip('/')}/api/blocklist/ttl", headers=_headers(secret), params={"key": key}, timeout=10.0)
    typer.echo(r.text)
    r.raise_for_status()

if __name__ == "__main__":
    app()
