import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ops logging
from core.exceptions import AppError
from ops.routes import deploys_router, errors_router, ops_router
from routes.auth import router as auth_router
from routes.balances import router as balance_router
from routes.debt_breakdown import router as debt_breakdown_router
from routes.friends import router as friends_router
from routes.group_expenses import router as groups_expense_router
from routes.group_member import router as group_member_router
from routes.groups import router as groups_router
from routes.personal_expenses import router as personal_expenses_router
from routes.settlements import router as settlement_router
from routes.users import router as users_router

# end ops logging

app = FastAPI(
    title="Evven API",
    description="API for Group and Personal Expense Management",
    version="0.0.1",
    docs_url=None,
    redoc_url=None,
)
FAVICON_URL = "/static/EvenUp-white.svg"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "exp://192.168.0.103:8081",
        "https://localhost:8081",
        "http://localhost:3000",
        "https://localhost:3000",
        "https://evven.xyz",
        "exp://192.168.0.103:8081",
        "https://app.evven.xyz",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Evven Docs",
        swagger_favicon_url=FAVICON_URL,
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title="Evven ReDoc",
        redoc_favicon_url=FAVICON_URL,
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(group_member_router)
app.include_router(groups_expense_router)
app.include_router(personal_expenses_router)
app.include_router(debt_breakdown_router)
app.include_router(balance_router)
app.include_router(settlement_router)
app.include_router(friends_router)

# ops logging
app.include_router(errors_router)
app.include_router(deploys_router)
app.include_router(ops_router)
# end ops logging


# ops logging — security headers
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    is_prod = os.getenv("ENVIRONMENT") == "production"
    if is_prod:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    if request.url.path.startswith("/ops"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com https://api.fontshare.com; "
            "img-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

    return response


# end ops logging


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse("templates/index.html")


# =========================================================================================
# Exception Handlers
# =========================================================================================


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def exception_error_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4()
    logger.error(
        "500 error_id=%s method=%s path=%s",
        error_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error_id": str(error_id)},
    )
