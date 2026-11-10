"""
Dhwani backend entry point.

Run from the backend/ folder:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications, forms
from app.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.api.routes import applications, forms, validation, voice,conversations,submissions


API_PREFIX = "/api"

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables that do not exist yet
    init_db()
    yield
    # Shutdown: nothing to close yet


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Voice-first education loan application assistant (Kannada / English).",
    version="0.2.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

register_exception_handlers(app)

# ---------- CORS (allows the Next.js frontend to call the API) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://dhwani-frontend[a-z0-9-]*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
api_router = APIRouter(prefix=API_PREFIX)


@api_router.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


api_router.include_router(forms.router)
api_router.include_router(applications.router)
api_router.include_router(validation.router)
api_router.include_router(voice.router)
# Added in later phases:
# api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(submissions.router)

app.include_router(api_router)
