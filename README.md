# LeanRock

Think deeply. Build lightly.

LeanRock 是一套安装到不同软件项目中的个人 Coding Agent 开发规则和工作流。V0.1
只支持 OpenAI Codex，只使用 Python 3 标准库；它不是新的大模型、自治 Agent、业务
框架，也不指定语言、数据库或 Web 框架。

它把常驻规则压缩在短小的 `AGENTS.md` 管理区块中，把 SPEC、实施、审查和状态维护
放进按需加载的 Skills，并用一个 repo-local Hook 保存本地准确消息、在上下文压缩后
恢复未纳入 checkpoint 的多轮内容。

## 设计来源与边界

LeanRock 借鉴 Ponytail 的核心开发纪律：先理解再最小化、优先删除和复用、修共同根因、
不为一个实现创建抽象，以及用可测量触发条件标记有意识的简化。归属与 MIT Notice 见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

LeanRock 与 Ponytail 的目标不同：第一版只面向 Codex；增加 Product Owner 决策边界、
Search Before Build、SPEC 复杂度控制、Git/worktree 工作约定、准确 turn 日志、CURRENT
checkpoint、安全安装/更新，以及跨项目经验收集和晋升。它没有模式切换、状态栏、Plugin、
MCP、后台服务、网络运行时、LLM 调用或自动 Git 写操作。

## Search Before Build

任何非平凡 SPEC 或实现开始前都要做简短 Reuse Check：

```md
## Reuse Check

- Existing repository implementation:
- Standard library:
- Framework/native/database capability:
- Already-installed dependency:
- Mature external solution required:
- Decision:
```

本地搜索始终执行。认证、授权、密码学、支付、标准协议、时区/日历边界、复杂解析器或
文件格式、序列化标准、安全敏感能力、重试/分布式协调，以及会长成小框架的能力，在
手写前还要检查当前维护的官方 SDK、成熟库或标准方案。

找到库不等于安装库。新增依赖需比较维护状态、官方文档、兼容性、License、安全记录、
间接依赖、包体/运行成本、API 稳定性、胶水代码、边界风险和长期维护成本。新增生产
依赖必须获得 Product Owner 明确批准。

## 最小 SPEC 与实现

`$leanrock-spec` 从用户可见结果和真实流程开始，强制给出复用检查、必须保持的不变量、
一屏内的最小目标流程、`REUSE / DELETE / MERGE / SIMPLIFY / ADD`、复杂度净变化、拒绝的
复杂度、最小垂直实施顺序和仍需 Product Owner 决定的问题。它默认只读，不把 Agent
提案写成批准决定，也不在架构获批前机械拆文件级任务。

`$leanrock-implement` 只实现明确授权的范围。它追踪真实调用流和所有相关调用者，在最小
共同根因修复，使用最少文件与最小正确 Diff，复用现有测试框架，并保留安全、数据、
支付、隐私、验证、错误处理和无障碍等真实边界。SPEC 批准不自动等于实施授权。

`$leanrock-review` 默认只读当前 Diff，用 `delete`、`reuse`、`stdlib`、`native`、
`dependency`、`yagni`、`merge`、`shrink`、`guard-required` 和 `guard-bloat` 区分可删
复杂度与必要防护。没有可删内容时输出 `Lean already. Ship.`

## 上下文连续性

安装后，本地状态位于：

```text
.leanrock/state/
├── ACTIVE_SESSION.json
├── CURRENT.md
├── RECOVERY.md
└── turns/
    └── <session_id>.jsonl
```

`ACTIVE_SESSION.json` 是 Hook 原子维护的当前主 Session 指针，包含原始 session ID、
最新 root turn ID、最新 seq 和准确 turn log 路径。Checkpoint 通过该指针定位日志，不猜测
最近修改文件、不扫描所有 Session，也不依赖聊天记忆。

`CURRENT.md` 是主 Agent 维护的短小当前事实：确认决定、未批准提案、开放问题、范围、
授权、阶段、阻塞和下一步。它不是聊天历史。只有当前 worktree 的主 Agent 可以修改；
子 Agent 只读。

`turns/<session_id>.jsonl` 是 Hook 从 `UserPromptSubmit.prompt` 和
`Stop.last_assistant_message` 获得的准确原文，每个 session 独立，按 `seq` 递增，不做
语义总结。`CURRENT.md` marker 只表示 checkpoint Skill 实际读过并吸收的最高序号。

当 `SessionStart.source` 为 `compact` 时，Hook 选择 marker 之后的全部消息，再合并当前
session 最近六条，去重并保持顺序，写入 `RECOVERY.md`。Hook 的 `additionalContext` 只
注入读取 CURRENT/RECOVERY 的短小控制指令和 session/seq/count 元数据，不注入历史消息
原文。RECOVERY 中的原文被明确标记为历史证据而不是 Developer 指令。它绝不会只恢复
最后一条消息，也不用 LLM 总结或挑选。

如果 JSONL 尾行损坏，Hook 在同一 session lock 内备份原文件、保留连续合法前缀并原子
重建当前日志；下一条消息从合法前缀的下一个 seq 继续，而不是清空历史从 1 重来。

