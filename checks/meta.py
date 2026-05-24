from bs4 import BeautifulSoup
from urllib.parse import urlparse


def _tag_issues(value, min_len, max_len, field_name):
    issues = []
    if not value:
        issues.append(f"{field_name}_missing")
    elif len(value) < min_len:
        issues.append(f"{field_name}_too_short")
    elif len(value) > max_len:
        issues.append(f"{field_name}_too_long")
    return issues


def check(fetch_result: dict) -> dict:
    html = fetch_result.get("html", "")
    final_url = fetch_result.get("final_url", "")
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_tag = soup.find("title")
    title_val = title_tag.get_text(strip=True) if title_tag else None
    title_issues = _tag_issues(title_val, 30, 60, "title")

    # Meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc_val = desc_tag.get("content", "").strip() if desc_tag else None
    desc_issues = _tag_issues(desc_val, 120, 160, "description")

    # Canonical
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical_val = canonical_tag.get("href", "").strip() if canonical_tag else None
    canonical_conflict = False
    canonical_issues = []
    if not canonical_val:
        canonical_issues.append("canonical_missing")
    else:
        # Conflict: canonical points to a different domain
        try:
            c_host = urlparse(canonical_val).netloc
            f_host = urlparse(final_url).netloc
            if c_host and f_host and c_host != f_host:
                canonical_conflict = True
                canonical_issues.append("canonical_conflict")
        except Exception:
            pass

    # Robots meta
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots_content = (robots_tag.get("content") or "").lower() if robots_tag else ""
    noindex = "noindex" in robots_content
    robots_issues = ["noindex_on_live_site"] if noindex else []

    # OG tags
    def og(prop):
        tag = soup.find("meta", attrs={"property": f"og:{prop}"})
        return tag.get("content", "").strip() if tag else None

    og_title = og("title")
    og_desc = og("description")
    og_image = og("image")
    og_issues = []
    if not og_title:
        og_issues.append("og_title_missing")
    if not og_desc:
        og_issues.append("og_description_missing")
    if not og_image:
        og_issues.append("og_image_missing")

    return {
        "title": {"value": title_val, "length": len(title_val) if title_val else 0, "issues": title_issues},
        "description": {"value": desc_val, "length": len(desc_val) if desc_val else 0, "issues": desc_issues},
        "canonical": {"value": canonical_val, "conflict": canonical_conflict, "issues": canonical_issues},
        "robots_meta": {"content": robots_content or None, "noindex": noindex, "issues": robots_issues},
        "og": {"title": og_title, "description": og_desc, "image": og_image, "issues": og_issues},
    }
