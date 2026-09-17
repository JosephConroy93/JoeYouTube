"""Cream-card thumbnail: hook lines left, one scene still as a tilted outlined card right, 1280x720.

    python thumb.py <series>/<slug> --name B-who-wore-this --scene 109 --centre 0.64 \
        --line WHO --line WORE --line "[THIS?]" [--replace]

A line in [brackets] takes the accent colour. Colours and font come from series.md
(`thumbnail.*`). Writes thumbnails/<name>.jpg and thumbnails/<name>-sizes.jpg (the image at
1280, 360 and 168 px wide). An existing <name>.jpg is moved to thumbnails/_archive/ only with
--replace; otherwise the script stops.
"""
import argparse, math, os, random, re, shutil, sys, time
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[4]
W, H = 1280, 720
CARD_SCALE = [1.0]
CARD_AR_OVERRIDE = [None]
TILT_OVERRIDE = [None]
CARD_DX = [0]
DISTRESS = [1.0]
INK_WEAR = [0.0]
CARD_WEAR = [0.0]
CARD_SEED = 20719
INK_SEED = 4711
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
    tex = noise(W, H).point(lambda v: round(128 + (v - 128) * GRAIN * DISTRESS[0] / 128))
    mottle = _amp(noise(40, 23).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18)), round(MOTTLE * (1 + (DISTRESS[0] - 1) * 0.3)))
    tex = ImageChops.add(tex, mottle, scale=1, offset=-128)
    creases = Image.new("L", (W, H), 128)
    d = ImageDraw.Draw(creases)
    for f in CREASES:
        x = round(f * W)
        d.line([(x - 3, 0), (x - 3, H)], fill=128 - 2 * MOTTLE, width=3)
        d.line([(x, 0), (x, H)], fill=128 + 2 * MOTTLE, width=2)
    tex = ImageChops.add(tex, creases.filter(ImageFilter.GaussianBlur(1.6)), scale=1, offset=-128)
    out = ImageChops.add(Image.new("RGB", (W, H), bg), tex.convert("RGB"), scale=1, offset=-128)
    if DISTRESS[0] > 1.0:
        # worn edges: the ground darkens and roughens toward the border, the way a
        # handled print does. A flat cream rectangle is what reads as "made in a script".
        k = DISTRESS[0]
        wear = Image.new("L", (W, H), 0)
        dw = ImageDraw.Draw(wear)
        band = round(26 * k)
        for i in range(band):
            v = round(255 * (1 - i / band) ** 2.2)
            dw.rectangle([i, i, W - 1 - i, H - 1 - i], outline=v)
        for _ in range(round(140 * k)):        # nicks along the border only: a scuff in
            edge = rnd.randrange(4)             # the middle of the page reads as mould
            d_ = rnd.randrange(band)
            x = rnd.randrange(W) if edge < 2 else (d_ if edge == 2 else W - 1 - d_)
            y = (d_ if edge == 0 else H - 1 - d_) if edge < 2 else rnd.randrange(H)
            r = rnd.randrange(1, max(2, round(4 * k)))
            dw.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randrange(90, 220))
        wear = wear.filter(ImageFilter.GaussianBlur(1.4))
        shade = Image.new("RGB", (W, H), tuple(max(0, c - round(34 * k)) for c in bg))
        out = Image.composite(shade, out, wear)
    return out


def scratched(im, amount):
    """Hairline scratches and a few cracks over the photo, as a handled print carries.

    Light scratches are drawn brighter than the image and dark ones darker, both at low
    opacity: a scratch that is pure white reads as a drawn line, not damage.
    """
    rnd = random.Random(CARD_SEED)
    w, h = im.size
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(round(26 * amount)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        ln = rnd.randrange(round(w * 0.04), round(w * 0.42))
        ang = rnd.uniform(-0.5, 0.5) + rnd.choice([0, 3.14159])
        x2, y2 = x + ln * math.cos(ang), y + ln * math.sin(ang) * 0.35
        light = rnd.random() < 0.7
        col = (255, 252, 242, rnd.randrange(26, 78)) if light else (20, 14, 10, rnd.randrange(20, 54))
        d.line([(x, y), (x2, y2)], fill=col, width=1)
    for _ in range(round(5 * amount)):        # crack clusters: one origin, a few branches
        cx, cy = rnd.randrange(w), rnd.randrange(h)
        for _ in range(rnd.randrange(2, 5)):
            a = rnd.uniform(0, 6.283); ln = rnd.randrange(round(w * 0.02), round(w * 0.11))
            d.line([(cx, cy), (cx + ln * math.cos(a), cy + ln * math.sin(a))],
                   fill=(255, 250, 238, rnd.randrange(40, 96)), width=1)
    lay = lay.filter(ImageFilter.GaussianBlur(0.35))
    out = im.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


def torn(alpha, amount):
    """Rough the card edge the way handled paper wears.

    Punching circles out of the border reads as perforation - a postage stamp, not a
    torn print. Instead the alpha is eroded by coarse noise confined to a narrow band
    at the edge, so the boundary goes fibrous and uneven without losing its shape.
    """
    rnd = random.Random(CARD_SEED + 1)
    w, h = alpha.size
    band = max(2, round(6 * amount))
    ramp = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(ramp)
    for i in range(band):
        d.rectangle([i, i, w - 1 - i, h - 1 - i], outline=round(255 * (1 - i / band) ** 0.8))
    cw, ch = max(8, w // 5), max(8, h // 5)
    n = Image.frombytes("L", (cw, ch), bytes(rnd.getrandbits(8) for _ in range(cw * ch)))
    n = n.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.7))
    bite = ImageChops.multiply(ramp, n.point(lambda v: 255 if v < 118 else 0))
    return ImageChops.subtract(alpha, bite)


