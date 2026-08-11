from pydantic import BaseModel, EmailStr

from schemas.user import TokenResponse, UserResponse


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
    # Tokens should not be send in RegisterResponse
    # tokens: TokenResponse | None = None


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    tokens: TokenResponse


class SendOtpResponse(BaseModel):
    message: str
    challenge_token: str | None = None


class VerifyOtpResponse(BaseModel):
    message: str
    user: UserResponse | None = None
    tokens: TokenResponse | None = None
    signup_token: str | None = None
    email: EmailStr | None = None


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = "email_verification"


class VerifyOtpRequest(BaseModel):
    email: EmailStr | None = None
    otp: str
    purpose: str = "email_verification"
    challenge_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
