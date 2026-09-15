"""命令行入口。

P0：只搭命令骨架，各命令对应后续里程碑的用例，当前打印占位信息。
"""
from __future__ import annotations

import argparse

from friday import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday",
        description="Friday 会成长的个人助手",
    )
    parser.add_argument("--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="command", required=True)

    # 个人数据库
    p = sub.add_parser("search", help="检索个人资料（返回 文件:行号 + 片段）")
    p.add_argument("query")
    p = sub.add_parser("ask", help="结合个人资料回答问题（带引用）")
    p.add_argument("question")

    # 邮箱
    sub.add_parser("inbox", help="收取新邮件、去重并生成回复草稿")
    p = sub.add_parser("draft", help="查看/编辑草稿")
    p.add_argument("draft_id")
    p = sub.add_parser("send", help="确认并发送草稿")
    p.add_argument("draft_id")

    # 求职招聘
    p = sub.add_parser("jobs", help="求职招聘（search/apply/status）")
    p.add_argument("action", choices=["search", "apply", "status"])
    p.add_argument("arg", nargs="?")

    # 手机端
    sub.add_parser("server", help="启动手机 Web 控制台")

    return parser


_HANDLERS: dict[str, str] = {
    "search": "SearchKnowledgeUseCase",
    "ask": "AnswerWithCitationsUseCase",
    "inbox": "ProcessInboxUseCase",
    "draft": "EditDraftUseCase",
    "send": "ConfirmAndSendUseCase",
    "jobs": "JobsUseCase",
    "server": "WebServer",
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _HANDLERS[args.command]
    print(f"[P0 骨架] 命令 `{args.command}` → 将调用 {handler}（尚未实现）")
    return 0
