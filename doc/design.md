# Friday 设计说明（软件工程规范版）

> 会成长的个人助手 —— 个人资料、邮件、办事大厅、手机四端联动。
> 本文按软件工程规范重新设计：以**分层架构 + 端口/适配器 + 依赖倒置**为核心，
> 目标是「新增需求只需加插件/适配器，更换模型只需换配置或适配器，核心不动」。

---

## 1. 设计目标与边界

### 1.1 目标

1. 满足实验五项能力（个人数据库 / smail 邮箱 / ehall / 手机联动 / 能力组合）。
2. **可演进**：新增需求、更换 LLM、更换存储，都不需要重写系统。
3. **可控**：业务规则与安全关卡是确定性代码，LLM 只承担「理解/生成」这类有界职责。
4. **可测、可审计**：核心不依赖外部服务即可单测；每一次副作用都有确认与日志。

### 1.2 MVP 范围（先做一条薄纵切，再逐步加厚）

**在 MVP 内**：
- 个人数据库：文件系统 + ripgrep 全文检索 + 引用定位 + 增量重索引。
- 邮箱：IMAP 收取、去重、往来关联、草稿生成、确认后发送。
- ehall：登录态 + 1 种只读查询 + 1 种事务（含确认关卡）。
- 手机端：FastAPI Web 控制台 + 任务队列 + 一次性确认令牌。
- 一条完整组合流程 + 规则注入（`rules.md`）。
- 单一 LLM 适配器（OpenAI 兼容），但接口按「可替换」设计。

**明确不在 MVP（架构预留，后续加）**：向量检索、多 LLM Provider、Telegram/多通知渠道、更多 ehall 事务、多用户/鉴权、可观测面板、密钥加密存储。

---

## 2. 架构原则

- **依赖倒置（DIP）**：业务代码只依赖接口（Ports），不依赖具体实现（Adapters）。
- **开闭原则（OCP）**：新增能力通过「新增适配器 / 插件 / 数据」，不修改既有核心。
- **单一职责（SRP）**：LLM 只做理解与生成；状态机、去重、风险分级、确认逻辑都是代码。
- **端口-适配器（Hexagonal）**：核心领域与外部世界（IMAP、浏览器、Web、数据库）完全解耦。
- **可测试性**：核心用内存 Fake 适配器即可测试，无需真实邮箱/浏览器。
- **配置即变体**：Provider、模型、后端、特性开关全部走配置，不写死在代码。

---

## 3. 分层架构

依赖方向：**外 → 内**（上层依赖下层接口，下层绝不依赖上层）。

```
┌────────────────────────────────────────────────────────────┐
│  delivery/        交付层：CLI / Web / Bot                    │
│                   （只调用 application 用例）                 │
├────────────────────────────────────────────────────────────┤
│  application/     应用层：用例编排 + 确定性状态机             │
│                   （编排 domain，依赖 ports）                 │
├────────────────────────────────────────────────────────────┤
│  domain/          领域层：实体、值对象、端口接口（Protocol）  │
│                   纯业务，无任何 I/O、无第三方依赖            │
├────────────────────────────────────────────────────────────┤
│  infrastructure/  基础设施层：Adapters 实现 ports            │
│                   （LLM、IMAP/SMTP、Playwright、SQLite、rg） │
└────────────────────────────────────────────────────────────┘
```

- `domain` 不知道有 FastAPI、Playwright、OpenAI 的存在。
- `application` 通过**端口接口**调用外部能力，具体实现由容器在启动时注入。
- 换模型/换存储 = 换 `infrastructure` 里的一个适配器，`domain`/`application` 零改动。

---

## 4. 端口（Ports）与适配器（Adapters）

端口是核心与外部世界的契约，用 `typing.Protocol` 定义。

```python
# domain/ports.py
from typing import Protocol, Sequence, Iterator

class LLMClient(Protocol):
    """模型能力的最小封装。换模型 = 换实现 / 换配置，不动业务。"""
    def complete(self, messages: Sequence[Message],
                 tools: Sequence[ToolSpec] | None = None) -> Completion: ...

class KnowledgeStore(Protocol):
    def search(self, query: str, *, limit: int = 10) -> list[Hit]:  # Hit(path, line, snippet)
        ...
    def get(self, path: str) -> Document: ...
    def save(self, doc: Document) -> None: ...
    def reindex(self, path: str | None = None) -> None: ...

class MailPort(Protocol):
    """只负责网络收发；是否重复、是否发送由 application 的规则决定。"""
    def fetch_new(self, after: MailCursor) -> list[EmailMessage]: ...
    def send(self, draft: Draft) -> SendReceipt: ...

class BrowserPort(Protocol):
    def query(self, spec: QuerySpec) -> dict: ...
    def fill_form(self, form: FormSpec, data: dict) -> FormPreview: ...
    def submit(self, preview_id: str) -> SubmitReceipt: ...

class StateStore(Protocol):
    """仓储接口。MVP 用 SQLite，未来可换 Postgres，业务无感。"""
    @property
    def tasks(self) -> TaskRepository: ...
    @property
    def mail_processed(self) -> MailProcessedRepository: ...
    @property
    def confirmations(self) -> ConfirmationRepository: ...
    @property
    def correspondence(self) -> CorrespondenceRepository: ...
    def transaction(self): ...   # 工作单元，保证「发信+打标」原子性

class NotifierPort(Protocol):
    def push(self, msg: Notification) -> None: ...
```

