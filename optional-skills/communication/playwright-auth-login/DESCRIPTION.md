# Playwright Auth Login

Playwright 认证登录 skill，支持：
1. 读取 YAML 配置，执行多步登录流程，保存 storage_state
2. 可选：登录后自动触发关联页面抓取（`--run-linked-pages`）

**安装方式：**
```bash
hermes skills install official/communication/playwright-auth-login
```

**依赖：** `playwright`（会自动提示安装 Chromium）
