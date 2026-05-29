import warnings
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import auth, documents, roles, rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Financial Document Management System",
    description=(
        "A FastAPI application for financial document management with "
        "AI-powered semantic analysis using RAG (Retrieval-Augmented Generation)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


def custom_openapi():
    """Remove 422 Validation Error from all endpoint docs."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path in schema.get("paths", {}).values():
        for method in path.values():
            responses = method.get("responses", {})
            responses.pop("422", None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

# Include routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(roles.router)
app.include_router(rag.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Financial Document Management System",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
