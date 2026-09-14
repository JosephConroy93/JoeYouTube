"""Mechanical checks on a video's scene-prompt manifest, run after every
scene-prompter Mode 2/3 pass and before generate-scenes submits.

    python check-manifest.py <series>/<slug> [--chapter level-03.md ...] [--root <project root>]

Checks the rules that are counting, matching or lookup, so the prompt writer
never does them by hand: row format and numbering against the index, the
per-file row cap, bookmarks verbatim and in order in the script (and any
narration no bookmark covers), the 11 s ceiling and the floor/ceiling band
shares from series.md's wpm_measured, style cells, reference cells (numbering,
files on disk, the 5-reference cap, every attachment bound in the prompt),
[[block]] tokens against cast.md, block text typed out in full, text-card
overlay notes, mascot leakage and the hook plan. A chapter at `beats` is
checked for bookmarks and bands only.

FAIL lines block submission (exit 1); WARN lines are for the driving session
or the operator to judge. Layouts and schemas: .claude/conventions.md.
"""
import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ORD = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8}
CEILING_S, FLOOR_S = 11.0, 4.0         # hard ceiling; floor
BAND_LOW_S, BAND_HIGH_S = 5.0, 8.0     # average range; outside it counts toward the band shares
# every band is compared in whole words, rounded from seconds at wpm_measured, as the agent's table is
BAND_SHARE = 0.10
MAX_ROWS, MAX_REFS, MAX_HOOK = 25, 5, 8

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def cells(line):
    t = line.strip()
    if not t.startswith('|'):
        return None
    t = t[1:]
    if t.endswith('|'):
        t = t[:-1]
    return [c.strip() for c in t.split('|')]


def table_value(path, key):
    for line in open(path, encoding='utf-8-sig'):
        c = cells(line)
        if c and len(c) >= 2 and c[0].strip('`') == key:
            return c[1]
    return None


