#!/usr/bin/env python3
"""
Offline preview of the runtime composite.

Mirrors drawComposite()/drawRecord() in index.html so frame geometry and record
placement can be checked without a camera. Substitute fonts are used, so treat
the text as a position/size check rather than a typography proof.

    python3 tools/preview_composite.py            # both frames, with a record
    python3 tools/preview_composite.py --blank    # no record entered
"""

import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIDE_FADE = 0.055    # keep in sync with index.html
PERSON_FIT = 0.92    # keep in sync with index.html

OUT_DIR = "/private/tmp/claude-501/-Users-sonhyebin-Desktop---------/95b69dfb-508b-45ae-afac-348f39d7726a/scratchpad"

LATIN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
KOREAN = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

# ── kept in sync with FRAME_DEFS in index.html ──────────────────────────────
FRAME_DEFS = {
    "ribbon": {
        "plate": "frame-ribbon.jpg",
        "w": 1055, "h": 1491,
        "fg": {"src": "frame-ribbon-fg.png", "x": 0.0, "y": 0.0, "w": 0.375, "h": 0.300},
        "stage": {"x": 0.075, "y": 0.028, "w": 0.850, "h": 0.754},
        "record": {
            "align": 0.8886,
            "time": {"y": 0.8598, "size": 0.0252, "color": (10, 10, 10)},
            "cat": {"y": 0.8770, "size": 0.0136, "color": (51, 51, 51), "maxW": 0.179},
        },
    },
    "sport": {
        "plate": "frame-sport.jpg",
        "w": 1024, "h": 1536,
        "fg": None,
        "stage": {"x": 0.170, "y": 0.100, "w": 0.660, "h": 0.682},
        "record": {
            "align": 0.8775,
            "time": {"y": 0.8522, "size": 0.0371, "color": (10, 10, 10)},
            "cat": {"y": 0.8865, "size": 0.0211, "color": (10, 10, 10), "maxW": 0.2475},
        },
    },
}

RECORD = {"time": "1:24:07", "category": "3인팀전", "name": "손혜빈"}
BLANK = {"time": None, "category": "개인전", "name": ""}


def demo_person(vw=720, vh=960):
    """Same silhouette buildDemoPerson() draws in the browser."""
    img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = vw / 2

    body = [
        (cx - vw * 0.135, vh * 0.40), (cx, vh * 0.365), (cx + vw * 0.135, vh * 0.40),
        (cx + vw * 0.30, vh * 0.62), (cx + vw * 0.26, vh),
        (cx - vw * 0.26, vh), (cx - vw * 0.30, vh * 0.62),
    ]
    d.polygon(body, fill=(70, 76, 86, 255))
    r = vw * 0.155
    d.ellipse([cx - r, vh * 0.24 - r, cx + r, vh * 0.24 + r], fill=(90, 96, 106, 255))

    # vertical gradient, matching the canvas version
    grad = Image.new("L", (1, vh))
    for y in range(vh):
        t = y / (vh - 1)
        grad.putpixel((0, y), int(255 * (1 - 0.55 * t)))
    shade = grad.resize((vw, vh))
    px = img.load()
    sp = shade.load()
    for y in range(vh):
        for x in range(vw):
            r_, g_, b_, a_ = px[x, y]
            if a_:
                k = sp[x, y] / 255.0
                px[x, y] = (int(r_ * k), int(g_ * k), int(b_ * k), a_)
    return img


def fit_font(path, text, size, max_w, index=None):
    while size > 8:
        f = ImageFont.truetype(path, int(round(size)), index=index) if index is not None \
            else ImageFont.truetype(path, int(round(size)))
        if f.getlength(text) <= max_w:
            return f
        size -= 0.5
    return f


def composite(key, record, person):
    d = FRAME_DEFS[key]
    W, H = d["w"], d["h"]
    canvas = Image.open(d["plate"]).convert("RGBA").resize((W, H), Image.LANCZOS)

    # ── person, clipped to the inside of the box ──
    st = d["stage"]
    sx, sy = st["x"] * W, st["y"] * H
    sw, sh = st["w"] * W, st["h"] * H
    scale = PERSON_FIT * min(sw / person.width, sh / person.height)
    dw, dh = person.width * scale, person.height * scale

    stage = Image.new("RGBA", (int(round(sw)), int(round(sh))), (0, 0, 0, 0))
    # centred horizontally, standing on the box floor
    stage.alpha_composite(person.resize((int(round(dw)), int(round(dh))), Image.LANCZOS),
                          (int(round((sw - dw) / 2)), int(round(sh - dh))))

    # soften the vertical edges (SIDE_FADE in index.html)
    edge = max(1.0, SIDE_FADE * stage.width)
    ramp = np.clip(np.minimum(np.arange(stage.width) / edge,
                              (stage.width - 1 - np.arange(stage.width)) / edge), 0.0, 1.0)
    alpha = np.array(stage.getchannel("A")).astype(np.float32) * ramp[None, :]
    stage.putalpha(Image.fromarray(alpha.astype(np.uint8)))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(stage, (int(round(sx)), int(round(sy))))

    # contact shadow, clipped to the stage like the canvas version
    shadow_a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(H * 0.014 / 4))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(shadow_a.point(lambda v: int(v * 0.30)))
    shadow = shadow.transform(
        (W, H), Image.AFFINE, (1, 0, 0, 0, 1, -H * 0.005), resample=Image.BILINEAR)
    clip = Image.new("L", (W, H), 0)
    ImageDraw.Draw(clip).rectangle([sx, sy, sx + sw, sy + sh], fill=255)
    shadow.putalpha(Image.composite(shadow.getchannel("A"), Image.new("L", (W, H), 0), clip))

    canvas.alpha_composite(shadow)
    canvas.alpha_composite(layer)

    # ── foreground element in front of the person ──
    if d["fg"]:
        fg = Image.open(d["fg"]["src"]).convert("RGBA")
        fw, fh = int(round(d["fg"]["w"] * W)), int(round(d["fg"]["h"] * H))
        canvas.alpha_composite(fg.resize((fw, fh), Image.LANCZOS),
                               (int(round(d["fg"]["x"] * W)), int(round(d["fg"]["y"] * H))))

    # ── record values ──
    r = d["record"]
    ax = r["align"] * W
    draw = ImageDraw.Draw(canvas)

    if record["time"]:
        f = ImageFont.truetype(LATIN, int(round(r["time"]["size"] * H)))
        draw.text((ax, r["time"]["y"] * H), record["time"],
                  font=f, fill=r["time"]["color"], anchor="rs")

    line = record["category"] or ""
    if record["name"]:
        line = (line + "  ·  " + record["name"]) if line else record["name"]
    if line:
        f = fit_font(KOREAN, line, r["cat"]["size"] * H, r["cat"]["maxW"] * W, index=2)
        draw.text((ax, r["cat"]["y"] * H), line,
                  font=f, fill=r["cat"]["color"], anchor="rs")

    return canvas.convert("RGB")


def main():
    record = BLANK if "--blank" in sys.argv else RECORD
    tag = "blank" if "--blank" in sys.argv else "filled"
    person = demo_person()
    for key in FRAME_DEFS:
        img = composite(key, record, person)
        path = f"{OUT_DIR}/composite-{key}-{tag}.png"
        img.save(path)
        print(path, img.size)


if __name__ == "__main__":
    main()
