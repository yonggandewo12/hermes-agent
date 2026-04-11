from __future__ import annotations
from page_capture_models import DomExtractionResult, DomFieldRule

def extract_dom_fields(page, rules: list[DomFieldRule]) -> DomExtractionResult:
    fields: dict[str, str] = {}
    missing_fields: list[str] = []
    for rule in rules:
        value = None
        if rule.kind == "title":
            value = page.title()
        elif rule.selector and rule.attribute:
            node = page.query_selector(rule.selector)
            value = node.get_attribute(rule.attribute) if node else None
        if value:
            fields[rule.field] = value
        elif rule.required:
            missing_fields.append(rule.field)
    return DomExtractionResult(fields=fields, missing_fields=missing_fields)
