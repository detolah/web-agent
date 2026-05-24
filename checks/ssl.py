import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse
import requests

TIMEOUT = 10


def check(url: str) -> dict:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    result = {
        "https": parsed.scheme == "https",
        "redirect_from_http": False,
        "cert_valid": None,
        "days_until_expiry": None,
        "issues": [],
    }

    # Check HTTP → HTTPS redirect
    try:
        http_url = f"http://{domain}"
        resp = requests.head(http_url, timeout=TIMEOUT, allow_redirects=True)
        result["redirect_from_http"] = resp.url.startswith("https://")
    except Exception:
        pass

    if not result["https"]:
        result["issues"].append("no_https")
        return result

    if not result["redirect_from_http"]:
        result["issues"].append("no_http_redirect")

    # Check cert validity + expiry
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.create_connection((domain, 443), timeout=TIMEOUT), server_hostname=domain) as sock:
            cert = sock.getpeercert()
            expiry_str = cert.get("notAfter", "")
            if expiry_str:
                expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                days = (expiry - datetime.utcnow()).days
                result["cert_valid"] = days > 0
                result["days_until_expiry"] = days
                if days <= 0:
                    result["issues"].append("cert_expired")
                elif days <= 14:
                    result["issues"].append("cert_expiring_soon")
    except ssl.SSLCertVerificationError:
        result["cert_valid"] = False
        result["issues"].append("cert_invalid")
    except Exception:
        result["cert_valid"] = None

    return result
