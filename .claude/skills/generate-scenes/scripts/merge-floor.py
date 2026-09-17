"""Merge sub-floor beat rows into a neighbour, split over-ceiling rows, renumber, rewrite index ranges.

    python merge-floor.py <series>/<slug> [--floor N] [--ceiling N] [--root <project root>]

Runs on chapters at status `beats` only (never a written chapter). A row
under --floor words joins the next row when the sum stays under --ceiling,
else the previous; text-card and `hook:` rows never merge (a hook shot is
one physical moment, often a single short sentence). --floor and --ceiling
default to 4 s and 11 s in words at `wpm_measured` (video.md, else
series.md). Bookmarks concatenate, beats
join with "; ", ids renumber continuously from the first beats chapter, and
the index ranges follow. The prompt pass reads every joined beat and picks
the image for the moment the line lands. Run after scene-prompter Mode 2
when check-manifest.py reports a floor band well over ~10%, or any
ceiling FAIL: a row over --ceiling (hook rows excepted) splits at the
sentence boundary nearest its middle when both halves reach --floor; the
second half keeps the type and characters, and its beat is marked "(cont.)".
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
    ap.add_argument('--floor', type=int)
    ap.add_argument('--ceiling', type=int)
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug_ = a.project.replace('\\', '/').split('/')
    cdir = os.path.join(a.root, 'content', series, slug_, 'claude')
    wpm = None
    for cfg in (os.path.join(a.root, 'content', series, slug_, 'video.md'), os.path.join(a.root, 'content', series, 'series.md')):
        for line in open(cfg, encoding='utf-8-sig'):
            c = cells(line)
            if wpm is None and c and len(c) >= 2 and c[0].strip('`') == 'wpm_measured':
                wpm = float(re.search(r'\d+(?:\.\d+)?', c[1]).group())
    a.floor = a.floor or round(4 * wpm / 60)
    a.ceiling = a.ceiling or round(11 * wpm / 60)
    print(f'wpm {wpm:g}: floor {a.floor} words, ceiling {a.ceiling} words')
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
    merged_total = split_total = 0
    ranges = {}
    for ch in beats:
        p = os.path.join(cdir, 'scene-prompts', ch['file'])
        lines = open(p, encoding='utf-8').read().split('\n')
        rows = [l.split('|') for l in lines if re.match(r'\| \d{3}_', l)]
        changed = True
        while changed:
            changed = False
            for i, c in enumerate(rows):
                fixed = lambda r: r[3].strip() == 'text-card' or 'hook:' in r[7]
                if words(c[2]) >= a.floor or fixed(c):
                    continue
                cand = []
                if i + 1 < len(rows) and not fixed(rows[i + 1]):
                    cand.append(('next', i + 1))
                if i - 1 >= 0 and not fixed(rows[i - 1]):
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
        i = 0
        while i < len(rows):
            c = rows[i]
            if words(c[2]) > a.ceiling and 'hook:' not in c[7]:
                sents = re.findall(r'[^.!?]+[.!?]+["”’)]*\s*', c[2].strip()) or [c[2].strip()]
                best = None
                for k in range(1, len(sents)):
                    left, right = ''.join(sents[:k]).strip(), ''.join(sents[k:]).strip()
                    if words(left) >= a.floor and words(right) >= a.floor:
                        score = abs(words(left) - words(right))
                        if best is None or score < best[0]:
                            best = (score, left, right)
                if best:
                    one, two = list(c), list(c)
                    one[2], two[2] = f' {best[1]} ', f' {best[2]} '
                    two[7] = ' ' + c[7].strip().rstrip('.') + ' (cont.) '
                    rows[i:i + 1] = [one, two]
                    split_total += 1
                    continue
            i += 1
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
    print(f'merged {merged_total} rows, split {split_total}; ' + ', '.join(f'{f} {b:03d}-{e:03d} ({n})' for f, (b, e, n) in ranges.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
