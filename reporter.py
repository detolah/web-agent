from datetime import datetime, timezone

CRITICAL_ISSUES = {
    "cert_expired", "cert_invalid", "no_https",
    "blocks_all_crawlers", "noindex_on_live_site",
}
WARNING_ISSUES = {
    "no_http_redirect", "cert_expiring_soon",
    "title_missing", "title_too_short", "title_too_long",
    "description_missing", "description_too_short", "description_too_long",
    "canonical_missing", "canonical_conflict",
    "og_title_missing", "og_description_missing", "og_image_missing",
    "no_sitemap_in_robots",
}


def _severity(issue: str) -> str:
    if issue in CRITICAL_ISSUES:
        return "critical"
    if issue in WARNING_ISSUES or issue.startswith("outdated") or issue.startswith("blocks_wp"):
        return "warning"
    return "info"


def _count_issues(issues: list) -> dict:
    counts = {"critical": 0, "warnings": 0, "info": 0, "total_issues": 0}
    for iss in issues:
        s = _severity(iss)
        if s == "critical":
            counts["critical"] += 1
        elif s == "warning":
            counts["warnings"] += 1
        else:
            counts["info"] += 1
        counts["total_issues"] += 1
    return counts


def _plugin_issues(plugins: list) -> list:
    return [f"outdated_plugin_{p['slug']}" for p in plugins if p.get("outdated")]


def _theme_issues(theme: dict | None) -> list:
    return ["outdated_theme"] if theme and theme.get("outdated") else []


def _maintenance_issues(m: dict) -> list:
    issues = []
    if m.get("wp_outdated"):
        issues.append("outdated_wordpress_core")
    if m.get("server_info_exposed"):
        issues.append("server_info_exposed")
    return issues


def assemble(
    url: str,
    wp: dict,
    ssl: dict,
    plugins: list,
    theme: dict | None,
    meta: dict,
    schema: dict,
    robots: dict,
    maintenance: dict,
) -> dict:
    all_issues = (
        ssl.get("issues", [])
        + meta["title"].get("issues", [])
        + meta["description"].get("issues", [])
        + meta["canonical"].get("issues", [])
        + meta["robots_meta"].get("issues", [])
        + meta["og"].get("issues", [])
        + schema.get("issues", [])
        + robots.get("issues", [])
        + _plugin_issues(plugins)
        + _theme_issues(theme)
        + _maintenance_issues(maintenance)
    )

    return {
        "url": url,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_wordpress": wp.get("is_wordpress", False),
        "wordpress_confidence": wp.get("confidence"),
        "ssl": ssl,
        "plugins": plugins,
        "theme": theme,
        "meta": meta,
        "schema": schema,
        "robots_txt": robots,
        "maintenance": maintenance,
        "summary": _count_issues(all_issues),
    }