def norm(text):
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    text = re.sub(r'[*_]{1,2}', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def words(text):
    return len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--chapter', action='append', default=[])
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()

    series, slug = a.project.replace('\\', '/').split('/')
    sdir = os.path.join(a.root, 'content', series)
    vdir = os.path.join(sdir, slug)
    cdir = os.path.join(vdir, 'claude')
    index = os.path.join(cdir, 'scene-prompts.md')
    if not os.path.exists(index):
        print(f'FAIL  no manifest index: {index}')
        return 1

    wpm = float(re.search(r'\d+(?:\.\d+)?', table_value(os.path.join(sdir, 'series.md'), 'wpm_measured')).group())
    style = re.sub(r'\(.*?\)', '', (table_value(os.path.join(vdir, 'video.md'), 'style') or '')).strip(' `*')
    style_bible = open(os.path.join(a.root, 'content', 'styles', 'style-bible.md'), encoding='utf-8').read()
    if not re.search(rf'^## {re.escape(style)}\b', style_bible, re.M):
        fail(f'video.md style "{style}" has no "## {style}" entry in the style bible')
    hook = (table_value(os.path.join(vdir, 'video.md'), 'hook') or '').strip()
    mascot = (table_value(os.path.join(sdir, 'series.md'), 'mascot.bible') or '')

    # blocks
    blocks = {}
    bpath = os.path.join(cdir, 'cast.md')
    if not os.path.exists(bpath):
        bpath = os.path.join(cdir, 'prompt-blocks.md')
    if os.path.exists(bpath):
        for line in open(bpath, encoding='utf-8-sig'):
            c = cells(line)
            if c and len(c) >= 2 and re.fullmatch(r'`?[A-Za-z_][\w.-]*`?', c[0]) and c[0].strip('`') != 'block':
                blocks[c[0].strip('`')] = c[1]

    # index
    chapters = []
    for line in open(index, encoding='utf-8-sig'):
        c = cells(line)
        if c and len(c) >= 4 and re.search(r'[\w.-]+\.md', c[1]):
            chapters.append({'title': c[0], 'file': re.search(r'([\w.-]+\.md)', c[1]).group(1), 'range': c[2], 'status': c[3]})
    written = [ch for ch in chapters if ch['status'] in ('written', 'beats')]
    if not written:
        print('FAIL  no written or beats chapters in the index')
        return 1

    script = open(os.path.join(cdir, 'script.md'), encoding='utf-8').read()
    refdir = os.path.join(vdir, 'reference-images')
    scenedir = os.path.join(vdir, 'scene-generation')

    wc = lambda sec: round(sec * wpm / 60)
    ceil_w, floor_w, low_w, high_w = wc(CEILING_S), wc(FLOOR_S), wc(BAND_LOW_S), wc(BAND_HIGH_S)
    selected = set(a.chapter) or {ch['file'] for ch in written}
    expected = 1
    all_rows = {}
    stats = []
    for ch in written:
        path = os.path.join(cdir, 'scene-prompts', ch['file'])
        if not os.path.exists(path):
            fail(f"{ch['file']}: listed as written but missing on disk")
            continue
        rows = []
        for n, line in enumerate(open(path, encoding='utf-8-sig'), 1):
            c = cells(line)
            if not c or not re.match(r'`?\d{3}_', c[0]):
                continue
            if len(c) != 7:
                fail(f"{ch['file']}:{n} has {len(c)} cells, expected 7 (a stray | in a cell?)")
                continue
            rows.append(dict(zip(['id', 'bookmark', 'type', 'prompt', 'style', 'refs', 'notes'], c), line=n))
        ids = [r['id'].strip('`') for r in rows]
        for i, sid in enumerate(ids):
            if not re.fullmatch(r'\d{3}_[a-z0-9-]+', sid):
                fail(f'{sid}: scene_id is not NNN_<kebab-slug>')
            if int(sid[:3]) != expected:
                fail(f'{sid}: numbering jumps (expected {expected:03d})')
            expected = int(sid[:3]) + 1
            if sid in all_rows:
                fail(f'{sid}: duplicate scene_id')
            all_rows[sid] = rows[i]
        if len(rows) > MAX_ROWS:
            fail(f"{ch['file']}: {len(rows)} rows (cap {MAX_ROWS}; split into a/b parts)")
        rng = re.findall(r'\d{3}', ch['range'])
        if ids and rng != [ids[0][:3], ids[-1][:3]] and not (len(ids) == 1 and rng == [ids[0][:3]]):
            fail(f"{ch['file']}: index range '{ch['range']}' does not match rows {ids[0][:3]}-{ids[-1][:3]}")
        if ch['file'] not in selected:
            continue

        # script span for this chapter
        title = norm(ch['title']).rstrip('.')
        m = re.search(rf'^##\s+{re.escape(title)}\.?\s*$', script, re.M)
        span = ''
        if not m:
            fail(f"{ch['file']}: no script heading matching '{ch['title']}'")
        else:
            nxt = re.search(r'^##\s', script[m.end():], re.M)
            span = norm(ch['title'] + ' ' + script[m.end(): m.end() + nxt.start() if nxt else len(script)])
        cursor = 0
        counts = []
        typed = {}
        empty = 0
        for r in rows:
            sid, bm = r['id'].strip('`'), norm(r['bookmark'])
            prompt = r['prompt']
            w = words(bm)
            s = w * 60 / wpm
            counts.append(w)
            if w > ceil_w:
                fail(f'{sid}: {w} words ≈ {s:.1f} s, over the {CEILING_S:.0f} s ceiling ({ceil_w} words); split it')
            elif w < floor_w:
                warn(f'{sid}: {w} words ≈ {s:.1f} s, under the {FLOOR_S:.0f} s floor ({floor_w} words)')
            if w > high_w and not re.search(r'ceiling|hold', r['notes'], re.I):
                warn(f'{sid}: ceiling-band row ({w} words ≈ {s:.1f} s) with no justification in notes')
            if span:
                pos = span.find(bm, cursor)
                if pos < 0:
                    fail(f'{sid}: script_bookmark not found verbatim (in order) in the script: "{bm[:60]}"')
                else:
                    gap = span[cursor:pos].strip(' .,;:!?"\'-')
                    if words(gap):
                        warn(f'{sid}: narration before this row is covered by no bookmark: "{gap[:80]}"')
                    cursor = pos + len(bm)
            # content
            if not prompt.strip():
                empty += 1
                if ch['status'] == 'written':
                    fail(f'{sid}: content_prompt is empty in a written chapter')
                continue
            if r['style'].strip('`') != style:
                fail(f"{sid}: style cell '{r['style']}' is not the resolved style '{style}'")
            if re.search(r'\bSTYLE:|\bNEGATIVE:', prompt):
                fail(f'{sid}: content_prompt carries STYLE/NEGATIVE text')
            if re.search(r'\{(?!ref\})[^}]*\}', prompt):
                fail(f'{sid}: unexpanded {{...}} placeholder in content_prompt')
            if mascot and re.search(r'\bWatcher\b|MASCOT-', prompt + r['refs']):
                fail(f'{sid}: mascot named in content_prompt or references')
            tokens = re.findall(r'\[\[([A-Za-z_][\w.-]*)\]\]', prompt)
            for t in tokens:
                if t not in blocks:
                    fail(f'{sid}: [[{t}]] is not defined in prompt-blocks.md')
            for bid, btext in blocks.items():
                if bid.startswith('_'):
                    continue
                paren = re.search(r'\((.{60,}?)\)\s*$', btext)
                if paren and paren.group(1)[:80] in prompt:
                    typed[bid] = typed.get(bid, 0) + 1
            refs = re.findall(r'image(\d+)\s*=\s*([^;]+)', r['refs'])
            nums = [int(n) for n, _ in refs]
            if nums != list(range(1, len(nums) + 1)):
                fail(f"{sid}: reference cell numbering not image1..imageN: '{r['refs']}'")
            if len(refs) > MAX_REFS:
                fail(f'{sid}: {len(refs)} references (cap {MAX_REFS}); recompose')
            elif len(refs) == MAX_REFS:
                warn(f'{sid}: {len(refs)} references, at the cap')
            if r['type'] == 'text-card' and refs:
                warn(f'{sid}: text-card carries references')
            if r['type'] not in ('illustrated', 'text-card'):
                fail(f"{sid}: scene_type '{r['type']}'")
            mentioned = {ORD[o] for o in re.findall(r'\b(\w+) attached reference image', prompt) if o in ORD}
            if re.search(r'\b(?:the )?attached reference image\b', prompt) and len(refs) == 1:
                mentioned.add(1)
            for n, entry in refs:
                n = int(n)
                ident = re.search(r'\(([^)]+)\)', entry)
                ident = ident.group(1).strip() if ident else ''
                stem = entry.split('(')[0].strip()
                bound = n in mentioned or any(t.split('.')[0] == ident for t in tokens)
                if not bound:
                    fail(f'{sid}: image{n} ({stem}) is attached but never bound in the prompt')
                gen = re.search(r'(?:generated scene\s+)?\b(\d{3})\b', entry) if re.match(r'\d{3}_|.*generated scene', entry) else None
                if gen:
                    if not any(f.startswith(gen.group(1) + '_') for f in os.listdir(scenedir)) if os.path.isdir(scenedir) else True:
                        fail(f'{sid}: image{n} generated scene {gen.group(1)} has no file in scene-generation/')
                elif not any(os.path.exists(os.path.join(refdir, stem + e)) for e in ('.jpg', '.jpeg', '.png')) and '/' not in stem:
                    fail(f'{sid}: image{n} reference file {stem}.jpg not found in reference-images/')
            for o in mentioned:
                if o > len(refs):
                    fail(f'{sid}: prompt names the attached reference #{o} but only {len(refs)} are attached')
            if r['type'] == 'text-card':
                if not re.search(r'overlay:\s*"[^"]+"', r['notes']):
                    warn(f'{sid}: text-card without an overlay: "<word>" note')
                if re.search(r'\b(reading|lettering|inscribed)\b', prompt, re.I) and re.search(r'"[^"]+"', prompt):
                    fail(f'{sid}: text-card asks the image model for text; generate the carrier blank')
        if empty and ch['status'] == 'beats':
            print(f"  {ch['file']}: beats, {empty} rows awaiting prompts")
        if typed:
            warn(f"{ch['file']}: block text typed out instead of [[ID]]: " + ', '.join(f'{b} in {n} rows' for b, n in typed.items()))
        if span:
            tail = span[cursor:].strip(' .,;:!?"\'-')
            if words(tail):
                warn(f"{ch['file']}: narration after the last row is covered by no bookmark: \"{tail[:80]}\"")
        stats.append((ch['file'], counts))

    mascot_rows = [sid for sid, r in all_rows.items() if re.search(r'mascot cameo', r['notes'], re.I)]
    if len(mascot_rows) > 1:
        fail(f'mascot cameo flagged on {len(mascot_rows)} rows: {mascot_rows}')

    if hook and hook.lower() not in ('none', 'no', '-') and chapters and chapters[0]['status'] == 'written':
        hp = os.path.join(cdir, 'hook-plan.md')
        if not os.path.exists(hp):
            fail('video.md sets hook but claude/hook-plan.md is missing')
        else:
            shots = [c for c in (cells(l) for l in open(hp, encoding='utf-8-sig')) if c and len(c) >= 5 and re.fullmatch(r'\d+', c[0])]
            if len(shots) > MAX_HOOK:
                fail(f'hook-plan.md has {len(shots)} shots (cap {MAX_HOOK})')
            for c in shots:
                sid = c[1].strip('`')
                if sid not in all_rows:
                    fail(f'hook shot {c[0]}: {sid} is not a manifest row')
                elif all_rows[sid]['type'] != 'illustrated':
                    fail(f'hook shot {c[0]}: {sid} is not illustrated')
                if c[3] not in ('4', '6', '8'):
                    fail(f'hook shot {c[0]}: duration_s {c[3]} is not 4, 6 or 8')

    print(f'check-manifest {a.project}  wpm={wpm:g}  style={style}  blocks={len(blocks)}  '
          f'words: floor {floor_w}, average {low_w}-{high_w}, ceiling {ceil_w}')
    everything = [w for _, ws in stats for w in ws]
    for f, ws in stats + ([('all selected', everything)] if len(stats) > 1 else []):
        if not ws:
            continue
        low = sum(w < low_w for w in ws) / len(ws)
        high = sum(w > high_w for w in ws) / len(ws)
        flag = '  <- review' if max(low, high) > BAND_SHARE + 0.03 else ''
        print(f'  {f}: {len(ws)} rows  avg {sum(ws) / len(ws):.1f} words ({sum(ws) / len(ws) * 60 / wpm:.1f} s)  '
              f'floor band {low:.0%}  ceiling band {high:.0%}{flag}')
    for m in fails:
        print('FAIL  ' + m)
    for m in warns:
        print('WARN  ' + m)
    print(f'{len(fails)} fail, {len(warns)} warn')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
