"""依赖注入容器：按配置把适配器装配给用例。

P0 只装配配置；后续里程碑在此逐步接入真实适配器，
从而让 application 层始终只依赖 ports，不依赖具体实现。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from friday.config import Config, load_config

if TYPE_CHECKING:
    from friday.domain.ports import (
        BrowserPort,
        KnowledgeStore,
        LLMClient,
        MailPort,
        NotifierPort,
        StateStore,
    )


@dataclass
class Container:
    config: Config
    llm: "LLMClient | None" = None
    knowledge: "KnowledgeStore | None" = None
    mail: "MailPort | None" = None
    browser: "BrowserPort | None" = None
    state: "StateStore | None" = None
    notifier: "NotifierPort | None" = None


def build_container(config: Config | None = None) -> Container:
    """装配容器。P0 阶段仅挂载配置，适配器后续接入。"""
    cfg = config or load_config()
    return Container(config=cfg)
