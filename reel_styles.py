"""Premium animated quote reels for @jada.sach.bol.diya.kya.

Three styles:
  noir  - black + film grain, words fade up one by one, punchline in glowing gold serif
  neon  - drifting neon light blobs, bold lines slam in, punchline on a pink marker, Follow pill
  chat  - late-night chat screen, typing dots, setup as incoming message, punchline as reply

Usage (CLI):  python3 reel_styles.py <style> "<quote>" out.mp4
Library:      render(style, quote, out_mp4)
Hindi (Devanagari) is detected automatically and set in FreeSans/FreeSerif with proper shaping.
"""
import math, random, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 8.0
HANDLE = "@jada.sach.bol.diya.kya"

F = {
    "lora": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf",
    "lora_i": "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf",
    "inter_black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "inter_xb": "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf",
    "inter_md": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "inter_sb": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "poppins_b": "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "hi_sans": "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "hi_serif": "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "hi_serif_i": "/usr/share/fonts/truetype/freefont/FreeSerifBoldItalic.ttf",
    "emoji": "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
}


# ---------- helpers ----------
def is_hindi(s):
    return any("ऀ" <= c <= "ॿ" for c in s)


def font(key, size, variation=None):
    if key.startswith("hi_"):
        return ImageFont.truetype(F[key], size, layout_engine=ImageFont.Layout.RAQM)
    f = ImageFont.truetype(F[key], size)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            f.set_variation_by_name(variation.encode())
    return f


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_back(t, s=1.7):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def split_quote(q):
    """Split into (setup, punchline)."""
    q = q.strip()
    if "..." in q:
        i = q.rfind("...")
        a, b = q[: i + 3].strip(), q[i + 3 :].strip()
        if a and b:
            return a, b
    for sep in [" — ", " - "]:
        if sep in q:
            a, b = q.rsplit(sep, 1)
            return a.strip(), b.strip()
    parts = [p for p in re.split(r"(?<=[.?!।])\s+", q) if p]
    if len(parts) > 1:
        return " ".join(parts[:-1]), parts[-1]
    words = q.split()
    k = max(1, int(len(words) * 0.55))
    return " ".join(words[:k]), " ".join(words[k:])


