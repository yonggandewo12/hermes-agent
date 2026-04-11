# Playwright Page Capture

Playwright 页面抓取，支持两种互补模式：

| 模式 | 调用 | 说明 |
|------|------|------|
| DOM 抓取 | `/playwright-page-capture page_id=<URL> --dom` | 直接返回 HTML + 截图，无需配置，无需飞书 |
| 飞书巡检 | `/playwright-page-capture page_id=<id>` | YAML 配置 + 字段提取 + 飞书通知 |

两种模式都支持 `--storage-state` 携带已登录态。

**安装方式：**
```bash
hermes skills install official/communication/playwright-page-capture
```

**依赖：** `playwright`（会自动提示安装 Chromium）
