"""Contact sheet of one level's scene images, for the operator's per-level look.

    python contact-sheet.py <series>/<slug> --chapter level-03.md [--latest] [--out <file>] [--root <project root>]

Tiles every scene id in the chapter file at 480 px wide, labelled with the
three-digit id, in manifest order. `--latest` shows each scene's highest
`.attempt-N` when there is one (a resubmit or rewrite), else the bare file;
a scene with no image yet is drawn as a grey box so gaps show. Writes
`scene-generation/_sheets/<chapter>.jpg` unless `--out` is given.
"""
import argparse
import glob
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')


def pick(sg, sid, latest):
    attempts = sorted(glob.glob(os.path.join(sg, sid + '.attempt-*.jpg')),
                      key=lambda p: int(re.search(r'attempt-(\d+)', p).group(1)))
    bare = os.path.join(sg, sid + '.jpg')
    if latest and attempts:
        return attempts[-1]
    return bare if os.path.exists(bare) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--chapter', required=True)
    ap.add_argument('--latest', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug = a.project.replace('\\', '/').split('/')
    vdir = os.path.join(a.root, 'content', series, slug)
    sg = os.path.join(vdir, 'scene-generation')
    chap = os.path.join(vdir, 'claude', 'scene-prompts', a.chapter)
    ids = [m.group(1) for m in (re.match(r'^\|\s*`?(\d{3}_[A-Za-z0-9-]+)`?\s*\|', l)
                                for l in open(chap, encoding='utf-8')) if m]
    if not ids:
        print('no scene rows in', chap)
        return 1
    try:
        font = ImageFont.truetype('arialbd.ttf', 22)
    except OSError:
        font = ImageFont.load_default()
    W, H, pad = 480, 270, 30
    cols = 5
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W, rows * (H + pad)), 'white')
    d = ImageDraw.Draw(sheet)
    missing = []
    for i, sid in enumerate(ids):
        x, y = (i % cols) * W, (i // cols) * (H + pad)
        f = pick(sg, sid, a.latest)
        if f:
            sheet.paste(Image.open(f).convert('RGB').resize((W - 4, H)), (x + 2, y + pad))
            label = sid[:3] + ('' if f.endswith(sid + '.jpg') else ' ' + re.search(r'attempt-\d+', f).group(0))
        else:
            d.rectangle((x + 2, y + pad, x + W - 2, y + pad + H), fill='#bbbbbb')
            label = sid[:3] + ' missing'
            missing.append(sid[:3])
        d.text((x + 6, y + 4), label, fill='black', font=font)
    out = a.out or os.path.join(sg, '_sheets', a.chapter.replace('.md', '.jpg'))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out, quality=85)
    print(f'{len(ids)} scenes -> {out}' + (f"; missing: {' '.join(missing)}" if missing else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
