from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.settings import get_settings
from src.api.routers.auth import router as auth_router
from src.api.routers.residents import router as residents_router

openapi_tags = [
    {"name": "Auth", "description": "Authentication endpoints (token-based)."},
    {"name": "Residents", "description": "Resident directory and profiles (privacy enforced)."},
]

app = FastAPI(
    title="Resident Directory Backend API",
    description=(
        "Backend service for the Resident Directory app.\n\n"
        "Authentication: obtain a JWT via `POST /auth/login`, then pass it as:\n"
        "`Authorization: Bearer <token>`.\n\n"
        "RBAC: admin-only endpoints are documented under Residents routes (create/update/delete)."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

s = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(residents_router)


@app.get("/", summary="Health Check", operation_id="health_check")
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint.

    Returns:
        JSON object with a simple status message.
    """
    return {"message": "Healthy"}


@app.get(
    "/docs/auth",
    summary="Auth usage help",
    description="Explains how to use the JWT token with the API.",
    operation_id="docs_auth_help",
    tags=["Auth"],
)
# PUBLIC_INTERFACE
def auth_usage_help():
    """Return a short guide for using the API authentication."""
    return {
        "login": {
            "method": "POST",
            "path": "/auth/login",
            "body": {"email": "user@example.com", "password": "your-password"},
        },
        "use_token": {
            "header": "Authorization: Bearer <access_token>",
            "note": "Include this header on all protected endpoints.",
        },
    }
