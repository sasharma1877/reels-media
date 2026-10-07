"""Trend-based reel styles (v2) for @jada.sach.bol.diya.kya.

  glass    - chat bubbles (frosted glass) over drifting night-city bokeh
  yellow   - "yellow font confession": big yellow outlined text, word-by-word, over bokeh
  notes    - notes-app screen, joke typed out with a blinking cursor
  tweet    - viral tweet card, metrics counting up, heart pops
  vhs      - retro camcorder: REC, scanlines, RGB-split text, glitch burst on the punchline

CLI: python3 reel_styles2.py <style> "<text>" out.mp4   (newlines = separate chat messages)
"""
import math, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import reel_styles as rs
from reel_styles import (W, H, FPS, HANDLE, font, is_hindi, layout, ease_out, ease_back, clamp,
                         split_quote, emoji_img, Encoder, chat_messages, draw_rich, text_len, EMOJI_RE)

DUR = 8.0


def two_parts(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 2:
        return " ".join(lines[:-1]), lines[-1]
    return split_quote(text)


def f_for(text, key, size, hi_key="hi_sans"):
    return font(hi_key, size) if is_hindi(text) else font(key, size)


# ---------------- animated bokeh background ----------------
class Bokeh:
    def __init__(self, seed=3, palette=None, n=34, base=(8, 8, 14)):
        r = random.Random(seed)
        self.palette = palette or [(255, 170, 70), (255, 90, 140), (150, 90, 255), (90, 160, 255), (255, 220, 150)]
        self.base = base
        self.c = [dict(x=r.uniform(0, 270), y=r.uniform(0, 480), rad=r.uniform(6, 30), col=r.choice(self.palette),
                       a=r.randint(60, 150), sp=r.uniform(0.2, 0.6), ph=r.uniform(0, 6.28), vy=r.uniform(2, 7))
                  for _ in range(n)]
        vig = Image.new("L", (270, 480), 0)
        ImageDraw.Draw(vig).ellipse((-60, -40, 330, 520), fill=255)
        self.vig = vig.filter(ImageFilter.GaussianBlur(60)).resize((W, H))

    def frame(self, t):
        im = Image.new("RGBA", (270, 480), self.base + (255,))
        for c in self.c:
            x = c["x"] + 10 * math.sin(t * c["sp"] + c["ph"])
            y = (c["y"] - t * c["vy"]) % 520 - 20
            rad = c["rad"] * (1 + 0.08 * math.sin(t * 1.3 + c["ph"]))
            a = int(c["a"] * (0.75 + 0.25 * math.sin(t * 0.9 + c["ph"] * 2)))
            lay = Image.new("RGBA", (270, 480), (0, 0, 0, 0))
            ImageDraw.Draw(lay).ellipse((x - rad, y - rad, x + rad, y + rad), fill=c["col"] + (a,))
            im.alpha_composite(lay)
        im = im.filter(ImageFilter.GaussianBlur(3.5)).resize((W, H), Image.BICUBIC)
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        dark.putalpha(self.vig.point(lambda v: 255 - int(v * 0.75)))
        im.alpha_composite(dark)
        return im


# ---------------- 1. GLASS CHAT ----------------
def render_glass(text, out):
    msgs = chat_messages(text)
    bok = Bokeh(seed=5)
    maxw = 700
    for scale in [1.0, 0.9, 0.82, 0.75]:
        lay = []
        for side, txt in msgs:
            fb = f_for(txt, "inter_md", int(54 * scale))
            lh = int((80 if is_hindi(txt) else 72) * scale)
            words, bh, _ = layout(txt, fb, maxw, lh, align="left", x0=0)
            wmax = max((x + ww for (w, x, yr, ww, li) in words), default=0)
            lay.append((side, words, wmax + 76, bh + int(56 * scale), fb))
        gap = 60 if len(msgs) > 2 else 100
        total = sum(l[3] for l in lay) + gap * (len(lay) - 1)
        if 600 + total <= 1470:
            break
    ys, y = [], max(560, 1010 - total / 2)
    for l in lay:
        ys.append(y)
        y += l[3] + gap
    times, t = [], 0.4
    for i, (side, txt) in enumerate(msgs):
        typ = 1.0 if i == 0 else 0.8
        times.append((t, t + typ))
        t += typ + max(0.5, min(1.6, 0.13 * len(txt.split())))
    t_last = times[-1][1]
    dur = max(DUR, t_last + 3.2)
    hdr_f, sub_f, time_f, cta_f, back_f, badge_f = (font("inter_sb", 44), font("inter_md", 30), font("inter_md", 28),
                                                    font("inter_sb", 36), font("inter_md", 80), font("inter_xb", 30))
    avatar, react, fire = emoji_img("😈", 70), emoji_img("🫦", 86), emoji_img("🔥", 48)

    def bubble_img(i):
        side, words, bw, bh, fb = lay[i]
        im = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if side == "in":
            d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=42, fill=(255, 255, 255, 40), outline=(255, 255, 255, 90), width=2)
        else:
            d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=42, fill=(255, 70, 140, 215), outline=(255, 160, 200, 160), width=2)
        pad = int((bh - (max(yr for (_, _, yr, _, _) in words) + fb.size * 1.25)) / 2)
        for (w, wx, yr, ww, li) in words:
            draw_rich(im, d, (38 + wx, pad + yr), w, fb, (255, 255, 255, 255))
        return im

    bimgs = [bubble_img(i) for i in range(len(lay))]
    enc = Encoder(out)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        im = bok.frame(t)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.rounded_rectangle((40, 170, W - 40, 330), radius=48, fill=(255, 255, 255, 28), outline=(255, 255, 255, 60), width=2)
        d.text((85, 250), "‹", font=back_f, fill=(255, 255, 255), anchor="lm")
        d.ellipse((140, 200, 240, 300), fill=(255, 255, 255, 40))
        ov.alpha_composite(avatar, (155, 215))
        d.text((265, 228), "Unknown Number", font=hdr_f, fill=(255, 255, 255), anchor="lm")
        typing_now = any(t0 <= t < t1 and msgs[i][0] == "in" for i, (t0, t1) in enumerate(times))
        d.text((265, 280), "typing..." if typing_now else "online", font=sub_f,
               fill=(140, 240, 170) if typing_now else (220, 220, 230), anchor="lm")
        d.rounded_rectangle((W - 200, 222, W - 80, 278), radius=28, fill=(255, 70, 140))
        d.text((W - 140, 250), "18+", font=badge_f, fill=(255, 255, 255), anchor="mm")
        d.rounded_rectangle((W / 2 - 110, 420, W / 2 + 110, 480), radius=30, fill=(255, 255, 255, 30))
        d.text((W / 2, 450), "2:14 AM", font=time_f, fill=(235, 235, 245), anchor="mm")
        for i, (t0, t1) in enumerate(times):
            side, words, bw, bh, fb = lay[i]
            x = 70 if side == "in" else W - 70 - bw
            if t0 <= t < t1:
                tx = 70 if side == "in" else W - 70 - 190
                ty = ys[i] + max(0, bh - 110)
                d.rounded_rectangle((tx, ty, tx + 190, ty + 110), radius=55, fill=(255, 255, 255, 40) if side == "in" else (255, 70, 140, 200))
                for k in range(3):
                    b = max(0, math.sin((t - t0) * 9 - k * 0.9))
                    d.ellipse((tx + 34 + k * 40, ty + 44 - 14 * b, tx + 56 + k * 40, ty + 66 - 14 * b), fill=(255, 255, 255))
            p = (t - t1) / 0.45
            if p > 0:
                k = max(0.05, ease_back(p))
                img = bimgs[i].resize((max(1, int(bw * k)), max(1, int(bh * k))))
                img.putalpha(img.getchannel("A").point(lambda v: int(v * clamp(p * 3))))
                ox = x if side == "in" else x + bw - img.width
                ov.alpha_composite(img, (int(ox), int(ys[i] + bh - img.height)))
        side, words, bw, bh, fb = lay[-1]
        r = (t - t_last - 0.8) / 0.4
        if r > 0:
            sz = max(1, int(86 * ease_back(r, 3)))
            rx = W - 70 - bw - sz / 2 + 10 if side == "out" else 70 + bw - sz / 2 - 10
            ov.alpha_composite(react.resize((sz, sz)), (int(rx), int(ys[-1] + bh - sz / 2)))
        c = (t - max(t_last + 1.3, dur - 2.4)) / 0.5
        if c > 0:
            a = clamp(c)
            yy = H - 300 + 20 * (1 - ease_out(c))
            d.rounded_rectangle((W / 2 - 400, yy - 60, W / 2 + 400, yy + 60), radius=60, fill=(255, 255, 255, int(40 * a)), outline=(255, 255, 255, int(90 * a)), width=2)
            d.text((W / 2 + 30, yy), f"Follow {HANDLE}", font=cta_f, fill=(255, 255, 255, int(255 * a)), anchor="mm")
            ov.alpha_composite(fire, (int(W / 2 - 355), int(yy - 24)))
        im.alpha_composite(ov)
        enc.write(im)
    enc.close()


