"""值对象与枚举：风险等级、任务状态等。

RiskLevel 是安全的核心：任何会改变外部状态的动作都必须标注等级。
"""
from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    READ = "read"        # 只读，自动执行
    DRAFT = "draft"      # 生成草稿，展示后待确认
    SUBMIT = "submit"    # 提交，必须逐字段回显 + 明确确认
    DANGER = "danger"    # 撤销投递/删除账号等破坏性操作：默认拒绝，绝不自动触发

    @property
    def rank(self) -> int:
        return {
            RiskLevel.READ: 0,
            RiskLevel.DRAFT: 1,
            RiskLevel.SUBMIT: 2,
            RiskLevel.DANGER: 3,
        }[self]

    def requires_confirmation(self) -> bool:
        """是否必须经过人工确认关卡。"""
        return self.rank >= RiskLevel.SUBMIT.rank


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"


class DraftStatus(str, Enum):
    NEW = "new"
    EDITED = "edited"
    CONFIRMED = "confirmed"
    SENT = "sent"


class ConfirmationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


# 允许的状态迁移（确定性状态机，不交给 LLM）
ALLOWED_TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELED},
    TaskStatus.RUNNING: {TaskStatus.AWAITING_CONFIRMATION, TaskStatus.DONE, TaskStatus.FAILED},
    TaskStatus.AWAITING_CONFIRMATION: {TaskStatus.DONE, TaskStatus.CANCELED, TaskStatus.RUNNING},
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: {TaskStatus.RUNNING},
    TaskStatus.CANCELED: set(),
}


def can_transition(src: TaskStatus, dst: TaskStatus) -> bool:
    return dst in ALLOWED_TASK_TRANSITIONS.get(src, set())
