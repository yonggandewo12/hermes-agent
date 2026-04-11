from pathlib import Path


def test_playwright_page_capture_skill_scaffold_exists():
    root = Path("optional-skills/communication/playwright-page-capture")
    assert (root / "SKILL.md").exists()
    assert (root / "scripts" / "run_page_capture.py").exists()
