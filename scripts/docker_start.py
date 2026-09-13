"""Prepare the persistent Docker demo database and start FastAPI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

DEFAULT_DATABASE_URL = "sqlite:////app/runtime/postupashki_mvp_large_demo.sqlite3"


def sqlite_path(database_url: str) -> Path:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        raise SystemExit("Docker quick start currently supports only a SQLite database.")

    path = Path(url.database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def run_script(script_name: str) -> None:
    subprocess.run([sys.executable, f"scripts/{script_name}"], check=True)


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    database_path = sqlite_path(database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if database_path.exists():
        print(f"Using existing Docker database: {database_path}", flush=True)
        run_script("init_db.py")
    else:
        print(f"Creating large Docker demo database: {database_path}", flush=True)
        run_script("seed_large_demo.py")

    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "postupashki_mvp.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--proxy-headers",
            "--forwarded-allow-ips=*",
        ],
    )


if __name__ == "__main__":
    main()
