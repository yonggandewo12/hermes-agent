---
name: playwright-page-capture
description: >
  Playwright 页面抓取 skill，支持两种互补模式：
  ① DOM 抓取（--dom）：直接返回页面 HTML + 结构化元素 + 截图，无需配置，无需飞书；
  ② 飞书巡检模式：不加 --dom，走 YAML 配置，提取字段并发送飞书。
  当用户提到抓取网页、获取页面内容、DOM、HTML、页面源码、截图、或提到飞书巡检、页面监控时使用此 skill。
version: 2.0.0
metadata:
  hermes:
    tags: [communication, playwright, browser, monitoring, feishu, dom, snapshot]
    requires_toolsets: [terminal]
---

# Playwright Page Capture

Playwright 页面抓取，支持两种独立模式：
- **DOM 模式**（`--dom`）：直接返回页面内容，无需配置
- **飞书巡检模式**：YAML 配置 + 字段提取 + 飞书通知

## 快速对比

| | DOM 模式 | 飞书巡检模式 |
|---|---|---|
| 调用 | `/playwright-page-capture page_id=<URL> --dom` | `/playwright-page-capture page_id=<id>` |
| YAML 配置 | 不需要 | 需要 |
| 飞书通知 | 不发送 | 发送 |
| 返回内容 | HTML + 截图 + 元素树 | 字段提取结果 + 飞书消息 |
| 已登录态 | `--storage-state` | `--storage-state` 或 YAML 中配置 |

**区分规则：**
- 用户要**看页面内容**（HTML、截图、DOM 结构）→ 用 `--dom`
- 用户要**监控/巡检**（字段对比、飞书通知）→ 不用 `--dom`，走 YAML

---

## 模式一：DOM 抓取（--dom）

无需 YAML 配置，无需飞书，直接返回页面内容。

### 用法

```bash
# 基础 DOM 抓取
/playwright-page-capture page_id=https://example.com --dom

# 输出结构化元素树（便于程序解析）
/playwright-page-capture page_id=https://example.com --dom --format json

# 携带已登录态抓取私有页面
/playwright-page-capture page_id=https://github.com --dom --storage-state github_com.js
```

### 返回内容（stdout JSON）

```json
{
  "status": "ok",
  "url": "https://example.com/",
  "title": "Example Domain",
  "html": "<!DOCTYPE html><html lang=\"en\">...",
  "elements": [
    {"tag": "div", "id": "container", "text": "Example Domain", "children": 3},
    {"tag": "p", "text": "This domain is for use in illustrative examples..."}
  ],
  "screenshot": "/var/folders/.../snapshot_xxx.png"
}
```

### 选择器陷阱：nth-child vs 子元素

当页面结构是「容器 `.item` 里包含值 `<p>` + 标签 `<p>`」时：

```html
<div class="current-basic___item">
    <p>66%</p>    <!-- 数值 -->
    <p>相对湿度</p> <!-- 标签 -->
</div>
```

❌ **错误做法**：`.current-basic___item:nth-child(2)` 
→ `inner_text()` 返回 `"66%\n\n相对湿度"`（值+标签混在一起）

✅ **正确做法**：`.current-basic___item:nth-child(2) p`（加 ` p` 子元素）
→ `inner_text()` 返回 `"66%"`（纯净数值）

### storage_state 路径规则（两种模式通用）

| 配置值 | 实际路径 |
|--------|---------|
| `github_com.js` | `~/.hermes/stats/github_com.js` |
| `feishu/oc_xxx.js` | `~/.hermes/stats/feishu/oc_xxx.js` |
| `/tmp/login.json` | `/tmp/login.json`（绝对路径直接用） |
| `~/Desktop/auth.json` | `/home/user/Desktop/auth.json`（~ 展开后再解析） |

### 使用场景

| 用户说 | 调用的命令 |
|--------|-----------|
| 帮我抓取这个网页的内容 | `/playwright-page-capture page_id=<URL> --dom` |
| 获取页面的 HTML 和截图 | `/playwright-page-capture page_id=<URL> --dom` |
| 抓取需要登录的 GitHub 页面 | `/playwright-page-capture page_id=<URL> --dom --storage-state github_com.js` |
| 分析这个页面的 DOM 结构 | `/playwright-page-capture page_id=<URL> --dom --format json` |

---

## 模式二：飞书巡检（YAML 配置）

需要先在 `~/.hermes/playwright-page-capture.yaml` 配置页面。

### 用法

```bash
# 使用 YAML 中已配置的 page_id
/playwright-page-capture page_id=github_dashboard

# 临时指定飞书 chat_id（覆盖 YAML 配置）
/playwright-page-capture page_id=https://www.baidu.com --feishu-chat-id oc_xxxx

# CLI --storage-state 覆盖 YAML 中的 storage_state_path
/playwright-page-capture page_id=github_dashboard --storage-state github_com.js
```

### YAML 配置示例

```yaml
pages:
  # ── 示例：GitHub 登录态巡检 ─────────────────────────────
  - page_id: github_dashboard
    name: GitHub Dashboard
    url: https://github.com
    storage_state_path: github_com.js   # 相对路径 → ~/.hermes/stats/github_com.js
    wait_for:
      load_state: networkidle
      selector: ".Header"
    network_probe:
      url_keywords:
        - "api.github.com"
        - "avatars.githubusercontent.com"
    dom_fields:
      - field: page_title
        kind: title
      - field: user_name
        selector: ".Header-profileName"
        kind: text
        required: true
    feishu_target:
      chat_id: oc_xxxxxxxxxx

  # ── 示例：百度搜索巡检 ─────────────────────────────────
  - page_id: baidu_poc
    name: 百度搜索 PoC
    url: https://www.baidu.com
    wait_for:
      load_state: networkidle
      selector: "input[name='wd']"
    network_probe:
      url_keywords:
        - "baidu.com"
        - "bdimg.com"
    dom_fields:
      - field: page_title
        kind: title
      - field: search_input_name
        selector: "input[name='wd']"
        attribute: name
        required: true
    feishu_target:
      chat_id: oc_xxxxxxxxxx
```

