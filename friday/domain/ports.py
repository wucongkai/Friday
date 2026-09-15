"""端口接口（Ports）：核心与外部世界之间的契约。

只定义能力，不依赖任何具体实现。基础设施层的 Adapter 必须满足这些契约。
换实现 = 换 Adapter，domain/application 零改动。
"""
from __future__ import annotations

from typing import Any, Protocol, Sequence

from friday.domain.entities import Document, Draft, EmailMessage, Hit


class LLMClient(Protocol):
    """模型能力的最小封装。换模型 = 换实现 / 换配置，不动业务。"""

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Any:
        """返回结构化完成结果（具体结构由 Adapter 约定）。"""
        ...


class KnowledgeStore(Protocol):
    """个人数据库：索引、检索、读写，回答可定位到原文。"""

    def search(self, query: str, *, limit: int = 10) -> list[Hit]: ...
    def get(self, path: str) -> Document: ...
    def save(self, doc: Document) -> None: ...
    def reindex(self, path: str | None = None) -> None: ...


class MailPort(Protocol):
    """只负责网络收发；是否重复、是否发送由 application 的规则决定。"""

    def fetch_new(self, after: Any = None) -> list[EmailMessage]: ...
    def send(self, draft: Draft) -> Any: ...


class BrowserPort(Protocol):
    """浏览器自动化：读职位 / 填申请表 / 提交（求职招聘场景）。"""

    def query(self, spec: Any) -> Any: ...
    def fill_form(self, form: Any, data: dict[str, Any]) -> Any: ...
    def submit(self, preview_id: str) -> Any: ...


class StateStore(Protocol):
    """仓储接口。MVP 用 SQLite，未来可换 Postgres，业务无感。"""

    @property
    def tasks(self) -> Any: ...
    @property
    def mail_processed(self) -> Any: ...
    @property
    def confirmations(self) -> Any: ...
    @property
    def correspondence(self) -> Any: ...
    def transaction(self) -> Any: ...


class NotifierPort(Protocol):
    """把通知/待确认事项推给手机端。"""

    def push(self, message: Any) -> None: ...
