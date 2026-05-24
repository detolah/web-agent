import requests
from urllib.parse import urlparse

TIMEOUT = 8
HEADERS = {"User-Agent": "Mozilla/5.0 WordPress-Auditor/1.0"}

SENSITIVE_PATHS = ["/wp-content/", "/wp-includes/"]


def check(fetch_result: dict) -> dict:
    final_url = fetch_result.get("final_url", "")
    parsed = urlparse(final_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "found": False,
        "blocks_all": False,
        "blocked_paths": [],
        "sitemap_declared": False,
        "issues": [],
    }

    try:
        resp = requests.get(f"{base}/robots.txt", headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            result["issues"].append("robots_txt_not_found")
            return result
        result["found"] = True
        text = resp.text
    except Exception:
        result["issues"].append("robots_txt_fetch_error")
        return result

    # Parse rules for User-agent: *
    in_global = False
    blocked = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            in_global = agent == "*"
        elif in_global and line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                blocked.append(path)
        elif line.lower().startswith("sitemap:"):
            result["sitemap_declared"] = True

    result["blocked_paths"] = blocked

    if "/" in blocked:
        result["blocks_all"] = True
        result["issues"].append("blocks_all_crawlers")

    for path in SENSITIVE_PATHS:
        if path in blocked:
            result["issues"].append(f"blocks_{path.strip('/')}")

    if not result["sitemap_declared"]:
        result["issues"].append("no_sitemap_in_robots")

    return result
