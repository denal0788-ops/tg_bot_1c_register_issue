from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


PRIORITY_NAMES: dict[Priority, str] = {
    Priority.LOW: "Низкий",
    Priority.NORMAL: "Обычный",
    Priority.HIGH: "Высокий",
}


class Category(BaseModel):
    id: str
    name: str


class CategoryList(BaseModel):
    items: list[Category]


class IssueCreate(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = None
    telegram_full_name: str
    category_id: str
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    priority: Priority


class Issue(BaseModel):
    id: str
    number: str
    category_name: str = ""
    subject: str = ""
    description: str = ""
    priority: Priority = Priority.NORMAL
    priority_name: str = "Обычный"
    status: str
    status_name: str
    created_at: datetime


class IssueList(BaseModel):
    items: list[Issue]
