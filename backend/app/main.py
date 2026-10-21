import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4


from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import settings, validate_startup_settings
from app.routers import admin, auth, brands, generations, health, keys, kit, me, preview, product_assets, trends

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Refuse to start production without AUTH_JWT_SECRET.
    validate_startup_settings()
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        # Imported lazily; the advisory lock makes concurrent starts safe.
        from app.db.migrate import run_migrations

        await asyncio.to_thread(run_migrations)
    yield


app = FastAPI(
    title="TRENDY AI API",
    description="API for TRENDY AI - Brand Management Platform",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(me.router, tags=["account"])
app.include_router(admin.router)
app.include_router(brands.router)
app.include_router(keys.router)
app.include_router(kit.router)
app.include_router(generations.router)
app.include_router(preview.router)
app.include_router(product_assets.router)
app.include_router(trends.router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException ):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=getattr(exc, "headers", None),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors = exc.errors()

    language_error = next(
        (
            error.get("msg")
            for error in errors
            if any(part == "language" for part in error.get("loc", []))
        ),
        None,
    )

    name_error = next(
        (
            error.get("msg")
            for error in errors
            if any(part == "name" for part in error.get("loc", []))
        ),
        None,
    )

    if language_error:
        message = "language must be one of: ar, en"
    else:
        message = name_error or "Invalid request payload"

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
                "request_id": str(uuid4()),
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # Check / unique / foreign-key violations that no service caught.
    logger.exception("Unhandled database integrity error", exc_info=exc)
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "DATA_CONSTRAINT_VIOLATION",
                "message": "The data could not be saved because it breaks a data rule.",
                "request_id": str(uuid4()),
            }
        },
    )


@app.get("/")
async def root():
    return {
        "message": "TRENDY AI API",
        "version": "0.1.0",
        "status": "running",
    }
