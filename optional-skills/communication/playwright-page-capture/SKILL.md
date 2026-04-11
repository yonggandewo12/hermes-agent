---
name: playwright-page-capture
description: 使用 Playwright 抓取固定页面，提取字段并将结果发送到飞书群。
metadata:
  hermes:
    tags: [communication, playwright, browser, monitoring]
    requires_toolsets: [terminal]
---

# Playwright Page Capture

## When to Use
- 用户要快速巡检任意 URL 是否可访问
- 用户要对固定页面执行 Playwright 抓取并推送飞书（支持 DOM 字段提取）
- 用户要通过 Hermes cron 定时触发同一抓取流程

## Inputs
- `page_id=<configured-page-id>` — YAML 模式，在 page-capture.yaml 中查找页面定义
- `page_id=<URL>` — URL 模式，直连 URL，无需配置文件；必须同时传入 `feishu_chat_id`
- `config=<optional-absolute-path>` — 可选，默认 `~/.hermes/playwright-page-capture.yaml`
- `feishu_chat_id=<optional-chat-id>` — 可选，URL 模式必须指定；YAML 模式可覆盖配置文件中的 chat_id

## Procedure
1. 调用 `python optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py ...`
2. 输出统一 JSON 结果
3. 使用同一 skill 支持手动与 cron 调用

## Two Modes

### YAML 模式（推荐用于定期巡检）
使用预定义的 page-capture.yaml 配置文件，支持：
- DOM 字段提取（页面标题、文本、属性值等）
- 网络请求探测（验证关键 API 是否正常响应）
- 灵活的等待策略（等待网络空闲或特定 DOM 元素出现）

### URL 模式（快速一次性巡检）
直接传入 URL，无需配置文件：
- 轻量，适合临时检查某个页面是否可访问
- 报告页面加载状态和标题
- 不支持 DOM 字段提取和网络探测

## Default Config Path
默认配置文件：`~/.hermes/playwright-page-capture.yaml`

将配置文件放在该路径即可，无需每次传递 `--config` 参数。

## Manual Trigger
```bash
# YAML 模式（使用默认配置路径）
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc"

# YAML 模式（指定配置文件）
hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc config=/path/to/page-capture.yaml"

# URL 模式（直连任意 URL）
hermes -q "使用 playwright-page-capture 处理 page_id=https://www.baidu.com feishu_chat_id=oc_xxxx"
```

## Cron Trigger
通过 `/cron add` 创建定时任务，YAML 模式示例：
```
使用 playwright-page-capture 处理 page_id=baidu_poc
```
（使用默认配置路径 `~/.hermes/playwright-page-capture.yaml`）
