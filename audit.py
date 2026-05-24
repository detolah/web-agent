#!/usr/bin/env python3
import argparse
import json
import sys
import os

from fetcher import fetch
from reporter import assemble
from checks import ssl, wordpress, plugins, themes, meta, schema, robots, maintenance


def audit_url(url: str, verbose: bool = False) -> dict:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if verbose:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"[audit] Starting: {url}", file=sys.stderr)

    fetched = fetch(url, verbose=verbose)

    if verbose:
        print(f"[audit] bot_protected={fetched['bot_protected']} error={fetched['error']}", file=sys.stderr)
        print(f"[audit] HTML available: {len(fetched['html'])} chars", file=sys.stderr)

    if fetched.get("error") and not fetched.get("html"):
        result = {
            "url": url,
            "error": fetched["error"],
            "bot_protected": fetched.get("bot_protected", False),
            "is_wordpress": False,
            "note": "Audit skipped — site blocked HTTP access. Use a browser to audit manually." if fetched.get("bot_protected") else None,
            "summary": {"total_issues": 0, "critical": 0, "warnings": 0, "info": 0},
        }
        if verbose:
            print(f"[audit] ⚠️  Skipping all checks — no HTML to analyse", file=sys.stderr)
        return result

    if verbose:
        print(f"[audit] Running: wordpress detection...", file=sys.stderr)
    wp = wordpress.check(fetched)
    if verbose:
        print(f"[audit]   → is_wordpress={wp['is_wordpress']} confidence={wp.get('confidence')} signals={wp.get('signals')}", file=sys.stderr)

    if verbose:
        print(f"[audit] Running: SSL check...", file=sys.stderr)
    ssl_result = ssl.check(url)
    if verbose:
        print(f"[audit]   → https={ssl_result['https']} cert_valid={ssl_result['cert_valid']} days={ssl_result['days_until_expiry']} issues={ssl_result['issues']}", file=sys.stderr)

    if verbose:
        print(f"[audit] Running: meta tags...", file=sys.stderr)
    meta_result = meta.check(fetched)
    if verbose:
        print(f"[audit]   → title issues={meta_result['title']['issues']}", file=sys.stderr)
        print(f"[audit]   → desc issues={meta_result['description']['issues']}", file=sys.stderr)
        print(f"[audit]   → robots noindex={meta_result['robots_meta']['noindex']}", file=sys.stderr)
        print(f"[audit]   → og issues={meta_result['og']['issues']}", file=sys.stderr)

    if verbose:
        print(f"[audit] Running: schema...", file=sys.stderr)
    schema_result = schema.check(fetched)
    if verbose:
        print(f"[audit]   → blocks={schema_result['blocks_found']} types={schema_result['types']} issues={schema_result['issues']}", file=sys.stderr)

    if verbose:
        print(f"[audit] Running: robots.txt...", file=sys.stderr)
    robots_result = robots.check(fetched)
    if verbose:
        print(f"[audit]   → found={robots_result['found']} blocks_all={robots_result['blocks_all']} sitemap={robots_result['sitemap_declared']} issues={robots_result['issues']}", file=sys.stderr)

    if verbose:
        print(f"[audit] Running: maintenance signals...", file=sys.stderr)
    maintenance_result = maintenance.check(fetched)
    if verbose:
        print(f"[audit]   → wp_version={maintenance_result['wp_version']} outdated={maintenance_result['wp_outdated']}", file=sys.stderr)
        print(f"[audit]   → last_modified={maintenance_result['last_modified_days_ago']} days ago", file=sys.stderr)

    if wp["is_wordpress"]:
        if verbose:
            print(f"[audit] Running: plugin scan...", file=sys.stderr)
        plugins_result = plugins.check(fetched)
        if verbose:
            print(f"[audit]   → {len(plugins_result)} plugins found", file=sys.stderr)
            for p in plugins_result:
                print(f"[audit]     {p['slug']} installed={p['installed_version']} latest={p['latest_version']} outdated={p['outdated']}", file=sys.stderr)

        if verbose:
            print(f"[audit] Running: theme scan...", file=sys.stderr)
        theme_result = themes.check(fetched)
        if verbose:
            print(f"[audit]   → theme={theme_result}", file=sys.stderr)
    else:
        if verbose:
            print(f"[audit] Skipping plugins + theme (WordPress not detected)", file=sys.stderr)
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

    parser.add_argument("--output", metavar="FILE", help="Write JSON to file")
    parser.add_argument("--output-dir", metavar="DIR", help="Write one JSON file per URL (batch mode)")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON (default: on)")
    parser.add_argument("--verbose", action="store_true", help="Log each audit step to stderr")

    args = parser.parse_args()
    indent = 2 if args.pretty else None

    if args.url:
        result = audit_url(args.url, verbose=args.verbose)
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
            result = audit_url(url, verbose=args.verbose)
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
