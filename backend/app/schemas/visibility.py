from pydantic import BaseModel


class VisibilityDecision(BaseModel):
    course_id: str
    group_id: str
    visible: bool


class VisibilityDecideRequest(BaseModel):
    decisions: list[VisibilityDecision]


class PendingCourseGroup(BaseModel):
    group_id: str
    group_name: str


class PendingCourse(BaseModel):
    course_id: str
    course_name: str
    course_code: str | None = None
    institution: str | None = None
    groups: list[PendingCourseGroup] = []


class PendingResponse(BaseModel):
    pending: list[PendingCourse] = []


class VisibilitySettingItem(BaseModel):
    course_id: str
    course_name: str
    group_id: str
    group_name: str
    visible: bool


class VisibilitySettingsResponse(BaseModel):
    settings: list[VisibilitySettingItem] = []
