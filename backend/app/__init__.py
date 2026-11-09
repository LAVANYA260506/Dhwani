"""
Dhwani backend package.

The project root (the folder that holds backend/, shared/, ai_engine/) is added
to the import path so the backend can import `shared` and `ai_engine` no matter
where the server is started from.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # app/__init__.py -> backend/ -> project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))