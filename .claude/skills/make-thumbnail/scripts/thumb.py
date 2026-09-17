"""Cream-card thumbnail: hook lines left, one scene still as a tilted outlined card right, 1280x720.

    python thumb.py <series>/<slug> --name B-who-wore-this --scene 109 --centre 0.64 \
        --line WHO --line WORE --line "[THIS?]" [--replace]

A line in [brackets] takes the accent colour. Colours and font come from series.md
(`thumbnail.*`). Writes thumbnails/<name>.jpg and thumbnails/<name>-sizes.jpg (the image at
1280, 360 and 168 px wide). An existing <name>.jpg is moved to thumbnails/_archive/ only with
--replace; otherwise the script stops.
"""
import argparse, random, re, shutil, sys, time
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[4]
W, H = 1280, 720
CARD_SCALE = [1.0]
CARD_W, CARD_AR, CARD_CX, CARD_CY, TILT, BORDER = 610, 1.23, 945, 360, -2.5, 10
# --card scales the tilted card about its own centre. The text block keeps its place,
# so a card much over 1.3 starts to crowd it; check the 168 px panel, not the big one.
TEXT_X, TEXT_W, TEXT_H, LEAD = 48, 540, 600, 10
MARK_SIZE, MARK_BOTTOM, TEXT_H_MARK = 52, H - 44, 520   # channel wordmark bottom-left; hook block stays above it
GRAIN, MOTTLE, CREASES, PAPER_SEED = 5, 9, (0.24, 0.47, 0.79), 1904   # aged-paper texture under the cream; fixed seed so a rebuild is identical


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


def _amp(layer, amp):
    """Rescale a grey layer so it spans 128 +/- amp, whatever the blur left of its range."""
    lo, hi = layer.getextrema()
    if hi == lo:
        return Image.new("L", layer.size, 128)
    return layer.point(lambda v: round(128 - amp + (v - lo) / (hi - lo) * 2 * amp))


def paper(bg):
    """The cream ground as aged paper: fine grain, soft mottling, a few vertical creases.

    Composited additively, not with ImageChops.overlay -- overlay scales a deviation by
    2*(255-base)/255, which on cream is ~4% and leaves the texture invisible.
    """
    rnd = random.Random(PAPER_SEED)
    noise = lambda w, h: Image.frombytes("L", (w, h), bytes(rnd.getrandbits(8) for _ in range(w * h)))
    tex = noise(W, H).point(lambda v: round(128 + (v - 128) * GRAIN / 128))
    mottle = _amp(noise(40, 23).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18)), MOTTLE)
    tex = ImageChops.add(tex, mottle, scale=1, offset=-128)
    creases = Image.new("L", (W, H), 128)
    d = ImageDraw.Draw(creases)
    for f in CREASES:
        x = round(f * W)
        d.line([(x - 3, 0), (x - 3, H)], fill=128 - 2 * MOTTLE, width=3)
        d.line([(x, 0), (x, H)], fill=128 + 2 * MOTTLE, width=2)
    tex = ImageChops.add(tex, creases.filter(ImageFilter.GaussianBlur(1.6)), scale=1, offset=-128)
    return ImageChops.add(Image.new("RGB", (W, H), bg), tex.convert("RGB"), scale=1, offset=-128)


def card(path, centre, ink, zoom=1.0, ymid=0.5):
    """zoom > 1 punches the crop in so one face fills the card; ymid places it vertically.

    A figure has to read at 168 px wide, where the whole card is only 80 px: a full-height
    scene crop leaves a head about 9 px tall, which is texture, not an expression.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw = min(w, round(h * CARD_AR / zoom))
    ch = min(h, round(cw / CARD_AR))
    x0 = min(max(0, round(centre * w - cw / 2)), w - cw)
    y0 = min(max(0, round(ymid * h - ch / 2)), h - ch)
    card_w = round(CARD_W * CARD_SCALE[0])
    c = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((card_w, round(card_w / CARD_AR)), Image.LANCZOS)
    framed = Image.new("RGBA", (c.width + 2 * BORDER, c.height + 2 * BORDER), ink + (255,))
    framed.paste(c, (BORDER, BORDER))
    return framed.rotate(TILT, resample=Image.BICUBIC, expand=True)


def text_block(canvas, lines, font, max_h=TEXT_H):
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
        if total <= max_h:
            break
        k -= 0.02
    y = (H - total) / 2
    for (t, col), b, f in zip(lines, boxes, fonts):
        d.text((TEXT_X - b[0], y - b[1]), t, font=f, fill=col)
        y += b[3] - b[1] + LEAD


def wordmark(canvas, font, ink, accent):
    """LIVED IT in the hook text's column, bottom-left, IT in the accent colour."""
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(font, MARK_SIZE)
    b = d.textbbox((0, 0), "LIVED IT", font=f)
    x, y = TEXT_X - b[0], MARK_BOTTOM - b[3]
    d.text((x, y), "LIVED", font=f, fill=ink)
    d.text((x + f.getlength("LIVED "), y), "IT", font=f, fill=accent)


ap = argparse.ArgumentParser()
ap.add_argument("project", help="<series>/<slug>")
ap.add_argument("--name", required=True)
src = ap.add_mutually_exclusive_group(required=True)
src.add_argument("--scene", help="scene id or its numeric prefix; canonical still only")
src.add_argument("--still", help="a named file in scene-generation/, e.g. an attempt whose flaw falls outside the crop")
ap.add_argument("--centre", type=float, default=0.5, help="horizontal centre of the card crop, 0-1")
ap.add_argument("--zoom", type=float, default=1.0, help="punch the crop in on the subject; 1 is the full-height scene")
ap.add_argument("--ymid", type=float, default=0.5, help="vertical centre of the card crop, 0-1; a head usually sits above 0.5")
ap.add_argument("--line", action="append", required=True)
ap.add_argument("--card", type=float, default=1.0, help="scale the tilted card, 1 is the standard layout")
ap.add_argument("--replace", action="store_true")
ap.add_argument("--mark", action="store_true", help="add the LIVED IT wordmark bottom-left")
a = ap.parse_args()
CARD_SCALE[0] = a.card

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
canvas = paper(bg)
c = card(matches[0], a.centre, ink, a.zoom, a.ymid)
# a bigger card grows both ways from its centre and would eat the text block,
# so it slides right as it grows, letting its outer edge bleed off the frame
cx = CARD_CX + round((CARD_SCALE[0] - 1.0) * 200)
pos = (cx - c.width // 2, CARD_CY - c.height // 2)
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
shadow.paste((0, 0, 0, 90), (pos[0] + 12, pos[1] + 16), c.split()[3])
shadow = shadow.filter(ImageFilter.GaussianBlur(14))
canvas.paste(shadow, (0, 0), shadow)
canvas.paste(c, pos, c)
text_block(canvas, lines, font, TEXT_H_MARK if a.mark else TEXT_H)
if a.mark:
    wordmark(canvas, font, ink, accent)
canvas.save(out, quality=95)

sheet = Image.new("RGB", (W + 360 + 168 + 80, H + 40), (15, 15, 15))
sheet.paste(canvas, (20, 20))
sheet.paste(canvas.resize((360, 202), Image.LANCZOS), (W + 40, 20))
sheet.paste(canvas.resize((168, 94), Image.LANCZOS), (W + 420, 20))
sheet.save(out_dir / f"{a.name}-sizes.jpg", quality=88)
print(out, "scene", matches[0].name)
