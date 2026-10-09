# Sources for the profile card

`scripts/build-hero.py` embeds everything here into `assets/readme-hero.svg`.

| File | From | Notes |
| --- | --- | --- |
| `siwoo-morning.jpg` | Bosong repo `design/widget/morning.png` | XIU stretching awake by a sunny window (Bosong's morning widget art), 1024 px, saved as JPEG to keep the repo small |
| `siwoo-rest-cushion.png` | Bosong repo `design/art/siwoo-rest-cushion.png` | XIU asleep on the mint cushion (Bosong's rest art), 640 px; kept for a night variant |
| `bosong-icon.png` | Bosong repo `apple/.../AppIcon.appiconset/icon-ios-1024.png` | Bosong app icon, 256 px |
| `livessh-icon.png` | XIUSoft repo `sites/livessh/assets/brand/livessh-icon-v2-512.png` | LiveSSH app icon, 256 px |
| `fonts/PatrickHand-Regular.ttf` | Google Fonts, SIL Open Font License (`fonts/OFL-PatrickHand.txt`) | Headings, the Bosong site's handwriting font |
| `fonts/Nunito-Variable.ttf` | Google Fonts, SIL Open Font License (`fonts/OFL-Nunito.txt`) | Body text, the Bosong site's body font |

The fonts are subset to the characters on the card at build time and inlined
as WOFF2, so the card looks the same on GitHub, which cannot load external
fonts into README images.
