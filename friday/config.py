"""配置加载：config.toml（非敏感）+ .env（敏感）。

换模型/换后端通常只需改 config.toml，业务代码不感知。
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LLMConfig:
    provider: str = "openai_compatible"
    model: str = ""
    api_base: str = ""
    api_key: str = ""          # 来自 .env
    temperature: float = 0.2
    max_tokens: int = 2048


@dataclass
class MailConfig:
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 465
    username: str = ""         # 来自 .env
    password: str = ""         # 来自 .env


@dataclass
class StorageConfig:
    state: str = "sqlite"
    db_path: str = "state/friday.db"


@dataclass
class KnowledgeConfig:
    backend: str = "ripgrep"
    root: str = "data"


@dataclass
class FeaturesConfig:
    mail: bool = True
    jobs: bool = True
    mobile: bool = True


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    mail: MailConfig = field(default_factory=MailConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    skills_paths: list[str] = field(default_factory=lambda: ["skills"])


def load_dotenv(path: Path) -> None:
    """极简 .env 加载：KEY=VALUE，已存在的环境变量不覆盖。"""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def find_root() -> Path:
    """向上查找包含 config.toml 或 pyproject.toml 的目录作为项目根。"""
    here = Path.cwd()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists() or (p / "config.toml").exists():
            return p
    return here


def load_config(root: Path | None = None) -> Config:
    """从项目根目录读取 config.toml 与 .env。"""
    root = (root or find_root()).resolve()

    load_dotenv(root / ".env")

    cfg = Config()
    toml_path = root / "config.toml"
    if toml_path.exists():
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        _apply_toml(cfg, raw)

    # 敏感信息只从环境变量注入，绝不写进 config.toml
    cfg.llm.api_key = os.environ.get("LLM_API_KEY", "")
    cfg.llm.model = os.environ.get("LLM_MODEL", cfg.llm.model)
    if api_base := os.environ.get("LLM_API_BASE"):
        cfg.llm.api_base = api_base
    cfg.mail.username = os.environ.get("MAIL_USERNAME", "")
    cfg.mail.password = os.environ.get("MAIL_PASSWORD", "")
    return cfg


def _apply_toml(cfg: Config, raw: dict) -> None:
    llm = raw.get("llm", {})
    if llm:
        cfg.llm.provider = str(llm.get("provider", cfg.llm.provider))
        cfg.llm.model = str(llm.get("model", cfg.llm.model))
        cfg.llm.api_base = str(llm.get("api_base", cfg.llm.api_base))
        cfg.llm.temperature = float(llm.get("temperature", cfg.llm.temperature))
        cfg.llm.max_tokens = int(llm.get("max_tokens", cfg.llm.max_tokens))

    mail = raw.get("mail", {})
    if mail:
        cfg.mail.imap_host = str(mail.get("imap_host", cfg.mail.imap_host))
        cfg.mail.imap_port = int(mail.get("imap_port", cfg.mail.imap_port))
        cfg.mail.smtp_host = str(mail.get("smtp_host", cfg.mail.smtp_host))
        cfg.mail.smtp_port = int(mail.get("smtp_port", cfg.mail.smtp_port))

    storage = raw.get("storage", {})
    if storage:
        cfg.storage.state = str(storage.get("state", cfg.storage.state))
        cfg.storage.db_path = str(storage.get("db_path", cfg.storage.db_path))

    knowledge = raw.get("knowledge", {})
    if knowledge:
        cfg.knowledge.backend = str(knowledge.get("backend", cfg.knowledge.backend))
        cfg.knowledge.root = str(knowledge.get("root", cfg.knowledge.root))

    features = raw.get("features", {})
    if features:
        cfg.features.mail = bool(features.get("mail", cfg.features.mail))
        cfg.features.jobs = bool(features.get("jobs", cfg.features.jobs))
        cfg.features.mobile = bool(features.get("mobile", cfg.features.mobile))

    skills = raw.get("skills", {})
    if skills:
        cfg.skills_paths = [str(p) for p in skills.get("paths", cfg.skills_paths)]
