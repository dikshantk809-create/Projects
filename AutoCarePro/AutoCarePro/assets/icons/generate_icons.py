"""
AutoCare Pro — PWA icon generator.

Draws the AutoCare Pro mark (shield + telemetry nodes + verification check)
at every size required by the web app manifest. Run once; the generated PNGs
are committed with the project so no build step is required to open the app.

    python3 assets/icons/generate_icons.py
"""

from PIL import Image, ImageDraw

BG = (7, 8, 9)
SURFACE = (17, 20, 25)
RED = (225, 6, 0)
RED_BRIGHT = (255, 43, 36)
GREEN = (57, 255, 136)
TEXT = (244, 246, 248)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
SS = 8  # supersampling factor for smooth edges


def shield_path(cx, cy, w, h):
    """Return the polygon points of a modern automotive shield."""
    half = w / 2
    top = cy - h / 2
    bottom = cy + h / 2
    shoulder = top + h * 0.60
    return [
        (cx - half, top + h * 0.06),
        (cx, top),
        (cx + half, top + h * 0.06),
        (cx + half * 0.94, shoulder),
        (cx, bottom),
        (cx - half * 0.94, shoulder),
    ]


def draw_icon(size, maskable=False):
    s = size * SS
    img = Image.new("RGBA", (s, s), BG + (255,))
    d = ImageDraw.Draw(img)

    # rounded plate
    pad = 0 if maskable else int(s * 0.02)
    d.rounded_rectangle(
        [pad, pad, s - pad, s - pad], radius=int(s * 0.22), fill=SURFACE + (255,)
    )

    # faint technical grid
    step = s // 10
    for i in range(1, 10):
        d.line([(i * step, 0), (i * step, s)], fill=(40, 45, 53, 55), width=max(1, s // 400))
        d.line([(0, i * step), (s, i * step)], fill=(40, 45, 53, 55), width=max(1, s // 400))

    # shield — scaled down for maskable so it survives the 20% safe-zone crop
    scale = 0.52 if maskable else 0.62
    w = s * scale
    h = s * scale * 1.14
    pts = shield_path(s / 2, s / 2, w, h)
    d.polygon(pts, fill=(13, 15, 18, 255), outline=RED + (255,), width=max(2, int(s * 0.022)))

    # inner glow edge
    inner = shield_path(s / 2, s / 2, w * 0.86, h * 0.86)
    d.polygon(inner, outline=(255, 43, 36, 90), width=max(1, int(s * 0.008)))

    # telemetry nodes (neural network motif)
    r = s * 0.020
    nodes = [
        (s / 2 - w * 0.24, s / 2 - h * 0.20),
        (s / 2 + w * 0.24, s / 2 - h * 0.20),
        (s / 2, s / 2 - h * 0.32),
    ]
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            d.line([nodes[a], nodes[b]], fill=(255, 43, 36, 150), width=max(1, int(s * 0.008)))
    for (nx, ny) in nodes:
        d.ellipse([nx - r, ny - r, nx + r, ny + r], fill=RED_BRIGHT + (255,))

    # verification check
    cw = max(3, int(s * 0.045))
    d.line(
        [
            (s / 2 - w * 0.24, s / 2 + h * 0.04),
            (s / 2 - w * 0.05, s / 2 + h * 0.22),
            (s / 2 + w * 0.27, s / 2 - h * 0.14),
        ],
        fill=GREEN + (255,),
        width=cw,
        joint="curve",
    )

    return img.resize((size, size), Image.LANCZOS)


def main():
    for size in SIZES:
        draw_icon(size).save(f"icon-{size}.png")
    draw_icon(512, maskable=True).save("maskable-512.png")
    draw_icon(180).save("apple-touch-icon.png")
    draw_icon(32).save("favicon-32.png")
    print("icons written")


if __name__ == "__main__":
    main()
