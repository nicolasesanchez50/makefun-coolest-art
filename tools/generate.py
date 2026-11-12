#!/usr/bin/env python3
"""Draws the entry image for make.fun coolest-art-01.

A total eclipse over a glass sea, seen past a bare tree on a rock.  The scene is
built from arithmetic only: a dithered five-stop sky, a corona made of angular
rays plus a bloom stack, water that mirrors the sky through per-row ripples, a
jagged rock silhouette, and a recursive branch routine for the tree.  The one
random source is seeded, so every run writes the same bytes.

Run:  python3 tools/generate.py art.png
"""

import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 2048                      # working square; the entry is downsampled to 1024
OUT_SIDE = 1024
HORIZON = 0.745               # fraction of the height where the sea starts
DISC = (0.615, 0.470, 0.150)  # cx, cy, radius as fractions of S

INK = (5, 6, 11)
SKY_STOPS = [
    (0.00, (6, 8, 26)),
    (0.26, (20, 20, 62)),
    (0.45, (62, 34, 96)),
    (0.60, (140, 60, 92)),
    (0.700, (236, 116, 70)),
    (0.745, (255, 190, 118)),
]


def sky_gradient(width, height, stops):
    """Vertical gradient with smoothstep between stops, as a float array."""
    rows = np.zeros((height, width, 3), dtype=np.float32)
    ys = np.linspace(0.0, 1.0, height, dtype=np.float32)
    for i in range(len(stops) - 1):
        a_pos, a_col = stops[i]
        b_pos, b_col = stops[i + 1]
        mask = (ys >= a_pos) & (ys <= b_pos)
        if not mask.any():
            continue
        t = (ys[mask] - a_pos) / max(b_pos - a_pos, 1e-6)
        t = t * t * (3.0 - 2.0 * t)
        for c in range(3):
            rows[mask, :, c] = (a_col[c] + (b_col[c] - a_col[c]) * t)[:, None]
    rows[: int(stops[0][0] * height) + 1] = stops[0][1]
    rows[int(stops[-1][0] * height):] = stops[-1][1]
    return rows


def layer(size, draw_fn, blur=0.0):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(img))
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def dither(size, rng, amount=1.0):
    """A +-amount noise field, so wide gradients do not band in 8 bits."""
    return rng.integers(-int(amount * 2 + 1), int(amount * 2 + 1), (size, size, 3), dtype=np.int16)


