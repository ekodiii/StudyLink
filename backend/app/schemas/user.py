from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: str
    username: str
    discriminator: str

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
