import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10


def fetch(url: str) -> dict:
    """Fetch URL, return html, headers, final_url, status_code. Never raises."""
    result = {
        "url": url,
        "html": "",
        "headers": {},
        "final_url": url,
        "status_code": None,
        "error": None,
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result["html"] = resp.text
        result["headers"] = dict(resp.headers)
        result["final_url"] = resp.url
        result["status_code"] = resp.status_code
    except requests.exceptions.SSLError as e:
        result["error"] = f"ssl_error: {e}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection_error: {e}"
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)
    return result
