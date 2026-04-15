# Playwright Auth Login

Playwright 认证登录 skill，支持：
1. 读取 YAML 配置，执行多步登录流程，保存 storage_state
2. 可选：登录后自动触发关联页面抓取（`--run-linked-pages`）

**安装方式：**
```bash
hermes skills install official/communication/playwright-auth-login
```

**依赖：** `playwright`（会自动提示安装 Chromium）

## 步骤类型

| action | selector | value_from | 说明 |
|--------|----------|------------|------|
| `fill` | CSS 选择器 | `username` / `password` | 填入凭据 |
| `click` | CSS 选择器 | - | 点击元素 |
| `press` | CSS 选择器（可选，默认 body） | `Enter` 等键名 | 按键盘键 |
| `wait_for_selector` | CSS 选择器 | - | 等待元素出现 |
| `wait_for_url` | - | `url_contains` / `url_not_contains` | 等待 URL 条件 |

## storage_state 路径规则

| 配置值 | 实际路径 |
|--------|---------|
| `github_com.js` | `~/.hermes/stats/github_com.js` |
| `feishu/oc_xxx.js` | `~/.hermes/stats/feishu/oc_xxx.js` |
| `/tmp/login.json` | `/tmp/login.json`（绝对路径直接用） |

## 登录状态返回

| 状态 | 含义 |
|------|------|
| `success` | 登录成功，storage_state 已保存 |
| `login_failed` | 步骤执行完但未满足 success_criteria |
| `step_failed` | 执行某一步时失败，如 selector 找不到 |
| `config_error` | site_id 不存在或配置缺失 |
