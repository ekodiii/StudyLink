from datetime import datetime

from pydantic import BaseModel


class VerificationBrief(BaseModel):
    id: str
    status: str
    verification_word: str
    verifier_id: str
    verifier_username: str
    requester_id: str
    requester_username: str


class ProgressAssignment(BaseModel):
    assignment_id: str
    name: str
    due_at: datetime | None = None
    status: str
    submitted_at: datetime | None = None
    verification: VerificationBrief | None = None


class ProgressCourse(BaseModel):
    course_id: str
    name: str
    course_code: str | None = None
    institution: str | None = None
    assignments: list[ProgressAssignment] = []


class ProgressMember(BaseModel):
    user_id: str
    username: str
    discriminator: str
    last_synced_at: datetime | None = None
    courses: list[ProgressCourse] = []


class GroupProgressResponse(BaseModel):
    group_id: str
    group_name: str
    members: list[ProgressMember] = []


class DashboardAssignment(BaseModel):
    assignment_id: str
    name: str
    due_at: datetime | None = None
    status: str
    course_name: str
    member_username: str
    member_user_id: str


class GroupDashboardResponse(BaseModel):
    upcoming: list[DashboardAssignment] = []
    missing: list[DashboardAssignment] = []
