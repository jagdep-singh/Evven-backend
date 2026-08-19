import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops.models import ClientError, DeployLog
from ops.schemas import ClientErrorCreate, DeployCreate


def _compute_stack_hash(
    message: str, stack_trace: str | None, error_type: str | None
) -> str:
    raw = f"{stack_trace or message}{error_type or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_error_log(
    db: AsyncSession,
    data: ClientErrorCreate,
    user_id: UUID | None = None,
) -> ClientError | None:
    stack_hash = _compute_stack_hash(data.message, data.stack_trace, data.error_type)

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
    stmt = select(ClientError).where(
        ClientError.stack_hash == stack_hash,
        ClientError.created_at > cutoff,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return None

    error = ClientError(
        message=data.message,
        error_type=data.error_type,
        stack_trace=data.stack_trace,
        route=data.route,
        method=data.method,
        user_id=user_id,
        app=data.app,
        version=data.version,
        stack_hash=stack_hash,
        client_timestamp=data.client_timestamp,
    )
    db.add(error)
    await db.commit()
    await db.refresh(error)
    return error


async def list_errors(
    db: AsyncSession,
    *,
    error_type: str | None = None,
    status: str = "all",
    q: str | None = None,
    app: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ClientError], int]:
    query = select(ClientError)
    count_query = select(func.count(ClientError.id))

    if error_type:
        query = query.where(ClientError.error_type == error_type)
        count_query = count_query.where(ClientError.error_type == error_type)

    if status == "open":
        query = query.where(ClientError.resolved_at.is_(None))
        count_query = count_query.where(ClientError.resolved_at.is_(None))
    elif status == "resolved":
        query = query.where(ClientError.resolved_at.isnot(None))
        count_query = count_query.where(ClientError.resolved_at.isnot(None))

    if q:
        like_pattern = f"%{q}%"
        query = query.where(
            ClientError.message.ilike(like_pattern)
            | ClientError.route.ilike(like_pattern)
        )
        count_query = count_query.where(
            ClientError.message.ilike(like_pattern)
            | ClientError.route.ilike(like_pattern)
        )

    if app:
        query = query.where(ClientError.app == app)
        count_query = count_query.where(ClientError.app == app)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ClientError.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def mark_resolved(db: AsyncSession, error_id: UUID) -> ClientError:
    stmt = select(ClientError).where(ClientError.id == error_id)
    result = await db.execute(stmt)
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    error.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(error)
    return error


async def mark_open(db: AsyncSession, error_id: UUID) -> ClientError:
    stmt = select(ClientError).where(ClientError.id == error_id)
    result = await db.execute(stmt)
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    error.resolved_at = None
    await db.commit()
    await db.refresh(error)
    return error


async def delete_error(db: AsyncSession, error_id: UUID) -> None:
    stmt = select(ClientError).where(ClientError.id == error_id)
    result = await db.execute(stmt)
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")

    await db.delete(error)
    await db.commit()


async def prune_errors(
    db: AsyncSession,
    *,
    older_than: timedelta,
    resolved_only: bool = False,
) -> int:
    from sqlalchemy import delete

    cutoff = datetime.now(timezone.utc) - older_than
    where = [ClientError.created_at < cutoff]
    if resolved_only:
        where.append(ClientError.resolved_at.isnot(None))

    stmt = delete(ClientError).where(*where)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def record_deploy(db: AsyncSession, data: DeployCreate) -> DeployLog:
    deploy = DeployLog(
        app=data.app,
        environment=data.environment,
        commit_sha=data.commit_sha,
        branch=data.branch,
        actor=data.actor,
        commit_message=data.commit_message,
        source=data.source,
        run_id=data.run_id,
    )
    db.add(deploy)
    await db.commit()
    await db.refresh(deploy)
    return deploy


async def list_deploys(
    db: AsyncSession,
    *,
    app: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[DeployLog], int]:
    query = select(DeployLog)
    count_query = select(func.count(DeployLog.id))

    if app:
        query = query.where(DeployLog.app == app)
        count_query = count_query.where(DeployLog.app == app)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DeployLog.pushed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total
