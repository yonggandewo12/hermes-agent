from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, SCRIPTS_DIR)

from page_capture_classify import classify_capture_result
from page_capture_config import load_page_capture_config
from page_capture_dom import extract_dom_fields
from page_capture_feishu import FeishuAppClient
from page_capture_probe import probe_network_events

def _build_message(page_name: str, state: str, fields: dict[str, str], probe) -> str:
    if state == "ok":
        return (
            f"【页面巡检结果】\n页面：{page_name}\n状态：ok\n"
            f"页面标题：{fields.get('page_title', '')}\n"
            f"搜索框名称：{fields.get('search_input_name', '')}\n"
            f"网络探测：{'命中' if probe.hit else '未命中'}\n"
            f"网络状态码：{probe.status if probe.status is not None else ''}\n"
            "结论：公共抓取链路运行正常"
        )
    if state == "field_missing":
        return f"【页面字段缺失】\n页面：{page_name}\n状态：field_missing\n缺失字段：{','.join(sorted(set(fields.get('_missing_fields', []))))}"
    if state == "login_required":
        return f"【页面需要登录】\n页面：{page_name}\n状态：login_required\n动作：请手工登录后重试"
    return f"【页面抓取失败】\n页面：{page_name}\n状态：fetch_failed\n原因：页面加载失败、超时或提取流程异常"

def run_capture_pipeline(*, config_path: str, page_id: str, feishu_client, browser_runner):
    config = load_page_capture_config(config_path)
    page_def = next(page for page in config.pages if page.page_id == page_id)
    runtime = browser_runner(page_def)
    probe = probe_network_events(runtime["events"], page_def.network_probe.url_keywords)
    dom_result = extract_dom_fields(runtime["page"], page_def.dom_fields)
    state = classify_capture_result(
        fetch_error=runtime["fetch_error"],
        missing_fields=dom_result.missing_fields,
        probe_hit=probe.hit,
        login_required=runtime["login_required"],
    )
    fields = dict(dom_result.fields)
    fields["_missing_fields"] = dom_result.missing_fields
    text = _build_message(page_def.name, state, fields, probe)
    message_id = feishu_client.send_text(chat_id=page_def.feishu_target.chat_id, text=text)
    return {"state": state, "message_id": message_id}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--page-id", required=True)
    args = parser.parse_args()
    client = FeishuAppClient(
        app_id=os.environ["FEISHU_APP_ID"],
        app_secret=os.environ["FEISHU_APP_SECRET"],
    )
    from page_capture_browser import run_browser_capture
    result = run_capture_pipeline(
        config_path=args.config,
        page_id=args.page_id,
        feishu_client=client,
        browser_runner=run_browser_capture,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())