#!/usr/bin/env python3
import argparse
import json
import sys
import os

from fetcher import fetch
from reporter import assemble
from checks import ssl, wordpress, plugins, themes, meta, schema, robots, maintenance


def audit_url(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    fetched = fetch(url)

    if fetched.get("error") and not fetched.get("html"):
        return {
            "url": url,
            "error": fetched["error"],
            "is_wordpress": False,
            "summary": {"total_issues": 0, "critical": 0, "warnings": 0, "info": 0},
        }

    wp = wordpress.check(fetched)
    ssl_result = ssl.check(url)
    meta_result = meta.check(fetched)
    schema_result = schema.check(fetched)
    robots_result = robots.check(fetched)
    maintenance_result = maintenance.check(fetched)

    if wp["is_wordpress"]:
        plugins_result = plugins.check(fetched)
        theme_result = themes.check(fetched)
    else:
        plugins_result = []
        theme_result = None

    return assemble(
        url=fetched["final_url"],
        wp=wp,
        ssl=ssl_result,
        plugins=plugins_result,
        theme=theme_result,
        meta=meta_result,
        schema=schema_result,
        robots=robots_result,
        maintenance=maintenance_result,
    )


def main():
    parser = argparse.ArgumentParser(
        description="WordPress site auditor — outputs JSON audit report"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("url", nargs="?", help="URL to audit")
    group.add_argument("--batch", metavar="FILE", help="File with one URL per line")

    parser.add_argument("--output", metavar="FILE", help="Write JSON to this file")
    parser.add_argument("--output-dir", metavar="DIR", help="Write one JSON file per URL (batch mode)")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON (default: on)")

    args = parser.parse_args()
    indent = 2 if args.pretty else None

    if args.url:
        result = audit_url(args.url)
        output = json.dumps(result, indent=indent)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(output)

    elif args.batch:
        with open(args.batch) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        results = []
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Auditing {url} ...", file=sys.stderr)
            result = audit_url(url)
            results.append(result)

            if args.output_dir:
                os.makedirs(args.output_dir, exist_ok=True)
                from urllib.parse import urlparse
                slug = urlparse(url).netloc.replace(".", "_")
                path = os.path.join(args.output_dir, f"{slug}.json")
                with open(path, "w") as f:
                    f.write(json.dumps(result, indent=indent))
                print(f"  → {path}", file=sys.stderr)

        if not args.output_dir:
            output = json.dumps(results, indent=indent)
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"Report written to {args.output}", file=sys.stderr)
            else:
                print(output)


if __name__ == "__main__":
    main()