**端口 → 适配器对照表**：

| 端口 | MVP 适配器 | 未来可替换 |
|---|---|---|
| `LLMClient` | `OpenAICompatibleClient` | Anthropic / 本地模型 / 多模型路由 |
| `KnowledgeStore` | `RipgrepKnowledgeStore` + 文件系统 | 向量库 / 全文引擎 |
| `MailPort` | `ImapSmtpMail` | 其他邮箱协议 / Graph API |
| `BrowserPort` | `PlaywrightBrowser` | 其他自动化方案 |
| `StateStore` | `SqliteStateStore` | Postgres / 云数据库 |
| `NotifierPort` | `WebNotifier` | Telegram / ntfy / 企业微信 |

---

## 5. 领域模型（domain）

### 5.1 实体

- `Task(id, type, params, status, result, confirm_token, timestamps)`
- `EmailMessage(message_id, folder, uid, uidvalidity, subject, sender, recipients, body, thread_id, received_at)`
- `Draft(id, email_id, subject, to, body, status, created_at)`
- `Confirmation(token, action, risk, summary, consequences, status, expires_at)`
- `Document(path, title, tags, mtime, content_hash)`
- `Contact(id, name, email, relation, notes)`
- `Correspondence(thread_id, contact, summary, last_email_id)`
- `Rule(id, trigger, correct_action, source, created_at)`
- `Skill(name, description, input_schema, risk, path)`

### 5.2 值对象 / 枚举

```python
class RiskLevel(str, Enum):
    READ   = "read"      # 只读，自动执行
    DRAFT  = "draft"     # 生成草稿，展示后待确认
    SUBMIT = "submit"    # 提交，必须逐字段回显 + 明确确认
    DANGER = "danger"    # 退课/撤销等破坏性操作：默认拒绝，绝不自动触发

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"
```

`RiskLevel` 是**安全的核心**，贯穿所有会改变外部状态的动作。

---

## 6. 应用层：用例 + 确定性状态机

### 6.1 用例（Application Services）

每个用例一个类，构造时注入所需端口，`__call__`/`run` 执行：

- `SearchKnowledgeUseCase` / `ReindexKnowledgeUseCase`
- `ProcessInboxUseCase`（收取→去重→分类→拟稿→通知）
- `EditDraftUseCase` / `ConfirmAndSendUseCase`
- `QueryEhallUseCase` / `PrepareFormUseCase` / `ConfirmAndSubmitUseCase`
- `SubmitMobileTaskUseCase` / `ListTasksUseCase`
- `LearnRuleUseCase`（把纠正写回 `rules.md`）

### 6.2 关键：业务规则在代码，LLM 只做有界的事

这是「换模型不破坏系统」的根本保证。**状态机、去重、风险分级、确认关卡全部是确定性代码**，
LLM 只负责：分类邮件、提取关键信息（截止时间/待补材料）、起草文本、选择技能。

```python
# application/services/inbox.py（示意）
class ProcessInbox:
    def __init__(self, mail: MailPort, state: StateStore, knowledge: KnowledgeStore,
                 llm: LLMClient, notifier: NotifierPort, rules: RuleSet): ...

    def run(self):
        for email in self.mail.fetch_new(after=self.state.last_cursor()):
            if self.state.mail_processed.exists(email.message_id):
                continue                         # ① 去重：代码保证，不依赖 LLM

            decision = self.llm.complete(        # ② LLM：只判断+拟稿
                render("classify_email", email=email, rules=rules))
            if decision.needs_reply:
                draft = self._build_draft(email, decision)
                self.state.drafts.save(draft)
                self.notifier.push(Notification(
                    kind="draft_ready", draft_id=draft.id,
                    summary=decision.summary))
            # ③ 只有用户确认发送后，才走 ConfirmAndSend，并原子地打 processed 标记
```

### 6.3 任务生命周期状态机

```
pending → running → awaiting_confirmation ──批准──→ done
                       │    │
                       │    └─拒绝/过期─→ canceled
                       └──运行出错──→ failed（可重试）
```

