import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import (
    DEPLOY_WEBHOOK_SECRET,
    ERRORS_INGEST_BUCKET_CAPACITY,
    ERRORS_INGEST_REFILL_RATE,
    OPS_LOGIN_BUCKET_CAPACITY,
    OPS_LOGIN_REFILL_RATE,
    OPS_PASSWORD,
    OPS_SESSION_TTL_DAYS,
    OPS_USERNAME,
    SECRET_KEY,
)
from core.deps import get_current_user_optional, get_db
from core.rate_limiter import create_rate_limiter
from ops import services
from ops.schemas import (
    ClientErrorCreate,
    ClientErrorOut,
    DeployCreate,
    DeployListResponse,
    DeployOut,
    ErrorListResponse,
    OpsLoginRequest,
)

# ops logging — rate limiters
errors_ingest_limiter = create_rate_limiter(
    capacity=ERRORS_INGEST_BUCKET_CAPACITY,
    refill_rate=ERRORS_INGEST_REFILL_RATE,
)

ops_login_limiter = create_rate_limiter(
    capacity=OPS_LOGIN_BUCKET_CAPACITY,
    refill_rate=OPS_LOGIN_REFILL_RATE,
)
# end ops logging

# ops logging — session helpers
COOKIE_NAME = "ops_session"
COOKIE_PATH = "/ops"


def _hmac_sign(message: str) -> str:
    return hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()


def create_ops_session_token(username: str) -> str:
    exp = int(
        (datetime.now(timezone.utc) + timedelta(days=OPS_SESSION_TTL_DAYS)).timestamp()
    )
    payload = f"{username}|{exp}"
    sig = _hmac_sign(payload)
    username_b64 = base64.urlsafe_b64encode(username.encode()).decode()
    exp_b64 = base64.urlsafe_b64encode(str(exp).encode()).decode()
    return f"{username_b64}.{exp_b64}.{sig}"


def verify_ops_session_token(token: str) -> str | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        username_b64, exp_b64, sig = parts
        username = base64.urlsafe_b64decode(username_b64.encode()).decode()
        exp = int(base64.urlsafe_b64decode(exp_b64.encode()).decode())

        if datetime.now(timezone.utc).timestamp() > exp:
            return None

        expected_payload = f"{username}|{exp}"
        expected_sig = _hmac_sign(expected_payload)

        if not secrets.compare_digest(sig, expected_sig):
            return None

        return username
    except Exception:
        return None


async def require_ops_session(request: Request) -> str:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="Authentication required")
    username = verify_ops_session_token(cookie)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired")
    return username


# end ops logging


# ── Errors ingestion router ────────────────────────────────────
errors_router = APIRouter(tags=["Ops - Errors"])


@errors_router.post(
    "/errors",
    status_code=status.HTTP_201_CREATED,
)
async def create_error(
    body: ClientErrorCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_optional),
    _: None = Depends(errors_ingest_limiter),
):
    user_id = user.id if user else None
    error = await services.create_error_log(db, body, user_id=user_id)

    if error is None:
        return {"status": "duplicate"}

    return {"status": "logged", "id": str(error.id)}


# ── Deploy ingestion router ────────────────────────────────────
deploys_router = APIRouter(tags=["Ops - Deploys"])


@deploys_router.post(
    "/logs/deploys",
    status_code=status.HTTP_201_CREATED,
)
async def create_deploy(
    body: DeployCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    deploy_token = request.headers.get("X-Deploy-Token", "")
    if not secrets.compare_digest(deploy_token, DEPLOY_WEBHOOK_SECRET or ""):
        raise HTTPException(status_code=401, detail="Invalid deploy token")

    deploy = await services.record_deploy(db, body)
    return {"status": "logged", "id": str(deploy.id)}


# ── Ops admin router ───────────────────────────────────────────
ops_router = APIRouter(tags=["Ops - Admin"])


@ops_router.get("/ops")
async def ops_page():
    return FileResponse("ops/templates/error-log.html")


@ops_router.get("/ops/api/me")
async def ops_me(username: str = Depends(require_ops_session)):
    return {"authenticated": True, "username": username}


@ops_router.post("/ops/login", status_code=status.HTTP_204_NO_CONTENT)
async def ops_login(
    body: OpsLoginRequest,
    _: None = Depends(ops_login_limiter),
):
    if not secrets.compare_digest(body.username, OPS_USERNAME or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not secrets.compare_digest(body.password, OPS_PASSWORD or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_ops_session_token(body.username)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    is_prod = os.getenv("ENVIRONMENT") == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        path=COOKIE_PATH,
        max_age=OPS_SESSION_TTL_DAYS * 86400,
    )
    return response


@ops_router.post(
    "/ops/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def ops_logout():
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)
    return response


@ops_router.get("/ops/api/errors", response_model=ErrorListResponse)
async def list_errors(
    error_type: str | None = None,
    status_filter: str = "all",
    q: str | None = None,
    app: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(require_ops_session),
):
    items, total = await services.list_errors(
        db,
        error_type=error_type,
        status=status_filter,
        q=q,
        app=app,
        page=page,
        page_size=page_size,
    )

    out = []
    for item in items:
        user_email = item.user.email if item.user else None
        out.append(
            ClientErrorOut(
                id=item.id,
                message=item.message,
                error_type=item.error_type,
                stack_trace=item.stack_trace,
                route=item.route,
                method=item.method,
                user_id=item.user_id,
                user_email=user_email,
                app=item.app,
                version=item.version,
                stack_hash=item.stack_hash,
                created_at=item.created_at,
                resolved_at=item.resolved_at,
            )
        )

    return ErrorListResponse(items=out, total=total, page=page, page_size=page_size)


@ops_router.post("/ops/api/errors/{error_id}/resolve")
async def resolve_error(
    error_id: UUID,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(require_ops_session),
):
    error = await services.mark_resolved(db, error_id)
    user_email = error.user.email if error.user else None
    return ClientErrorOut(
        id=error.id,
        message=error.message,
        error_type=error.error_type,
        stack_trace=error.stack_trace,
        route=error.route,
        method=error.method,
        user_id=error.user_id,
        user_email=user_email,
        app=error.app,
        version=error.version,
        stack_hash=error.stack_hash,
        created_at=error.created_at,
        resolved_at=error.resolved_at,
    )


@ops_router.post("/ops/api/errors/{error_id}/reopen")
async def reopen_error(
    error_id: UUID,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(require_ops_session),
):
    error = await services.mark_open(db, error_id)
    user_email = error.user.email if error.user else None
    return ClientErrorOut(
        id=error.id,
        message=error.message,
        error_type=error.error_type,
        stack_trace=error.stack_trace,
        route=error.route,
        method=error.method,
        user_id=error.user_id,
        user_email=user_email,
        app=error.app,
        version=error.version,
        stack_hash=error.stack_hash,
        created_at=error.created_at,
        resolved_at=error.resolved_at,
    )


@ops_router.delete(
    "/ops/api/errors/{error_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_error(
    error_id: UUID,
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(require_ops_session),
):
    await services.delete_error(db, error_id)


@ops_router.get("/ops/api/deploys", response_model=DeployListResponse)
async def list_deploys(
    app: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _username: str = Depends(require_ops_session),
):
    items, total = await services.list_deploys(
        db, app=app, page=page, page_size=page_size
    )
    return DeployListResponse(
        items=[DeployOut.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )
