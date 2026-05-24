import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10
BROWSER_TIMEOUT = 35000  # ms
BROWSER_SETTLE = 3000    # ms extra wait after networkidle

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


def session_get(url: str, fetch_result: dict, **kwargs) -> requests.Response | None:
    """requests.get that injects browser session cookies when available. Never raises."""
    cookies = fetch_result.get("session_cookies") or {}
    try:
        return requests.get(
            url,
            headers=HEADERS,
            cookies=cookies,
            timeout=TIMEOUT,
            allow_redirects=True,
            **kwargs,
        )
    except Exception:
        return None


def _fetch_with_browser(url: str, verbose: bool) -> dict:
    """Launch headless Chromium, pass JS challenge, return rendered HTML + session cookies."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    result = {
        "url": url,
        "html": "",
        "headers": {},
        "final_url": url,
        "status_code": None,
        "error": None,
        "bot_protected": True,
        "fetched_via": "browser",
        "session_cookies": {},
    }

    if verbose:
        print(f"[fetch] 🌐 Launching headless Chromium for {url}", flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()

            final_response_holder = {}

            def on_response(response):
                if response.request.resource_type == "document":
                    final_response_holder["response"] = response

            page.on("response", on_response)

            try:
                page.goto(url, wait_until="networkidle", timeout=BROWSER_TIMEOUT)
            except PWTimeout:
                if verbose:
                    print(f"[fetch]   networkidle timeout — capturing partial page", flush=True)

            page.wait_for_timeout(BROWSER_SETTLE)

            # If still on challenge, wait longer
            if any(p in page.title().lower() for p in _CHALLENGE_TITLES):
                if verbose:
                    print(f"[fetch]   Challenge still active, waiting 8s more...", flush=True)
                page.wait_for_timeout(8000)

            result["html"] = page.content()
            result["final_url"] = page.url

            # Extract cookies so all secondary requests (robots.txt, readme.txt, etc.) can reuse the session
            raw_cookies = context.cookies()
            result["session_cookies"] = {c["name"]: c["value"] for c in raw_cookies}

            resp = final_response_holder.get("response")
            if resp:
                result["status_code"] = resp.status
                try:
                    result["headers"] = dict(resp.all_headers())
                except Exception:
                    result["headers"] = {}

            final_title = page.title().lower()
            if not any(p in final_title for p in _CHALLENGE_TITLES):
                result["bot_protected"] = False
                if verbose:
                    print(
                        f"[fetch]   ✅ Challenge passed — {len(result['html'])} chars, "
                        f"{len(result['session_cookies'])} session cookies extracted",
                        flush=True,
                    )
            else:
                result["error"] = "browser_challenge_unsolved: challenge did not resolve after browser execution"
                result["html"] = ""
                if verbose:
                    print(f"[fetch]   ❌ Challenge not solved — title: '{page.title()}'", flush=True)

            browser.close()

    except Exception as e:
        result["error"] = f"browser_error: {e}"
        if verbose:
            print(f"[fetch]   ❌ Browser error: {e}", flush=True)

    return result


def fetch(url: str, verbose: bool = False) -> dict:
    """Fetch URL. Falls back to headless browser if a bot-challenge is detected. Never raises."""
    result = {
        "url": url,
        "html": "",
        "headers": {},
        "final_url": url,
        "status_code": None,
        "error": None,
        "bot_protected": False,
        "fetched_via": "http",
        "session_cookies": {},
    }

    if verbose:
        print(f"[fetch] GET {url}", flush=True)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result["html"] = resp.text
        result["headers"] = dict(resp.headers)
        result["final_url"] = resp.url
        result["status_code"] = resp.status_code

        if verbose:
            print(f"[fetch] status={resp.status_code} final_url={resp.url}", flush=True)
            print(f"[fetch] Server: {resp.headers.get('Server', 'n/a')}", flush=True)
            print(f"[fetch] HTML length: {len(resp.text)} chars", flush=True)

        if _is_challenge_page(resp.status_code, resp.text, dict(resp.headers)):
            if verbose:
                print(f"[fetch] ⚠️  Bot challenge detected — falling back to browser", flush=True)
            return _fetch_with_browser(url, verbose)

    except requests.exceptions.SSLError as e:
        result["error"] = f"ssl_error: {e}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection_error: {e}"
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)

    return result
