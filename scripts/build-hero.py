#!/usr/bin/env python3
"""Build assets/readme-hero.svg: the XIU profile card.

A night-sky card in the tone of Bosong (bosong.xiu.kr): navy sky with a few
quiet stars, a crescent moon, soft hills, and XIU the puppy asleep on a mint
cushion. The left side carries the XIUSoft line ("We build small, and run it
properly.") and the two products, LiveSSH and Bosong.

Everything the card needs is embedded, because GitHub shows README images
through its image proxy where no external file can be loaded:
  * fonts: Patrick Hand (headings) and Nunito (body), the same OFL fonts the
    Bosong site uses, subset to the characters on the card and inlined as WOFF2
  * pictures: the sleeping XIU from Bosong's art, the Bosong and LiveSSH app
    icons, inlined as PNG

Motion is CSS only (no scripts, which GitHub strips anyway): the stars
twinkle, XIU breathes at Bosong's breathing pace (4 s in, 6 s out) and a few
small z's float up. Everything stops under prefers-reduced-motion.

Run `python scripts/build-hero.py` (needs Pillow, fonttools and brotli), or
let .github/workflows/rebuild-hero-card.yml do it on every push to main.
Sources live in assets/src (art + fonts); the output is assets/readme-hero.svg.
"""
from __future__ import annotations

import base64
import hashlib
import io
import random
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "src"
OUTPUT = ROOT / "assets" / "readme-hero.svg"
README = ROOT / "README.md"

W, H = 1200, 720

# ─── Palette (Bosong night sky, from site/assets/site.css and the hero art) ──
SKY_TOP = "#3A4888"
SKY_MID = "#2F3975"
SKY_BOTTOM = "#232D60"
HILL_BACK = "#2C3772"
HILL_FRONT = "#333E7A"
CREAM = "#FAF0DB"          # --night-text
MUTED = "#D3D6EA"          # --night-muted
FAINT = "#9AA2C8"
PINK = "#F7C7CE"           # --hero-sub
MOON = "#FBEFC4"
STAR = "#FAF0DB"
PILL = "rgba(250,240,219,0.07)"
PILL_LINE = "rgba(250,240,219,0.16)"

# ─── Fonts ─────────────────────────────────────────────────────────────────
HAND_TTF = SRC / "fonts" / "PatrickHand-Regular.ttf"
BODY_TTF = SRC / "fonts" / "Nunito-Variable.ttf"
HAND = "'XIU Hand','Patrick Hand','Comic Sans MS','Chalkboard SE',system-ui,sans-serif"
BODY = "'XIU Body','Nunito',-apple-system,system-ui,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"

# ─── Copy ──────────────────────────────────────────────────────────────────
TITLE = "XIU — We build small, and run it properly."
EYEBROW = "XIUSoft · Hwaseong, Korea"
WORDMARK = "XIU"
TAGLINE = "We build small, and run it properly."
LEAD = [
    "A small software company making web, mobile and desktop apps,",
    "and running them ourselves after launch.",
]
PRODUCTS = [
    {
        "icon": "livessh-icon.png",
        "name": "LiveSSH",
        "status": "coming soon",
        "tag": "SSH and SFTP client",
        "desc": "user@host and you are in. File transfers, tmux resume, AI-agent approvals.",
        "platforms": "iPhone · iPad · Mac  ·  Android  ·  Windows",
    },
    {
        "icon": "bosong-icon.png",
        "name": "Bosong",
        "status": "coming soon",
        "tag": "The mood diary where even a rest counts",
        "desc": "A few feelings and how strong they are. Entries stay on your device.",
        "platforms": "iPhone · iPad · Mac · Apple Watch  ·  9 languages",
    },
]
FOOTER_LEFT = "xiu.kr  ·  bosong.xiu.kr  ·  livessh.xiu.kr  ·  contact@xiu.kr"
FOOTER_RIGHT = "click anywhere to visit xiu.kr"


