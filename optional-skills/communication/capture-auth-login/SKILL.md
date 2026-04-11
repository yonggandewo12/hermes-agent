---
name: capture-auth-login
description: >
  交互式登录捕获 skill。给定 URL，自动检测登录跳转，打开浏览器让用户完成登录（含扫码登录），
  然后将 Playwright storage_state 自动保存到 ~/.hermes/stats/{域名}.js，CLI 输出成功信息。
  当用户提到"登录"、"auth"、"扫码"、"storage_state"、"capture login"、"帮我登录"时使用此 skill。
version: 1.0.0
metadata:
  hermes:
    tags: [auth, login, playwright, browser, session, cookies, storage-state]
    requires_toolsets: [terminal]
---

# Capture Auth Login

交互式登录捕获。给定 URL → 检测登录跳转 → 打开浏览器让用户完成登录 → 自动保存 storage_state。

## 核心流程

```
URL → 登录跳转检测 → 浏览器弹出 → 用户登录/扫码 → storage_state 保存 → CLI 成功提示
```

## 使用场景

| 用户说 | 说明 |
|--------|------|
| `/capture-auth-login https://github.com` | 登录 GitHub |
| 帮我登录这个网站 | Agent 自动调用 |
| save login state | 保存登录态 |
| capture auth | 捕获认证状态 |

## 命令行用法

### Slash 命令（推荐）
```
/capture-auth-login https://github.com
/capture-auth-login https://feishu.cn --timeout 600
```

### hermes -q
```bash
hermes -q "/capture-auth-login https://github.com"
hermes -q "帮我登录 https://example.com"
```

### 直接运行脚本
```bash
python optional-skills/communication/capture-auth-login/scripts/capture_auth_login.py \
    --url https://github.com
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--url <URL>` | **必填** | 目标 URL |
| `--output-dir` | `~/.hermes/stats/` | storage_state 保存目录 |
| `--output-name` | `{域名}.js` | 保存文件名（含 `.js` 后缀） |
| `--timeout` | `300` | 最大等待登录完成秒数 |
| `--poll-interval` | `1.5` | 检测登录状态轮询间隔（秒） |

### 输出路径规则

```bash
# --output-name 默认自动从 URL 提取域名
--url https://github.com/login   → ~/.hermes/stats/github_com.js
--output-name github.js           → ~/.hermes/stats/github.js
--output-name feishu/oc_xxx.js   → ~/.hermes/stats/feishu/oc_xxx.js

# 绝对路径直接使用
--output-name /tmp/login.json     → /tmp/login.json
```

## 返回结果（stdout JSON）

```json
{
  "status": "success",
  "url": "https://github.com/",
  "output_path": "/home/user/.hermes/stats/github_com.js",
  "elapsed_seconds": 45.2
}
```

其他可能状态：`no_login_detected`、`timeout`

## 登录检测机制

**URL 模式**：检测路径中是否包含以下关键词
`/login`, `/signin`, `/sign-in`, `/auth`, `/oauth`, `/authorize`, `/account/login`, `/accounts/login`, `/session`

**DOM 模式**：检测页面是否存在登录特征元素
`input[type=password]`, `[name=username]`, `[name=email]`, `[class*=login]`, `form[action*=login]`

**登录完成判定**：
- URL 离开登录路径 + 出现 session cookies
- Session cookies 包含：`session`, `token`, `auth`, `user`, `jwt`, `access_token`

## 结合 playwright-page-capture 使用

```bash
# 1. 先登录，保存 storage_state
/capture-auth-login https://github.com

# 2. DOM 模式抓取（携带登录态）
/playwright-page-capture page_id=https://github.com --dom --storage-state github_com.js

# 3. 飞书巡检模式（携带登录态）
# 先配置 ~/.hermes/playwright-page-capture.yaml
# page_id=github_dashboard 中配置 storage_state_path: github_com.js
/playwright-page-capture page_id=github_dashboard
```

## 依赖

- `playwright`（会自动提示安装 Chromium）
- `playwright install chromium`（如果未安装）