任何 `SUBMIT`/`DANGER` 级动作都必须经过 `awaiting_confirmation`，靠一次性确认令牌（§8）放行。

---

## 7. 可扩展性：新增需求与更换模型

### 7.1 变化 → 改动点对照表

| 未来变化 | 只需改动 | 完全不用动 |
|---|---|---|
| 更换/升级 LLM 模型 | `infrastructure/llm/` 加一个适配器 或 改 `[llm]` 配置 | domain / application / delivery |
| 调整提示词（按模型微调） | `application/prompts/` 模板资产 | 代码 |
| 新增能力（日历、网盘…） | 新增 Port + Adapter + UseCase（+可选 Skill） | 既有端口与编排核心 |
| 新增一种 ehall 事务 | 新增一个 `skills/<name>/` 插件目录 | 核心 |
| 换存储 / 检索后端 | 新增 `StateStore` / `KnowledgeStore` 适配器 | 业务逻辑 |
| 新增通知渠道 | 新增 `NotifierPort` 适配器 | 业务逻辑 |
| 新增纠正规则 | 写 `memory/rules.md` 数据 | 代码 |

### 7.2 技能（Skills）= 能力插件

「能力」做成**插件式技能**，通过目录发现加载，新增能力 = 加一个目录，不改核心：

```python
# domain/skills.py
class SkillContext(Protocol):
    knowledge: KnowledgeStore
    browser: BrowserPort
    state: StateStore
    llm: LLMClient

class Skill(Protocol):
    name: str
    description: str
    input_schema: dict      # JSON Schema，供 LLM 结构化调用
    risk: RiskLevel
    def run(self, ctx: SkillContext, inputs: dict) -> SkillResult: ...
```

```
skills/
├── reply_email/
│   ├── SKILL.md        # 描述、用法、输入输出、风险
│   └── run.py
├── ehall_leave_request/
│   ├── SKILL.md
│   └── run.py          # 封装「填表→preview→等待确认→submit」
└── ...
```

### 7.3 提示词资产化

提示词不进代码，放 `application/prompts/`（Jinja2 模板），按名加载；不同模型用不同模板集，改提示词无需发版改代码。

---

## 8. 确认机制（安全核心）

```python
class Confirmation:
    token: str                 # 一次性、短时（如 15 分钟）
    action: str                # "send_email:draft-12" / "submit_form:leave-3"
    risk: RiskLevel
    summary: dict              # 关键字段回显
    consequences: str          # 后果说明
    status: ConfirmationStatus # pending/approved/denied/expired
    expires_at: datetime
```

规则：
- `SUBMIT` 必须回显所有关键字段 + 后果，用户显式批准。
- `DANGER` 默认拒绝，需额外确认，且**绝不**由 Agent 自行触发。
- 令牌一次性、过期作废；批准/拒绝都写审计日志。
- 「发送/提交」与「打已处理标记」放在同一事务里，保证幂等。

---

## 9. 配置管理

非敏感配置用 `config.toml`，敏感信息用 `.env`（均不提交，提交 `.env.example` 与样例）。

```toml
[llm]
provider = "openai_compatible"      # 换模型往往只改这一节
model = "gpt-4o-mini"
api_base = "https://..."
temperature = 0.2

[mail]
imap_host = "..."; imap_port = 993
smtp_host = "..."; smtp_port = 465

[storage]
state = "sqlite"                   # 未来可换 postgres
db_path = "state/friday.db"

[knowledge]
backend = "ripgrep"                # 未来可换 vector
root = "data"

[skills]
paths = ["skills", "friday/skills"]

[features]                         # 特性开关：灰度、降级、关危险能力
mail = true
ehall = true
mobile = true
```

依赖注入容器 `container.py` 按配置装配适配器并注入用例：

```python
def build_container(cfg: Config) -> Container:
    llm       = make_llm(cfg.llm)                  # 按 provider 选适配器
    mail      = ImapSmtpMail(cfg.mail, cfg.secrets)
    browser   = PlaywrightBrowser(cfg.ehall)
    knowledge = RipgrepKnowledge(cfg.knowledge)
    state     = SqliteState(cfg.storage)
    notifier  = WebNotifier()
    skills    = load_skills(cfg.skills)
    return Container(..., services=wire_services(...))
```

---

## 10. 目录结构（按层组织）

