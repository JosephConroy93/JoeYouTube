"""Cream-card thumbnail: hook lines left, one scene still as a tilted outlined card right, 1280x720.

    python thumb.py <series>/<slug> --name B-who-wore-this --scene 109 --centre 0.64 \
        --line WHO --line WORE --line "[THIS?]" [--replace]

A line in [brackets] takes the accent colour. Colours and font come from series.md
(`thumbnail.*`). Writes thumbnails/<name>.jpg and thumbnails/<name>-sizes.jpg (the image at
1280, 360 and 168 px wide). An existing <name>.jpg is moved to thumbnails/_archive/ only with
--replace; otherwise the script stops.
"""
import argparse, re, shutil, sys, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[4]
W, H = 1280, 720
CARD_W, CARD_AR, CARD_CX, CARD_CY, TILT, BORDER = 610, 1.23, 945, 360, -2.5, 10
TEXT_X, TEXT_W, TEXT_H, LEAD = 48, 540, 600, 10


def series_keys(series):
    keys = {}
    for line in (ROOT / "content" / series / "series.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            code = re.search(r"`([^`]+)`", m.group(2))
            keys[m.group(1)] = code.group(1) if code else m.group(2)
    need = ["thumbnail.background", "thumbnail.ink", "thumbnail.accent", "thumbnail.font"]
    missing = [k for k in need if k not in keys]
    if missing:
        sys.exit(f"series.md is missing {', '.join(missing)}")
    rgb = lambda v: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return rgb(keys[need[0]]), rgb(keys[need[1]]), rgb(keys[need[2]]), keys[need[3]]


def card(path, centre, ink):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw = min(w, round(h * CARD_AR))
    x0 = min(max(0, round(centre * w - cw / 2)), w - cw)
    c = im.crop((x0, 0, x0 + cw, h)).resize((CARD_W, round(CARD_W / CARD_AR)), Image.LANCZOS)
    framed = Image.new("RGBA", (c.width + 2 * BORDER, c.height + 2 * BORDER), ink + (255,))
    framed.paste(c, (BORDER, BORDER))
    return framed.rotate(TILT, resample=Image.BICUBIC, expand=True)


def text_block(canvas, lines, font):
    """Each line sized to fill the column, then all scaled together to fit the height."""
    d = ImageDraw.Draw(canvas)

    def fit(t):
        size = 320
        while size > 40 and d.textbbox((0, 0), t, font=ImageFont.truetype(font, size))[2] > TEXT_W:
            size -= 2
        return size

    sizes, k = [fit(t) for t, _ in lines], 1.0
    while True:
        fonts = [ImageFont.truetype(font, max(20, round(s * k))) for s in sizes]
        boxes = [d.textbbox((0, 0), t, font=f) for (t, _), f in zip(lines, fonts)]
        total = sum(b[3] - b[1] for b in boxes) + LEAD * (len(lines) - 1)
        if total <= TEXT_H:
            break
        k -= 0.02
    y = (H - total) / 2
    for (t, col), b, f in zip(lines, boxes, fonts):
        d.text((TEXT_X - b[0], y - b[1]), t, font=f, fill=col)
        y += b[3] - b[1] + LEAD


ap = argparse.ArgumentParser()
ap.add_argument("project", help="<series>/<slug>")
ap.add_argument("--name", required=True)
src = ap.add_mutually_exclusive_group(required=True)
src.add_argument("--scene", help="scene id or its numeric prefix; canonical still only")
src.add_argument("--still", help="a named file in scene-generation/, e.g. an attempt whose flaw falls outside the crop")
ap.add_argument("--centre", type=float, default=0.5, help="horizontal centre of the card crop, 0-1")
ap.add_argument("--line", action="append", required=True)
ap.add_argument("--replace", action="store_true")
a = ap.parse_args()

series, slug = a.project.split("/")
bg, ink, accent, font = series_keys(series)
video = ROOT / "content" / series / slug
if a.still:
    matches = [video / "scene-generation" / a.still]
    if not matches[0].is_file():
        sys.exit(f"{matches[0]} not found")
else:
    # canonical stills only: <scene_id>.jpg, never <scene_id>.attempt-N.jpg or other dotted leftovers
    matches = sorted(p for p in (video / "scene-generation").glob(f"{a.scene}*.jpg") if "." not in p.stem)
    if len(matches) != 1:
        sys.exit(f"scene {a.scene!r} matched {len(matches)} canonical images in scene-generation/")
out_dir = video / "thumbnails"
out = out_dir / f"{a.name}.jpg"
if out.exists():
    if not a.replace:
        sys.exit(f"{out} exists; pass --replace to archive it and write a new one")
    (out_dir / "_archive").mkdir(parents=True, exist_ok=True)
    shutil.move(out, out_dir / "_archive" / f"{a.name}-{time.strftime('%Y%m%d-%H%M%S')}.jpg")
out_dir.mkdir(parents=True, exist_ok=True)

lines = [(t[1:-1], accent) if t.startswith("[") and t.endswith("]") else (t, ink) for t in a.line]
canvas = Image.new("RGB", (W, H), bg)
c = card(matches[0], a.centre, ink)
pos = (CARD_CX - c.width // 2, CARD_CY - c.height // 2)
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
shadow.paste((0, 0, 0, 90), (pos[0] + 12, pos[1] + 16), c.split()[3])
shadow = shadow.filter(ImageFilter.GaussianBlur(14))
canvas.paste(shadow, (0, 0), shadow)
canvas.paste(c, pos, c)
text_block(canvas, lines, font)
canvas.save(out, quality=95)

sheet = Image.new("RGB", (W + 360 + 168 + 80, H + 40), (15, 15, 15))
sheet.paste(canvas, (20, 20))
sheet.paste(canvas.resize((360, 202), Image.LANCZOS), (W + 40, 20))
sheet.paste(canvas.resize((168, 94), Image.LANCZOS), (W + 420, 20))
sheet.save(out_dir / f"{a.name}-sizes.jpg", quality=88)
print(out, "scene", matches[0].name)
