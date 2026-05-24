# Web Agent — WordPress Site Auditor

A CLI + MCP tool that audits WordPress websites and outputs structured JSON. Built for local agencies to identify maintenance leads and demonstrate value to business owners.

No browser required — all checks run over HTTP using raw HTML and response headers.

---

## What It Checks

| Check | What it detects |
|---|---|
| **WordPress detection** | Wappalyzer fingerprint + HTML signals (`/wp-content/`, generator meta) |
| **SSL / HTTPS** | HTTPS present, HTTP→HTTPS redirect, cert validity, days until expiry |
| **Plugin versions** | Installed version vs latest on WordPress.org. Always probes Yoast SEO, Elementor, WooCommerce, Contact Form 7, Wordfence, UpdraftPlus |
| **Theme version** | Installed version vs latest on WordPress.org. Detects child themes |
| **Meta tags** | Title (length), meta description (length), canonical (conflicts), `noindex` on live site |
| **Open Graph** | `og:title`, `og:description`, `og:image` — flags missing tags |
| **Schema markup** | Extracts all `application/ld+json` blocks, detects duplicate types, invalid JSON |
| **robots.txt** | `Disallow: /` (blocks all crawlers), missing sitemap declaration, blocked WP paths |
| **Maintenance signals** | WordPress core version, last modified date, last blog post date, server info leak (`X-Powered-By`) |

### Severity levels

- **critical** — immediate damage: no HTTPS, `noindex` on live site, cert expired, `Disallow: /`
- **warning** — needs fixing: outdated plugins/theme/WP core, missing meta description, no OG image
- **info** — minor: tag length issues

---

## Installation

**Requirements:** Python 3.11+

```bash
git clone https://github.com/detolah/web-agent ~/Web-agent
cd ~/Web-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## CLI Usage

```bash
# Audit a single URL — prints JSON to stdout
.venv/bin/python audit.py https://example.com

# Write to a file
.venv/bin/python audit.py https://example.com --output report.json

# Batch mode — one URL per line in a text file
.venv/bin/python audit.py --batch urls.txt

# Batch with one output file per site
.venv/bin/python audit.py --batch urls.txt --output-dir ./reports/
```

`urls.txt` format — one URL per line, `#` for comments:
```
https://clientone.com
https://clienttwo.com
# https://skip-this-one.com
```

---

## JSON Output

```json
{
  "url": "https://example.com",
  "audited_at": "2026-05-24T10:30:00Z",
  "is_wordpress": true,
  "wordpress_confidence": "high",
  "ssl": {
    "https": true,
    "redirect_from_http": true,
    "cert_valid": true,
    "days_until_expiry": 42,
    "issues": []
  },
  "plugins": [
    {
      "slug": "wordpress-seo",
      "name": "Yoast SEO",
      "installed_version": "21.0",
      "latest_version": "27.6",
      "outdated": true
    }
  ],
  "theme": {
    "slug": "astra",
    "installed_version": "4.0.0",
    "latest_version": "4.6.2",
    "outdated": true,
    "is_child_theme": false
  },
  "meta": {
    "title": { "value": "Home", "length": 4, "issues": ["title_too_short"] },
    "description": { "value": null, "issues": ["description_missing"] },
    "canonical": { "value": "https://example.com/", "conflict": false, "issues": [] },
    "robots_meta": { "noindex": false, "issues": [] },
    "og": { "title": "...", "description": "...", "image": null, "issues": ["og_image_missing"] }
  },
  "schema": {
    "blocks_found": 2,
    "types": ["WebSite", "LocalBusiness"],
    "issues": ["duplicate_WebSite"]
  },
  "robots_txt": {
    "found": true,
    "blocks_all": false,
    "blocked_paths": ["/wp-admin/"],
    "sitemap_declared": true,
    "issues": []
  },
  "maintenance": {
    "wp_version": "5.1.4",
    "wp_outdated": true,
    "last_modified_days_ago": 1158,
    "sitemap_found": true,
    "last_post_days_ago": 4069,
    "server_info_exposed": true
  },
  "summary": {
    "total_issues": 10,
    "critical": 2,
    "warnings": 7,
    "info": 1
  }
}
```

---

## MCP Integration (Claude Code)

The MCP server exposes `audit_site(url)` as a native tool in Claude Code. Once configured, you can say **"audit https://example.com"** and Claude calls the tool, reads the JSON, and gives a full recommendation — no CLI needed.

### Setup

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "wp-auditor": {
      "command": "/Users/YOURUSERNAME/Web-agent/.venv/bin/python",
      "args": ["/Users/YOURUSERNAME/Web-agent/mcp_server.py"]
    }
  }
}
```

Replace `YOURUSERNAME` with your macOS username:
```bash
echo $USER
```

Restart Claude Code. The `audit_site` tool will be available in all sessions.

### Example prompts

- *"Audit https://appledentalmilton.ca and tell me if they'd be a good maintenance lead"*
- *"Audit these 3 dental clinics and rank them by how badly they need help: [urls]"*
- *"Write a cold outreach email for this site based on the audit: https://example.com"*

---

## Project Structure

```
web-agent/
├── audit.py              # CLI entry point
├── mcp_server.py         # MCP server — exposes audit_site() tool
├── fetcher.py            # HTTP fetch (single request per site)
├── reporter.py           # Assembles results + severity tagging
├── requirements.txt
├── CLAUDE.md             # Instructions for Claude Code
└── checks/
    ├── ssl.py            # HTTPS, redirect, cert expiry
    ├── wordpress.py      # WP detection
    ├── plugins.py        # Plugin versions vs WordPress.org API
    ├── themes.py         # Theme version vs WordPress.org API
    ├── meta.py           # Title, description, OG, canonical, noindex
    ├── schema.py         # application/ld+json blocks
    ├── robots.py         # robots.txt parsing
    └── maintenance.py    # WP version, last modified, server info
```

---

## Example: Real Audit Result

Auditing `appledentalmilton.ca` found **2 critical + 7 warnings**:

| Severity | Issue |
|---|---|
| 🔴 Critical | `noindex` on live site — invisible to Google |
| 🔴 Critical | No HTTPS — browser shows "Not Secure" |
| 🟡 Warning | Yoast SEO: version `12.4` installed, latest `27.6` |
| 🟡 Warning | WordPress core: `5.1.4` (2019) — 7 major versions behind |
| 🟡 Warning | Last site update: 1,158 days ago (~3 years) |
| 🟡 Warning | Last blog post: 4,069 days ago (~11 years) |
| 🟡 Warning | No meta description |
| 🟡 Warning | No canonical tag |
| 🟡 Warning | No OG image |

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP fetching |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `python-wappalyzer` | Technology fingerprinting |
| `packaging` | Version comparison |
| `mcp` | MCP server (Claude Code integration) |
