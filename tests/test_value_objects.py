from friday.domain.value_objects import (
    RiskLevel,
    TaskStatus,
    can_transition,
)


def test_risk_level_ordering():
    assert (
        RiskLevel.READ.rank
        < RiskLevel.DRAFT.rank
        < RiskLevel.SUBMIT.rank
        < RiskLevel.DANGER.rank
    )


def test_requires_confirmation():
    assert not RiskLevel.READ.requires_confirmation()
    assert not RiskLevel.DRAFT.requires_confirmation()
    assert RiskLevel.SUBMIT.requires_confirmation()
    assert RiskLevel.DANGER.requires_confirmation()


def test_task_transitions():
    assert can_transition(TaskStatus.PENDING, TaskStatus.RUNNING)
    assert not can_transition(TaskStatus.PENDING, TaskStatus.DONE)
    assert can_transition(TaskStatus.RUNNING, TaskStatus.AWAITING_CONFIRMATION)
    assert not can_transition(TaskStatus.DONE, TaskStatus.RUNNING)
    assert can_transition(TaskStatus.FAILED, TaskStatus.RUNNING)  # 失败可重试
