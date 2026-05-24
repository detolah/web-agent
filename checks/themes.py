import re
import requests
from packaging.version import Version, InvalidVersion

TIMEOUT = 8
WP_THEMES_API = "https://api.wordpress.org/themes/info/1.1/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 WordPress-Auditor/1.0"
}


def _get_installed_version(base_url: str, slug: str) -> tuple[str | None, bool]:
    """Returns (version, is_child_theme)."""
    try:
        url = f"{base_url.rstrip('/')}/wp-content/themes/{slug}/style.css"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            version = None
            is_child = False
            for line in resp.text.splitlines()[:30]:
                if line.lower().startswith("version:"):
                    version = line.split(":", 1)[1].strip()
                if line.lower().startswith("template:"):
                    is_child = True
            return version, is_child
    except Exception:
        pass
    return None, False


def _get_latest_version(slug: str) -> str | None:
    try:
        resp = requests.get(
            WP_THEMES_API,
            params={"action": "theme_information", "slug": slug},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("version")
    except Exception:
        pass
    return None


def _is_outdated(installed: str, latest: str) -> bool:
    try:
        return Version(installed) < Version(latest)
    except InvalidVersion:
        return installed != latest


def check(fetch_result: dict) -> dict | None:
    html = fetch_result.get("html", "")
    base_url = fetch_result.get("final_url", "").rstrip("/")

    slugs = re.findall(r"/wp-content/themes/([^/\"']+)/", html)
    if not slugs:
        return None

    slug = slugs[0]
    installed, is_child = _get_installed_version(base_url, slug)
    latest = _get_latest_version(slug)

    result = {
        "slug": slug,
        "installed_version": installed,
        "latest_version": latest,
        "outdated": False,
        "is_child_theme": is_child,
    }

    if installed and latest:
        result["outdated"] = _is_outdated(installed, latest)
    elif installed and not latest:
        result["outdated"] = None  # custom/private theme

    return result
