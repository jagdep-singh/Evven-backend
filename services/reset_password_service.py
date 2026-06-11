import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import resend
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import (
    BACKEND_URL,
    RESEND_API_KEY,
    RESEND_FROM,
)
from models.user import AuthProvider
from repository.reset_token_repositery import ResetRepositery
from repository.user_repository import UserRepository
from services.auth_service import hash_password

resend.api_key = RESEND_API_KEY


async def request_password_reset(email: str, db: AsyncSession):
    repo = UserRepository(db)
    repo_auth = ResetRepositery(db)
    user = await repo.get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=404, detail="No account found with that email address"
        )

    if user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(status_code=400, detail="This account uses Google Sign-In")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    await repo_auth.save_reset_token(user.id, token_hash, expire_at)

    email_sent = await send_reset_email(user.email, raw_token)

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

    return {"success": True, "message": "Reset email sent"}


async def reset_password(token: str, new_password: str, db: AsyncSession):
    repo_auth = ResetRepositery(db)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    reset_record = await repo_auth.get_valid_reset_token(token_hash)

    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    repo = UserRepository(db)
    user = await repo.get_user_by_id(reset_record.user_id)
    user.password_hash = hash_password(new_password)
    await repo.update_user(user)

    await repo_auth.mark_token_as_used(reset_record)

    return {"message": "Password reset successfully"}


async def send_reset_email(to_email: str, raw_token: str):
    reset_url = f"{BACKEND_URL}/auth/reset-password?token={raw_token}"

    html_content = Path("templates/email/password-reset-email.html").read_text(
        encoding="utf-8"
    )

    html_content = html_content.replace(
        "__RESET_URL__",
        reset_url,
    )

    try:
        resend.Emails.send(
            {
                "from": f"Evven <{RESEND_FROM}>",
                "to": [to_email],
                "subject": "Reset Your Password",
                "html": html_content,
            }
        )
        return True
    except Exception as e:
        print(f"[send_reset_email] failed for {to_email}: {e}")
        return False
