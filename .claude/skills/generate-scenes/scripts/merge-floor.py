"""Merge sub-floor beat rows into a neighbour, renumber, rewrite index ranges.

    python merge-floor.py <series>/<slug> [--floor 11] [--ceiling 31] [--root <project root>]

Runs on chapters at status `beats` only (never a written chapter). A row
under --floor words joins the next row when the sum stays under --ceiling,
else the previous; text-card rows never merge. Bookmarks concatenate, beats
join with "; ", ids renumber continuously from the first beats chapter, and
the index ranges follow. The prompt pass reads every joined beat and picks
the image for the moment the line lands. Run after scene-prompter Mode 2
when check-manifest.py reports a floor band well over ~10%.
"""
import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')


def cells(line):
    t = line.strip()
    if not t.startswith('|'):
        return None
    t = t[1:]
    if t.endswith('|'):
        t = t[:-1]
    return [c.strip() for c in t.split('|')]


def words(t):
    return len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", t))


def slug(bm):
    w = re.findall(r"[a-z0-9]+", bm.lower().replace('’', "'").replace("'", ''))
    return '-'.join(w[:6])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--floor', type=int, default=11)
    ap.add_argument('--ceiling', type=int, default=31)
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug_ = a.project.replace('\\', '/').split('/')
    cdir = os.path.join(a.root, 'content', series, slug_, 'claude')
    index = os.path.join(cdir, 'scene-prompts.md')
    chapters = []
    for line in open(index, encoding='utf-8-sig'):
        c = cells(line)
        if c and len(c) >= 4 and re.search(r'[\w.-]+\.md', c[1]):
            chapters.append({'file': re.search(r'([\w.-]+\.md)', c[1]).group(1), 'range': c[2], 'status': c[3]})
    beats = [ch for ch in chapters if ch['status'] == 'beats']
    if not beats:
        print('no chapters at beats; nothing to do')
        return 0
    # numbering continues after the last written chapter
    nxt = 1
    for ch in chapters:
        if ch['status'] == 'written':
            nums = re.findall(r'\d{3}', ch['range'])
            if nums:
                nxt = max(nxt, int(nums[-1]) + 1)
    merged_total = 0
    ranges = {}
    for ch in beats:
        p = os.path.join(cdir, 'scene-prompts', ch['file'])
        lines = open(p, encoding='utf-8').read().split('\n')
        rows = [l.split('|') for l in lines if re.match(r'\| \d{3}_', l)]
        changed = True
        while changed:
            changed = False
            for i, c in enumerate(rows):
                if words(c[2]) >= a.floor or c[3].strip() == 'text-card':
                    continue
                cand = []
                if i + 1 < len(rows) and rows[i + 1][3].strip() != 'text-card':
                    cand.append(('next', i + 1))
                if i - 1 >= 0 and rows[i - 1][3].strip() != 'text-card':
                    cand.append(('prev', i - 1))
                for kind, j in cand:
                    if words(c[2]) + words(rows[j][2]) <= a.ceiling:
                        first, second = (c, rows[j]) if kind == 'next' else (rows[j], c)
                        new = list(first)
                        new[2] = ' ' + first[2].strip() + ' ' + second[2].strip() + ' '
                        new[7] = ' ' + first[7].strip().rstrip('.') + '; ' + second[7].strip() + ' '
                        rows[min(i, j)] = new
                        del rows[max(i, j)]
                        merged_total += 1
                        changed = True
                        break
                if changed:
                    break
        start = nxt
        for c in rows:
            c[1] = f' {nxt:03d}_{slug(c[2])} '
            nxt += 1
        ranges[ch['file']] = (start, nxt - 1, len(rows))
        out = []
        for l in lines:
            if re.match(r'\| \d{3}_', l):
                continue
            out.append(l)
            if l.startswith('|---'):
                out.extend('|'.join(c) for c in rows)
        open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(out).rstrip('\n') + '\n')
    s = open(index, encoding='utf-8-sig').read()
    for f, (b, e, n) in ranges.items():
        rng = f'{b:03d}–{e:03d}'
        s = re.sub(rf'(\| [^|]+\| {re.escape(f)} \| )[^|]+(\| beats \|)', lambda m: m.group(1) + rng + ' ' + m.group(2), s)
    open(index, 'w', encoding='utf-8', newline='\n').write(s)
    print(f'merged {merged_total} rows; ' + ', '.join(f'{f} {b:03d}-{e:03d} ({n})' for f, (b, e, n) in ranges.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
