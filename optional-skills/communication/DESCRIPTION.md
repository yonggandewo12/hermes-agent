Communication and decision-making frameworks — structured response formats for proposals, trade-off analysis, and stakeholder-ready recommendations.

## Skills in this category

| Skill | Description | Install |
|-------|-------------|---------|
| `playwright-page-capture` | Playwright 页面抓取：DOM 模式（--dom，直接返回 HTML+截图）和飞书巡检模式（YAML 配置+字段提取+飞书通知）| `hermes skills install official/communication/playwright-page-capture` |
| `capture-auth-login` | 交互式登录捕获：检测登录跳转，打开浏览器完成登录，自动保存 storage_state | `hermes skills install official/communication/capture-auth-login` |

## Quick Start

```bash
# 1. 登录（保存 storage_state）
/capture-auth-login https://github.com
# → ~/.hermes/stats/github_com.js

# 2. DOM 抓取（无需配置）
/playwright-page-capture page_id=https://github.com --dom --storage-state github_com.js

# 3. 飞书巡检（需要 YAML 配置）
/playwright-page-capture page_id=github_dashboard
```
