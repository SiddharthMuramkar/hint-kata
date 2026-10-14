"""Tutor retrieval: embed the learner's question, then hybrid-search the ingested docs.

It never raises. Without DATABASE_URL, without the tables, or without an embedding key it returns
no hits and the tutor works from the lesson text alone, as before. Retrieved text is untrusted.
"""

import logging
from functools import partial

import anyio
from anyio import to_thread

from app.config import settings
from app.ingest.embed import make_embedder
from app.ingest.search import Hit, hybrid_search
from app.store_pg import connect_pg

log = logging.getLogger(__name__)
TIMEOUT_S = 6.0  # embedding call + Neon wake-up; a slow search must not stall the tutor
_told: set[str] = set()


def _lesson_only(reason: str, detail: str = "") -> list[Hit]:
    """Say why there are no hits (once per reason, at info level), then fall back to lesson-only."""
    if reason not in _told:
        _told.add(reason)
        log.info("tutor retrieval is off, using the lesson text only: %s %s", reason, detail)
    return []


def retrieve(question: str, *, track: str, k: int = 6) -> list[Hit]:
    """The `k` best docs chunks for the question, from the lesson's track when `track` is given."""
    if not settings.database_url:
        return _lesson_only("DATABASE_URL is not set")
    if not question.strip():
        return []
    try:
        vector = make_embedder().embed_query_sync(question).embeddings[0]
        if len(vector) != settings.embed_dims:
            raise ValueError(f"got {len(vector)} dims, expected EMBED_DIMS={settings.embed_dims}")
        with connect_pg(settings.database_url) as conn:
            hits = hybrid_search(conn, vector, question, k=k, source=track or None)
    except Exception as e:  # no key, no network, no tables, wrong dims: all mean lesson-only
        return _lesson_only(type(e).__name__, str(e))
    # Citations become links, so only web URLs may pass.
    return [h for h in hits if h.url and h.url.startswith(("https://", "http://"))]


async def retrieve_async(question: str, *, track: str, k: int = 6) -> list[Hit]:
    """`retrieve` off the event loop, with a time limit. Any failure means no hits."""
    if not settings.rag_enabled:
        return []
    try:
        with anyio.fail_after(TIMEOUT_S):
            return await to_thread.run_sync(
                partial(retrieve, question, track=track, k=k), abandon_on_cancel=True
            )
    except TimeoutError:
        log.warning("tutor retrieval took over %.0f s, using the lesson text only", TIMEOUT_S)
        return []
    except Exception:
        log.warning("tutor retrieval failed, using the lesson text only", exc_info=True)
        return []
