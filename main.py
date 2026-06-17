from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.requests import router as requests_router
from app.api.v1.reviewer import router as reviewer_router
from app.core.config import settings
from app.core.exceptions import AppException


app = FastAPI(
    title=settings.APP_NAME,
    description="Workflow Approval Management System - Csyrus Internship Assessment",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Register routers
app.include_router(health_router, tags=["health"])
app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(reviewer_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}