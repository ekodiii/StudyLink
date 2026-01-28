from datetime import datetime

from pydantic import BaseModel


class ProgressAssignment(BaseModel):
    assignment_id: str
    name: str
    due_at: datetime | None = None
    status: str
    submitted_at: datetime | None = None


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