# ---------------- 2. YELLOW CONFESSION ----------------
YEL = (255, 230, 0)


def render_yellow(text, out):
    setup, punch = two_parts(text)
    bok = Bokeh(seed=11, palette=[(255, 180, 80), (255, 140, 60), (255, 230, 160), (120, 140, 255)], base=(6, 6, 10))
    fs = f_for(setup, "inter_black", 84)
    fp = f_for(punch, "inter_black", 92)
    sw, sh, _ = layout(setup, fs, 900, 112 if not is_hindi(setup) else 124)
    pw, ph, _ = layout(punch, fp, 900, 120 if not is_hindi(punch) else 132)
    gap = 80
    top = 930 - (sh + gap + ph) / 2
    words = [(w, x, top + yr, fs, (255, 255, 255)) for (w, x, yr, ww, li) in sw]
    words += [(w, x, top + sh + gap + yr, fp, YEL) for (w, x, yr, ww, li) in pw]
    starts, t = [], 0.35
    for i, wd in enumerate(words):
        if i == len(sw):
            t += 0.7
        starts.append(t)
        t += 0.16 if i < len(sw) else 0.2
    t_end = t
    small = font("inter_sb", 34)
    enc = Encoder(out)
    for fi in range(int(DUR * FPS)):
        tt = fi / FPS
        im = bok.frame(tt)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.text((W / 2, 230), "sach bolu toh... 🌚".replace(" 🌚", ""), font=small, fill=(255, 255, 255, 170), anchor="mm")
        d.rounded_rectangle((W / 2 - 60, 270, W / 2 + 60, 316), radius=23, outline=YEL, width=3)
        d.text((W / 2, 293), "18+", font=font("inter_xb", 26), fill=YEL, anchor="mm")
        for (w, x, y, f, col), st in zip(words, starts):
            p = (tt - st) / 0.28
            if p <= 0:
                continue
            k = ease_back(p, 2.2)
            sc = 0.6 + 0.4 * k
            fz = f.font_variant(size=max(8, int(f.size * sc))) if sc < 0.999 else f
            ww = text_len(w, f)
            cx = x + ww / 2
            if EMOJI_RE.search(w):
                wz = text_len(w, fz)
                draw_rich(ov, d, (cx - wz / 2, y + f.size * 0.6 - fz.size * 0.62), w, fz, col + (int(255 * clamp(p * 3)),),
                          stroke_width=max(1, int(7 * sc)), stroke_fill=(0, 0, 0, int(255 * clamp(p * 3))))
            else:
                d.text((cx, y + f.size * 0.6), w, font=fz, fill=col + (int(255 * clamp(p * 3)),), anchor="mm",
                       stroke_width=max(1, int(7 * sc)), stroke_fill=(0, 0, 0, int(255 * clamp(p * 3))))
        c = (tt - max(t_end + 0.8, 5.6)) / 0.5
        if c > 0:
            d.text((W / 2, H - 280), f"follow {HANDLE} for more", font=small, fill=(255, 255, 255, int(220 * clamp(c))), anchor="mm",
                   stroke_width=3, stroke_fill=(0, 0, 0, int(220 * clamp(c))))
        im.alpha_composite(ov)
        enc.write(im)
    enc.close()


