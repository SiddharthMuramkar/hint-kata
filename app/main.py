from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import logfire
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from markupsafe import Markup

from app.config import settings
from app.content import Lesson, Source, load_lessons, load_sources
from app.deps import get_store, get_user_id
from app.mastery import log_config, refresh
from app.review import due_items
from app.routes.check import router as check_router
from app.routes.quiz import router as quiz_router
from app.routes.review import router as review_router
from app.routes.review import templates
from app.routes.trace import router as trace_router
from app.store import Store, open_store

HERE = Path(__file__).parent

TRACKS = {
    "pydantic-ai": "Pydantic AI",
    "fastapi": "FastAPI",
    "github": "GitHub for the Claude Code era",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    if settings.logfire_token:
        logfire.configure(
            token=settings.logfire_token, send_to_logfire="if-token-present", console=False
        )
        logfire.instrument_fastapi(app)
    root = Path(settings.content_root)
    app.state.lessons = load_lessons(root)
    app.state.sources = load_sources(root / "sources.yaml")
    store = open_store(settings.hintkata_db_path)
    try:
        log_config(store, store.ensure_user("owner"))
    finally:
        store.close()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(trace_router)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
app.include_router(check_router)
app.include_router(quiz_router)
app.include_router(review_router)


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> HTMLResponse:
    lessons: dict[str, Lesson] = request.app.state.lessons
    mastery = refresh(store, lessons, user_id)
    tracks = [
        {"name": name, "lessons": [x for x in lessons.values() if x.track == key]}
        for key, name in TRACKS.items()
    ]
    return templates.TemplateResponse(
        request=request, name="home.html", context={"tracks": tracks, "mastery": mastery}
    )


@app.get("/api/progress")
def api_progress(
    request: Request,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    lessons: dict[str, Lesson] = request.app.state.lessons
    due = due_items(store, lessons, user_id, datetime.now(UTC))
    return {"mastery": refresh(store, lessons, user_id), "due": len(due)}


@app.get("/lessons/{lesson_id}", response_class=HTMLResponse)
async def lesson_page(request: Request, lesson_id: str) -> HTMLResponse:
    lesson: Lesson | None = request.app.state.lessons.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    sources: dict[str, Source] = request.app.state.sources
    context = {
        "lesson": lesson,
        "lesson_id": lesson.id,
        "task_kind": lesson.task_kind,
        "task_readme_html": Markup(lesson.task_readme_html),
        "has_trace": lesson.has_trace,
        "track_name": TRACKS.get(lesson.track, lesson.track),
        "sources": [sources[s] for s in lesson.sources if s in sources],
    }
    return templates.TemplateResponse(request=request, name="lesson.html", context=context)


@app.get("/api/lessons")
async def api_lessons(request: Request) -> list[dict[str, str | int]]:
    return [
        {"id": x.id, "track": x.track, "title": x.title, "minutes": x.minutes}
        for x in request.app.state.lessons.values()
    ]


@app.get("/licenses", response_class=HTMLResponse)
async def licenses(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="licenses.html")


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
