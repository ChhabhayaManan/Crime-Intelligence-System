import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import pytest

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_BASE = "http://127.0.0.1:8000"
TEST_JWT_SECRET = "tests-local-only-secret-not-a-real-key"
ROOT = Path(__file__).resolve().parents[1]

_server = None


def pytest_addoption(parser):
    parser.addoption(
        "--remote",
        action="store_true",
        help="Allow running against a non-local API. Never needed for local work.",
    )


def _reachable(base):
    """Ready, not merely listening - /health answers 200 even with a dead database."""
    try:
        with urllib.request.urlopen(f"{base}/health/ready", timeout=2) as res:
            return res.status == 200
    except Exception:
        return False


def _start_server(base):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "App.main:app", "--host", "127.0.0.1",
         "--port", str(urlsplit(base).port or 80), "--log-level", "warning"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        if _reachable(base):
            return proc
        if proc.poll() is not None:
            return None
        time.sleep(0.2)
    proc.terminate()
    return None


def pytest_configure(config):
    global _server

    base = (os.getenv("API_BASE") or DEFAULT_BASE).rstrip("/")
    host = urlsplit(base).hostname
    if host not in LOCAL_HOSTS and not config.getoption("--remote"):
        raise pytest.UsageError(
            f"API_BASE points at {host!r}, which is not local. These tests must never "
            "run against deployed infrastructure. Unset API_BASE, or pass --remote if "
            "you really mean it."
        )

    os.environ["API_BASE"] = base
    # Importing the app needs this, and the server we start inherits it, so a
    # minted token and the server agree. An externally started server must use
    # the same value, which is why an existing JWT_SECRET always wins.
    os.environ.setdefault("JWT_SECRET", TEST_JWT_SECRET)
    config.api_base = base

    if not _reachable(base) and os.getenv("DATABASE_URL"):
        _server = _start_server(base)
        if _server is None:
            raise pytest.UsageError(
                f"DATABASE_URL is set but no API came up on {base}, so the integration "
                "tests would silently skip. Something else is probably holding that port."
            )


def pytest_unconfigure(config):
    if _server is not None:
        _server.terminate()
        _server.wait(timeout=10)


def pytest_collection_modifyitems(config, items):
    live = _reachable(config.api_base)
    skip = pytest.mark.skip(
        reason=f"No ready API at {config.api_base}. Set DATABASE_URL to a local Postgres "
               "and pytest will start one, or start it yourself. If something is already "
               "on that port but cannot reach its database, stop it first."
    )
    for item in items:
        if item.nodeid.startswith("tests/test_api.py"):
            item.add_marker("integration")
            if not live:
                item.add_marker(skip)
        else:
            item.add_marker("unit")