LeanRock 不解析 `transcript_path`，因为 Codex 官方文档明确声明 transcript 格式不是
稳定 Hook 接口。LeanRock 保存自己稳定、准确、逐 session 的消息记录。V0.1 不捕获未完成
的半条 Assistant 输出，也不记录 `PostToolUse`。

## 六个 Skill

Codex CLI 和 IDE extension 使用 `$skill-name` 显式调用；用 `/skills` 查看可用 Skills。
所有 LeanRock Skill 都设置 `allow_implicit_invocation: false`，关键动作不会被自动触发。
安装或更新后若没有立即出现，重启 Codex。

```text
$leanrock-setup install
$leanrock-setup update
$leanrock-setup doctor

$leanrock-learn capture
$leanrock-learn promote

$leanrock-spec
$leanrock-implement
$leanrock-review
$leanrock-checkpoint
```

前两个是用户级 Skill；后四个安装到项目 `.agents/skills/`。Codex 已弃用 Custom Prompts，
所以 LeanRock 使用 Skills 提供命令式入口。

## Bootstrap 用户级 Skill

默认只预览：

```bash
python3 bootstrap.py
```

确认后写入 `$HOME/.agents/skills`：

```bash
python3 bootstrap.py --apply
```

Bootstrap 幂等、更新前备份、不删除其他 Skill，并把 LeanRock 源仓库绝对路径写入
macOS/Linux 的 `~/.config/leanrock/config.json` 或 Windows 的
`%APPDATA%\leanrock\config.json`。安装后必要时重启 Codex。

## 项目安装、更新与检查

三个命令都要求目标位于 Git 仓库中。`install` 和 `update` 默认 dry-run：

```bash
python3 install.py install /path/to/project
python3 install.py install /path/to/project --apply

python3 install.py update /path/to/project
python3 install.py update /path/to/project --apply

python3 install.py doctor /path/to/project
```

安装器只管理带标记的 `AGENTS.md`/`.gitignore` 区块、四个 `leanrock-` Skill、LeanRock
Hook handler/script 和安装版本。它保留既有 Hook，不删除业务文件，写前备份，不 commit、
push 或自动信任 Hook。`CURRENT.md` 仅在不存在时创建，update 永远不覆盖它。无法安全
合并时停止对应写入并报告。

`doctor` 完全只读，检查 managed block、Skills、hooks、Hook 脚本、CURRENT、版本，并
提醒 Hook trust 状态可能因定义变化而需要复审。

## Hook trust

项目级 Hook 仅在项目 `.codex/` 层受信时加载。安装或 Hook 定义改变后，必须在 Codex
打开 `/hooks`，逐项查看命令和来源，然后明确 trust。LeanRock 不会代替用户信任 Hook。
四个事件全部运行同一个 `.codex/hooks/leanrock_continuity.py`，timeout 为 5 秒；只有
`SessionStart` 与 `SubagentStart` 输出模型可见上下文。

## 本地记录与隐私

消息日志只保存在本地，不联网、不调用 LLM，也不读取 Secret 文件。不要在聊天中粘贴
Secret：准确记录意味着原文会写入磁盘。支持的平台上，Hook 尽量把状态文件权限限制为
当前用户可读写。`.gitignore` 默认忽略 ACTIVE_SESSION、CURRENT、RECOVERY、turns、备份和学习 inbox；
仍应按项目的数据分类与设备安全策略管理本地磁盘。

## Capture 与 Promote

`$leanrock-learn capture` 把经用户确认的经验写进当前项目
`.leanrock/learnings/inbox/`，不直接修改 LeanRock 源。

`$leanrock-learn promote` 先分为临时状态、单项目规则、跨项目规则。只有在两个以上项目
重复发生，或防止一次真实严重事故时，才可提议进入 LeanRock。它先搜索已有规则、优先
修改现有表达、展示最小提案，获得明确批准后才修改版本、CHANGELOG 和最小测试；不会
自动更新业务项目。

## 卸载

先备份项目。手动删除 `AGENTS.md` 中 `<!-- LEANROCK:START -->` 到
`<!-- LEANROCK:END -->` 的区块，以及 `.gitignore` 中 `# LEANROCK:START` 到
`# LEANROCK:END` 的区块；再删除四个
`.agents/skills/leanrock-*` 目录、`.codex/hooks/leanrock_continuity.py`、
`.leanrock/VERSION`，并只从 `.codex/hooks.json` 删除命令包含
`leanrock_continuity.py` 的四个 handler。不要删除其他 Hook 或业务内容。

是否删除 `.leanrock/state/` 和 `.leanrock/learnings/` 由用户决定；它们可能包含本地状态
和经验，安装器不会替你删除。用户级 Skill 可从 `$HOME/.agents/skills/leanrock-setup`
与 `leanrock-learn` 手动移除，不影响其他 Skill。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile bootstrap.py install.py template/.codex/hooks/leanrock_continuity.py
```

官方依据：Codex 的 [AGENTS.md 加载规则](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、
[Skills](https://learn.chatgpt.com/docs/build-skills)、[Hooks](https://learn.chatgpt.com/docs/hooks)
与 [Custom Prompts 弃用说明](https://learn.chatgpt.com/docs/custom-prompts)。
