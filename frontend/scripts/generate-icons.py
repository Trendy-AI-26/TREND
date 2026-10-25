"""
Generate the TRENDY AI browser icons from the brand logo.

Usage (from TREND/frontend):
    ..\\backend\\.venv\\Scripts\\python.exe scripts/generate-icons.py
    # or any Python with Pillow installed:  python scripts/generate-icons.py

Input : public/trendy_logo.png
Output: app/favicon.ico      multi-resolution ICO (16x16, 32x32, 48x48), transparent
        app/apple-icon.png   180x180 PNG on a solid cream (#FFF8F0) background

Steps: (1) if the logo has an opaque near-white background, turn it into alpha
(the cream centre sparkle is not near-white enough to be touched; a logo that is
already transparent is left as is), (2) trim the empty margin, (3) pad to a square
with a small margin, (4) resize with LANCZOS to each icon size.

Next.js App Router picks up app/favicon.ico and app/apple-icon.png by file
convention, so no metadata.icons entry is needed in app/layout.tsx.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "trendy_logo.png"
FAVICON = ROOT / "app" / "favicon.ico"
APPLE = ROOT / "app" / "apple-icon.png"

ICO_SIZES = (16, 32, 48)
FAVICON_MARGIN = 0.07  # fraction of the square side, per edge
APPLE_SIZE = 180
APPLE_MARGIN = 0.12
APPLE_BG = (255, 248, 240, 255)  # #FFF8F0

# Near-white background removal: fully transparent at/above HI, fully opaque
# at/below LO (min channel), linear in between for soft anti-aliased edges.
WHITE_LO = 235
WHITE_HI = 252


def remove_white_background(img: Image.Image) -> Image.Image:
    """Return RGBA; only acts if the image has an opaque near-white border."""
    img = img.convert("RGBA")
    w, h = img.size
    corners = [img.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    if not all(c[3] == 255 and min(c[:3]) >= WHITE_HI for c in corners):
        return img  # already transparent (or not a white background): keep as is

    # Only pixels connected to the border count as background, so a light
    # interior detail (the cream sparkle) can never be removed.
    px = img.load()

    def is_bg_candidate(x, y):
        return min(px[x, y][:3]) >= WHITE_LO

    seen = bytearray(w * h)
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [
        (x, y) for y in range(h) for x in (0, w - 1)
    ]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x]:
            continue
        if not is_bg_candidate(x, y):
            continue
        seen[y * w + x] = 1
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    for y in range(h):
        for x in range(w):
            if seen[y * w + x]:
                r, g, b, _ = px[x, y]
                m = min(r, g, b)
                a = round(255 * (WHITE_HI - m) / (WHITE_HI - WHITE_LO))
                px[x, y] = (r, g, b, max(0, min(255, a)))
    return img


def trim(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A").point(lambda v: 255 if v > 8 else 0)
    bbox = alpha.getbbox()
    return img.crop(bbox) if bbox else img


def pad_square(img: Image.Image, margin: float) -> Image.Image:
    w, h = img.size
    side = round(max(w, h) * (1 + 2 * margin))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return canvas


def main() -> None:
    art = trim(remove_white_background(Image.open(SRC)))

    # favicon.ico: render each frame separately so small sizes stay crisp.
    sq = pad_square(art, FAVICON_MARGIN)
    frames = [sq.resize((s, s), Image.LANCZOS) for s in ICO_SIZES]
    largest = frames[-1]
    largest.save(
        FAVICON,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[:-1],
    )

    # apple-icon.png: opaque background (iOS does not handle transparency well).
    sq = pad_square(art, APPLE_MARGIN).resize((APPLE_SIZE, APPLE_SIZE), Image.LANCZOS)
    bg = Image.new("RGBA", (APPLE_SIZE, APPLE_SIZE), APPLE_BG)
    bg.alpha_composite(sq)
    bg.convert("RGB").save(APPLE, format="PNG", optimize=True)

    print(f"wrote {FAVICON} ({FAVICON.stat().st_size} bytes)")
    print(f"wrote {APPLE} ({APPLE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
