from datetime import datetime as dt
from uuid import UUID

from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name : str
    email: EmailStr
    password: str
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class GoogleAuthRequest(BaseModel):
    token: str
    
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    
class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    auth_provider: str
    profile_picture: str | None = None
    created_at: dt
    
    model_config = {
        "from_attributes": True
    }
    
class UserUpdate(BaseModel):
    name: str | None = None
    profile_picture: str | None = None
    
    