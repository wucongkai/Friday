"""领域实体（纯数据，无 I/O）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from friday.domain.value_objects import (
    ConfirmationStatus,
    DraftStatus,
    RiskLevel,
    TaskStatus,
)


@dataclass
class Task:
    id: str
    type: str
    params: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: dict | None = None
    confirm_token: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmailMessage:
    message_id: str
    folder: str
    uid: int
    uidvalidity: int
    subject: str
    sender: str
    recipients: list[str] = field(default_factory=list)
    body: str = ""
    thread_id: str | None = None
    received_at: datetime | None = None


@dataclass
class Draft:
    id: str
    subject: str
    to: str
    body: str
    email_id: str | None = None
    status: DraftStatus = DraftStatus.NEW


@dataclass
class Confirmation:
    token: str
    action: str
    risk: RiskLevel
    summary: dict
    consequences: str
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    expires_at: datetime | None = None


@dataclass
class Hit:
    path: str
    line: int
    snippet: str
    title: str | None = None


@dataclass
class Document:
    path: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    mtime: float = 0.0
