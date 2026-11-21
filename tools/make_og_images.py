"""Create the 1200x630 Open Graph images (assets/og-image-en.jpg / og-image-ar.jpg)
from the logo and the dashboard screenshots. Requires Pillow: pip install pillow"""
import os
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda *p: os.path.join(ROOT, 'assets', *p)
W, H, BG = 1200, 630, (11, 18, 32)

def rounded(im, r):
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, *im.size), r, fill=255)
    out = im.convert('RGBA'); out.putalpha(m); return out

for lang in ('en', 'ar'):
    c = Image.new('RGB', (W, H), BG)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * .25, -260, W * .95, 360), fill=(43, 190, 190, 70))
    c.paste(glow.filter(ImageFilter.GaussianBlur(120)), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    logo = Image.open(A('spacesoft-logo.png')).convert('RGBA')
    lw = 330; logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    lx = 60 if lang == 'en' else W - 60 - lw
    c.paste(logo, (lx, 52), logo)
    shot = Image.open(A(f'dashboard-{lang}.webp')).convert('RGB')
    sw = 1020; shot = shot.resize((sw, round(shot.height * sw / shot.width)), Image.LANCZOS)
    bar = Image.new('RGB', (sw, 34), (236, 238, 241)); d = ImageDraw.Draw(bar)
    for i in range(3): d.ellipse((16 + i * 18, 12, 26 + i * 18, 22), fill=(207, 211, 216))
    frame = Image.new('RGB', (sw, 34 + shot.height)); frame.paste(bar, (0, 0)); frame.paste(shot, (0, 34))
    frame = rounded(frame, 16)
    shadow = Image.new('RGBA', (sw + 80, frame.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((40, 40, sw + 40, frame.height + 40), 16, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    x, y = (W - sw) // 2, 170
    c.paste(shadow, (x - 40, y - 30), shadow); c.paste(frame, (x, y), frame)
    c.save(A(f'og-image-{lang}.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
    print(lang, os.path.getsize(A(f'og-image-{lang}.jpg')) // 1024, 'KB')
