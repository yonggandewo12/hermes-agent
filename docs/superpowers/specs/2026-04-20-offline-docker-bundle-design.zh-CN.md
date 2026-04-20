# Hermes Agent 离线 Docker 交付设计

## 背景

目标是在联网环境中构建出一个包含项目完整依赖的大型 Docker 镜像，并将其导出为可交付制品，使离线环境无需再次联网拉取任何 Python、npm、Playwright 或系统依赖，即可直接完成镜像加载与部署。

本次需求不包含“离线环境重新 build 镜像”的能力，重点是一次构建、多次离线部署。

## 目标

- 在联网环境中基于当前项目构建完整镜像。
- 镜像保留当前 Dockerfile 对完整能力集的支持，包括：
  - Debian 基础系统依赖
  - Python `pip install -e ".[all]"`
  - 根目录 `npm install`
  - `scripts/whatsapp-bridge` 下的 `npm install`
  - Playwright Chromium 浏览器及其依赖
- 生成标准化离线交付目录，便于复制到内网或隔离环境。
- 提供一个可重复复用的一键式脚本，统一构建与导出流程。
- 更新中英文文档，说明构建、导出、传输、加载与运行步骤。

## 非目标

- 不支持离线环境重新执行 `docker build`。
- 不新增 slim / minimal 版镜像。
- 不引入私有镜像仓库推送逻辑。
- 不对当前 Dockerfile 做围绕“减小体积”的专项优化。
- 不扩展为多平台镜像矩阵构建。

## 用户场景

### 场景 1：外网构建，内网部署

1. 在联网机器拉取项目代码。
2. 执行一键脚本构建完整镜像。
3. 脚本导出 tar 包、校验文件、离线部署脚本和构建元信息。
4. 将整个交付目录复制到离线环境。
5. 在离线环境执行加载脚本，并使用镜像启动服务。

### 场景 2：重复发版

1. 开发者在新代码版本上重新执行同一脚本。
2. 生成新 tar 包和构建信息。
3. 离线环境按相同流程替换镜像版本。

## 当前状态

当前仓库已有 `Dockerfile`，其行为为：

- 安装系统包：`build-essential`、`nodejs`、`npm`、`python3`、`python3-pip`、`ripgrep`、`ffmpeg`、`gcc`、`python3-dev`、`libffi-dev`
- 复制整个仓库到 `/opt/hermes`
- 执行：
  - `pip install --no-cache-dir -e ".[all]" --break-system-packages`
  - `npm install --prefer-offline --no-audit`
  - `npx playwright install --with-deps chromium --only-shell`
  - `scripts/whatsapp-bridge` 下的 `npm install --prefer-offline --no-audit`
- 设置入口脚本为 `docker/entrypoint.sh`

这已经满足“在联网构建时拉齐完整依赖”的前提。当前缺少的是标准化交付流程和文档。

## 方案概述

采用“完整镜像交付 + 一键导出脚本”的方案：

1. 继续使用当前 `Dockerfile` 构建完整镜像。
2. 新增脚本 `scripts/build_offline_docker_bundle.sh`，在联网环境一键完成：
   - 镜像构建
   - 镜像导出为 tar
   - 生成 sha256 校验文件
   - 生成离线部署辅助脚本
   - 生成构建元信息文件
3. 将交付结果统一输出到 `dist/docker/`。
4. 更新 README 和部署文档，明确离线部署方式。

## 文件变更设计

### 新增文件

#### `scripts/build_offline_docker_bundle.sh`

一键构建并导出离线 Docker 交付物。

#### `docs/deployment/offline-docker.md`

补充完整离线交付文档。

### 更新文件

#### `README.md`

新增英文离线 Docker 交付章节。

#### `README.zh-CN.md`

新增中文离线 Docker 交付章节。

## 一键脚本设计

### 脚本路径

`scripts/build_offline_docker_bundle.sh`

### 默认行为

无参执行即可完成标准流程：

- 默认 Dockerfile：`./Dockerfile`
- 默认镜像 tag：`hermes-agent:offline-full`
- 默认输出目录：`dist/docker`

### 支持参数

- `--tag <image_tag>`：自定义镜像 tag
- `--output-dir <path>`：自定义输出目录
- `--dockerfile <path>`：自定义 Dockerfile 路径

### 脚本步骤

