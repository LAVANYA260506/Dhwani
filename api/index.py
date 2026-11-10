"""Vercel entry point for the Dhwani backend (FastAPI)."""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402,F401  (Vercel looks for `app`)

# Serverless: make sure the tables exist (does nothing when they already do)
try:
    from app.core.database import init_db  # noqa: E402

    init_db()
except Exception:  # the first request will show the real error
    logging.getLogger("dhwani").exception("init_db failed at startup")