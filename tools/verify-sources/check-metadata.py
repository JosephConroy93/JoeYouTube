#!/usr/bin/env python3
"""Check that each live Archive.org / Gutenberg link is the work the table claims.

Run after verify-links.py, in the same directory (it reads link-report.csv):

    python check-metadata.py [dir]

For every Archive.org identifier it fetches https://archive.org/metadata/<id>; for
every Gutenberg number it fetches the ebook page title. The claimed title's words are
compared with the repository's: MATCH (>= 50% of words present), WEAK (>= 25%) or
MISMATCH. WEAK and MISMATCH need a human read — accents, CJK titles, truncated
repository titles and volume numbering all score low while being correct. Writes
metadata-report.csv. Stdlib only.
"""

import csv, json, re, html, os, sys, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; JoeYouTube-source-check/1.0)"
STOP = set("the of and a an in to on by with from for at or its his her their vol vols volume".split())


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def ia_id(url):
    m = re.search(r"archive\.org/(?:details|stream|download)/([^/?#]+)", url)
    return m.group(1) if m else None


def gb_id(url):
    m = re.search(r"gutenberg\.org/(?:ebooks/|cache/epub/|files/)(\d+)", url)
    return m.group(1) if m else None


def words(s):
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split() if len(w) > 2 and w not in STOP}


def score(claimed, actual):
    c = words(claimed)
    return len(c & words(actual)) / len(c) if c else 0.0


def verdict(s):
    return "MATCH" if s >= 0.5 else ("WEAK" if s >= 0.25 else "MISMATCH")


def check(row):
    url, claimed = row["url"], row["title"]
    iid, gid = ia_id(url), gb_id(url)
    try:
        if iid:
            md = json.loads(fetch(f"https://archive.org/metadata/{iid}")).get("metadata") or {}
            if not md:
                return [row["topic"], claimed, "IA", iid, "", "", "", "0.00", "NO-METADATA"]
            j = lambda v: "; ".join(v) if isinstance(v, list) else (v or "")
            t, cr, yr = j(md.get("title")), j(md.get("creator")), j(md.get("date") or md.get("year"))
            s = score(claimed, t)
            return [row["topic"], claimed, "IA", iid, t, cr, yr, f"{s:.2f}", verdict(s)]
        if gid:
            m = re.search(r"<title>(.*?)</title>", fetch(f"https://www.gutenberg.org/ebooks/{gid}"), re.S)
            t = re.sub(r"\s*\|\s*Project Gutenberg.*$", "", html.unescape(m.group(1)).strip()) if m else ""
            s = score(claimed, t)
            return [row["topic"], claimed, "GB", gid, t, "", "", f"{s:.2f}", verdict(s)]
        return [row["topic"], claimed, "OTHER", url, "", "", "", "", "NOT-CHECKED"]
    except Exception as e:  # noqa: BLE001 - report rather than crash
        repo = "IA" if iid else ("GB" if gid else "OTHER")
        return [row["topic"], claimed, repo, iid or gid or url, "", "", "", "0.00",
                f"ERROR {type(e).__name__}: {str(e)[:60]}"]


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(d, "link-report.csv")
    if not os.path.exists(src):
        sys.exit(f"{src} not found: run verify-links.py first")
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8")) if r["verdict"] == "OK"]
    print(f"checking {len(rows)} live URLs against repository metadata...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=6) as pool:
        out = list(pool.map(check, rows))
    dst = os.path.join(d, "metadata-report.csv")
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["topic", "claimed_title", "repo", "id", "actual_title", "actual_creator",
                    "actual_date", "score", "verdict"])
        w.writerows(out)
    print("verdicts:", dict(Counter(r[8].split(" ")[0] for r in out)), file=sys.stderr)
    for r in out:
        if r[8] != "MATCH":
            print(f"  {r[8]:<12} {r[0]} | {r[1][:50]} | {r[2]} {r[3][:36]} | {r[4][:60]}", file=sys.stderr)
    print(f"wrote {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
