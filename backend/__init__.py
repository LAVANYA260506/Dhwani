"""Dhwani backend package."""

import sys
from pathlib import Path

# Make the project root importable so that `shared` (form schema, glossary,
# constants) and `ai_engine` work from inside the backend, whichever folder
# the server is started from.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))