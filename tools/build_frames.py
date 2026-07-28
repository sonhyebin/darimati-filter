#!/usr/bin/env python3
"""
Build runtime frame assets from the source renders in assets-src/.

For each frame we produce:
  frame-<name>.jpg      opaque background plate, with the baked-in record values
                        (finish time / 종목) erased so the app can draw live values
  frame-<name>-fg.png   optional transparent foreground layer that must sit in
                        FRONT of the person cutout (e.g. the ribbon bow)

Run from the repo root:  python3 tools/build_frames.py
"""

import os
import numpy as np
from scipy import ndimage
from PIL import Image, ImageFilter

SRC = "assets-src"
OUT = "."
JPEG_QUALITY = 90

FRAMES = {
    "ribbon": {
        "src": "frame-ribbon.png",
        # flat bar background sampled from the artwork
        "patch_fill": (235, 234, 234),
        # fractional rects covering the baked finish-time + 종목 text
        "erase": [
            (0.745, 0.833, 0.902, 0.884),
        ],
        # region containing the foreground element, extracted by luminance
        # the ribbon bow is tied on the front of the box, so it must occlude the
        # person; `hi` is the luminance cut that separates satin from white card
        "foreground": {"rect": (0.0, 0.0, 0.375, 0.300), "hi": 120},
    },
    "sport": {
        "src": "frame-sport.png",
        "patch_fill": (233, 233, 233),
        "erase": [
            (0.688, 0.819, 0.890, 0.8585),   # 4:03:02  (keeps gold rule at .862)
            (0.770, 0.8640, 0.888, 0.8940),  # 개인전
        ],
        "foreground": None,
    },
}


def px(frac, total):
    return int(round(frac * total))


def erase_regions(img, rects, fill):
    a = np.array(img)
    W, H = img.size
    for (x0, y0, x1, y1) in rects:
        a[px(y0, H):px(y1, H), px(x0, W):px(x1, W)] = fill
    return Image.fromarray(a)


def extract_foreground(img, rect, hi):
    """Pull a dark element out of the artwork as a transparent overlay.

    Everything darker than `hi` is a candidate; the result is cropped to `rect`
    and the app places it back using the same fractions.
    """
    W, H = img.size
    x0, y0, x1, y1 = (px(rect[0], W), px(rect[1], H), px(rect[2], W), px(rect[3], H))

    crop = np.array(img.crop((x0, y0, x1, y1))).astype(np.uint8)
    lum = crop.astype(np.float32).mean(axis=2)

    # Keep only the element itself — the box's inner creases sit near the
    # threshold and would otherwise ghost over the person.
    labels, n = ndimage.label(lum < hi)
    if n == 0:
        raise SystemExit("foreground extraction found nothing below the threshold")
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    seed = labels == (int(np.argmax(sizes)) + 1)

    # Close the silhouette so interior detail (the gold DARIMATI lettering, satin
    # highlights) stays fully opaque instead of letting the person show through.
    mask = Image.fromarray((seed.astype(np.uint8) * 255))
    mask = mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(11))
    # 1px feather so the outline is not aliased
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    alpha = np.array(mask).astype(np.float32) / 255.0

    a8 = (alpha * 255).astype(np.uint8)
    # zero the colour channels where nothing shows through — keeps the PNG small
    crop = crop.copy()
    crop[a8 < 3] = 0

    return Image.fromarray(np.dstack([crop, a8]))


def main():
    for name, cfg in FRAMES.items():
        path = os.path.join(SRC, cfg["src"])
        img = Image.open(path).convert("RGB")
        print(f"{name}: {img.size[0]}x{img.size[1]}")

        plate = erase_regions(img, cfg["erase"], cfg["patch_fill"])
        jpg = os.path.join(OUT, f"frame-{name}.jpg")
        plate.save(jpg, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        print(f"  -> {jpg}  {os.path.getsize(jpg)/1024:.0f} KB")

        fg_cfg = cfg["foreground"]
        if fg_cfg:
            fg = extract_foreground(img, fg_cfg["rect"], fg_cfg["hi"])
            png = os.path.join(OUT, f"frame-{name}-fg.png")
            fg.save(png, "PNG", optimize=True)
            print(f"  -> {png}  {os.path.getsize(png)/1024:.0f} KB")


if __name__ == "__main__":
    main()