# ---------------- 3. NOTES APP ----------------
AMBER = (232, 162, 20)


def render_notes(text, out):
    setup, punch = two_parts(text)
    paper = Image.new("RGBA", (W, H), (252, 250, 243, 255))
    pd = ImageDraw.Draw(paper)
    for y in range(640, H - 360, 92):
        pd.line((70, y + 74, W - 70, y + 74), fill=(232, 226, 210), width=2)
    nav_f, title_f, date_f = font("inter_md", 44), font("inter_xb", 64), font("inter_md", 32)
    fb_s = f_for(setup, "inter_md", 58)
    fb_p = f_for(punch, "inter_xb", 60)
    s_lines = layout(setup, fb_s, 930, 92, align="left", x0=75)
    p_lines = layout(punch, fb_p, 930, 92, align="left", x0=75)
    moon = emoji_img("🌚", 64)
    enc = Encoder(out)
    chars_s, chars_p = len(setup), len(punch)
    t_s0, cps = 0.6, 22
    t_s1 = t_s0 + chars_s / cps
    t_p0 = t_s1 + 0.9
    t_p1 = t_p0 + chars_p / (cps * 0.8)

    def draw_typed(d, lines_info, frac_chars, y0, f, col):
        words, bh, _ = lines_info
        shown = frac_chars
        cur = None
        for (w, x, yr, ww, li) in words:
            if shown <= 0:
                break
            part = w[: int(shown)]
            draw_rich(im, d, (x, y0 + yr), part, f, col + (255,))
            cur = (x + text_len(part, f), y0 + yr)
            shown -= len(w) + 1
        return cur

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = paper.copy()
        d = ImageDraw.Draw(im)
        d.text((60, 150), "‹ Notes", font=nav_f, fill=AMBER, anchor="lm")
        d.text((W - 60, 150), "Done", font=font("inter_sb", 44), fill=AMBER, anchor="rm")
        d.text((W / 2, 300), "Today at 2:14 AM", font=date_f, fill=(150, 145, 135), anchor="mm")
        d.text((75, 420), "things i'll never say out loud", font=title_f.font_variant(size=56), fill=(30, 28, 25), anchor="lm")
        im.alpha_composite(moon, (75, 480))
        d.rounded_rectangle((160, 488, 260, 540), radius=26, outline=(255, 70, 140), width=3)
        d.text((210, 514), "18+", font=font("inter_xb", 26), fill=(255, 70, 140), anchor="mm")
        ns = clamp((t - t_s0) / (t_s1 - t_s0)) * (chars_s + 1)
        cur = draw_typed(d, s_lines, ns, 640, fb_s, (40, 38, 35))
        py = 640 + s_lines[1] + 50
        if t >= t_p0:
            np_ = clamp((t - t_p0) / (t_p1 - t_p0)) * (chars_p + 1)
            c2 = draw_typed(d, p_lines, np_, py, fb_p, (20, 18, 15))
            cur = c2 or cur
            if t > t_p1:
                hl = clamp((t - t_p1) / 0.5)
                for (w, x, yr, ww, li) in p_lines[0]:
                    pass
        if cur and int(t * 2.2) % 2 == 0:
            d.rectangle((cur[0] + 4, cur[1] + 6, cur[0] + 9, cur[1] + 72), fill=AMBER)
        c = (t - max(t_p1 + 0.8, 5.8)) / 0.5
        if c > 0:
            d.text((W / 2, H - 260), HANDLE, font=font("inter_sb", 36), fill=(150, 145, 135, int(255 * clamp(c))), anchor="mm")
        enc.write(im)
    enc.close()


