---
name: playwright-auth-login
description: >
  Playwright 认证登录 skill，支持读取 YAML 配置执行多步登录流程并保存 storage_state。
  可选地，登录后自动触发关联页面抓取（--run-linked-pages），通过 auth_site_id 关联 page-capture 页面。
  当用户提到登录、认证、storage_state、或提到需要登录才能访问的页面时使用此 skill。
version: 1.0.0
metadata:
  hermes:
    tags: [communication, playwright, auth, login, browser]
    requires_toolsets: [terminal]
---

# Playwright Auth Login

执行 Playwright 多步登录，保存认证状态到 storage_state 文件。

## 用法

```bash
# 基础登录
/playwright-auth-login --site-id github_com

# 登录后自动抓取关联页面
/playwright-auth-login --site-id github_com --run-linked-pages
```

## CLI 参数

| 参数 | 说明 |
|------|------|
| `--site-id` | **必填**，在 auth config 中定义的 site_id |
| `--run-linked-pages` | 登录后自动抓取 auth_site_id 匹配的 page-capture 页面 |
| `--config` | 手动指定 auth 配置文件，默认 `~/.hermes/playwright-auth.yaml` |
| `--capture-config` | 指定 page-capture 配置文件（配合 `--run-linked-pages` 使用） |

## 支持的 steps actions

| action | selector | value_from | 说明 |
|--------|----------|------------|------|
| `fill` | CSS 选择器 | `username` / `password` | 填入凭据 |
| `click` | CSS 选择器 | - | 点击元素 |
| `press` | CSS 选择器 | `Enter` 等键名 | 对元素按键盘键（无 selector 时默认 `body`） |
| `wait_for_selector` | CSS 选择器 | - | 等待元素出现 |
| `wait_for_url` | - | - | 等待 URL 条件，参数 `url_contains` 或 `url_not_contains` |

## YAML 配置示例

```yaml
sites:
  - site_id: github_com
    name: GitHub
    login_url: https://github.com/login
    username: your_email@example.com
    password: your_password
    storage_state_path: github_com.js
    steps:
      - action: fill
        selector: "#login_field"
        value_from: username
      - action: fill
        selector: "#password"
        value_from: password
      - action: click
        selector: "button[type='submit']"
      - action: wait_for_url
        url_not_contains: /login
    success_criteria:
      url_not_contains:
        - /login
        - /sign_in
      cookie_names:
        - logged_in
```

**注意**：SPA（单页应用）站点可能没有 `button[type='submit']`，改用 `press` + `Enter` 更可靠：

```yaml
    steps:
      - action: fill
        selector: "input[placeholder='Email/phone']"
        value_from: username
      - action: fill
        selector: "input[placeholder='Password']"
        value_from: password
      - action: press
        selector: "input[placeholder='Password']"
        value_from: Enter
      - action: wait_for_url
        url_not_contains: /login
```

## 无需登录：直接按 page_id 抓取

如果某个 `site_id` 的 auth 配置不完整（如第三方页面、不需要独立登录的子页面），可以在 `playwright-auth.yaml` 中只填 `site_id`，留空 `login_url` / `username` / `password`。运行时传入 `--run-linked-pages`，CLI 会：

1. 检测到 auth 配置不完整，跳过登录
2. 按 `page_id`（而非 `auth_site_id`）在 page-capture 配置中查找对应页面
3. 直接执行页面抓取

page-capture YAML 中对应页面的 `auth_site_id` 可以随意填写（不需要与 auth site_id 一致），匹配完全靠 `page_id == site_id`：

```yaml
# playwright-page-capture.yaml
pages:
  - page_id: weather-bj
    name: 和风天气-北京
    url: https://www.qweather.com/weather/beijing-101010100.html
    storage_state_path: ~/.hermes/stats/console_qweather_com.js
    auth_site_id: weather-bj   # ← 随意，与 auth site_id 无关
```

```yaml
# playwright-auth.yaml
sites:
  - site_id: weather-bj         # ← 与 page_id 完全相同
    name: weather-bj
    # login_url / username / password 全部留空 → 跳过登录
```

**注意**：`load_state` 设 `networkidle` 容易超时，建议用 `load` 或 `domcontentloaded`。

## auth_site_id 关联机制

在 `playwright-page-capture.yaml` 中配置页面时，设置 `auth_site_id`：

```yaml
pages:
  - page_id: github_dashboard
    name: GitHub Dashboard
    url: https://github.com
    auth_site_id: github_com   # ← 关联到 auth config 中的 site_id
    storage_state_path: github_com.js
    ...
```

使用 `--run-linked-pages` 时，auth CLI 会：
1. 读取 page-capture 配置
2. 筛选 `auth_site_id == site_id` 的所有页面
3. 对每个页面调用 `run_capture_pipeline`

## storage_state 路径规则

| 配置值 | 实际路径 |
|--------|---------|
| `github_com.js` | `~/.hermes/stats/github_com.js` |
| `feishu/oc_xxx.js` | `~/.hermes/stats/feishu/oc_xxx.js` |
| `/tmp/login.json` | `/tmp/login.json`（绝对路径直接用） |

## 跳过登录模式（auth 配置不完整）