1. 检查 `docker` 命令是否存在。
2. 校验 Docker daemon 可访问。
3. 校验传入的 Dockerfile 存在。
4. 创建输出目录。
5. 读取当前 git commit（若当前目录是 git 仓库且可访问）。
6. 执行 `docker build` 构建完整镜像。
7. 执行 `docker save` 导出镜像 tar 包。
8. 生成 tar 包的 sha256 文件。
9. 生成 `load-and-run.sh`。
10. 生成 `build-info.txt`。
11. 打印产物路径和后续离线部署提示。

### 输出文件命名

默认命名规则：

- `hermes-agent-offline-full.tar`
- `hermes-agent-offline-full.tar.sha256`
- `load-and-run.sh`
- `build-info.txt`

如果用户自定义 tag，tar 文件名应做安全化处理（将 `/`、`:` 等不适合作为文件名的字符替换为 `-`），确保输出文件名稳定可用。

## 离线交付目录设计

默认输出目录：`dist/docker/`

目录示意：

```text
dist/docker/
├── hermes-agent-offline-full.tar
├── hermes-agent-offline-full.tar.sha256
├── load-and-run.sh
└── build-info.txt
```

## `load-and-run.sh` 设计

### 职责

该脚本面向离线环境，不负责构建镜像，仅负责：

1. 加载 tar 包中的镜像
2. 输出推荐运行命令

### 不直接写死完整 `docker run`

由于不同部署环境需要不同的：

- 环境变量
- volume 挂载
- 端口映射
- 重启策略
- 数据目录

因此 `load-and-run.sh` 采用更保守的设计：

- 自动执行 `docker load -i <tar>`
- 打印推荐 `docker run` 示例
- 提示用户按场景补充环境变量

这样既能保证离线环境快速上手，也不会把运行参数耦合死。

### 推荐输出示例

脚本在 load 成功后，输出类似：

```bash
docker run -it --rm \
  -v hermes-data:/opt/data \
  hermes-agent:offline-full
```

如项目需要实际运行时配置 API Key，则文档中说明用户需额外传入 `-e` 参数。

## 构建元信息设计

`build-info.txt` 至少包含：

- image tag
- tar file name
- dockerfile path
- git commit
- build timestamp

可选补充：

- hostname
- current branch

其目的是便于离线环境追踪制品来源，而非作为机器可解析协议。

## 文档设计

### `README.md`

新增 “Offline Docker Bundle” 章节，内容包括：

- 适用场景
- 一键构建命令
- 产物目录说明
- 离线环境加载方式
- 运行命令示例

### `README.zh-CN.md`

新增“离线 Docker 交付”章节，内容与英文 README 对齐。

### `docs/deployment/offline-docker.md`

提供更完整说明：

- 背景与适用范围
- 脚本参数说明
- 输出目录结构
- 外网构建步骤
- 离线拷贝步骤
- 离线加载与运行方式
- 常见问题（镜像大、构建慢、需 Docker daemon、首次构建联网）

## 错误处理设计

脚本应在以下情况快速失败并给出明确错误：

- `docker` 未安装
- Docker daemon 不可用
- 指定 Dockerfile 不存在
- `docker build` 失败
- `docker save` 失败
- sha256 生成失败

脚本应使用严格模式（如 `set -euo pipefail`），避免部分成功、部分失败后留下不明确状态。

## 测试与验证设计

至少覆盖以下验证：

1. 在联网环境运行脚本可成功构建镜像。
2. 输出目录包含预期四类文件。
3. tar 包可被 `docker load` 成功加载。
4. `load-and-run.sh` 可在离线环境执行镜像加载动作。
5. README 与部署文档中的命令和脚本实际行为一致。

## 风险与取舍

### 镜像体积大

这是本方案的显式取舍。因为目标是完整离线部署，而不是最小化镜像。

### 构建过程仍依赖外网

这是符合需求的，因为要求是在外网先构建完整镜像，并不要求离线 build。

### 运行参数无法完全统一

不同用户环境差异较大，因此不把业务参数写死在离线脚本中，而是提供保守示例和文档说明。

## 完成标准

满足以下条件即可视为完成：

- 仓库内存在可重复执行的一键构建脚本。
- 脚本可产出标准化离线 Docker 交付目录。
- 离线环境可通过交付目录中的 tar 包完成 `docker load`。
- 中英文 README 已补充离线 Docker 交付说明。
- 新增部署文档说明完整流程。

## 后续可选优化

本次不做，但未来可以考虑：

- 多阶段构建，减小最终镜像体积
- 生成 slim / full 两档镜像
- 增加镜像 tag 中的版本号或 commit 后缀
- 增加自动清理旧产物的选项
- 增加对 `docker run` 参数模板的自定义支持
