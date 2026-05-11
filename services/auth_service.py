from models.user import AuthProvider, User
from fastapi import HTTPException #type: ignore
from sqlalchemy.ext.asyncio import AsyncSession #type: ignore

from datetime import datetime, timedelta

from jose import jwt, JWTError #type: ignore
from passlib.context import CryptContext #type: ignore

from repos.user_repository import UserRepository
from schemas.user import UserCreate , UserLogin

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def password_hashing(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(
        plain_password: str, 
        hashed_password: str
    ) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(
        data: dict, 
        expires_delta: timedelta | None = None
    ) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
        data: dict, 
        expires_delta: timedelta | None = None
    ) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
    
async def register_user(
        user_data : UserCreate, 
        db : AsyncSession
    ) -> dict:
    
    repo = UserRepository(db)
    
    existing_user = await repo.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )
    
    hashed_password = password_hashing(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        auth_provider=AuthProvider.LOCAL
    )
    
    created_user = await repo.create_user(new_user)
    
    payload = {
        "sub": str(created_user.id)
    }
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    
    return {
        "message": "User created successfully",
        "user": created_user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
async def login_user(
        login_data : UserLogin, 
        db : AsyncSession
    ) -> dict:
    
    repo = UserRepository(db)
    
    user = await repo.get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=401, 
            detail="Invalid email or password"
        )
    
    payload = {
        "sub": str(user.id)
    }
    
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    
    return {
        "message": "Login successful",
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
