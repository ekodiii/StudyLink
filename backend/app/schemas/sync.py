from datetime import datetime

from pydantic import BaseModel


class SubmissionData(BaseModel):
    status: str = "unsubmitted"
    submitted_at: datetime | None = None


class AssignmentData(BaseModel):
    canvas_assignment_id: str
    name: str
    due_at: datetime | None = None
    points_possible: float | None = None
    submission: SubmissionData | None = None


class CourseData(BaseModel):
    canvas_course_id: str
    name: str
    course_code: str | None = None
    assignments: list[AssignmentData] = []


class SyncRequest(BaseModel):
    institution_domain: str
    canvas_user_id: str
    courses: list[CourseData] = []


class SyncResponse(BaseModel):
    synced_courses: int
    synced_assignments: int
    new_courses_needing_visibility: list[dict] = []
    hidden_course_ids: list[str] = []
