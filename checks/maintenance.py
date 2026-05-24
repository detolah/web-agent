import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse
import re

from fetcher import session_get

TIMEOUT = 8
WP_VERSION_API = "https://api.wordpress.org/core/version-check/1.7/"


def _days_ago(dt: datetime) -> int | None:
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def _parse_http_date(s: str) -> datetime | None:
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _latest_wp_version() -> str | None:
    try:
        resp = requests.get(WP_VERSION_API, timeout=TIMEOUT)
        data = resp.json()
        offers = data.get("offers", [])
        if offers:
            return offers[0].get("version")
    except Exception:
        pass
    return None


def check(fetch_result: dict) -> dict:
    html = fetch_result.get("html", "")
    headers = fetch_result.get("headers", {})
    final_url = fetch_result.get("final_url", "")
    parsed = urlparse(final_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "wp_version": None,
        "wp_outdated": None,
        "last_modified_days_ago": None,
        "sitemap_found": False,
        "last_post_days_ago": None,
        "server_info_exposed": False,
    }

    soup = BeautifulSoup(html, "lxml")
    gen = soup.find("meta", attrs={"name": "generator"})
    if gen:
        content = gen.get("content") or ""
        m = re.search(r"WordPress\s+([\d.]+)", content)
        if m:
            result["wp_version"] = m.group(1)
            latest = _latest_wp_version()
            if latest and result["wp_version"]:
                from packaging.version import Version, InvalidVersion
                try:
                    result["wp_outdated"] = Version(result["wp_version"]) < Version(latest)
                except InvalidVersion:
                    result["wp_outdated"] = None

    lm = headers.get("Last-Modified") or headers.get("last-modified")
    if lm:
        dt = _parse_http_date(lm)
        result["last_modified_days_ago"] = _days_ago(dt)

    if headers.get("X-Powered-By") or headers.get("x-powered-by"):
        result["server_info_exposed"] = True

    resp = session_get(f"{base}/sitemap.xml", fetch_result)
    if resp and resp.status_code == 200:
        result["sitemap_found"] = True
        sm_soup = BeautifulSoup(resp.text, "lxml-xml")
        lastmods = sm_soup.find_all("lastmod")
        if lastmods:
            dates = []
            for tag in lastmods:
                try:
                    dates.append(datetime.fromisoformat(tag.text.strip().replace("Z", "+00:00")))
                except ValueError:
                    pass
            if dates:
                result["last_modified_days_ago"] = _days_ago(max(dates))

    resp = session_get(f"{base}/feed/", fetch_result)
    if resp and resp.status_code == 200:
        feed_soup = BeautifulSoup(resp.text, "lxml-xml")
        pub_dates = feed_soup.find_all("pubDate")
        if pub_dates:
            dt = _parse_http_date(pub_dates[0].text.strip())
            result["last_post_days_ago"] = _days_ago(dt)

    return result
