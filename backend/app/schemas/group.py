from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupResponse(BaseModel):
    id: str
    name: str
    invite_code: str
    is_leader: bool = False
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class GroupDetailResponse(BaseModel):
    id: str
    name: str
    invite_code: str
    leader: "MemberBrief"
    members: list["MemberInfo"]

    class Config:
        from_attributes = True


class MemberBrief(BaseModel):
    id: str
    username: str
    discriminator: str


class MemberInfo(BaseModel):
    id: str
    username: str
    discriminator: str
    joined_at: datetime
    last_synced_at: datetime | None = None


class JoinGroupRequest(BaseModel):
    invite_code: str


class TransferLeadershipRequest(BaseModel):
    new_leader_id: str