def main(path):
    rng = np.random.default_rng(20261112)
    cx, cy, rad = DISC[0] * S, DISC[1] * S, DISC[2] * S
    horizon = int(HORIZON * S)

    # ---- sky -------------------------------------------------------------
    image = Image.fromarray(sky_gradient(S, S, SKY_STOPS).clip(0, 255).astype(np.uint8), "RGB")

    # ---- stars -----------------------------------------------------------
    stars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stars)
    for _ in range(700):
        x, y = rng.uniform(0, S), rng.uniform(0, horizon * 0.92)
        fade = 1.0 - (y / (horizon * 0.92)) ** 1.7
        b = int(60 + 185 * rng.random() * fade)
        r = rng.uniform(0.5, 1.9) * (0.5 + 0.9 * fade)
        sd.ellipse([x - r, y - r, x + r, y + r],
                   fill=(b, b, min(255, b + 22), int(210 * fade)))
    image = Image.alpha_composite(image.convert("RGBA"), stars)

    # ---- corona: angular rays, then a stacked bloom ----------------------
    def rays(d):
        for i in range(2200):
            ang = (i / 2200.0) * math.tau
            wobble = (1.0 + 0.20 * math.sin(ang * 9.0 + 0.4)
                      + 0.12 * math.sin(ang * 17.0 + 1.1))
            reach = rad * wobble * (1.02 + 1.55 * rng.random() ** 4)
            w = 0.0012 + 0.0034 * rng.random()
            a = 26 + int(34 * rng.random())
            d.polygon([(cx + math.cos(ang - w) * rad * 0.995, cy + math.sin(ang - w) * rad * 0.995),
                       (cx + math.cos(ang + w) * rad * 0.995, cy + math.sin(ang + w) * rad * 0.995),
                       (cx + math.cos(ang) * reach, cy + math.sin(ang) * reach)],
                      fill=(255, 226, 182, a))

    image = Image.alpha_composite(image, layer(S, rays, S * 0.0035))

    def bloom(d):
        for step in range(70):
            t = step / 69.0
            r = rad * (1.005 + 1.35 * t)
            a = int(86 * math.exp(-4.2 * t))
            if a <= 0:
                continue
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 205, 150, a),
                      width=max(1, int(S * 0.010 * (1 - 0.5 * t))))

    image = Image.alpha_composite(image, layer(S, bloom, S * 0.010))

    def inner(d):
        for step in range(40):
            t = step / 39.0
            r = rad * (0.995 + 0.10 * t)
            d.ellipse([cx - r, cy - r, cx + r, cy + r],
                      outline=(255, 246, 226, int(150 * (1 - t) ** 1.5)),
                      width=max(1, int(S * 0.004 * (1 - 0.7 * t))))

    image = Image.alpha_composite(image, layer(S, inner, S * 0.0035))

    # ---- the disc and its chromosphere rim -------------------------------
    disc = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(disc)
    dd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=INK + (255,))
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    for k in range(240):
        t = k / 239.0
        ang = math.tau * t
        rr = rad * 0.0035
        rd.ellipse([cx + math.cos(ang) * rad * 1.006 - rr, cy + math.sin(ang) * rad * 1.006 - rr,
                    cx + math.cos(ang) * rad * 1.006 + rr, cy + math.sin(ang) * rad * 1.006 + rr],
                   fill=(255, 236, 200, 190))
    rim = rim.filter(ImageFilter.GaussianBlur(S * 0.0018))
    image = Image.alpha_composite(image, rim)
    image = Image.alpha_composite(image, disc)

    def diamond(d):
        x = cx + rad * math.cos(math.radians(214))
        y = cy + rad * math.sin(math.radians(214))
        for r, a in ((rad * 0.10, 55), (rad * 0.05, 120), (rad * 0.018, 240)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 252, 240, a))

    image = Image.alpha_composite(image, layer(S, diamond, S * 0.005))

    # ---- the sea ---------------------------------------------------------
    sky_rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    water_h = S - horizon
    mirror = sky_rgb[horizon - water_h: horizon][::-1].copy()
    rows = np.arange(water_h, dtype=np.float32)[:, None]
    depth = rows / max(water_h - 1, 1)
    xs = np.arange(S, dtype=np.float32)[None, :]
    shift = (np.sin(rows / 11.0) * 2.0 + np.sin(rows / 31.0 + 1.3) * 5.0) * (0.22 + depth)
    idx = np.clip((xs + shift).astype(np.int32), 0, S - 1)
    mirror = np.take_along_axis(mirror, idx[:, :, None].repeat(3, axis=2), axis=1)
    falloff = (0.66 - 0.48 * depth)[:, :, None]
    water = mirror * falloff + np.array([9, 13, 25], dtype=np.float32) * (1 - falloff)
    image.paste(Image.fromarray(water.clip(0, 255).astype(np.uint8), "RGB"), (0, horizon))
    image = image.convert("RGBA")

    def ripples(d):
        y = horizon + 2
        while y < S:
            t = (y - horizon) / water_h
            amp = 1.2 + 11.0 * t
            phase = rng.uniform(0, math.tau)
            pts = [(x, y + math.sin(x / (46 + 300 * t) + phase) * amp) for x in range(0, S + 1, 16)]
            a = int(40 * (1 - t) ** 1.5 + 5)
            d.line(pts, fill=(255, 220, 178, a), width=max(1, int(1 + 2.4 * t)))
            y += int(8 + 28 * t)

    image = Image.alpha_composite(image, layer(S, ripples, S * 0.0012))

    def column(d):
        for i in range(260):
            t = i / 259.0
            y = horizon + t * water_h
            half = S * (0.022 + 0.075 * t) * (0.5 + 0.5 * math.sin(t * 19.0 + 0.7) ** 2)
            a = int(34 * (1 - t) ** 1.3)
            d.line([(cx - half, y), (cx + half, y)], fill=(255, 210, 160, a),
                   width=max(1, int(1 + 3.2 * t)))

    image = Image.alpha_composite(image, layer(S, column, S * 0.0045))

    # glitter dashes on the light path
    def glitter(d):
        for _ in range(240):
            t = rng.random() ** 1.6
            y = horizon + t * water_h
            spread = S * (0.02 + 0.09 * t)
            x = cx + rng.normal(0, spread)
            if not (0 <= x < S):
                continue
            w = rng.uniform(3, 4 + 26 * t)
            d.line([(x - w / 2, y), (x + w / 2, y)], fill=(255, 238, 206, int(90 * (1 - t))),
                   width=max(1, int(1 + 2 * t)))

    image = Image.alpha_composite(image, layer(S, glitter, S * 0.001))

    # ---- rock and tree ---------------------------------------------------
    base_x, base_y = S * 0.285, horizon + S * 0.070
    rock_w, rock_h = S * 0.150, S * 0.058
    silhouette = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(silhouette)
    top = []
    steps = 64
    for i in range(steps + 1):
        u = i / steps
        x = base_x - rock_w + 2 * rock_w * u
        hump = math.sin(math.pi * u) ** 0.55
        jag = 0.006 * math.sin(u * 41.0 + 0.9) + 0.004 * math.sin(u * 97.0 + 2.1)
        top.append((x, base_y - rock_h * hump + S * jag))
    sd.polygon(top + [(base_x + rock_w, base_y + S * 0.030), (base_x - rock_w, base_y + S * 0.030)],
               fill=INK + (255,))

    def branch(d, x, y, ang, length, width, depth):
        x2 = x + math.cos(ang) * length
        y2 = y + math.sin(ang) * length
        d.line([(x, y), (x2, y2)], fill=INK + (255,), width=max(1, int(round(width))))
        if depth <= 0:
            return
        spread = 0.46 + 0.10 * math.sin(depth * 2.3)
        for sign in (-1, 1):
            if depth > 3 and rng.random() < 0.13:
                continue
            branch(d, x2, y2, ang + sign * spread * (0.75 + 0.55 * rng.random()),
                   length * (0.70 + 0.09 * rng.random()), width * 0.68, depth - 1)

    # trunk: a tapered polygon with a root flare, then recursive branches
    trunk_top = base_y - S * 0.150
    sd.polygon([(base_x - S * 0.0150, base_y + S * 0.004),
                (base_x + S * 0.0130, base_y + S * 0.004),
                (base_x + S * 0.0072, trunk_top),
                (base_x - S * 0.0080, trunk_top)], fill=INK + (255,))
    sd.polygon([(base_x - S * 0.0240, base_y + S * 0.004),
                (base_x - S * 0.0150, base_y - S * 0.012),
                (base_x - S * 0.0150, base_y + S * 0.004)], fill=INK + (255,))
    sd.polygon([(base_x + S * 0.0130, base_y - S * 0.010),
                (base_x + S * 0.0245, base_y + S * 0.004),
                (base_x + S * 0.0130, base_y + S * 0.004)], fill=INK + (255,))
    branch(sd, base_x, trunk_top, -math.pi / 2, S * 0.070, S * 0.0068, 8)
    image = Image.alpha_composite(image, silhouette)

    # a thin rim of eclipse light down the trunk's left edge
    def rim_light(d):
        d.line([(base_x - S * 0.0148, base_y), (base_x - S * 0.0078, trunk_top)],
               fill=(255, 200, 150, 40), width=max(1, int(S * 0.0018)))

    image = Image.alpha_composite(image, layer(S, rim_light, S * 0.002))

    # ---- its reflection --------------------------------------------------
    tree_layer = silhouette.crop([0, int(trunk_top - S * 0.02), S, int(base_y + S * 0.030)])
    refl = tree_layer.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(S * 0.005))
    refl = refl.resize((S, max(1, int(refl.height * 0.68))), Image.LANCZOS)
    refl.putalpha(refl.getchannel("A").point(lambda v: int(v * 0.28)))
    image.alpha_composite(refl, (0, int(base_y + S * 0.026)))

    # ---- three birds, for scale ------------------------------------------
    def birds(d):
        for bx, by, s in ((0.445, 0.325, 1.0), (0.492, 0.288, 0.74), (0.516, 0.352, 0.58)):
            x, y, w = bx * S, by * S, S * 0.016 * s
            d.line([(x - w, y), (x, y - w * 0.62), (x + w, y)], fill=(255, 232, 204, 235),
                   width=max(2, int(S * 0.0026 * s)))

    image = Image.alpha_composite(image, layer(S, birds, S * 0.0006))

    # ---- vignette and dither --------------------------------------------
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
    d2 = ((xx - 0.52) ** 2 + (yy - 0.50) ** 2) ** 0.5
    vig = np.clip(1.0 - 1.25 * np.clip(d2 - 0.26, 0, None) ** 1.35, 0.36, 1.0)[:, :, None]
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) * vig
    image = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")

    final = np.asarray(image.resize((OUT_SIDE, OUT_SIDE), Image.LANCZOS), dtype=np.float32)
    out = Image.fromarray(final.clip(0, 255).astype(np.uint8), "RGB")
    out.save(path, "PNG", optimize=True)
    print(f"wrote {path} ({OUT_SIDE}x{OUT_SIDE})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "art.png")