# ─── Embedding helpers ─────────────────────────────────────────────────────
def png_data_uri(path: Path, size: int, colors: int | None = 256) -> str:
    """Resize a PNG to `size` px (longest side) and inline it. Palette
    quantisation keeps the alpha channel and roughly halves the bytes."""
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    if colors:
        img = img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def font_data_uri(path: Path, text: str) -> str:
    """Subset a TTF to the characters in `text` and inline it as WOFF2."""
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "mark", "mkmk"]
    opts.name_IDs = [1, 2]            # family + style only; drops the long notices
    opts.name_legacy = False
    opts.notdef_outline = True
    opts.hinting = False
    font = TTFont(str(path), recalcTimestamp=False)  # same bytes on every rebuild
    sub = subset.Subsetter(options=opts)
    sub.populate(text=text + " ")
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


class Measure:
    """Text widths from the real font, so the layout can be checked
    (pill widths, right-aligned text) instead of guessed."""

    def __init__(self, path: Path):
        self.font = TTFont(str(path))
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        self.upem = self.font["head"].unitsPerEm

    def width(self, text: str, size: float) -> float:
        total = 0
        for ch in text:
            gname = self.cmap.get(ord(ch)) or ".notdef"
            total += self.hmtx[gname][0]
        return total * size / self.upem


# ─── Sky ───────────────────────────────────────────────────────────────────
def stars_svg(rng: random.Random) -> str:
    """Small dots plus a few four-point sparkles, each with its own twinkle
    timing. Kept off the text column (x < 640, 60 < y < 600) and off XIU."""
    parts: list[str] = []
    n = 0
    while n < 58:
        x = rng.uniform(20, W - 20)
        y = rng.uniform(16, 560)
        if x < 640 and 70 < y < 620:
            continue
        if 720 < x < 1190 and 300 < y < 600:   # XIU and the cushion
            continue
        r = rng.choice([0.9, 1.1, 1.3, 1.6, 2.0])
        o = rng.uniform(0.35, 0.9)
        dur = rng.uniform(3.2, 6.8)
        delay = rng.uniform(-6, 0)
        parts.append(
            f'<circle class="tw" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{STAR}" opacity="{o:.2f}" '
            f'style="animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s"/>'
        )
        n += 1
    sparkles = [(140, 36, 7), (470, 44, 9), (690, 92, 6), (820, 150, 8), (1160, 72, 7), (980, 300, 6), (590, 24, 5), (1100, 420, 6)]
    for i, (x, y, s) in enumerate(sparkles):
        parts.append(
            f'<path class="tw" d="M{x} {y - s} Q{x} {y} {x + s} {y} Q{x} {y} {x} {y + s} Q{x} {y} {x - s} {y} Q{x} {y} {x} {y - s}Z" '
            f'fill="{STAR}" opacity="0.85" style="animation-duration:{4.2 + i * 0.7:.1f}s;animation-delay:{-i * 1.3:.1f}s"/>'
        )
    return "\n    ".join(parts)


def hills_svg() -> str:
    back = (f"M0 626 C120 596 230 590 330 606 S520 650 640 622 S860 576 980 602 S1120 650 {W} 618 V{H} H0 Z")
    front = (f"M0 666 C140 640 260 638 380 656 S600 690 740 664 S960 626 1080 650 S1160 672 {W} 660 V{H} H0 Z")
    return (
        f'<path d="{back}" fill="{HILL_BACK}"/>\n'
        f'    <path d="{front}" fill="{HILL_FRONT}"/>'
    )


def moon_svg(cx: int, cy: int, r: int) -> str:
    """A crescent: a full disc with a second disc masked out of its upper right."""
    return f'''<g class="moon">
      <circle cx="{cx}" cy="{cy}" r="{r + 60}" fill="url(#moon-glow)"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{MOON}" mask="url(#moon-mask)"/>
    </g>'''


