#!/usr/bin/env python3
"""Verify every URL in the source-candidate tables actually resolves.

The candidate rows were gathered in a sandbox with no outbound network, so no link
in them has ever been fetched. Run this from a machine with real internet access
before promoting any row into content/SOURCES.md.

    python verify-links.py [dir]            # default: this script's directory
    python verify-links.py [dir] --workers 8 --timeout 30

Writes link-report.md and link-report.csv next to the tables. Stdlib only.
"""

import argparse
import csv
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; JoeYouTube-source-check/1.0)"
URL_RE = re.compile(r"https?://[^\s)|;,]+")
ACCESS_TOKENS = ("FULL-DOWNLOAD", "BORROW-ONLY", "LINK-ONLY", "UNKNOWN")


def rows_from(path):
    """Yield (line_no, title, access, url) for each URL in each table row."""
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.startswith("|") or line.startswith("|-") or "| Title " in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            title = cells[1] if len(cells) > 1 else "?"
            access = next(
                (c for c in cells for t in ACCESS_TOKENS if c.startswith(t)), ""
            )
            access = access.split("(")[0].strip()
            for url in URL_RE.findall(line):
                yield n, title, access, url.rstrip(".,;")


def check(url, timeout):
    """Return (status, final_url, content_type, size). HEAD, falling back to GET."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                size = resp.headers.get("Content-Length", "") or ""
                ctype = (resp.headers.get("Content-Type", "") or "").split(";")[0]
                return str(resp.status), resp.url, ctype, size
        except urllib.error.HTTPError as e:
            # Some hosts reject HEAD but serve GET; only retry for that class.
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return f"HTTP {e.code}", url, "", ""
        except urllib.error.URLError as e:
            return f"ERROR {e.reason}", url, "", ""
        except Exception as e:  # noqa: BLE001 - report anything else rather than crash
            return f"ERROR {type(e).__name__}: {e}", url, "", ""
    return "ERROR unreachable", url, "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    tables = sorted(
        os.path.join(args.dir, f)
        for f in os.listdir(args.dir)
        if f.endswith(".md") and not f.startswith(("README", "link-report"))
    )
    if not tables:
        sys.exit(f"no candidate tables found in {args.dir}")

    jobs = []
    for path in tables:
        topic = os.path.basename(path)[:-3]
        for n, title, access, url in rows_from(path):
            jobs.append([topic, n, title, access, url])

    print(f"checking {len(jobs)} URLs from {len(tables)} tables...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda j: check(j[4], args.timeout), jobs))

    ok = 0
    rows = []
    for job, (status, final, ctype, size) in zip(jobs, results):
        good = status.isdigit() and status.startswith("2")
        ok += good
        rows.append(job + [status, "OK" if good else "CHECK", final, ctype, size])
        print(f"  {status:<12} {job[4][:90]}", file=sys.stderr)

    csv_path = os.path.join(args.dir, "link-report.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["topic", "line", "title", "access", "url",
             "status", "verdict", "final_url", "content_type", "size"]
        )
        w.writerows(rows)

    md_path = os.path.join(args.dir, "link-report.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# Link verification report\n\n")
        fh.write(f"{ok} of {len(rows)} URLs returned 2xx.\n\n")
        fh.write("Only promote rows marked OK into `content/SOURCES.md`.\n\n")
        fh.write("| Topic | Title | Access | Status | Verdict | Type | URL |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            topic, _, title, access, url, status, verdict, _, ctype, _ = r
            title = title.replace("|", "\\|")[:70]
            fh.write(
                f"| {topic} | {title} | {access} | {status} | {verdict} | {ctype} | {url} |\n"
            )

    print(f"\n{ok}/{len(rows)} OK. Wrote {md_path} and {csv_path}", file=sys.stderr)
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
