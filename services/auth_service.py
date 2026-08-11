import hashlib
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import resend
from fastapi import HTTPException  # type: ignore
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    GOOGLE_CLIENT_ID,
    REFRESH_TOKEN_EXPIRE_DAYS,
    RESEND_API_KEY,
    RESEND_FROM,
    RESET_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
)
from models.user import AuthProvider, User
from repository.email_verification_repository import EmailVerificationRepository
from repository.refresh_token_repository import RefreshTokenRepository
from repository.user_repository import UserRepository
from schemas.auth import (
    LoginResponse,
    RegisterResponse,
    SendOtpResponse,
    VerifyOtpResponse,
)
from schemas.user import GoogleAuthRequest, TokenResponse, UserCreate, UserLogin
from utils.user_utils import generate_user_code

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
resend.api_key = RESEND_API_KEY


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_temporary_token(
    data: dict,
    *,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    to_encode = data.copy()
    expire = utc_now() + expires_delta
    to_encode.update(
        {
            "exp": expire,
            "type": token_type,
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
    expires_at: datetime | None = None,
) -> str:
    to_encode = data.copy()
    if expires_at:
        expire = expires_at
    elif expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": str(to_encode.get("jti") or uuid4()),
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token_with_claims(
    *,
    user_id: UUID,
    token_id: UUID,
    expires_at: datetime,
) -> str:
    return create_refresh_token(
        {"sub": str(user_id), "jti": str(token_id)},
        expires_at=expires_at,
    )


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


async def issue_token_pair(user: User, db: AsyncSession) -> TokenResponse:
    refresh_token_id = uuid4()
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token_with_claims(
        user_id=user.id,
        token_id=refresh_token_id,
        expires_at=expires_at,
    )

    refresh_repo = RefreshTokenRepository(db)
    await refresh_repo.create(
        token_id=refresh_token_id,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        family_id=refresh_token_id,
        expires_at=expires_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def cleanup_old_refresh_tokens(
    refresh_repo: RefreshTokenRepository,
) -> None:
    try:
        cutoff = utc_now() - timedelta(days=7)
        await refresh_repo.delete_expired_before(cutoff)
    except Exception:
        pass


async def rotate_refresh_token(
    raw_refresh_token: str, db: AsyncSession
) -> TokenResponse:
    payload = decode_token(raw_refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    token_id = payload.get("jti")
    if not user_id or not token_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = UUID(user_id)
        token_uuid = UUID(token_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    refresh_repo = RefreshTokenRepository(db)
    row = await refresh_repo.get_by_id(token_uuid)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    now = utc_now()
    if row.token_hash != hash_refresh_token(raw_refresh_token):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if row.revoked_at is not None:
        await refresh_repo.revoke_family(row.family_id, now)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if ensure_aware(row.expires_at) < now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    repo = UserRepository(db)
    user = await repo.get_user_by_id(user_uuid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_token_id = uuid4()
    new_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token_with_claims(
        user_id=user.id,
        token_id=new_token_id,
        expires_at=new_expires_at,
    )

    await refresh_repo.rotate(
        current_token=row,
        new_token_id=new_token_id,
        new_token_hash=hash_refresh_token(new_refresh_token),
        new_expires_at=new_expires_at,
        revoked_at=now,
    )

    if random.random() < 0.01:
        await cleanup_old_refresh_tokens(refresh_repo)

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


async def revoke_refresh_token(
    raw_refresh_token: str,
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
) -> None:
    payload = decode_token(raw_refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    token_id = payload.get("jti")
    if not token_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        token_uuid = UUID(token_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    refresh_repo = RefreshTokenRepository(db)
    row = await refresh_repo.get_by_id(token_uuid)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if user_id is not None and row.user_id != user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if row.token_hash != hash_refresh_token(raw_refresh_token):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if row.revoked_at is None:
        await refresh_repo.revoke(row, utc_now())


async def register_user(user_data: UserCreate, db: AsyncSession) -> RegisterResponse:
    repo = UserRepository(db)
    verification_repo = EmailVerificationRepository(db)

    existing_user = await repo.get_user_by_email(user_data.email)

    signup_verified_email: str | None = None
    if user_data.signup_token:
        payload = decode_token(user_data.signup_token, expected_type="signup_verified")
        if not payload:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired signup verification token",
            )

        signup_verified_email = payload.get("email")
        if not signup_verified_email:
            raise HTTPException(
                status_code=400,
                detail="Invalid signup verification token",
            )

        if str(user_data.email).lower() != str(signup_verified_email).lower():
            raise HTTPException(
                status_code=400,
                detail="Signup verification token does not match the email",
            )
        if existing_user and existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Email already registered")
    elif existing_user:
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
        is_verified=bool(signup_verified_email),
    )

    if existing_user and signup_verified_email:
        existing_user.name = user_data.name
        existing_user.password_hash = hashed_password
        existing_user.auth_provider = AuthProvider.LOCAL
        existing_user.is_verified = True
        created_user = await repo.update_user(existing_user)
    else:
        created_user = await repo.create_user(new_user)

    if signup_verified_email:
        return RegisterResponse(
            message="User created successfully.",
            user=created_user,
            tokens=await issue_token_pair(created_user, db),
        )

    token = await create_and_send_verification_code(
        user=created_user, repo=verification_repo
    )

    if not token:
        await repo.delete_user(created_user)
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email",
        )

    return RegisterResponse(
        message="User created successfully. Check your email for the verification code.",
        user=created_user,
    )


async def login_user(login_data: UserLogin, db: AsyncSession) -> LoginResponse:
    repo = UserRepository(db)

    user = await repo.get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in.",
        )

    return LoginResponse(
        message="Login successful",
        user=user,
        tokens=await issue_token_pair(user, db),
    )


async def google_login(auth_data: GoogleAuthRequest, db: AsyncSession) -> LoginResponse:

    repo = UserRepository(db)
    try:
        idinfo = google_id_token.verify_oauth2_token(
            auth_data.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = idinfo["sub"]
    email = idinfo.get("email")
    name = idinfo.get("name") or (email.split("@")[0] if email else "User")
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = await repo.get_user_by_google_id(google_id)

    if not user:
        existing_email_user = await repo.get_user_by_email(email)

        if existing_email_user:
            if existing_email_user.auth_provider == AuthProvider.LOCAL:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered with password login. Please log in with your password instead.",
                )
            # Edge case: same email under GOOGLE provider but different google_id somehow
            user = existing_email_user
        else:
            while True:
                code = generate_user_code()
                existing = await repo.get_user_by_user_code(code)
                if not existing:
                    break

            new_user = User(
                user_code=code,
                name=name,
                email=email,
                google_id=google_id,
                auth_provider=AuthProvider.GOOGLE,
                profile_picture=picture,
            )
            user = await repo.create_user(new_user)

    return LoginResponse(
        message="Google login successful",
        user=user,
        tokens=await issue_token_pair(user, db),
    )


def _generate_verification_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_verification_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


async def send_verification_email(to_email: str, otp: str, name: str) -> bool:
    html_content = (
        Path("templates/email/email-verification-otp.html")
        .read_text(encoding="utf-8")
        .replace("__USER_NAME__", name)
        .replace("__OTP_CODE__", otp)
        .replace("__EXPIRY_MINUTES__", str(RESET_TOKEN_EXPIRE_MINUTES))
    )

    try:
        resend.Emails.send(
            {
                "from": f"Evven <{RESEND_FROM}>",
                "to": [to_email],
                "subject": "Verify your Evven email",
                "html": html_content,
            }
        )
        return True
    except Exception as exc:
        print(f"[send_verification_email] failed for {to_email}: {exc}")
        return False


async def create_and_send_verification_code(
    *,
    user: User,
    repo: EmailVerificationRepository,
) -> str | None:
    otp = _generate_verification_otp()
    token = await repo.create_token(
        user_id=user.id,
        token_hash=_hash_verification_otp(otp),
        expires_at=utc_now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )

    sent = await send_verification_email(user.email, otp, user.name)
    if not sent:
        await repo.delete_token(token)
        return None

    return otp


async def create_and_send_signup_verification_code(
    *,
    email: str,
    repo: UserRepository,
) -> dict[str, str]:
    existing_user = await repo.get_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp = _generate_verification_otp()
    challenge_token = create_temporary_token(
        {
            "email": email,
            "otp_hash": _hash_verification_otp(otp),
        },
        token_type="signup_challenge",
        expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )

    sent = await send_verification_email(
        email,
        otp,
        email.split("@", 1)[0] if "@" in email else "there",
    )
    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email",
        )

    return {
        "message": "Verification code sent",
        "challenge_token": challenge_token,
    }


async def resend_verification_code(email: str, db: AsyncSession) -> dict[str, str]:
    repo = UserRepository(db)
    verification_repo = EmailVerificationRepository(db)

    user = await repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account is already verified")

    otp = await create_and_send_verification_code(user=user, repo=verification_repo)

    if not otp:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    return {"message": "Verification code sent"}


async def send_otp_for_signup(email: str, db: AsyncSession) -> dict[str, str]:
    repo = UserRepository(db)
    return await create_and_send_signup_verification_code(email=email, repo=repo)


async def verify_otp(
    email: str | None,
    otp: str,
    db: AsyncSession,
    *,
    purpose: str = "email_verification",
    challenge_token: str | None = None,
) -> VerifyOtpResponse:
    repo = UserRepository(db)

    if purpose == "signup":
        if not challenge_token:
            raise HTTPException(
                status_code=400, detail="Signup verification token is required"
            )

        payload = decode_token(challenge_token, expected_type="signup_challenge")
        if not payload:
            raise HTTPException(
                status_code=400, detail="Invalid or expired signup verification token"
            )

        token_email = payload.get("email")
        token_hash = payload.get("otp_hash")
        if not token_email or not token_hash:
            raise HTTPException(
                status_code=400, detail="Invalid signup verification token"
            )

        if email and str(email).lower() != str(token_email).lower():
            raise HTTPException(
                status_code=400, detail="Signup verification email does not match"
            )

        if token_hash != _hash_verification_otp(otp):
            raise HTTPException(
                status_code=400, detail="Invalid or expired verification code"
            )

        signup_token = create_temporary_token(
            {"email": token_email},
            token_type="signup_verified",
            expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )

        return VerifyOtpResponse(
            message="Email verified successfully",
            signup_token=signup_token,
            email=token_email,
        )

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    verification_repo = EmailVerificationRepository(db)

    user = await repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account is already verified")

    token = await verification_repo.get_latest_valid_token(user.id)
    if not token or token.token_hash != _hash_verification_otp(otp):
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification code"
        )

    user.is_verified = True
    await repo.update_user(user)
    await verification_repo.mark_token_as_used(token)

    return VerifyOtpResponse(
        message="Email verified successfully",
        user=user,
        tokens=await issue_token_pair(user, db),
    )