# ─── Card ──────────────────────────────────────────────────────────────────
def build_svg() -> str:
    rng = random.Random(817)  # XIU's birthday, 17 August: a fixed sky

    hand_m = Measure(HAND_TTF)
    body_m = Measure(BODY_TTF)

    hand_text = WORDMARK + TAGLINE + "zZ"
    body_text = EYEBROW + "".join(LEAD) + FOOTER_LEFT + FOOTER_RIGHT + "".join(
        p["name"] + p["status"] + p["tag"] + p["desc"] + p["platforms"] for p in PRODUCTS
    )
    hand_font = font_data_uri(HAND_TTF, hand_text)
    body_font = font_data_uri(BODY_TTF, body_text)

    siwoo = png_data_uri(SRC / "siwoo-rest-cushion.png", 470)
    icons = {p["icon"]: png_data_uri(SRC / p["icon"], 128) for p in PRODUCTS}

    # left column
    x0 = 72
    col_w = 560

    # product cards
    card_h = 118
    text_w = col_w - 92 - 22
    cards: list[str] = []
    y = 352
    for i, p in enumerate(PRODUCTS):
        desc_w = body_m.width(p["desc"], 13.5)
        if desc_w > text_w:
            raise SystemExit(f"{p['name']}: description is {desc_w:.0f}px, card text column is {text_w}px: shorten it")
        name_w = body_m.width(p["name"], 23) * 1.04  # bold runs a little wider than the default instance
        status_w = body_m.width(p["status"], 12.5) + 20
        sx = x0 + 92 + name_w + 12
        cards.append(f'''<g class="card">
      <rect x="{x0}" y="{y}" width="{col_w}" height="{card_h}" rx="24" fill="{PILL}" stroke="{PILL_LINE}"/>
      <rect x="{x0 + 20}" y="{y + 22}" width="56" height="56" rx="14" fill="{SKY_BOTTOM}" opacity="0.6"/>
      <image href="{icons[p['icon']]}" x="{x0 + 20}" y="{y + 22}" width="56" height="56" clip-path="url(#icon-{i})"/>
      <text x="{x0 + 92}" y="{y + 36}" font-family="{BODY}" font-weight="700" font-size="23" fill="{CREAM}">{escape(p['name'])}</text>
      <rect x="{sx:.0f}" y="{y + 19}" width="{status_w:.0f}" height="22" rx="11" fill="{PINK}" opacity="0.18"/>
      <text x="{sx + status_w / 2:.0f}" y="{y + 34.5}" text-anchor="middle" font-family="{BODY}" font-weight="600" font-size="12.5" fill="{PINK}">{escape(p['status'])}</text>
      <text x="{x0 + 92}" y="{y + 59}" font-family="{BODY}" font-weight="600" font-size="15.5" fill="{MUTED}">{escape(p['tag'])}</text>
      <text x="{x0 + 92}" y="{y + 80}" font-family="{BODY}" font-size="13.5" fill="{MUTED}" opacity="0.85">{escape(p['desc'])}</text>
      <text x="{x0 + 92}" y="{y + 101}" font-family="{BODY}" font-size="12.5" fill="{FAINT}">{escape(p['platforms'])}</text>
    </g>''')
        y += card_h + 18

    footer_right_w = body_m.width(FOOTER_RIGHT, 13)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(TITLE)}</title>
  <desc id="desc">XIUSoft makes LiveSSH, an SSH and SFTP client, and Bosong, a gentle mood diary. XIU the puppy sleeps on a mint cushion under a crescent moon.</desc>

  <defs>
    <style>
      @font-face {{ font-family: 'XIU Hand'; src: url("{hand_font}") format("woff2"); font-weight: 400; }}
      @font-face {{ font-family: 'XIU Body'; src: url("{body_font}") format("woff2"); font-weight: 200 1000; }}
      text {{ -webkit-font-smoothing: antialiased; }}
      .tw {{ animation: twinkle 5s ease-in-out infinite; }}
      @keyframes twinkle {{
        0%, 100% {{ opacity: 0.25; }}
        50% {{ opacity: 1; }}
      }}
      .siwoo {{ transform-origin: 935px 650px; animation: breathe 10s ease-in-out infinite; }}
      @keyframes breathe {{
        0% {{ transform: scale(1, 1); }}
        40% {{ transform: scale(1.012, 1.02); }}
        100% {{ transform: scale(1, 1); }}
      }}
      .z {{ animation: zfloat 6s ease-in-out infinite; opacity: 0; }}
      .z2 {{ animation-delay: 2s; }}
      .z3 {{ animation-delay: 4s; }}
      @keyframes zfloat {{
        0% {{ transform: translate(0, 0); opacity: 0; }}
        15% {{ opacity: 0.9; }}
        70% {{ opacity: 0.9; }}
        100% {{ transform: translate(14px, -34px); opacity: 0; }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .tw, .siwoo {{ animation: none; }}
        .z {{ animation: none; opacity: 0.7; }}
      }}
    </style>

    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{SKY_TOP}"/>
      <stop offset="0.5" stop-color="{SKY_MID}"/>
      <stop offset="1" stop-color="{SKY_BOTTOM}"/>
    </linearGradient>
    <radialGradient id="moon-glow">
      <stop offset="0" stop-color="{MOON}" stop-opacity="0.16"/>
      <stop offset="0.45" stop-color="{MOON}" stop-opacity="0.07"/>
      <stop offset="1" stop-color="{MOON}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="cushion-glow" cx="0.5" cy="0.6" r="0.5">
      <stop offset="0" stop-color="{CREAM}" stop-opacity="0.10"/>
      <stop offset="1" stop-color="{CREAM}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="icon-0"><rect x="{x0 + 20}" y="{352 + 22}" width="56" height="56" rx="14"/></clipPath>
    <clipPath id="icon-1"><rect x="{x0 + 20}" y="{352 + 136 + 22}" width="56" height="56" rx="14"/></clipPath>
    <mask id="moon-mask">
      <rect width="{W}" height="{H}" fill="black"/>
      <circle cx="1068" cy="112" r="46" fill="white"/>
      <circle cx="1090" cy="98" r="40" fill="black"/>
    </mask>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="28"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <!-- sky -->
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    {stars_svg(rng)}
    {moon_svg(1068, 112, 46)}

    <!-- hills -->
    {hills_svg()}

    <!-- XIU asleep on the cushion -->
    <ellipse cx="935" cy="560" rx="290" ry="190" fill="url(#cushion-glow)"/>
    <g class="siwoo">
      <image href="{siwoo}" x="700" y="226" width="470" height="470"/>
    </g>
    <g font-family="{HAND}" fill="{CREAM}" opacity="0.9">
      <text class="z"    x="988" y="296" font-size="20">z</text>
      <text class="z z2" x="1006" y="272" font-size="26">z</text>
      <text class="z z3" x="1030" y="244" font-size="32">Z</text>
    </g>

    <!-- identity -->
    <text x="{x0}" y="96" font-family="{BODY}" font-weight="600" font-size="14" letter-spacing="0.6" fill="{FAINT}">{escape(EYEBROW)}</text>
    <text x="{x0 - 4}" y="206" font-family="{HAND}" font-size="128" fill="{CREAM}">{WORDMARK}</text>
    <text x="{x0}" y="258" font-family="{HAND}" font-size="40" fill="{PINK}">{escape(TAGLINE)}</text>
    <text x="{x0}" y="296" font-family="{BODY}" font-size="16.5" fill="{MUTED}">{escape(LEAD[0])}</text>
    <text x="{x0}" y="320" font-family="{BODY}" font-size="16.5" fill="{MUTED}">{escape(LEAD[1])}</text>

    <!-- products -->
    {"".join(cards)}

    <!-- footer -->
    <text x="{x0}" y="{H - 36}" font-family="{BODY}" font-weight="600" font-size="13" letter-spacing="0.3" fill="{FAINT}">{escape(FOOTER_LEFT)}</text>
    <text x="{W - 72}" y="{H - 36}" text-anchor="end" font-family="{BODY}" font-size="13" fill="{FAINT}" opacity="0.85">{escape(FOOTER_RIGHT)}</text>
  </g>

  <!-- frame hairline -->
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" stroke="{PILL_LINE}"/>
</svg>
'''


def sync_readme_cachebuster(svg: str) -> None:
    """Rewrite README's hero <img src="...?v=HASH"> with a hash of the SVG.

    GitHub's image proxy caches by URL; a new query string only when the file
    really changes means no churn on idle rebuilds and no stale card after one.
    """
    if not README.exists():
        return
    token = hashlib.sha256(svg.encode("utf-8")).hexdigest()[:10]
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(r"(readme-hero\.svg)(\?v=[A-Za-z0-9]+)?")
    new_text, n = pattern.subn(rf"\1?v={token}", text, count=1)
    if n and new_text != text:
        README.write_text(new_text, encoding="utf-8")
        print(f"updated README cache buster -> v={token}")


def main() -> int:
    svg = build_svg()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(svg) / 1024:.0f} KB)")
    sync_readme_cachebuster(svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
