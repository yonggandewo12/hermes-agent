<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

<p align="center">
  <a href="./README.md"><img src="https://img.shields.io/badge/English-View-0A66C2?style=for-the-badge" alt="English"></a>
  <a href="./README.zh-CN.md"><img src="https://img.shields.io/badge/简体中文-当前-2ea44f?style=for-the-badge" alt="简体中文"></a>
</p>

<p align="center">
  <a href="./CONTRIBUTING.md">Contributing Guide (English)</a> ·
  <a href="./CONTRIBUTING.zh-CN.md">贡献指南（中文）</a>
</p>

# Hermes Agent ☤

**[Nous Research](https://nousresearch.com) 打造的自我进化 AI Agent。** 它内置完整的学习闭环：能从经验中创建技能、在使用过程中持续改进技能、主动推动知识持久化、搜索自己的历史对话，并在跨会话中逐步形成更深入的用户模型。你既可以把它跑在一台 5 美元的 VPS 上，也可以运行在 GPU 集群或几乎闲置零成本的无服务器基础设施上。它不依赖你的笔记本电脑——甚至可以在云端 VM 上工作时，通过 Telegram 和它对话。

你可以使用任意模型： [Nous Portal](https://portal.nousresearch.com)、[OpenRouter](https://openrouter.ai)（200+ 模型）、[z.ai/GLM](https://z.ai)、[Kimi/Moonshot](https://platform.moonshot.ai)、[MiniMax](https://www.minimax.io)、OpenAI，或你自己的兼容端点。通过 `hermes model` 即可切换，无需改代码，没有供应商锁定。

<table>
<tr><td><b>真正可用的终端界面</b></td><td>完整 TUI，支持多行编辑、斜杠命令补全、会话历史、中断并重定向、以及工具输出流式展示。</td></tr>
<tr><td><b>存在于你的工作流中</b></td><td>可同时接入 Telegram、Discord、Slack、WhatsApp、Signal 和 CLI，由单一 gateway 进程统一驱动。支持语音消息转写与跨平台会话连续性。</td></tr>
<tr><td><b>闭环学习能力</b></td><td>具备 Agent 管理的记忆系统与周期性提醒；复杂任务后可自动生成技能；技能会在使用中自我优化；支持基于 FTS5 的历史会话搜索与 LLM 摘要回忆；集成 <a href="https://github.com/plastic-labs/honcho">Honcho</a> 辩证式用户建模；兼容 <a href="https://agentskills.io">agentskills.io</a> 开放标准。</td></tr>
<tr><td><b>定时自动化</b></td><td>内置 cron 调度器，可将结果投递到任意平台。日报、夜间备份、每周审计等任务都可以用自然语言配置并无人值守运行。</td></tr>
<tr><td><b>委派与并行执行</b></td><td>可启动隔离的子代理并行处理多个工作流；也能编写 Python 脚本经 RPC 调用工具，把多步流程压缩为零上下文成本的执行回合。</td></tr>
<tr><td><b>可运行在任何地方，而不只是本机</b></td><td>支持六种终端后端：local、Docker、SSH、Daytona、Singularity 和 Modal。Daytona 与 Modal 支持近似无感持久化：环境闲置时休眠、需要时唤醒，在会话之间几乎不产生额外成本。既能部署在 5 美元 VPS 上，也能运行在 GPU 集群。</td></tr>
<tr><td><b>面向研究</b></td><td>支持批量轨迹生成、Atropos RL 环境，以及用于训练下一代工具调用模型的轨迹压缩能力。</td></tr>
</table>

---

## 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

支持 Linux、macOS、WSL2，以及 Android 的 Termux 环境。安装脚本会自动处理不同平台的特定安装逻辑。

> **Android / Termux：** 推荐使用已验证的手动流程，见 [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux)。在 Termux 上，Hermes 安装的是定制的 `.[termux]` extra，因为完整的 `.[all]` 目前会拉取与 Android 不兼容的语音依赖。
>
> **Windows：** 目前不支持原生 Windows。请先安装 [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install)，再执行上面的命令。

安装完成后：

```bash
source ~/.bashrc    # 重新加载 shell（或执行：source ~/.zshrc）
hermes              # 开始对话
```

---

## 快速开始

```bash
hermes              # 进入交互式 CLI，开始一个会话
hermes model        # 选择 LLM 提供商与模型
hermes tools        # 配置启用哪些工具
hermes config set   # 设置单个配置项
hermes gateway      # 启动消息网关（Telegram、Discord 等）
hermes setup        # 运行完整安装向导（一次性完成配置）
hermes claw migrate # 从 OpenClaw 迁移（如果你来自 OpenClaw）
hermes update       # 更新到最新版本
hermes doctor       # 诊断问题
```

📖 **[完整文档 →](https://hermes-agent.nousresearch.com/docs/)**

## 中文快速导航

- [快速开始](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
- [CLI 使用](https://hermes-agent.nousresearch.com/docs/user-guide/cli)
- [配置说明](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [消息网关](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)
- [工具与技能](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
- [记忆系统](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [MCP 集成](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Cron 定时任务](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [项目架构](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [贡献指南](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)
- [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)

## CLI 与消息平台速查

Hermes 有两个主要入口：一是直接运行 `hermes` 打开终端 UI；二是启动 gateway，然后通过 Telegram、Discord、Slack、WhatsApp、Signal 或 Email 与它交互。进入会话后，很多斜杠命令在两种入口中是共通的。

| 操作 | CLI | 消息平台 |
|---------|-----|---------------------|
| 开始聊天 | `hermes` | 运行 `hermes gateway setup` + `hermes gateway start`，然后给机器人发消息 |
| 新建会话 | `/new` 或 `/reset` | `/new` 或 `/reset` |
| 切换模型 | `/model [provider:model]` | `/model [provider:model]` |
| 设置 personality | `/personality [name]` | `/personality [name]` |
| 重试或撤销上一步 | `/retry`, `/undo` | `/retry`, `/undo` |
| 压缩上下文 / 查看用量 | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| 浏览技能 | `/skills` 或 `/<skill-name>` | `/skills` 或 `/<skill-name>` |
| 中断当前任务 | `Ctrl+C` 或直接发送新消息 | `/stop` 或直接发送新消息 |
| 平台专属状态命令 | `/platforms` | `/status`, `/sethome` |

完整命令列表请参考 [CLI guide](https://hermes-agent.nousresearch.com/docs/user-guide/cli) 和 [Messaging Gateway guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)。

---

## 文档

所有文档都集中在 **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**：

| 部分 | 内容 |
|---------|---------------|
| [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) | 2 分钟内完成安装、配置和第一次对话 |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli) | 命令、快捷键、personality、会话管理 |
| [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) | 配置文件、provider、model 与全部选项 |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) | Telegram、Discord、Slack、WhatsApp、Signal、Home Assistant |
| [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security) | 命令审批、DM 配对、容器隔离 |
| [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) | 40+ 工具、toolset 系统、终端后端 |
| [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) | 程序化记忆、Skills Hub、技能创建 |
| [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) | 持久记忆、用户画像、最佳实践 |
| [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) | 连接任意 MCP server 以扩展能力 |
| [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) | 带平台投递能力的定时任务 |
| [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files) | 影响每次对话的项目上下文文件 |
| [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) | 项目结构、agent loop、关键类 |
| [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) | 开发环境、PR 流程、代码风格 |
| [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) | 所有命令与参数 |
| [Environment Variables](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) | 完整环境变量参考 |

---

### Playwright Page Capture Skill

页面抓取工作流可以：
- 使用 Playwright 打开固定页面
- 探测网络响应
- 提取 DOM 字段
- 将结果发送到飞书群

**推荐配置路径：**

```bash
hermes setup
```

在 tools 阶段启用并配置 Playwright Page Capture。配置会写入：

```bash
~/.hermes/playwright-page-capture.yaml
```

**手动运行示例：**

```bash
# YAML 模式：使用默认配置路径 ~/.hermes/playwright-page-capture.yaml
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc"

# YAML 模式：指定自定义配置文件
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc config=/path/to/my-config.yaml"

# URL 模式：直连任意 URL，无需配置文件
hermes -q "使用 playwright-page-capture 处理 page_id=https://www.baidu.com feishu_chat_id=oc_xxxx"
```

> 默认配置文件路径：`~/.hermes/playwright-page-capture.yaml`
> YAML 模式和 URL 模式都支持 `--feishu-chat-id` 参数覆盖配置文件中的 chat_id

### Playwright Auth Login Skill

自动化用户名/密码登录，支持配置化步骤流，保存 Playwright `storage_state`，可选串联 page capture 抓取关联页面。

**配置步骤：**

```bash
# 复制示例配置文件
cp optional-skills/communication/playwright-auth-login/examples/playwright-auth.example.yaml \
   ~/.hermes/playwright-auth.yaml
```

**使用示例：**

```bash
# 仅登录 — 保存 storage_state
hermes -q "使用 playwright-auth-login 处理 site_id=github_com"
/playwright-auth-login site_id=github_com

# 登录并触发所有关联页面抓取
hermes -q "使用 playwright-auth-login 处理 site_id=github_com run_linked_pages=true"
/playwright-auth-login site_id=github_com --run-linked-pages
```

> 默认 auth 配置路径：`~/.hermes/playwright-auth.yaml`
> 在 `~/.hermes/playwright-page-capture.yaml` 中设置 `auth_site_id` 即可关联页面

**页面配置变更：**

`~/.hermes/playwright-page-capture.yaml` 的 page 条目新增可选字段 `auth_site_id`：

```yaml
pages:
  - page_id: github_dashboard
    auth_site_id: github_com   # ← 新增：关联到 auth 配置中的 site_id
    url: https://github.com
    storage_state_path: github_com.js
    ...
```

---

## 从 OpenClaw 迁移

如果你之前使用的是 OpenClaw，Hermes 可以自动导入你的配置、记忆、技能与 API keys。

**首次配置期间：** 安装向导（`hermes setup`）会自动检测 `~/.openclaw`，并在正式配置前询问是否迁移。

**安装后任意时刻：**

```bash
hermes claw migrate              # 交互式迁移（完整预设）
hermes claw migrate --dry-run    # 预览将会迁移什么
hermes claw migrate --preset user-data   # 不迁移敏感信息
hermes claw migrate --overwrite  # 覆盖已有冲突项
```

可迁移内容包括：
- **SOUL.md** —— persona 文件
- **Memories** —— MEMORY.md 与 USER.md 条目
- **Skills** —— 用户自定义技能，迁移至 `~/.hermes/skills/openclaw-imports/`
- **Command allowlist** —— 命令审批白名单
- **Messaging settings** —— 平台配置、允许用户、工作目录
- **API keys** —— allowlist 中的敏感信息（Telegram、OpenRouter、OpenAI、Anthropic、ElevenLabs）
- **TTS assets** —— 工作区音频资源
- **Workspace instructions** —— AGENTS.md（配合 `--workspace-target`）

更多选项请查看 `hermes claw migrate --help`，或使用 `openclaw-migration` skill 获取带 dry-run 预览的交互式迁移体验。

---

## 参与贡献

欢迎贡献！请先阅读 [Contributing Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)，其中包含开发环境、代码风格与 PR 流程说明。

贡献者快速开始：

```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all,dev]"
python -m pytest tests/ -q
```

> **RL Training（可选）：** 如果你要参与 RL / Tinker-Atropos 相关开发：
> ```bash
> git submodule update --init tinker-atropos
> uv pip install -e "./tinker-atropos"
> ```

---

## 社区

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 💡 [Discussions](https://github.com/NousResearch/hermes-agent/discussions)

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

由 [Nous Research](https://nousresearch.com) 打造。
