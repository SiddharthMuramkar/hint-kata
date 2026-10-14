from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import logfire
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routes import trace
from app.routes.check import router as check_router

HERE = Path(__file__).parent

# Placeholder until lessons are read from content/ (task #4).
TRACKS = [
    {"name": "Pydantic AI", "lessons": ["Your first agent", "Structured output", "Tools"]},
    {"name": "FastAPI", "lessons": ["Routes and models", "Dependencies", "Streaming"]},
    {"name": "GitHub flow", "lessons": ["Branches", "Pull requests", "Reviews"]},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    if settings.logfire_token:
        logfire.configure(
            token=settings.logfire_token, send_to_logfire="if-token-present", console=False
        )
        logfire.instrument_fastapi(app)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(trace.router)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
app.include_router(check_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="home.html", context={"tracks": TRACKS})


@app.get("/licenses", response_class=HTMLResponse)
async def licenses(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="licenses.html")


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
