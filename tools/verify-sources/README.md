# verify-sources

Proves a batch of candidate source links before any row is promoted into
`content/SOURCES.md`. Point it at a folder of markdown tables whose rows carry a
URL and an access flag (`FULL-DOWNLOAD` / `BORROW-ONLY` / `LINK-ONLY` / `UNKNOWN`).

```bash
PYTHONUTF8=1 python tools/verify-sources/verify-links.py <dir>     # HEAD/GET every URL -> link-report.md/.csv
PYTHONUTF8=1 python tools/verify-sources/check-metadata.py <dir>   # live IA/Gutenberg rows vs repository metadata -> metadata-report.csv
```

A 2xx proves the page exists, not that it is the edition claimed; the metadata check
covers that for Archive.org and Gutenberg. Read every WEAK/MISMATCH by hand before
deciding — accents, CJK titles and truncated repository titles score low while being
right. Other hosts (ANU repository, ctext, Wikisource, museum viewers) are link-checked
only. A 403 usually means the host blocks scripts; open it in a browser.
