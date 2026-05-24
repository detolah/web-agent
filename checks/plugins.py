import re
import requests
from packaging.version import Version, InvalidVersion

from fetcher import session_get

TIMEOUT = 8
WP_API = "https://api.wordpress.org/plugins/info/1.2/"

PRIORITY_SLUGS = [
    "wordpress-seo",
    "elementor",
    "woocommerce",
    "contact-form-7",
    "wordfence",
    "updraftplus",
]


def _get_installed_version(base_url: str, slug: str, fetch_result: dict) -> str | None:
    url = f"{base_url.rstrip('/')}/wp-content/plugins/{slug}/readme.txt"
    resp = session_get(url, fetch_result)
    if resp and resp.status_code == 200:
        for line in resp.text.splitlines():
            if line.lower().startswith("stable tag:"):
                return line.split(":", 1)[1].strip()
    return None


def _get_latest_version(slug: str) -> tuple[str | None, str | None]:
    try:
        resp = requests.get(WP_API, params={"action": "plugin_information", "slug": slug}, timeout=TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("version"), data.get("name")
    except Exception:
        pass
    return None, None


def _is_outdated(installed: str, latest: str) -> bool:
    try:
        return Version(installed) < Version(latest)
    except InvalidVersion:
        return installed != latest


def check(fetch_result: dict) -> list:
    html = fetch_result.get("html", "")
    base_url = fetch_result.get("final_url", "").rstrip("/")

    found_slugs = set(re.findall(r"/wp-content/plugins/([^/\"']+)/", html))
    all_slugs = found_slugs | set(PRIORITY_SLUGS)

    results = []
    for slug in all_slugs:
        installed = _get_installed_version(base_url, slug, fetch_result)
        latest, name = _get_latest_version(slug)

        if installed is None and latest is None:
            continue

        entry = {
            "slug": slug,
            "name": name or slug,
            "installed_version": installed,
            "latest_version": latest,
            "outdated": False,
        }

        if installed and latest:
            entry["outdated"] = _is_outdated(installed, latest)
        elif installed and not latest:
            entry["outdated"] = None
        elif not installed:
            continue

        results.append(entry)

    return results
