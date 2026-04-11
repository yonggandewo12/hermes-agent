from __future__ import annotations

import json


def main() -> int:
    print(json.dumps({"status": "not_implemented"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
