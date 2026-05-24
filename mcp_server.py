#!/usr/bin/env python3
"""MCP server exposing audit_site as a Claude Code tool."""
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from audit import audit_url

server = Server("wp-auditor")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="audit_site",
            description=(
                "Audit a website (ideally WordPress) for: SSL status, "
                "plugin versions vs latest, theme version, meta tags, "
                "Open Graph tags, canonical, schema markup, robots.txt, "
                "and maintenance signals (WP version, last updated, server info leak). "
                "Returns structured JSON. Use to identify issues and recommend fixes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to audit, e.g. https://example.com",
                    }
                },
                "required": ["url"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "audit_site":
        raise ValueError(f"Unknown tool: {name}")

    url = arguments.get("url", "")
    if not url:
        raise ValueError("url is required")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, audit_url, url)

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
