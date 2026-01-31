from datetime import datetime

from pydantic import BaseModel


class VerificationCreateRequest(BaseModel):
    assignment_id: str
    verifier_id: str
    group_id: str


class VerificationConfirmRequest(BaseModel):
    verification_word: str


class VerificationResponse(BaseModel):
    id: str
    assignment_id: str
    assignment_name: str
    group_id: str
    group_name: str
    requester_id: str
    requester_username: str
    verifier_id: str
    verifier_username: str
    status: str
    verification_word: str
    requested_at: datetime
    verified_at: datetime | None = None
