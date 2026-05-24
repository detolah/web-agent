import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10

# Patterns that indicate a bot-challenge interstitial, not the real page
_CHALLENGE_TITLES = [
    "just a moment",
    "checking your browser",
    "please wait",
    "security check",
    "ddos protection",
    "attention required",
    "one moment, please",
]
_CHALLENGE_SERVERS = ["cloudflare", "hcdn", "sucuri"]


def _is_challenge_page(status_code: int, html: str, headers: dict) -> bool:
    if status_code in (403, 503):
        title_start = html.lower().find("<title>")
        title_end = html.lower().find("</title>")
        if title_start != -1 and title_end != -1:
            title = html[title_start:title_end].lower()
            if any(p in title for p in _CHALLENGE_TITLES):
                return True
    server = headers.get("Server", headers.get("server", "")).lower()
    if any(s in server for s in _CHALLENGE_SERVERS) and status_code in (403, 503):
        return True
    return False


def fetch(url: str, verbose: bool = False) -> dict:
    """Fetch URL, return html, headers, final_url, status_code. Never raises."""
    result = {
        "url": url,
        "html": "",
        "headers": {},
        "final_url": url,
        "status_code": None,
        "error": None,
        "bot_protected": False,
    }
    if verbose:
        print(f"[fetch] GET {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result["html"] = resp.text
        result["headers"] = dict(resp.headers)
        result["final_url"] = resp.url
        result["status_code"] = resp.status_code
        if verbose:
            print(f"[fetch] status={resp.status_code} final_url={resp.url}")
            print(f"[fetch] Server: {resp.headers.get('Server', 'n/a')}")
            print(f"[fetch] Content-Type: {resp.headers.get('Content-Type', 'n/a')}")
            print(f"[fetch] HTML length: {len(resp.text)} chars")
        if _is_challenge_page(resp.status_code, resp.text, dict(resp.headers)):
            result["bot_protected"] = True
            result["error"] = "bot_challenge: site requires JavaScript execution to access (Cloudflare/hcdn/similar). Manual audit required."
            result["html"] = ""  # discard challenge page HTML — don't audit it
            if verbose:
                print(f"[fetch] ⚠️  Bot challenge detected — discarding HTML")
    except requests.exceptions.SSLError as e:
        result["error"] = f"ssl_error: {e}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection_error: {e}"
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)
    return result