```
Friday/
├── friday/
│   ├── domain/                 # 纯业务，零 I/O 依赖
│   │   ├── entities.py
│   │   ├── value_objects.py    # RiskLevel / TaskStatus ...
│   │   ├── ports.py            # 端口协议
│   │   └── skills.py           # Skill 协议 + SkillContext
│   ├── application/            # 用例编排 + 状态机 + 提示词资产
│   │   ├── services/           # inbox / drafts / ehall / knowledge / rules
│   │   ├── orchestrator.py     # 确定性状态机
│   │   └── prompts/            # jinja2 模板（可版本化、按模型微调）
│   ├── infrastructure/         # 适配器
│   │   ├── llm/openai_compatible.py
│   │   ├── mail/imap_smtp.py
│   │   ├── browser/playwright_adapter.py
│   │   ├── knowledge/ripgrep_store.py
│   │   ├── state/sqlite_store.py
│   │   ├── notify/web_notifier.py
│   │   └── skills/loader.py
│   ├── delivery/               # CLI / Web / Bot
│   │   ├── cli.py
│   │   └── web/app.py, routes.py
│   ├── config.py               # 加载 config.toml + .env
│   ├── container.py            # 依赖注入装配
│   └── main.py
├── skills/                     # 插件式技能（能力扩展点）
├── data/                       # 个人资料（Markdown，gitignore）
│   ├── profile/ contacts/ documents/ events/ correspondence/
│   └── index/                  # 生成的索引（gitignore）
├── memory/rules.md             # 纠正规则（提交入库）
├── application/prompts -> friday/application/prompts
├── config/config.toml + secrets/（gitignore）
├── tests/
│   ├── unit/                   # 领域纯单测
│   ├── integration/            # 适配器集成测试
│   └── e2e/                    # 组合流程（用 Fake）
├── .env.example
└── .gitignore
```

---

## 11. 测试策略

| 层级 | 内容 | 依赖 |
|---|---|---|
| 单元测试 | 领域实体、状态机、去重、风险分级、用例逻辑 | 无外部依赖，用内存 Fake |
| 契约测试 | 每个 Adapter 必须满足 Port 的契约 | Fake 或 fixture |
| 集成测试 | SQLite 仓储、ripgrep 检索、IMAP（用本地测试邮箱） | 标记慢测试 |
| E2E | 组合流程（收通知→检索→拟稿→确认→发送→归档） | 全 Fake，跑通全链路 |

- 提供 `FakeLLM / FakeMail / FakeBrowser / InMemoryStateStore / FakeNotifier`，核心逻辑可离线跑通。
- 真实服务用 `scripts/smoke_test.py` 手动冒烟（脚本不提交敏感数据）。

---

## 12. 分期实施（薄纵切优先）

1. **P0 骨架**：分层包结构、`ports.py`、`container.py`、`config.toml`、SQLite、日志、`.env.example`、CI 跑单测。
2. **P1 走通骨架**：用 Fake 适配器把「手机提交任务 → 状态机 → 返回结果」这条竖切跑通（Walking Skeleton）。
3. **P2 个人数据库**：真实 `RipgrepKnowledgeStore` + 文件监听增量索引 + 引用定位。
4. **P3 邮件**：真实 IMAP 收取 + 去重 + 草稿 + 确认发送（接入确认令牌）。
5. **P4 ehall**：登录态 + 1 只读查询 + 1 事务技能（`RiskLevel` 关卡）。
6. **P5 手机端**：FastAPI Web 控制台 + 任务队列 + 确认页。
7. **P6 组合流程 + 成长机制**：打通完整流程、规则注入、成功流程固化为技能。

---

## 13. 为什么这样设计能应对「需求增加 / 模型更新」

1. **模型更新**：LLM 是端口，换模型只换 `infrastructure/llm` 适配器或改 `[llm]` 配置；业务规则、状态机、安全关卡都在代码里，与模型无关；提示词是资产，可按模型单独调。
2. **需求增加**：新能力 = 新端口 + 新适配器 + 新用例（+可选 Skill 插件），开闭原则下**只增不改**。
3. **存储/检索/通知后端更换**：换适配器即可，仓储接口不变，业务无感。
4. **纠正与成长**：规则是数据（`rules.md`），成功流程是插件（`skills/`），都无需改核心代码。

---

## 14. 风险与对策

| 风险 | 对策 |
|---|---|
| 重复发信/提交 | UID + Message-ID 去重；动作与打标同事务；状态机保证幂等 |
| Agent 自行退课/撤销 | `RiskLevel.DANGER` 默认拒绝；绝不自动触发 |
| 密钥/个人数据入库 | secrets 目录与 data 目录 gitignore；只提交样例 |
| 手机端依赖桌面窗口 | 后台 daemon + Web 入口；任务队列持久化 |
| 模型输出不可信 | 输出过 Pydantic 校验；失败重试/降级；副作用动作不交由模型直接执行 |
| 业务规则散落 | 状态机/去重/风险分级集中在 application，单测覆盖 |