def card(path, centre, ink, zoom=1.0, ymid=0.5):
    """zoom > 1 punches the crop in so one face fills the card; ymid places it vertically.

    A figure has to read at 168 px wide, where the whole card is only 80 px: a full-height
    scene crop leaves a head about 9 px tall, which is texture, not an expression.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    ar = CARD_AR_OVERRIDE[0] or CARD_AR
    cw = min(w, round(h * ar / zoom))
    ch = min(h, round(cw / ar))
    x0 = min(max(0, round(centre * w - cw / 2)), w - cw)
    y0 = min(max(0, round(ymid * h - ch / 2)), h - ch)
    card_w = round(CARD_W * CARD_SCALE[0])
    c = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((card_w, round(card_w / ar)), Image.LANCZOS)
    if CARD_WEAR[0] > 0:
        c = scratched(c, CARD_WEAR[0])
    framed = Image.new("RGBA", (c.width + 2 * BORDER, c.height + 2 * BORDER), ink + (255,))
    framed.paste(c, (BORDER, BORDER))
    if CARD_WEAR[0] > 0:
        framed.putalpha(torn(framed.split()[3], CARD_WEAR[0]))
    return framed.rotate(TILT if TILT_OVERRIDE[0] is None else TILT_OVERRIDE[0],
                         resample=Image.BICUBIC, expand=True)


def ink_wear(alpha, amount):
    """Erode a text layer the way a worn screen print does: small voids lifted out of
    the ink, a harder bite along the letter edges, and a few dry-roller streaks.

    Two things keep it reading as print rather than sandpaper. The noise is generated
    coarse and upscaled, so a void is a flake rather than a pixel; and the cutoff is
    taken from the histogram so a fixed *fraction* of ink lifts however the blur fell,
    instead of a fixed grey level that removes half the letter once blurring narrows
    the range.
    """
    rnd = random.Random(INK_SEED)
    w, h = alpha.size
    cw, ch = max(8, w // 3), max(8, h // 3)
    n = Image.frombytes("L", (cw, ch), bytes(rnd.getrandbits(8) for _ in range(cw * ch)))
    n = n.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))

    def cut(frac):
        """Grey level below which `frac` of the pixels sit."""
        want, run = frac * w * h, 0
        for v, c in enumerate(n.histogram()):
            run += c
            if run >= want:
                return v
        return 255

    holes = n.point(lambda v, t=cut(0.05 * amount): 0 if v < t else 255)
    d = ImageDraw.Draw(holes)
    for _ in range(round(9 * amount)):        # dry streaks where the roller skipped
        y = rnd.randrange(h); x0 = rnd.randrange(w); ln = rnd.randrange(w // 8, w // 3)
        d.line([(x0, y), (x0 + ln, y)], fill=0, width=1)
    holes = holes.filter(ImageFilter.GaussianBlur(0.5))
    edge = ImageChops.difference(alpha, alpha.filter(ImageFilter.MinFilter(3)))
    edge_holes = n.point(lambda v, t=cut(0.30 * amount): 0 if v < t else 255)
    alpha = ImageChops.subtract(alpha, ImageChops.multiply(edge, ImageChops.invert(edge_holes)))
    return ImageChops.multiply(alpha, holes)


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
    if INK_WEAR[0] <= 0:
        for (t, col), b, f in zip(lines, boxes, fonts):
            d.text((TEXT_X - b[0], y - b[1]), t, font=f, fill=col)
            y += b[3] - b[1] + LEAD
        return
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    for (t, col), b, f in zip(lines, boxes, fonts):
        dl.text((TEXT_X - b[0], y - b[1]), t, font=f, fill=tuple(col) + (255,))
        y += b[3] - b[1] + LEAD
    layer.putalpha(ink_wear(layer.split()[3], INK_WEAR[0]))
    canvas.paste(layer, (0, 0), layer)


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
src.add_argument("--import", dest="imp", metavar="FILE",
                 help="size a finished thumbnail made elsewhere (e.g. in an image model): exact 16:9 crop, 1280x720, "
                      "JPEG under YouTube's 2 MB cap, plus the size-check sheet. No text or card is drawn.")
src.add_argument("--scene", help="scene id or its numeric prefix; canonical still only")
src.add_argument("--still", help="a named file in scene-generation/, e.g. an attempt whose flaw falls outside the crop")
ap.add_argument("--centre", type=float, default=0.5, help="horizontal centre of the card crop, 0-1")
ap.add_argument("--zoom", type=float, default=1.0, help="punch the crop in on the subject; 1 is the full-height scene")
ap.add_argument("--ymid", type=float, default=0.5, help="vertical centre of the card crop, 0-1; a head usually sits above 0.5")
ap.add_argument("--line", action="append")
ap.add_argument("--card", type=float, default=1.0, help="scale the tilted card, 1 is the standard layout")
ap.add_argument("--card-ar", type=float, default=None, dest="card_ar",
                help="card aspect ratio; default 1.23. The stills are 1.79, so the default throws away a third of the width — pass ~1.6-1.79 to keep a wide composition whole")
ap.add_argument("--tilt", type=float, default=None,
                help="card rotation in degrees; positive is anticlockwise (the card angles UP to the right). Default -2.5")
ap.add_argument("--card-x", type=int, default=0, dest="card_dx", help="nudge the card left (negative) or right, in pixels")
ap.add_argument("--distress", type=float, default=1.0,
                help="age the cream ground: scales the grain and mottling and, above 1, wears the edges")
ap.add_argument("--ink-wear", type=float, default=0.0, dest="ink_wear",
                help="wear the lettering like a worn screen print: flecks out of the ink, a bite at the edges, dry streaks. Try 0.8-1.6")
ap.add_argument("--font", default=None, help="override series.md thumbnail.font, e.g. C:/Windows/Fonts/impact.ttf")
ap.add_argument("--card-wear", type=float, default=0.0, dest="card_wear",
                help="age the photo card: hairline scratches and cracks over the image, and nicks bitten out of the frame edge. Try 0.8-1.5")
ap.add_argument("--replace", action="store_true")
ap.add_argument("--mark", action="store_true", help="add the LIVED IT wordmark bottom-left")
a = ap.parse_args()
CARD_SCALE[0] = a.card

CARD_AR_OVERRIDE[0] = a.card_ar
TILT_OVERRIDE[0] = a.tilt
CARD_DX[0] = a.card_dx
DISTRESS[0] = a.distress
INK_WEAR[0] = a.ink_wear
CARD_WEAR[0] = a.card_wear

series, slug = a.project.split("/")
bg, ink, accent, font = series_keys(series)
if a.font:
    font = a.font
video = ROOT / "content" / series / slug
(video / "thumbnails").mkdir(parents=True, exist_ok=True)
if a.imp:
    im = Image.open(a.imp).convert("RGB")
    w, h = im.size
    if abs(w / h - 16 / 9) > 1e-4:   # crop first, or the resize stretches the lettering
        if w / h > 16 / 9:
            nw = round(h * 16 / 9); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = round(w * 9 / 16); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        print(f"cropped {w}x{h} -> {im.size[0]}x{im.size[1]} for exact 16:9")
    im = im.resize((1280, 720), Image.LANCZOS)
    out = os.path.join(str(ROOT / 'content' / a.project.split('/')[0] / a.project.split('/')[1] / 'thumbnails'), a.name + ".jpg")
    for q in (95, 92, 90, 88, 85, 82):
        im.save(out, quality=q, optimize=True, progressive=True)
        if os.path.getsize(out) <= 2_000_000:
            break
    else:
        sys.exit(f"{out}: still over YouTube's 2 MB cap at quality 82")
    sheet = Image.new("RGB", (1280 + 420, 740), "black")
    sheet.paste(im, (0, 10))
    sheet.paste(im.resize((360, 202), Image.LANCZOS), (1290, 10))
    sheet.paste(im.resize((168, 94), Image.LANCZOS), (1290, 230))
    sheet.save(os.path.join(str(ROOT / 'content' / a.project.split('/')[0] / a.project.split('/')[1] / 'thumbnails'), a.name + "-sizes.jpg"), quality=88)
    print(f"{out}  1280x720  {os.path.getsize(out):,} bytes (cap 2,097,152)  q{q}")
    print("check the 168 px panel in the -sizes sheet: that is the size the click is decided at")
    sys.exit(0)
if not a.line:
    sys.exit("--line is required unless --import is used")
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
out_dir.mkdir(parents=True, exist_ok=True)

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
cx = CARD_CX + round((CARD_SCALE[0] - 1.0) * 200) + CARD_DX[0]
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
