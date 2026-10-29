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
from app.redis_cache import load as redis_load
from app.redis_cache import save as redis_save
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

_NS = f"fs:score:{VERSION}"  # Redis key namespace; unread old VERSIONs expire on their own


def _redis_key(session_key: int) -> str:
    return f"{_NS}:{session_key}"


def _disk_path(session_key: int) -> Path:
    return DIR / f"{VERSION}-{session_key}.pkl"


def load(session_key: int) -> SessionScore | None:
    # Redis first — survives API redeploys
    hit = redis_load(_redis_key(session_key))
    if isinstance(hit, SessionScore):
        return hit

    # Disk fallback — works locally and when Redis is unavailable
    path = _disk_path(session_key)
    if not path.exists():
        return None
    try:
        score = pickle.loads(path.read_bytes())  # noqa: S301
    except Exception:
        logger.warning("Discarding unreadable saved score %s", path.name)
        path.unlink(missing_ok=True)
        return None
    if not isinstance(score, SessionScore):
        return None

    # Promote disk hit to Redis so future restarts are faster
    redis_save(_redis_key(session_key), score)
    return score


def save(score: SessionScore) -> None:
    key = score.session.session_key

    # Write to Redis (primary)
    redis_save(_redis_key(key), score)

    # Write to disk (fallback)
    path = _disk_path(key)
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(score, protocol=pickle.HIGHEST_PROTOCOL))
        tmp.replace(path)
    except OSError:
        logger.warning("Could not save score for session %d to disk", key)


def prune() -> None:
    """Delete disk scores saved by an older version of the scoring code."""
    if not DIR.exists():
        return
    for path in DIR.iterdir():
        if not path.name.startswith(f"{VERSION}-"):
            path.unlink(missing_ok=True)
