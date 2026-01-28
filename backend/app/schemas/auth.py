from pydantic import BaseModel


class AppleAuthRequest(BaseModel):
    identity_token: str
    authorization_code: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserBrief"


class UserBrief(BaseModel):
    id: str
    username: str
    discriminator: str
    is_new_user: bool = False

    class Config:
        from_attributes = True


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
