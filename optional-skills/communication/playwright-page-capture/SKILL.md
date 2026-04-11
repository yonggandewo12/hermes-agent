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
- 用户要先用公开页面验证页面抓取框架
- 用户要对固定页面执行 Playwright 抓取并推送飞书
- 用户要通过 Hermes cron 定时触发同一抓取流程

## Inputs
- `page_id=<configured-page-id>`
- `config=<optional-absolute-path>` — 可选，默认 `~/.hermes/playwright-page-capture.yaml`

## Procedure
1. 调用 `python optional-skills/communication/playwright-page-capture/scripts/run_page_capture.py ...`
2. 输出统一 JSON 结果
3. 使用同一 skill 支持手动与 cron 调用

## Default Config Path
默认配置文件：`~/.hermes/playwright-page-capture.yaml`

将配置文件放在该路径即可，无需每次传递 `--config` 参数。

## Manual Trigger
- 对话触发：`使用 playwright-page-capture 处理 page_id=baidu_poc`（使用默认路径）
- CLI 触发：`hermes -q "使用 playwright-page-capture 处理 page_id=baidu_poc"`
- 指定配置：`使用 playwright-page-capture 处理 page_id=baidu_poc config=/path/to/page-capture.yaml`

## Cron Trigger
- 通过 `/cron add` 创建定时任务，prompt 中调用同一个 skill：
  `使用 playwright-page-capture 处理 page_id=baidu_poc`
  （使用默认配置路径 `~/.hermes/playwright-page-capture.yaml`）
