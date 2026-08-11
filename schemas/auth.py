from pydantic import BaseModel, EmailStr

from schemas.user import TokenResponse, UserResponse


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    tokens: TokenResponse


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = "email_verification"


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    purpose: str = "email_verification"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