# ---------------- 4. TWEET CARD ----------------
def fmt_k(n):
    return f"{n/1000:.1f}K" if n >= 1000 else str(int(n))


def render_tweet(text, out):
    setup, punch = two_parts(text)
    bok = Bokeh(seed=21, palette=[(90, 120, 255), (150, 90, 255), (60, 200, 255), (255, 90, 160)], base=(5, 6, 14))
    body = setup + "\n" + punch
    fb = f_for(body, "inter_md", 52)
    fb_p = f_for(punch, "inter_sb", 52)
    s_lines = layout(setup, fb, 860, 74, align="left", x0=0)
    p_lines = layout(punch, fb_p, 860, 74, align="left", x0=0)
    card_h = 240 + s_lines[1] + 40 + p_lines[1] + 230
    cx0, cw = 70, W - 140
    cy0 = (H - card_h) / 2 - 40
    name_f, handle_f, meta_f, num_f = font("inter_xb", 44), font("inter_md", 36), font("inter_md", 32), font("inter_sb", 34)
    targets = (1240, 8400, 47900)
    heart = emoji_img("❤️", 44)
    enc = Encoder(out)
    t_card, t_s, t_p = 0.2, 0.9, 2.6
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = bok.frame(t)
        p = ease_back((t - t_card) / 0.6, 1.3)
        if p > 0:
            card = Image.new("RGBA", (cw, int(card_h)), (0, 0, 0, 0))
            d = ImageDraw.Draw(card)
            d.rounded_rectangle((0, 0, cw - 1, card_h - 1), radius=44, fill=(18, 20, 26, 245), outline=(255, 255, 255, 30), width=2)
            d.ellipse((50, 55, 160, 165), fill=(255, 70, 140))
            d.text((105, 110), "J", font=font("inter_black", 56), fill=(255, 255, 255), anchor="mm")
            d.text((190, 88), "Jada Sach Bol Diya Kya", font=name_f, fill=(255, 255, 255), anchor="lm")
            d.text((190, 138), "@jada.sach.bol.diya.kya", font=handle_f, fill=(140, 145, 160), anchor="lm")
            d.rounded_rectangle((cw - 160, 70, cw - 50, 120), radius=25, outline=(255, 70, 140), width=3)
            d.text((cw - 105, 95), "18+", font=font("inter_xb", 26), fill=(255, 70, 140), anchor="mm")
            y = 220
            a_s = clamp((t - t_s) / 0.4)
            for (w, x, yr, ww, li) in s_lines[0]:
                draw_rich(card, d, (50 + x, y + yr), w, fb, (235, 235, 240, int(255 * a_s)))
            y += s_lines[1] + 40
            a_p = clamp((t - t_p) / 0.35)
            for (w, x, yr, ww, li) in p_lines[0]:
                draw_rich(card, d, (50 + x, y + yr + 20 * (1 - a_p)), w, fb_p, (255, 255, 255, int(255 * a_p)))
            y += p_lines[1] + 50
            d.text((50, y), "2:14 AM · Oct 6, 2026", font=meta_f, fill=(140, 145, 160))
            d.line((50, y + 70, cw - 50, y + 70), fill=(255, 255, 255, 30), width=2)
            g = clamp((t - (t_p + 0.4)) / 2.2)
            g = 1 - (1 - g) ** 3
            labels = ["replies", "reposts", "likes"]
            for i, (tg, lb) in enumerate(zip(targets, labels)):
                xx = 50 + i * 255
                d.text((xx, y + 125), fmt_k(tg * g), font=num_f, fill=(255, 255, 255), anchor="lm")
                d.text((xx + num_f.getlength(fmt_k(tg * g)) + 12, y + 125), lb, font=meta_f, fill=(140, 145, 160), anchor="lm")
            hp = (t - (t_p + 2.0)) / 0.35
            if hp > 0:
                sz = max(1, int(70 * ease_back(hp, 3)))
                card.alpha_composite(heart.resize((sz, sz)), (int(cw - 85 - sz / 2), int(y + 125 - sz / 2)))
            sc = 0.85 + 0.15 * p
            card2 = card.resize((max(1, int(cw * sc)), max(1, int(card_h * sc))))
            card2.putalpha(card2.getchannel("A").point(lambda v: int(v * clamp(p * 2))))
            im.alpha_composite(card2, (int(W / 2 - card2.width / 2), int(cy0 + 120 * (1 - p) + (card_h - card2.height) / 2)))
        c = (t - 6.0) / 0.5
        if c > 0:
            d2 = ImageDraw.Draw(im)
            d2.text((W / 2, H - 230), "follow for daily 2 AM thoughts 🌚".replace(" 🌚", ""), font=font("inter_sb", 36),
                    fill=(255, 255, 255, int(220 * clamp(c))), anchor="mm")
        enc.write(im)
    enc.close()


