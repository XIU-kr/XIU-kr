#!/usr/bin/env python3
"""Build assets/readme-hero.svg: the XIU profile card.

A morning card in the tone of Bosong (bosong.xiu.kr) in its light mode:
cream paper, navy text, a pink handwritten line, warm sunlight, and on the
right XIU the puppy stretching awake by a sunny window (Bosong's morning
widget art), fading into the cream so picture and card read as one scene.
The left side introduces XIU (founder of XIUSoft, a curious developer), the
line "I build small things, and run them properly." and the two products
built at XIUSoft, LiveSSH and Bosong.

Everything the card needs is embedded, because GitHub shows README images
through its image proxy where no external file can be loaded:
  * fonts: Patrick Hand (headings) and Nunito (body), the same OFL fonts the
    Bosong site uses, subset to the characters on the card and inlined as WOFF2
  * pictures: the morning XIU as JPEG, the Bosong and LiveSSH app icons as PNG

Motion is CSS only (no scripts, which GitHub strips anyway): a few warm
sparkles twinkle and XIU rises and settles very slightly at Bosong's
breathing pace (4 s in, 6 s out). Everything stops under
prefers-reduced-motion.

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

# ─── Palette (Bosong light mode, from site/assets/site.css) ─────────────────
PAPER = "#FFFBF5"          # --bg
PAPER2 = "#FDF3EC"         # --bg2
SUN = "#FFF1DF"            # --b-soft, the warm glow
SUN_DEEP = "#FFC98B"       # --b, sparkles
SURFACE = "#FFFFFF"        # --surface, product cards
LINE = "#F1E2D6"           # --line
TEXT = "#3A3F63"           # --text
MUTED = "#62657F"          # --muted
FAINT = "#9A9CB4"          # a readable step between --muted and --faint
ROSE = "#E4818F"           # --rose, the handwritten line
PINK = "#FDE6E8"           # --pink, status pill
PINK_INK = "#A8475A"       # --link, status pill text

# ─── Fonts ─────────────────────────────────────────────────────────────────
HAND_TTF = SRC / "fonts" / "PatrickHand-Regular.ttf"
BODY_TTF = SRC / "fonts" / "Nunito-Variable.ttf"
HAND = "'XIU Hand','Patrick Hand','Comic Sans MS','Chalkboard SE',system-ui,sans-serif"
BODY = "'XIU Body','Nunito',-apple-system,system-ui,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"

# ─── Copy ──────────────────────────────────────────────────────────────────
TITLE = "XIU — founder of XIUSoft, a curious developer. I build small things, and run them properly."
DESC = ("XIU, founder of XIUSoft and a curious developer, builds and runs LiveSSH, an SSH and SFTP client, "
        "and Bosong, a gentle mood diary. XIU the puppy stretches awake by a sunny window.")
WORDMARK = "XIU"
IDENTITY = "Founder of XIUSoft  ·  a curious developer"
TAGLINE = "I build small things, and run them properly."
LEAD = [
    "Every project started with “could I build this myself?”",
    "I design, build and run them on my own — now as XIUSoft,",
    "a one-person software company in Hwaseong, Korea.",
]
SECTION = "Building at XIUSoft"
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

# ─── Layout ────────────────────────────────────────────────────────────────
X0 = 72            # left column
COL_W = 560
CARDS_Y = 384
CARD_H = 112
CARD_GAP = 18
ART_X = 560        # where the morning picture starts; it fades in over FADE_W
FADE_W = 260
ART_H = H          # the picture is square: ART_H wide, so it runs past the right edge
ART_SHIFT = -80    # the square picture ends exactly at the right edge, so XIU's paws stay in


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


def jpeg_data_uri(path: Path, size: int, quality: int = 84) -> str:
    """Resize an opaque picture to `size` px (longest side) and inline it as JPEG."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


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
    (pill widths, line wrapping) instead of guessed."""

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


# ─── Decoration ────────────────────────────────────────────────────────────
def sparkles_svg(rng: random.Random) -> str:
    """A few warm four-point sparkles and dust motes in the sunlight, each
    with its own twinkle timing. Kept off the text column and off XIU."""
    parts: list[str] = []
    fixed = [(760, 64, 9), (826, 150, 6), (1120, 48, 7), (1160, 190, 5), (700, 36, 5), (1060, 120, 4)]
    for i, (x, y, s) in enumerate(fixed):
        parts.append(
            f'<path class="tw" d="M{x} {y - s} Q{x} {y} {x + s} {y} Q{x} {y} {x} {y + s} Q{x} {y} {x - s} {y} Q{x} {y} {x} {y - s}Z" '
            f'fill="{SUN_DEEP}" opacity="0.8" style="animation-duration:{4.4 + i * 0.6:.1f}s;animation-delay:{-i * 1.1:.1f}s"/>'
        )
    n = 0
    while n < 22:
        x = rng.uniform(740, W - 24)
        y = rng.uniform(24, 300)
        if 860 < x < 1120 and y > 220:   # XIU's head
            continue
        r = rng.choice([1.2, 1.6, 2.0, 2.4])
        parts.append(
            f'<circle class="tw" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{SUN_DEEP}" opacity="{rng.uniform(0.3, 0.7):.2f}" '
            f'style="animation-duration:{rng.uniform(3.6, 7):.1f}s;animation-delay:{rng.uniform(-6, 0):.1f}s"/>'
        )
        n += 1
    return "\n    ".join(parts)


# ─── Card ──────────────────────────────────────────────────────────────────
def build_svg() -> str:
    rng = random.Random(817)  # XIU's birthday, 17 August: the same sparkles on every rebuild

    body_m = Measure(BODY_TTF)

    hand_text = WORDMARK + TAGLINE
    body_text = IDENTITY + SECTION + "".join(LEAD) + FOOTER_LEFT + FOOTER_RIGHT + "".join(
        p["name"] + p["status"] + p["tag"] + p["desc"] + p["platforms"] for p in PRODUCTS
    )
    hand_font = font_data_uri(HAND_TTF, hand_text)
    body_font = font_data_uri(BODY_TTF, body_text)

    morning = jpeg_data_uri(SRC / "siwoo-morning.jpg", 760)
    icons = {p["icon"]: png_data_uri(SRC / p["icon"], 128) for p in PRODUCTS}

    # lead lines must fit the column
    lead_lines = []
    for j, line in enumerate(LEAD):
        if body_m.width(line, 16.5) > COL_W:
            raise SystemExit(f"lead line {j + 1} is wider than {COL_W}px: rewrap it")
        lead_lines.append(f'<text x="{X0}" y="{288 + j * 23}" font-family="{BODY}" font-size="16.5" fill="{MUTED}">{escape(line)}</text>')
    lead_svg = "\n    ".join(lead_lines)

    # product cards
    text_w = COL_W - 92 - 22
    cards: list[str] = []
    clips: list[str] = []
    y = CARDS_Y
    for i, p in enumerate(PRODUCTS):
        desc_w = body_m.width(p["desc"], 13.5)
        if desc_w > text_w:
            raise SystemExit(f"{p['name']}: description is {desc_w:.0f}px, card text column is {text_w}px: shorten it")
        name_w = body_m.width(p["name"], 23) * 1.04  # bold runs a little wider than the default instance
        status_w = body_m.width(p["status"], 12.5) + 20
        sx = X0 + 92 + name_w + 12
        clips.append(f'<clipPath id="icon-{i}"><rect x="{X0 + 20}" y="{y + 28}" width="56" height="56" rx="14"/></clipPath>')
        cards.append(f'''<g class="card">
      <rect x="{X0}" y="{y + 2}" width="{COL_W}" height="{CARD_H}" rx="24" fill="{LINE}"/>
      <rect x="{X0}" y="{y}" width="{COL_W}" height="{CARD_H}" rx="24" fill="{SURFACE}" stroke="{LINE}"/>
      <image href="{icons[p['icon']]}" x="{X0 + 20}" y="{y + 28}" width="56" height="56" clip-path="url(#icon-{i})"/>
      <text x="{X0 + 92}" y="{y + 35}" font-family="{BODY}" font-weight="700" font-size="23" fill="{TEXT}">{escape(p['name'])}</text>
      <rect x="{sx:.0f}" y="{y + 18}" width="{status_w:.0f}" height="22" rx="11" fill="{PINK}"/>
      <text x="{sx + status_w / 2:.0f}" y="{y + 33.5}" text-anchor="middle" font-family="{BODY}" font-weight="600" font-size="12.5" fill="{PINK_INK}">{escape(p['status'])}</text>
      <text x="{X0 + 92}" y="{y + 57}" font-family="{BODY}" font-weight="600" font-size="15.5" fill="{TEXT}" opacity="0.85">{escape(p['tag'])}</text>
      <text x="{X0 + 92}" y="{y + 77}" font-family="{BODY}" font-size="13.5" fill="{MUTED}">{escape(p['desc'])}</text>
      <text x="{X0 + 92}" y="{y + 97}" font-family="{BODY}" font-size="12.5" fill="{FAINT}">{escape(p['platforms'])}</text>
    </g>''')
        y += CARD_H + CARD_GAP

    art_x = ART_X + ART_SHIFT
    hint_w = body_m.width(FOOTER_RIGHT, 13) + 28

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(TITLE)}</title>
  <desc id="desc">{escape(DESC)}</desc>

  <defs>
    <style>
      @font-face {{ font-family: 'XIU Hand'; src: url("{hand_font}") format("woff2"); font-weight: 400; }}
      @font-face {{ font-family: 'XIU Body'; src: url("{body_font}") format("woff2"); font-weight: 200 1000; }}
      text {{ -webkit-font-smoothing: antialiased; }}
      .tw {{ animation: twinkle 5s ease-in-out infinite; }}
      @keyframes twinkle {{
        0%, 100% {{ opacity: 0.15; }}
        50% {{ opacity: 0.9; }}
      }}
      .siwoo {{ transform-origin: {art_x + ART_H / 2:.0f}px {H}px; animation: breathe 10s ease-in-out infinite; }}
      @keyframes breathe {{
        0% {{ transform: scale(1, 1); }}
        40% {{ transform: scale(1.008, 1.012); }}
        100% {{ transform: scale(1, 1); }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .tw, .siwoo {{ animation: none; }}
      }}
    </style>

    <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{PAPER}"/>
      <stop offset="1" stop-color="{PAPER2}"/>
    </linearGradient>
    <radialGradient id="sun" cx="0.78" cy="0.08" r="0.6">
      <stop offset="0" stop-color="{SUN}" stop-opacity="0.9"/>
      <stop offset="0.5" stop-color="{SUN}" stop-opacity="0.35"/>
      <stop offset="1" stop-color="{SUN}" stop-opacity="0"/>
    </radialGradient>
    <!-- the picture fades in from the left so it melts into the paper -->
    <linearGradient id="art-fade" gradientUnits="userSpaceOnUse" x1="{ART_X}" y1="0" x2="{ART_X + FADE_W}" y2="0">
      <stop offset="0" stop-color="#000"/>
      <stop offset="0.35" stop-color="#555"/>
      <stop offset="1" stop-color="#fff"/>
    </linearGradient>
    <mask id="art-mask">
      <rect x="{ART_X}" y="0" width="{W - ART_X}" height="{H}" fill="url(#art-fade)"/>
    </mask>
    {"".join(clips)}
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="28"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <!-- paper and morning light -->
    <rect width="{W}" height="{H}" fill="url(#paper)"/>
    <rect width="{W}" height="{H}" fill="url(#sun)"/>

    <!-- XIU stretching awake by the window -->
    <g class="siwoo">
      <image href="{morning}" x="{art_x}" y="0" width="{ART_H}" height="{ART_H}" preserveAspectRatio="xMidYMid slice" mask="url(#art-mask)"/>
    </g>
    {sparkles_svg(rng)}

    <!-- identity -->
    <text x="{X0 - 4}" y="172" font-family="{HAND}" font-size="128" fill="{TEXT}">{WORDMARK}</text>
    <text x="{X0}" y="202" font-family="{BODY}" font-weight="600" font-size="15" letter-spacing="0.4" fill="{MUTED}">{escape(IDENTITY)}</text>
    <text x="{X0}" y="252" font-family="{HAND}" font-size="40" fill="{ROSE}">{escape(TAGLINE)}</text>
    {lead_svg}
    <text x="{X0}" y="{CARDS_Y - 14}" font-family="{BODY}" font-weight="700" font-size="13" letter-spacing="1.2" fill="{ROSE}">{escape(SECTION)}</text>

    <!-- products -->
    {"".join(cards)}

    <!-- footer -->
    <text x="{X0}" y="{H - 36}" font-family="{BODY}" font-weight="600" font-size="13" letter-spacing="0.3" fill="{FAINT}">{escape(FOOTER_LEFT)}</text>
    <rect x="{W - 72 - hint_w:.0f}" y="{H - 52}" width="{hint_w:.0f}" height="24" rx="12" fill="{SURFACE}" opacity="0.72"/>
    <text x="{W - 72 - hint_w / 2:.0f}" y="{H - 35.5}" text-anchor="middle" font-family="{BODY}" font-size="13" fill="{MUTED}">{escape(FOOTER_RIGHT)}</text>
  </g>

  <!-- frame hairline -->
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" stroke="{LINE}"/>
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
