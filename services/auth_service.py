from datetime import datetime, timedelta, timezone

from fastapi import HTTPException  # type: ignore
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    GOOGLE_CLIENT_ID,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from models.user import AuthProvider, User
from repository.user_repository import UserRepository
from schemas.auth import LoginResponse, RegisterResponse
from schemas.user import GoogleAuthRequest, TokenResponse, UserCreate, UserLogin
from utils.user_utils import generate_user_code

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


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


async def google_login(auth_data: GoogleAuthRequest, db: AsyncSession) -> LoginResponse:

    repo = UserRepository(db)
    try:
        idinfo = google_id_token.verify_oauth2_token(auth_data.token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    google_id = idinfo["sub"]
    email = idinfo.get("email")
    name = idinfo.get("name") or (email.split('@')[0] if email else "User")
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

    payload = {"sub": str(user.id)}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    return LoginResponse(
        message="Google login successful",
        user=user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
    )