# ---------------- 5. VHS GLITCH ----------------
def render_vhs(text, out):
    setup, punch = two_parts(text)
    rnd = random.Random(9)
    mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
    osd = ImageFont.truetype(mono, 40)
    fs = f_for(setup, "poppins_b", 78)
    fp = f_for(punch, "poppins_b", 86)
    sw, sh, _ = layout(setup, fs, 900, 108)
    pw, ph, _ = layout(punch, fp, 900, 118)
    gap = 80
    top = 930 - (sh + gap + ph) / 2
    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for y in range(0, H, 6):
        sd.line((0, y, W, y), fill=(0, 0, 0, 70), width=2)
    noise = rs.grain_layers(n=6, amount=34)
    base = rs.radial((W, H), (30, 26, 44), (4, 4, 8), radius=1400)
    t_s, t_p = 0.4, 2.8
    enc = Encoder(out)

    def rgb_text(d_layer, pos, txt, f, a, off):
        x, y = pos
        d_layer.text((x - off, y), txt, font=f, fill=(255, 40, 80, int(a * 0.8)))
        d_layer.text((x + off, y), txt, font=f, fill=(40, 220, 255, int(a * 0.8)))
        d_layer.text((x, y), txt, font=f, fill=(255, 255, 255, a))

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        im = base.copy()
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        a_s = int(255 * clamp((t - t_s) / 0.25))
        if a_s:
            for (w, x, yr, ww, li) in sw:
                rgb_text(d, (x, top + yr), w, fs, a_s, 3)
        if t >= t_p:
            a_p = int(255 * clamp((t - t_p) / 0.15))
            burst = max(0.0, 1 - (t - t_p) / 0.7)
            for (w, x, yr, ww, li) in pw:
                rgb_text(d, (x, top + sh + gap + yr), w, fp, a_p, 4 + int(22 * burst))
        im.alpha_composite(txt)
        # glitch: slice shifts, strongest right after punchline
        glitch = 0.15 + (2.5 * max(0, 1 - (t - t_p) / 0.7) if t >= t_p else 0) + (1.2 if 0.4 <= t < 0.6 else 0)
        if rnd.random() < 0.25 * glitch:
            for _ in range(int(2 + 4 * glitch)):
                y0 = rnd.randint(0, H - 80)
                hgt = rnd.randint(8, 70)
                band = im.crop((0, y0, W, y0 + hgt))
                im.paste(band, (rnd.randint(-int(60 * glitch), int(60 * glitch)), y0))
        # rolling tracking bar
        ty = int((t * 260) % (H + 200)) - 100
        bar = Image.new("RGBA", (W, 60), (255, 255, 255, 18))
        im.alpha_composite(bar, (0, ty))
        im.alpha_composite(scan)
        im.alpha_composite(noise[fi % len(noise)])
        d = ImageDraw.Draw(im)
        if int(t * 2) % 2 == 0:
            d.ellipse((70, 140, 104, 174), fill=(255, 40, 40))
        d.text((120, 157), "REC", font=osd, fill=(255, 255, 255), anchor="lm")
        d.text((W - 70, 157), "18+  SP", font=osd, fill=(255, 255, 255), anchor="rm")
        secs = 37 + int(t)
        d.text((70, H - 170), "OCT 06 2026", font=osd, fill=(255, 255, 255), anchor="lm")
        d.text((W - 70, H - 170), f"02:14:{secs:02d}", font=osd, fill=(255, 255, 255), anchor="rm")
        c = (t - 5.6) / 0.4
        if c > 0:
            d.text((W / 2, H - 280), HANDLE, font=ImageFont.truetype(mono, 36), fill=(255, 255, 255, int(230 * clamp(c))), anchor="mm")
        enc.write(im)
    enc.close()


