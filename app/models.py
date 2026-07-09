from datetime import date
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Text, text
from sqlmodel import Field, SQLModel


class Status(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    ARCHIVED = "archived"


class Project(SQLModel, table=True):
    __tablename__ = "project"
    __table_args__ = (
        Index(
            "ix_project_title_active",
            "title",
            unique=True,
            sqlite_where=text("deleted = false"),
        ),
        Index(
            "ix_project_serial_num_active",
            "serial_num",
            unique=True,
            sqlite_where=text("deleted = false"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    serial_num: int
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    start_date: date | None = Field(default=None)
    finished_date: date | None = Field(default=None)
    notes: str | None = Field(default=None, sa_type=Text)
    status: Status = Field(
        default=Status.NEW,
        sa_type=SAEnum(Status, name="status", values_callable=lambda enum: [e.value for e in enum]),
    )
    deleted: bool = Field(default=False)


class GroupTask(SQLModel, table=True):
    __tablename__ = "group_task"
    __table_args__ = (
        Index(
            "ix_group_task_project_title_active",
            "project_id",
            "title",
            unique=True,
            sqlite_where=text("deleted = false"),
        ),
        Index(
            "ix_group_task_project_serial_num_active",
            "project_id",
            "serial_num",
            unique=True,
            sqlite_where=text("deleted = false"),
        ),
        Index("ix_group_task_project_id", "project_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    serial_num: int
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    start_date: date | None = Field(default=None)
    finished_date: date | None = Field(default=None)
    notes: str | None = Field(default=None, sa_type=Text)
    status: Status = Field(
        default=Status.NEW,
        sa_type=SAEnum(Status, name="status", values_callable=lambda enum: [e.value for e in enum]),
    )
    deleted: bool = Field(default=False)
