"""
Scored races on disk, so a restart (or Render waking the service) loads them instead of
re-scoring the season against OpenF1's rate limit. Only settled races are saved.

Files carry a fingerprint of the code that produces scores, so changing the formula, the photo
lookup or the OpenF1 schemas discards every saved score rather than serving stale ones. The
files are pickles written by this process into its own cache directory.
"""

import hashlib
import logging
import pickle
from pathlib import Path

from app.openf1.client import CACHE_DIR
from app.scoring.pipeline import SessionScore

logger = logging.getLogger(__name__)

_APP = Path(__file__).resolve().parent
_SOURCES = sorted(
    [
        *(_APP / "scoring").glob("*.py"),
        _APP / "headshots.py",
        _APP / "teams.py",
        _APP / "openf1" / "schemas.py",
    ]
)
VERSION = hashlib.sha256(b"".join(p.read_bytes() for p in _SOURCES)).hexdigest()[:12]
DIR = CACHE_DIR / "scores"


def _path(session_key: int) -> Path:
    return DIR / f"{VERSION}-{session_key}.pkl"


def load(session_key: int) -> SessionScore | None:
    path = _path(session_key)
    if not path.exists():
        return None
    try:
        score = pickle.loads(path.read_bytes())
    except Exception:
        logger.warning("Discarding unreadable saved score %s", path.name)
        path.unlink(missing_ok=True)
        return None
    return score if isinstance(score, SessionScore) else None


def save(score: SessionScore) -> None:
    path = _path(score.session.session_key)
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(score, protocol=pickle.HIGHEST_PROTOCOL))
        tmp.replace(path)
    except OSError:
        logger.warning("Could not save score for session %d", score.session.session_key)


def prune() -> None:
    """Delete scores saved by an older version of the scoring code."""
    if not DIR.exists():
        return
    for path in DIR.iterdir():
        if not path.name.startswith(f"{VERSION}-"):
            path.unlink(missing_ok=True)
