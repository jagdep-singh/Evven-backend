from pydantic import BaseModel

from schemas.user import TokenResponse, UserResponse


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
    tokens: TokenResponse
    # can add phone number and stuff later if we want


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    tokens: TokenResponse
