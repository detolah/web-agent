# WP Site Auditor

## What this project does

CLI + MCP tool that audits WordPress (and any) websites. Checks SSL, plugin/theme versions, meta tags, schema, robots.txt, and maintenance signals. Returns structured JSON.

## MCP Setup (one-time)

Add to your `~/.claude/settings.json` under `mcpServers`:

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

Replace `YOURUSERNAME` with your macOS username (`echo $USER` to check).

After saving, restart Claude Code. The `audit_site` tool will be available.

## How to use

Just say: **"audit https://example.com"** or **"run a site audit on example.com"**.

Claude will call `audit_site(url)`, receive the JSON, and give you a full breakdown.

## What Claude should do with results

When you receive audit JSON:

1. **Lead scoring** — flag sites with `critical >= 1` as hot leads
2. **Key pitch points** — pull the most impactful issues (noindex, no SSL, outdated WP core, ancient plugins)
3. **Action list** — translate issues into plain-English fixes a client can understand
4. **Maintenance package framing** — map issues to recurring value: "we keep your plugins updated so you don't get hacked", "we monitor your SSL so your site never goes down"

## Severity guide

| Level | Meaning | Examples |
|---|---|---|
| `critical` | Immediate damage — losing traffic or insecure | `noindex`, no HTTPS, expired cert |
| `warning` | Needs fixing — affecting SEO or UX | Outdated plugins, missing meta description |
| `info` | Nice to fix | Minor tag length issues |

## CLI usage (alternative to MCP)

```bash
cd ~/Web-agent
.venv/bin/python audit.py https://example.com
.venv/bin/python audit.py --batch urls.txt --output-dir ./reports/
```
