"""Render quote reels for @jada.sach.bol.diya.kya.

Usage: python3 make_reels.py quotes.json reels/2026-10-07
quotes.json is a JSON list of strings. Writes 1.mp4, 2.mp4, ... (1080x1920, 8s, slow zoom, 18+ badge).
Hindi (Devanagari) text is detected automatically and rendered with FreeSans + RAQM shaping.
"""
import json, os, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
HINDI = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
HANDLE = "@jada.sach.bol.diya.kya"

THEMES = [
    ((18, 18, 24), (52, 30, 70), (255, 214, 102)),   # night purple / gold
    ((10, 25, 30), (20, 70, 75), (120, 240, 210)),   # deep teal / mint
    ((30, 12, 12), (90, 30, 30), (255, 170, 140)),   # oxblood / peach
    ((12, 12, 12), (45, 45, 45), (255, 90, 120)),    # charcoal / hot pink
]

def gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img

def render(quote, theme_idx, out_png):
    top, bottom, accent = THEMES[theme_idx % len(THEMES)]
    img = gradient(top, bottom)
    d = ImageDraw.Draw(img)
    if any("ऀ" <= ch <= "ॿ" for ch in quote):
        font = ImageFont.truetype(HINDI, 76, layout_engine=ImageFont.Layout.RAQM)
        lines, lh = textwrap.wrap(quote, width=22), 118
    else:
        font = ImageFont.truetype(SERIF, 74)
        lines, lh = textwrap.wrap(quote, width=20), 100
    y = H // 2 - len(lines) * lh // 2
    d.text((W // 2, y - 140), "“", font=ImageFont.truetype(SERIF, 200), fill=accent, anchor="mm")
    for ln in lines:
        d.text((W // 2, y), ln, font=font, fill=(245, 245, 245), anchor="mt")
        y += lh
    d.line([(W // 2 - 60, y + 40), (W // 2 + 60, y + 40)], fill=accent, width=5)
    d.text((W // 2, H - 260), HANDLE, font=ImageFont.truetype(SANS, 40), fill=(200, 200, 200), anchor="mm")
    d.rounded_rectangle([W - 210, 120, W - 70, 200], radius=40, outline=accent, width=4)
    d.text((W - 140, 160), "18+", font=ImageFont.truetype(SERIF, 44), fill=accent, anchor="mm")
    img.save(out_png)

def to_video(png, mp4, seconds=8):
    frames = seconds * 30
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png,
        "-vf", f"scale=2160:-1,zoompan=z='min(zoom+0.0006,1.08)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,fade=t=in:st=0:d=0.6",
        "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4,
    ], check=True)

if __name__ == "__main__":
    quotes = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    offset = sum(map(ord, out))  # vary colour themes day to day
    for i, q in enumerate(quotes, 1):
        png = f"/tmp/reel_{i}.png"
        render(q, offset + i, png)
        to_video(png, f"{out}/{i}.mp4")
        print(f"{out}/{i}.mp4")