def layout(text, fnt, maxw, lh, align="center", x0=W // 2):
    """Greedy word wrap. Returns list of (word, x, y_rel, width) and block height."""
    words = text.split()
    space = fnt.getlength(" ")
    lines, cur, curw = [], [], 0
    for w in words:
        ww = fnt.getlength(w)
        if cur and curw + space + ww > maxw:
            lines.append((cur, curw))
            cur, curw = [], 0
        curw = curw + (space if cur else 0) + ww
        cur.append((w, ww))
    if cur:
        lines.append((cur, curw))
    out = []
    for li, (ws, lw) in enumerate(lines):
        x = x0 - lw / 2 if align == "center" else x0
        for w, ww in ws:
            out.append((w, x, li * lh, ww, li))
            x += ww + space
    return out, len(lines) * lh, len(lines)


def emoji_img(ch, size):
    f = ImageFont.truetype(F["emoji"], 109)
    im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((70, 70), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox() or (0, 0, 140, 140))
    return im.resize((size, size), Image.LANCZOS)


def grain_layers(n=4, amount=18):
    rnd = random.Random(7)
    out = []
    for _ in range(n):
        small = Image.effect_noise((W // 2, H // 2), 60).resize((W, H))
        a = small.point(lambda v: int(abs(v - 128) / 128 * amount))
        g = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        g.putalpha(a)
        out.append(g)
    return out


def radial(size, inner, outer, center=None, radius=None):
    w, h = size
    small = Image.new("RGB", (w // 8, h // 8))
    cx, cy = (center or (w / 2, h / 2))
    cx, cy = cx / 8, cy / 8
    r = (radius or max(w, h) * 0.7) / 8
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            d = clamp(math.hypot(x - cx, y - cy) / r)
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * d) for i in range(3))
    return small.resize(size, Image.BICUBIC).convert("RGBA")


def blob(color, d=900):
    s = d // 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((s * 0.2, s * 0.2, s * 0.8, s * 0.8), fill=color + (200,))
    im = im.filter(ImageFilter.GaussianBlur(s * 0.12))
    return im.resize((d, d), Image.BICUBIC)


def soft_glow(layer, radius=14):
    small = layer.resize((W // 2, H // 2))
    return small.filter(ImageFilter.GaussianBlur(radius / 2)).resize((W, H))


class Encoder:
    def __init__(self, out):
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
             "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
            stdin=subprocess.PIPE)

    def write(self, im):
        self.p.stdin.write(im.convert("RGB").tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def word_timings(n, start, span, per=0.4):
    stagger = min(0.13, span / max(n, 1))
    return [start + i * stagger for i in range(n)], start + n * stagger + per


# ---------- style 1: NOIR GOLD ----------
GOLD, CREAM = (231, 194, 125), (243, 235, 221)


def render_noir(quote, out):
    setup, punch = split_quote(quote)
    hi = is_hindi(quote)
    fs = font("hi_serif", 80) if hi else font("lora", 78, "SemiBold")
    fp = font("hi_serif_i", 88) if hi else font("lora_i", 86, "Bold Italic")
    lhs, lhp = (118, 128) if hi else (108, 118)
    s_words, s_h, _ = layout(setup, fs, 860, lhs)
    p_words, p_h, _ = layout(punch, fp, 860, lhp)
    gap = 70
    top = 940 - (s_h + gap + p_h) / 2
    s_t, s_end = word_timings(len(s_words), 0.35, 2.2)
    p_t, p_end = word_timings(len(p_words), s_end + 0.45, 1.4, 0.5)

    base = radial((W, H), (46, 34, 20), (8, 7, 6), center=(W / 2, 900), radius=1300)
    grain = grain_layers()
    label_f = font("inter_md", 28)
    small_f = font("inter_md", 34)
    badge_f = font("inter_sb", 30)
    enc = Encoder(out)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = base.copy()
        # breathing warm glow
        glow_a = int(28 + 18 * math.sin(t * 1.4))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((140, 520, 940, 1320), fill=GOLD + (glow_a,))
        im.alpha_composite(glow.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(40)).resize((W, H)))

        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # frame draw-on
        k = ease_out(t / 0.9)
        m = 64
        for (x1, y1, x2, y2) in [(m, m, m + (W - 2 * m) * k, m), (W - m, H - m, W - m - (W - 2 * m) * k, H - m)]:
            d.line((x1, y1, x2, y2), fill=GOLD + (150,), width=2)
        for (x1, y1, x2, y2) in [(m, m, m, m + (H - 2 * m) * k), (W - m, H - m, W - m, H - m - (H - 2 * m) * k)]:
            d.line((x1, y1, x2, y2), fill=GOLD + (150,), width=2)
        # header
        a = int(255 * ease_out(t / 0.6))
        label = "  ".join("JADA SACH BOL DIYA KYA")
        d.text((W // 2, 200), "J A D A   S A C H   B O L   D I Y A   K Y A", font=label_f, fill=GOLD + (a,), anchor="mm")
        d.line((W // 2 - 50, 245, W // 2 + 50, 245), fill=GOLD + (a,), width=2)
        d.rounded_rectangle((W - m - 130, m + 40, W - m - 30, m + 96), radius=28, outline=GOLD + (a,), width=2)
        d.text((W - m - 80, m + 68), "18+", font=badge_f, fill=GOLD + (a,), anchor="mm")
        # setup words
        for (w, x, yr, ww, li), st in zip(s_words, s_t):
            p = ease_out((t - st) / 0.45)
            if p <= 0:
                continue
            d.text((x, top + yr + 26 * (1 - p)), w, font=fs, fill=CREAM + (int(255 * p),))
        # punch words (+ glow layer)
        pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pl)
        py = top + s_h + gap
        for (w, x, yr, ww, li), st in zip(p_words, p_t):
            p = ease_out((t - st) / 0.5)
            if p <= 0:
                continue
            pd.text((x, py + yr + 30 * (1 - p)), w, font=fp, fill=GOLD + (int(255 * p),))
        if t > p_t[0]:
            ov.alpha_composite(soft_glow(pl, 18))
        ov.alpha_composite(pl)
        # divider before punch
        dp = ease_out((t - (p_t[0] - 0.3)) / 0.5)
        if dp > 0:
            d.line((W / 2 - 70 * dp, py - gap / 2, W / 2 + 70 * dp, py - gap / 2), fill=GOLD + (200,), width=3)
        # CTA
        c = ease_out((t - max(p_end, 5.2)) / 0.6)
        if c > 0:
            d.text((W // 2, H - 250 + 20 * (1 - c)), "Follow for daily 18+ sarcasm", font=small_f, fill=CREAM + (int(200 * c),), anchor="mm")
            d.text((W // 2, H - 195 + 20 * (1 - c)), HANDLE, font=label_f, fill=GOLD + (int(230 * c),), anchor="mm")
        # progress line
        d.line((m, H - m - 30, m + (W - 2 * m) * (t / DUR), H - m - 30), fill=GOLD + (120,), width=3)
        im.alpha_composite(ov)
        im.alpha_composite(grain[fi % len(grain)])
        enc.write(im)
    enc.close()


# ---------- style 2: NEON PULSE ----------
PINK, VIOLET, ORANGE = (255, 46, 136), (123, 44, 255), (255, 122, 69)


def render_neon(quote, out):
    setup, punch = split_quote(quote)
    hi = is_hindi(quote)
    fs = font("hi_sans", 92) if hi else font("inter_black", 92)
    fp = font("hi_sans", 96) if hi else font("inter_black", 96)
    lh = 126 if hi else 112
    s_words, s_h, s_lines = layout(setup, fs, 900, lh)
    p_words, p_h, p_lines = layout(punch, fp, 860, lh + 14)
    gap = 60
    top = 930 - (s_h + gap + p_h) / 2
    blobs = [(blob(PINK), 0.0), (blob(VIOLET), 2.1), (blob(ORANGE), 4.2)]
    grain = grain_layers(amount=10)
    pill_f, handle_f, btn_f = font("inter_xb", 34), font("inter_sb", 38), font("inter_xb", 34)
    enc = Encoder(out)
    line_start = [0.3 + i * 0.28 for i in range(s_lines)]
    p_start = (line_start[-1] if line_start else 0.3) + 0.8
    p_line_start = [p_start + i * 0.28 for i in range(p_lines)]
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = Image.new("RGBA", (W, H), (13, 6, 20, 255))
        for i, (b, ph) in enumerate(blobs):
            x = W / 2 - 450 + 330 * math.sin(t * 0.55 + ph) + (i - 1) * 120
            y = 700 + i * 380 + 220 * math.cos(t * 0.45 + ph * 1.3)
            im.alpha_composite(b, (int(x), int(y) - 450))
        dim = Image.new("RGBA", (W, H), (8, 3, 14, 60))
        im.alpha_composite(dim)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # pulsing 18+ pill
        s = 1 + 0.04 * math.sin(t * 5)
        pw, ph_ = 250 * s, 74 * s
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((W / 2 - pw / 2, 210 - ph_ / 2, W / 2 + pw / 2, 210 + ph_ / 2), radius=40, fill=PINK + (200,))
        ov.alpha_composite(soft_glow(glow, 30))
        d.rounded_rectangle((W / 2 - pw / 2, 210 - ph_ / 2, W / 2 + pw / 2, 210 + ph_ / 2), radius=40, fill=PINK + (255,))
        d.text((W / 2, 210), "18+ ONLY", font=pill_f, fill=(255, 255, 255), anchor="mm")
        # setup lines slam in
        for (w, x, yr, ww, li) in s_words:
            p = (t - line_start[li]) / 0.45
            if p <= 0:
                continue
            k = ease_back(p)
            sc = 1.35 - 0.35 * k
            a = int(255 * clamp(p * 2.5))
            cx, cy = W / 2, top + yr + lh / 2
            nx = cx + (x - cx) * sc
            ny = cy + (top + yr - cy) * sc
            fsz = fs if sc == 1 else fs.font_variant(size=max(10, int(fs.size * sc)))
            d.text((nx, ny), w, font=fsz, fill=(255, 255, 255, a))
        # punchline marker + text
        py = top + s_h + gap
        lines = {}
        for (w, x, yr, ww, li) in p_words:
            l = lines.setdefault(li, [x, x + ww, yr])
            l[0], l[1] = min(l[0], x), max(l[1], x + ww)
        for li, (x1, x2, yr) in lines.items():
            m = ease_out((t - p_line_start[li]) / 0.4)
            if m <= 0:
                continue
            d.rounded_rectangle((x1 - 22, py + yr - 6, x1 - 22 + (x2 - x1 + 44) * m, py + yr + lh + 6), radius=18, fill=PINK + (235,))
        for (w, x, yr, ww, li) in p_words:
            a = clamp((t - p_line_start[li] - 0.2) / 0.25)
            if a > 0:
                d.text((x, py + yr + 4), w, font=fp, fill=(255, 255, 255, int(255 * a)))
        # handle + follow pill pops
        c = (t - max(p_line_start[-1] + 0.9, 5.0)) / 0.5
        if c > 0:
            k = ease_back(c)
            a = int(255 * clamp(c * 2))
            y = H - 380
            hw = handle_f.getlength(HANDLE)
            gx = W / 2 - (hw + 100) / 2
            d.ellipse((gx, y - 40, gx + 80, y + 40), fill=PINK + (a,))
            d.text((gx + 40, y), "J", font=btn_f, fill=(255, 255, 255, a), anchor="mm")
            d.text((gx + 100, y), HANDLE, font=handle_f, fill=(255, 255, 255, a), anchor="lm")
            bw, bh = 300 * k, 84 * k
            by = y + 120
            d.rounded_rectangle((W / 2 - bw / 2, by - bh / 2, W / 2 + bw / 2, by + bh / 2), radius=42, fill=(255, 255, 255))
            if k > 0.6:
                d.text((W / 2, by), "+ FOLLOW", font=btn_f.font_variant(size=max(10, int(36 * k))), fill=PINK, anchor="mm")
        im.alpha_composite(ov)
        im.alpha_composite(grain[fi % len(grain)])
        enc.write(im)
    enc.close()


# ---------- style 3: 2 AM CHAT ----------
def render_chat(quote, out):
    setup, punch = split_quote(quote)
    hi = is_hindi(quote)
    fb = font("hi_sans", 56) if hi else font("inter_md", 54)
    lh = 80 if hi else 72
    maxw = 700
    bubbles = [("in", setup, 0.5), ("out", punch, 0.0)]
    # layout bubbles
    lay = []
    for side, txt, _ in bubbles:
        words, bh, nl = layout(txt, fb, maxw, lh, align="left", x0=0)
        wmax = max((x + ww for (w, x, yr, ww, li) in words), default=0)
        lay.append((side, words, wmax + 76, bh + 56))
    y_in = 620
    y_out = y_in + lay[0][3] + 110
    t_type1, t_msg1 = 0.4, 1.5
    t_type2 = t_msg1 + 0.9
    t_msg2 = t_type2 + 1.4
    t_react = t_msg2 + 0.9
    base = Image.new("RGBA", (W, H), (11, 12, 16, 255))
    hg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(hg)
    for y in range(0, 520):
        a = int(70 * (1 - y / 520) ** 2)
        bd.line((0, y, W, y), fill=(120, 80, 255, a))
    base.alpha_composite(hg)
    hdr_f, sub_f, time_f, tick_f, cta_f = font("inter_sb", 44), font("inter_md", 30), font("inter_md", 28), font("inter_md", 26), font("inter_sb", 36)
    avatar = emoji_img("😈", 70)
    react = emoji_img("😏", 86)
    fire = emoji_img("🔥", 60)
    enc = Encoder(out)
    grad = Image.linear_gradient("L").rotate(90).resize((maxw + 120, 400))
    out_fill = Image.merge("RGBA", (
        grad.point(lambda v: int(108 + (168 - 108) * v / 255)),
        grad.point(lambda v: int(92 + (85 - 92) * v / 255)),
        grad.point(lambda v: int(231 + (247 - 231) * v / 255)),
        Image.new("L", grad.size, 255)))

    def bubble(ov, side, words, bw, bh, y, p):
        k = ease_back(p)
        if k <= 0:
            return
        x = 70 if side == "in" else W - 70 - bw
        layer = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        if side == "in":
            ld.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=42, fill=(38, 42, 51, 255))
        else:
            mask = Image.new("L", layer.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=42, fill=255)
            layer.paste(out_fill.crop((0, 0, int(bw), int(bh))), (0, 0), mask)
            ld = ImageDraw.Draw(layer)
        for (w, wx, yr, ww, li) in words:
            ld.text((38 + wx, 26 + yr), w, font=fb, fill=(255, 255, 255))
        sc = max(0.05, k)
        lw, lh_ = max(1, int(bw * sc)), max(1, int(bh * sc))
        layer = layer.resize((lw, lh_))
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * clamp(p * 3))))
        ox = x if side == "in" else x + bw - lw
        ov.alpha_composite(layer, (int(ox), int(y + bh - lh_)))

    def typing(ov, side, y, t0, t1, t):
        if not (t0 <= t < t1):
            return
        d = ImageDraw.Draw(ov)
        x = 70 if side == "in" else W - 70 - 190
        d.rounded_rectangle((x, y, x + 190, y + 110), radius=55, fill=(38, 42, 51) if side == "in" else (108, 92, 231))
        for i in range(3):
            bounce = max(0, math.sin((t - t0) * 9 - i * 0.9))
            d.ellipse((x + 45 + i * 40 - 11, y + 55 - 11 - 14 * bounce, x + 45 + i * 40 + 11, y + 55 + 11 - 14 * bounce), fill=(200, 200, 210))

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = base.copy()
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # header
        d.line((0, 330, W, 330), fill=(255, 255, 255, 25), width=2)
        d.text((70, 250), "‹", font=font("inter_md", 80), fill=(180, 160, 255), anchor="lm")
        d.ellipse((130, 200, 230, 300), fill=(60, 40, 110))
        ov.alpha_composite(avatar, (145, 215))
        d.text((255, 228), "Unknown Number", font=hdr_f, fill=(255, 255, 255), anchor="lm")
        typing_now = (t_type1 <= t < t_msg1)
        status = "typing..." if typing_now else "online"
        d.text((255, 280), status, font=sub_f, fill=(140, 220, 160) if typing_now else (150, 150, 165), anchor="lm")
        d.rounded_rectangle((W - 190, 222, W - 70, 278), radius=28, outline=(255, 70, 140), width=3)
        d.text((W - 130, 250), "18+", font=font("inter_xb", 30), fill=(255, 70, 140), anchor="mm")
        # time chip
        d.rounded_rectangle((W / 2 - 110, 430, W / 2 + 110, 490), radius=30, fill=(255, 255, 255, 18))
        d.text((W / 2, 460), "2:14 AM", font=time_f, fill=(170, 170, 185), anchor="mm")
        # messages
        side, words, bw, bh = lay[0]
        typing(ov, "in", y_in + bh - 110, t_type1, t_msg1, t)
        bubble(ov, side, words, bw, bh, y_in, (t - t_msg1) / 0.45)
        side2, words2, bw2, bh2 = lay[1]
        typing(ov, "out", y_out + bh2 - 110, t_type2, t_msg2, t)
        bubble(ov, side2, words2, bw2, bh2, y_out, (t - t_msg2) / 0.45)
        if t > t_msg2 + 0.3:
            a = int(255 * clamp((t - t_msg2 - 0.3) / 0.3))
            d.text((W - 70, y_out + bh2 + 36), "Seen ✓✓", font=tick_f, fill=(150, 150, 165, a), anchor="rm")
        r = (t - t_react) / 0.4
        if r > 0:
            k = ease_back(r, 3)
            sz = max(1, int(86 * k))
            ov.alpha_composite(react.resize((sz, sz)), (int(W - 70 - bw2 - sz / 2 + 10), int(y_out + bh2 - sz / 2)))
        # CTA
        c = (t - max(t_react + 0.5, 5.6)) / 0.5
        if c > 0:
            a = int(255 * clamp(c))
            yy = H - 300 + 20 * (1 - ease_out(c))
            d.rounded_rectangle((W / 2 - 400, yy - 60, W / 2 + 400, yy + 60), radius=60, fill=(255, 255, 255, int(a * 0.08)), outline=(255, 255, 255, int(a * 0.25)), width=2)
            d.text((W / 2 + 30, yy), f"Follow {HANDLE}", font=cta_f, fill=(255, 255, 255, a), anchor="mm")
            ov.alpha_composite(fire.resize((48, 48)), (int(W / 2 - 360), int(yy - 24)))
        im.alpha_composite(ov)
        enc.write(im)
    enc.close()


STYLES = {"noir": render_noir, "neon": render_neon, "chat": render_chat}


def render(style, quote, out):
    STYLES[style](quote, out)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3])
