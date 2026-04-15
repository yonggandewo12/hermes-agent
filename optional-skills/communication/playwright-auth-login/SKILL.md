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

## 完整使用链

```bash
# 1. 首次登录（保存 storage_state）
/playwright-auth-login --site-id github_com

# 2. 登录并触发关联页面抓取
/playwright-auth-login --site-id github_com --run-linked-pages

# 3. 配置 YAML 页面关联
# 在 ~/.hermes/playwright-page-capture.yaml 中设置 auth_site_id: github_com

# 4. 定时巡检
/capture-auth-login --site-id github_com --run-linked-pages
```
