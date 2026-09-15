"""任务编排：确定性状态机 + 确认关卡。

业务规则（状态迁移、风险分级、确认）都在这里用代码表达，不交给 LLM。
"""
from __future__ import annotations

from dataclasses import dataclass

from friday.domain.entities import Task
from friday.domain.value_objects import RiskLevel, TaskStatus, can_transition


class InvalidTransition(Exception):
    """非法的任务状态迁移。"""


@dataclass
class Orchestrator:
    """P0：只提供状态机；P1 起接入任务队列与用例分派。"""

    def transition(self, task: Task, to: TaskStatus) -> None:
        if not can_transition(task.status, to):
            raise InvalidTransition(f"非法迁移：{task.status.value} -> {to.value}")
        task.status = to

    def requires_confirmation(self, risk: RiskLevel) -> bool:
        return risk.requires_confirmation()
