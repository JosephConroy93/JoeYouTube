"""Head-crop sheet of a video's figure references, for the Step 6 glance.

    python reference-heads.py <series>/<slug> [--out <file>] [--root <project root>]

Crops the upper-centre third of every `reference-images/*.jpg` that is not a
`Loc-`/`Obj-` file and tiles them at 400 px, so a nose, ear, neck or tinted
head shows at a glance before a reference is used. A reference that carries
any of them is re-rendered: every scene that attaches it inherits the fault.
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--out')
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
    a = ap.parse_args()
    series, slug = a.project.replace('\\', '/').split('/')
    rdir = os.path.join(a.root, 'content', series, slug, 'reference-images')
    files = [f for f in sorted(glob.glob(os.path.join(rdir, '*.jpg')))
             if not os.path.basename(f).startswith(('_', 'Loc-', 'Obj-'))]
    if not files:
        print('no figure references in', rdir)
        return 1
    try:
        font = ImageFont.truetype('arialbd.ttf', 20)
    except OSError:
        font = ImageFont.load_default()
    W = H = 400
    cols, pad = 5, 30
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W, rows * (H + pad)), 'white')
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(f).convert('RGB')
        w, h = im.size
        crop = im.crop((int(w * 0.33), int(h * 0.02), int(w * 0.67), int(h * 0.5))).resize((W, H))
        x, y = (i % cols) * W, (i // cols) * (H + pad)
        sheet.paste(crop, (x, y + pad))
        d.text((x + 6, y + 4), os.path.basename(f)[:-4][:32], fill='black', font=font)
    out = a.out or os.path.join(rdir, '_heads-sheet.jpg')
    sheet.save(out, quality=85)
    print(f'{len(files)} references -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
