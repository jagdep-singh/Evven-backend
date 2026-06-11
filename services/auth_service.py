from datetime import datetime, timedelta, timezone

from fastapi import HTTPException  # type: ignore
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from models.user import AuthProvider, User
from repository.user_repository import UserRepository
from schemas.auth import LoginResponse, RegisterResponse
from schemas.user import TokenResponse, UserCreate, UserLogin
from utils.user_utils import generate_user_code

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# resend.api_key = RESEND_API_KEY


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(
    token: str,
    expected_type: str | None = None,
) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if expected_type and payload.get("type") != expected_type:
            return None

        return payload

    except JWTError:
        return None


async def register_user(user_data: UserCreate, db: AsyncSession) -> RegisterResponse:
    repo = UserRepository(db)

    existing_user = await repo.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    while True:
        code = generate_user_code()

        existing = await repo.get_user_by_user_code(code)

        if not existing:
            break

    hashed_password = hash_password(user_data.password)

    new_user = User(
        user_code=code,
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        auth_provider=AuthProvider.LOCAL,
    )

    created_user = await repo.create_user(new_user)

    payload = {"sub": str(created_user.id)}
    access_token = create_access_token(payload)

    refresh_token = create_refresh_token(payload)

    return RegisterResponse(
        message="User created successfully",
        user=created_user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
    )


async def login_user(login_data: UserLogin, db: AsyncSession) -> LoginResponse:
    repo = UserRepository(db)

    user = await repo.get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    payload = {"sub": str(user.id)}

    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    return LoginResponse(
        message="Login successful",
        user=user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
    )


# async def request_password_reset(email: str, db: AsyncSession):
#     repo = UserRepository(db)
#     repo_auth = AuthRepository(db)
#     user = await repo.get_user_by_email(email)

#     if not user:
#         raise HTTPException(
#             status_code=404, detail="No account found with that email address"
#         )

#     if user.auth_provider != AuthProvider.LOCAL:
#         raise HTTPException(status_code=400, detail="This account uses Google Sign-In")

#     raw_token = secrets.token_urlsafe(32)
#     token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
#     expire_at = datetime.now(timezone.utc) + timedelta(minutes=10)

#     await repo_auth.save_reset_token(user.id, token_hash, expire_at)

#     email_sent = await send_reset_email(user.email, raw_token)

#     if not email_sent:
#         raise HTTPException(status_code=500, detail="Failed to send reset email")

#     return {"success": True, "message": "Reset email sent"}


# async def reset_password(token: str, new_password: str, db: AsyncSession):
#     repo_auth = AuthRepository(db)
#     token_hash = hashlib.sha256(token.encode()).hexdigest()

#     reset_record = await repo_auth.get_valid_reset_token(token_hash)

#     if not reset_record:
#         raise HTTPException(status_code=400, detail="Invalid or expired token")

#     repo = UserRepository(db)
#     user = await repo.get_user_by_id(reset_record.user_id)
#     user.password_hash = hash_password(new_password)
#     await repo.update_user(user)

#     await repo_auth.mark_token_as_used(reset_record)

#     return {"message": "Password reset successfully"}


# async def send_reset_email(to_email: str, raw_token: str):
#     reset_url = f"{BACKEND_URL}/auth/reset-password?token={raw_token}"

#     html_content = Path("templates/email/password-reset-email.html").read_text(
#         encoding="utf-8"
#     )

#     html_content = html_content.replace(
#         "__RESET_URL__",
#         reset_url,
#     )

#     try:
#         resend.Emails.send(
#             {
#                 "from": f"Evven <{RESEND_FROM}>",
#                 "to": [to_email],
#                 "subject": "Reset Your Password",
#                 "html": html_content,
#             }
#         )
#         return True
#     except Exception as e:
#         print(f"[send_reset_email] failed for {to_email}: {e}")
#         return False


# Created a delete token Function in user_repo and added a template for reset password in main.py
