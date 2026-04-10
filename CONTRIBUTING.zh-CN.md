# Contributing to Hermes Agent（中文安装与部署指南）

本文档是 `CONTRIBUTING.md` 中安装与部署部分的中文对应版本，聚焦开发环境搭建、内网源码安装，以及本地 / 自建 LLM 配置。

---

## Development Setup

### 前置要求

| 要求 | 说明 |
|------|------|
| **Git** | 建议支持 `--recurse-submodules` |
| **Python 3.11+** | 缺失时可由 `uv` 自动安装 |
| **uv** | 高性能 Python 包管理器（[安装方式](https://docs.astral.sh/uv/)） |
| **Node.js 18+** | 可选，仅在使用浏览器工具或 WhatsApp bridge 时需要 |

### 完整安装步骤

#### 1. 克隆代码库

```bash
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
```

> 注意：如果你已经拿到了仓库，但子模块尚未初始化，请执行：
> ```bash
> git submodule update --init --recursive
> ```

#### 2. 创建虚拟环境并安装

```bash
# 创建 Python 3.11 虚拟环境
uv venv venv --python 3.11

# 激活虚拟环境
source venv/bin/activate

# 安装项目及全部可选依赖
uv pip install -e ".[all,dev]"

# 可选：RL 训练子模块
# git submodule update --init tinker-atropos && uv pip install -e "./tinker-atropos"

# 可选：浏览器工具（需要 Node.js）
npm install
```

#### 3. 配置运行环境

```bash
# 创建必要目录
mkdir -p ~/.hermes/{cron,sessions,logs,memories,skills}

# 复制配置文件
cp cli-config.yaml.example ~/.hermes/config.yaml
touch ~/.hermes/.env

# 至少填入一个 LLM provider 的 API key
# 按你实际使用的 provider 替换
echo 'OPENROUTER_API_KEY=sk-or-v1-your-key' >> ~/.hermes/.env

# 其他可选 provider key
echo 'ANTHROPIC_API_KEY=sk-ant-your-key' >> ~/.hermes/.env
echo 'OPENAI_API_KEY=sk-your-key' >> ~/.hermes/.env
```

#### 4. 将 Hermes 加入 PATH（可选）

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/venv/bin/hermes" ~/.local/bin/hermes

# 确认 hermes 可全局调用
# 需要提前把 ~/.local/bin 加入 PATH
hermes doctor
```

#### 5. 验证安装

```bash
hermes doctor           # 完整诊断
hermes model            # 选择 LLM 模型
hermes chat -q "Hello" # 快速对话验证
```

#### 6. 运行测试

```bash
# 激活虚拟环境后执行
source venv/bin/activate
pytest tests/ -v
```

### 安装方式对比

| 方式 | 命令 | 说明 |
|------|------|------|
| **源码开发安装（推荐）** | `uv pip install -e ".[all,dev]"` | 可编辑安装，包含全部可选功能 |
| **仅核心功能** | `uv pip install -e "."` | 仅安装核心依赖、CLI 与基础 Agent 能力 |
| **指定 extras** | `uv pip install -e ".[messaging,cron,cli]"` | 按需安装指定功能组 |
| **构建发布包** | `python -m build` | 从源码构建 wheel 和 sdist |
| **内网源码安装（Linux/macOS）** | `./scripts/install-from-source.sh --source-dir /path/to/hermes-agent` | 适合源码已在本地、不能直接从 GitHub clone 的环境 |
| **内网源码安装（Windows）** | `powershell -ExecutionPolicy Bypass -File .\scripts\install-from-source.ps1 -SourceDir C:\path\to\hermes-agent` | 在 Windows 上从本地源码树安装 |

### 内网源码安装说明

适用于以下场景：
- 已经拿到 Hermes 的源码目录或源码包
- 不能直接从 GitHub clone 仓库
- 需要在公司内网、受限网络或私有软件源环境中部署
- 仍然可以访问 Python / npm 软件源，或已经准备好内部镜像源

#### 前置依赖

| 依赖 | 是否必需 | 说明 |
|------|----------|------|
| **Git** | 必需 | 安装脚本会检查 Git 是否可用 |
| **Python 3.11+** | 必需 | 安装脚本会优先通过 `uv` 准备 Python 3.11 |
| **pip** | 必需 | 只检查，不自动安装；缺失时脚本直接退出 |
| **npm** | 必需 | 只检查，不自动安装；缺失时脚本直接退出 |
| **uv** | 推荐 | 缺失时脚本会自动安装 |
| **Node.js** | 可选 | 不影响核心安装，但缺失时会跳过部分浏览器相关功能和 bridge 依赖 |
| **ripgrep / ffmpeg** | 可选 | 安装脚本可能尝试自动安装，用于搜索和音视频相关能力 |

#### 网络要求

内网源码安装脚本**不会从 GitHub clone 仓库**，但默认仍会安装 Python 与 npm 依赖。因此，至少需要满足以下其一：

- 机器可以访问公共 PyPI 与 npm 源
- 机器已经配置为使用公司内部的 PyPI / npm 镜像
- 在安装前已经准备好依赖缓存或镜像包

#### 安装步骤

Linux / macOS：

```bash
chmod +x ./scripts/install-from-source.sh
./scripts/install-from-source.sh --source-dir /path/to/hermes-agent --skip-setup
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-from-source.ps1 -SourceDir C:\path\to\hermes-agent -SkipSetup
```

如果你希望安装脚本自动创建虚拟环境并初始化 `~/.hermes/config.yaml`、`~/.hermes/.env` 等文件，请保持默认行为。`--skip-setup` 只会跳过交互式初始化向导。

#### 本地 LLM 配置

内网部署通常会搭配本地或自建推理服务。Hermes 支持任何 OpenAI-compatible endpoint。你可以通过 `hermes model` 或直接编辑 `~/.hermes/config.yaml` 进行配置。

**场景 1：本地 / 内网 LLM 需要 API key**

适用于带鉴权的公司内网网关、代理服务，或需要令牌访问的私有推理端点：

```yaml
model:
  provider: custom
  default: your-model-name
  base_url: http://your-internal-llm.example.com/v1
  api_key: your-api-key
```

**场景 2：本地 LLM 不需要 API key**

适用于 Ollama、LM Studio、vLLM、llama.cpp 等本地服务。`api_key` 可以省略或留空：

```yaml
model:
  provider: custom
  default: your-model-name
  base_url: http://localhost:11434/v1
```

常见本地服务示例：
- **Ollama**：`http://localhost:11434/v1`
- **LM Studio**：`http://localhost:1234/v1`
- **vLLM**：`http://localhost:8000/v1`
- **llama.cpp**：`http://localhost:8080/v1`

也可以运行：

```bash
hermes model
```

然后选择 **Custom endpoint (self-hosted / VLLM / etc.)** 进行交互式配置。

#### 验证命令

```bash
hermes --version
hermes doctor
hermes model
```

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| `matrix` extra 安装失败 | `libolm` 与 macOS Clang 21+ 不兼容；如有需要请单独安装 Matrix 支持 |
| Termux 环境安装 | 使用 `.[termux]` 而不是 `.[all]`，以避免不兼容的 `faster-whisper` 依赖 |
| 浏览器工具不可用 | 确保已安装 Node.js 18+，并执行 `npm install` |
| `ripgrep` 缺失 | 请手动安装，例如 `brew install ripgrep`；否则文件搜索会回退到 grep |
