import re
from bs4 import BeautifulSoup

try:
    from Wappalyzer import Wappalyzer, WebPage
    _WAPPALYZER = True
except Exception:
    _WAPPALYZER = False


def check(fetch_result: dict) -> dict:
    html = fetch_result.get("html", "")
    headers = fetch_result.get("headers", {})
    final_url = fetch_result.get("final_url", "")

    signals = []

    if _WAPPALYZER:
        try:
            wapp = Wappalyzer.latest()
            page = WebPage(final_url, html, headers)
            techs = wapp.analyze(page)
            if any("WordPress" in str(t) for t in techs):
                signals.append("wappalyzer")
        except Exception:
            pass

    if "/wp-content/" in html:
        signals.append("wp_content")
    if "/wp-includes/" in html:
        signals.append("wp_includes")
    if "/wp-json/" in html or "/wp-json/" in final_url:
        signals.append("wp_json")

    soup = BeautifulSoup(html, "lxml")
    gen = soup.find("meta", attrs={"name": "generator"})
    if gen and "WordPress" in (gen.get("content") or ""):
        signals.append("generator_meta")

    is_wp = len(signals) > 0
    if len(signals) >= 2 or (len(signals) == 1 and "wappalyzer" in signals):
        confidence = "high"
    elif len(signals) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "is_wordpress": is_wp,
        "confidence": confidence if is_wp else None,
        "signals": signals,
    }