### 完整字段说明

| YAML 字段 | 类型 | 说明 |
|-----------|------|------|
| `page_id` | string | 唯一标识，CLI 中引用 |
| `name` | string | 页面名称，用于日志和消息 |
| `url` | string | 目标 URL |
| `storage_state_path` | string | 已登录态文件路径（绝对或相对） |
| `wait_for.load_state` | string | 等待策略：`domcontentloaded` / `load` / `networkidle`（默认） |
| `wait_for.selector` | string | 可选，等待特定 DOM 元素出现 |
| `network_probe.url_keywords` | list[string] | 探测网络请求，验证关键 API 正常 |
| `dom_fields[].field` | string | 提取字段名 |
| `dom_fields[].selector` | string | CSS 选择器 |
| `dom_fields[].kind` | string | 提取方式：`title` / `text` / `attribute` |
| `dom_fields[].attribute` | string | 当 kind=attribute 时，指定属性名 |
| `dom_fields[].required` | bool | 是否必填，缺失时状态为 `field_missing` |
| `feishu_target.chat_id` | string | 飞书群 ID |

### storage_state_path 优先级

```
CLI --storage-state > YAML storage_state_path > 无（匿名访问）
```

### 与 playwright-auth-login 联动

若页面依赖自动登录站点，可在页面配置中增加 `auth_site_id`：

```yaml
pages:
  - page_id: github_dashboard
    name: GitHub Dashboard
    url: https://github.com
    auth_site_id: github_com
```

然后通过 `playwright-auth-login` 执行登录并触发关联抓取：

```bash
/playwright-auth-login --site-id github_com --run-linked-pages
```

`--run-linked-pages` 会自动查找所有 `auth_site_id` 匹配该 site_id 的页面，逐个执行抓取并推送飞书通知。

---

## 命令行参数（两种模式通用）

| 参数 | 说明 |
|------|------|
| `page_id=<id>` | YAML 模式：从 page-capture.yaml 查找的页面 ID |
| `page_id=<URL>` | URL 模式：直连 URL；需配合 `--feishu-chat-id` 或 `--dom` |
| `--dom` | **DOM 抓取模式**：返回 HTML + 截图，不发飞书 |
| `--feishu-chat-id <id>` | 飞书模式：指定接收通知的飞书群 |
| `--storage-state <path>` | **两种模式都支持** storage_state（绝对或相对路径） |
| `--format html\|json` | `--dom` 模式输出格式 |
| `--config <path>` | 手动指定配置文件，默认 `~/.hermes/playwright-page-capture.yaml` |

### 飞书消息格式

状态为 `ok` 时，飞书消息包含所有提取的 `dom_fields`（除 `page_title` 外），示例：

```
【页面巡检结果】
页面：和风搜天气
状态：ok
页面标题：和风天气控制台

available_quota：可用配额
available_quota_value：xxx 次

网络探测：命中
网络状态码：200
结论：页面加载正常
```

因此配置 `dom_fields` 时将 `field` 设为中文名称，推送消息即可直接展示。

---

## 使用场景速查

| 用户意图 | 命令 |
|---------|------|
| 抓页面内容（HTML + 截图） | `/playwright-page-capture page_id=<URL> --dom` |
| 抓已登录页面内容 | `/playwright-page-capture page_id=<URL> --dom --storage-state github_com.js` |
| 分析页面 DOM 结构 | `/playwright-page-capture page_id=<URL> --dom --format json` |
| 巡检已配置页面 | `/playwright-page-capture page_id=github_dashboard` |
| 巡检并携带登录态 | `/playwright-page-capture page_id=github_dashboard --storage-state github_com.js` |
| 临时 URL 推飞书 | `/playwright-page-capture page_id=<URL> --feishu-chat-id oc_xxxx` |

---

## 完整使用链

```bash
# 1. 登录并保存 storage_state
/capture-auth-login https://github.com
# → ~/.hermes/stats/github_com.js

# 2. 配置 YAML（~/.hermes/playwright-page-capture.yaml）
pages:
  - page_id: github_dashboard
    name: GitHub Dashboard
    url: https://github.com
    storage_state_path: github_com.js
    ...

# 3. DOM 抓取（无需 YAML）
/playwright-page-capture page_id=https://github.com --dom --storage-state github_com.js

# 4. 飞书巡检（需要 YAML）
/playwright-page-capture page_id=github_dashboard

# 5. Cron 定时巡检
/capture-auth-login https://example.com
hermes -q "/cron add 使用 playwright-page-capture page_id=github_dashboard"
```

---

## 默认配置路径

`~/.hermes/playwright-page-capture.yaml`

示例文件位置：
`optional-skills/communication/playwright-page-capture/examples/page-capture.example.yaml`

## 飞书凭证配置（三种方式，按优先级）

1. YAML 顶层 `feishu:` 字段
2. `~/.hermes/config.yaml` → `tools.playwright_page_capture.feishu`
3. 环境变量 `FEISHU_APP_ID` + `FEISHU_APP_SECRET`