# ---------------- 6. WHITE BOX (Sahil's pick) ----------------
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def render_whitebox(text, out):
    """Black screen, full-width white box, black monospace text (like classic meme-page reels).
    Each line of `text` is revealed one after another; Hindi words use a Devanagari font."""
    msgs = [l.strip() for l in text.split("\n") if l.strip()]
    size = 66
    while True:
        f_lat = ImageFont.truetype(MONO, size)
        f_hi = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", int(size * 1.05), layout_engine=ImageFont.Layout.RAQM)
        lh = int(size * 1.45)
        space = f_lat.getlength(" ")
        inner = 1080 - 60 - 2 * 50
        lines = []  # (msg_index, [(word, font, width)], line_width)
        for mi, m in enumerate(msgs):
            cur, cw = [], 0
            for w in m.split():
                f = f_hi if is_hindi(w) else f_lat
                ww = text_len(w, f)
                if cur and cw + space + ww > inner:
                    lines.append((mi, cur, cw)); cur, cw = [], 0
                cw = cw + (space if cur else 0) + ww
                cur.append((w, f, ww))
            if cur:
                lines.append((mi, cur, cw))
        box_h = len(lines) * lh + 2 * 60
        if box_h <= 1300 or size <= 40:
            break
        size -= 4
    bx0, bx1 = 30, W - 30
    by0 = int(H / 2 - box_h / 2)
    appear = [0.35 + i * 1.3 for i in range(len(msgs))]
    dur = max(7.0, appear[-1] + 3.6)
    small = ImageFont.truetype(MONO, 30)
    enc = Encoder(out)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        k = ease_out(t / 0.35)
        if k > 0:
            hh = box_h * (0.92 + 0.08 * k)
            d.rectangle((bx0, H / 2 - hh / 2, bx1, H / 2 + hh / 2), fill=(250, 250, 250, int(255 * k)),
                        outline=(200, 200, 200, int(255 * k)), width=2)
        for li, (mi, words, lw) in enumerate(lines):
            p = clamp((t - appear[mi]) / 0.25)
            if p <= 0:
                continue
            x = W / 2 - lw / 2
            y = by0 + 60 + li * lh + 8 * (1 - p)
            for (w, f, ww) in words:
                yy = y + (lh - f.size * 1.2) / 2 - (2 if f is f_hi else 0)
                draw_rich(ov, d, (x, yy), w, f, (20, 20, 20, int(255 * p)))
                x += ww + space
        c = clamp((t - appear[-1] - 1.0) / 0.5)
        if c > 0:
            d.text((W / 2, H - 230), HANDLE + "  ·  18+", font=small, fill=(150, 150, 150, int(200 * c)), anchor="mm")
        im.alpha_composite(ov)
        enc.write(im)
    enc.close()


STYLES = {"glass": render_glass, "yellow": render_yellow, "notes": render_notes, "tweet": render_tweet, "vhs": render_vhs, "whitebox": render_whitebox}

if __name__ == "__main__":
    STYLES[sys.argv[1]](sys.argv[2].replace("\\n", "\n"), sys.argv[3])