如果 `site_id` 的 auth 配置缺少关键字段（`login_url`、`username`、`password` 任一为空），auth 流程会被跳过，直接按 `page_id` 匹配 `playwright-page-capture.yaml` 中的页面进行抓取。

这适用于：站点本身无需单独登录（共享其他站点的 storage_state）、或只需临时抓取一个页面。

```yaml
# playwright-auth.yaml — weather-bj 配置不完整，跳过登录
- site_id: weather-bj
  name: 和风搜天气-北京
  login_url:          # ← 空，跳过登录
  storage_state_path: # ← 空，从 page-capture YAML 读取
  username:
  password:
  steps: []
```

对应的 `playwright-page-capture.yaml` 中配置 `page_id: weather-bj` 和 `storage_state_path` 即可：
```yaml
- page_id: weather-bj
  name: 和风搜天气-北京
  url: https://www.qweather.com/weather/beijing-101010100.html
  storage_state_path: ~/.hermes/stats/console_qweather_com.js
  auth_site_id: weather-bj
```

运行效果：
```bash
/playwright-auth-login --site-id weather-bj --run-linked-pages
# → {"status": "auth_skipped", "linked_pages": [{"page_id": "weather-bj", "status": "ok", ...}]}
```

**注意**：`load_state` 不要用 `networkidle`，国内站点容易因 CDN/广告请求导致超时，建议用 `load` 或 `domcontentloaded`。实测 `weather-bj` 页面 `networkidle` → 超时 30s；改为 `domcontentloaded` 后正常。

### weather / weather-bj 配置区别（常见踩坑）

| site_id | 用途 | 登录行为 | 结果 |
|---------|------|---------|------|
| `weather` | 更新登录凭证 | 完整走登录流程 | `step_failed` 超时（id.qweather.com 加载慢） |
| `weather-bj` | 跳过登录直接抓取 | auth_skipped，按 page_id 匹配抓取 | `ok` |

**踩坑原因**：传了 `weather`（完整登录配置），但 id.qweather.com 登录页加载超过 30s 限制导致超时。应该用 `weather-bj`（不完整配置，跳过登录，直接用已有 storage_state 抓取）。

如果确实要更新登录凭证：
1. 先增大 `--goto-timeout`（默认 30000ms）
2. 或者单独跑一次登录保存凭证（不加 `--run-linked-pages`）
3. 然后再用 `weather-bj --run-linked-pages` 触发抓取

## 登录状态返回

| 状态 | 含义 |
|------|------|
| `success` | 登录成功，storage_state 已保存 |
| `login_failed` | 步骤执行完但未满足 success_criteria |
| `step_failed` | 执行某一步时失败，如 selector 找不到 |
| `config_error` | site_id 不存在或配置缺失 |

## 完整使用链

```bash
# 1. 配置 auth YAML
# 将示例文件复制到配置路径：
cp optional-skills/communication/playwright-auth-login/examples/playwright-auth.example.yaml \
   ~/.hermes/playwright-auth.yaml

# 2. 首次登录（保存 storage_state）
/playwright-auth-login --site-id github_com

# 3. 在 page-capture.yaml 中关联页面
# 设置 auth_site_id: github_com

# 4. 登录并触发关联页面抓取
/playwright-auth-login --site-id github_com --run-linked-pages

# 5. 定时巡检（cron）
hermes -q "/cron add /playwright-auth-login --site-id github_com --run-linked-pages"
```

## CLI 直接运行（绕过 slash command）

如果通过 Hermes CLI 执行，需注意：

1. **先确认当前 Hermes 运行环境里已经有 playwright：**
   ```bash
   ~/Documents/project/hermes-agent/venv/bin/python3 -c "import playwright"
   ~/Documents/project/hermes-agent/venv/bin/python3 -m playwright install chromium
   ```

   如果第一条命令报 `ModuleNotFoundError`，再补装：
   ```bash
   cd ~/Documents/project/hermes-agent
   ./venv/bin/python3 -m ensurepip
   ./venv/bin/python3 -m pip install playwright
   ./venv/bin/python3 -m playwright install chromium
   ```

2. **入口脚本是 `playwright_auth_login.py`**（不是 `playwright_auth_runner.py`）：
   ```bash
   cd ~/.hermes/skills/communication/playwright-auth-login
   ~/Documents/project/hermes-agent/venv/bin/python3 scripts/playwright_auth_login.py \
     --site-id weather --run-linked-pages
   ```

3. **关键路径**：
   - skill 脚本目录：`~/.hermes/skills/communication/playwright-auth-login/scripts/`
   - 默认 auth 配置：`~/.hermes/playwright-auth.yaml`
   - 默认 page-capture 配置：`~/.hermes/playwright-page-capture.yaml`
   - venv Python：`~/Documents/project/hermes-agent/venv/bin/python3`

## 依赖与前置条件

- `playwright`（会自动提示安装 Chromium）
- `--run-linked-pages` 依赖飞书凭证：可通过 `~/.hermes/playwright-page-capture.yaml` 的 `feishu:` 字段、环境变量 `FEISHU_APP_ID` + `FEISHU_APP_SECRET`，或 Hermes 全局配置提供
