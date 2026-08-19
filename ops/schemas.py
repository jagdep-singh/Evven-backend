from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ClientErrorCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    error_type: str | None = Field(None, max_length=100)
    stack_trace: str | None = None
    route: str | None = Field(None, max_length=500)
    method: str | None = Field(None, max_length=20)
    app: Literal["web", "mobile"] = Field("web")
    version: str | None = Field(None, max_length=50)
    client_timestamp: datetime | None = None


class ClientErrorOut(BaseModel):
    id: UUID
    message: str
    error_type: str | None = None
    stack_trace: str | None = None
    route: str | None = None
    method: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    app: str
    version: str | None = None
    stack_hash: str
    created_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True


class DeployCreate(BaseModel):
    app: Literal["frontend", "backend"]
    environment: str = Field("production", max_length=20)
    commit_sha: str = Field(..., min_length=1, max_length=64)
    branch: str | None = Field(None, max_length=100)
    actor: str = Field(..., min_length=1, max_length=200)
    commit_message: str | None = Field(None, max_length=500)
    source: str = Field("github_actions", max_length=20)
    run_id: str | None = Field(None, max_length=100)


class DeployOut(BaseModel):
    id: UUID
    app: str
    environment: str
    commit_sha: str
    branch: str | None = None
    actor: str
    commit_message: str | None = None
    source: str
    run_id: str | None = None
    pushed_at: datetime

    class Config:
        from_attributes = True


class ErrorListResponse(BaseModel):
    items: list[ClientErrorOut]
    total: int
    page: int
    page_size: int


class DeployListResponse(BaseModel):
    items: list[DeployOut]
    total: int
    page: int
    page_size: int


class OpsLoginRequest(BaseModel):
    username: str
    password: str
