from pydantic import BaseModel, EmailStr

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


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
