import json
from bs4 import BeautifulSoup
from collections import Counter


def check(fetch_result: dict) -> dict:
    html = fetch_result.get("html", "")
    soup = BeautifulSoup(html, "lxml")

    blocks = soup.find_all("script", attrs={"type": "application/ld+json"})
    issues = []
    types = []

    for i, block in enumerate(blocks):
        try:
            data = json.loads(block.string or "")
        except (json.JSONDecodeError, TypeError):
            issues.append(f"invalid_json_block_{i}")
            continue

        # Handle @graph arrays
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if "@context" not in item:
                issues.append("missing_at_context")
            t = item.get("@type")
            if isinstance(t, list):
                types.extend(t)
            elif t:
                types.append(t)

    # Duplicate type detection
    counts = Counter(types)
    for t, n in counts.items():
        if n > 1:
            issues.append(f"duplicate_{t}")

    return {
        "blocks_found": len(blocks),
        "types": list(dict.fromkeys(types)),  # deduplicated, order preserved
        "issues": issues,
    }
