#!/usr/bin/env python3
"""ساخت آیکون سادهٔ اپ بدون هیچ کتابخانهٔ بیرونی (PNG دستی)."""
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "src", "main", "res")

BG = (15, 20, 26)
GRID = (32, 41, 52)
BLUE = (61, 126, 255)
GOLD = (232, 179, 75)


def rounded(x, y, n, r):
    """آیا نقطه داخل مربع با گوشه‌های گرد است؟"""
    cx = min(max(x, r), n - 1 - r)
    cy = min(max(y, r), n - 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    t = ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5


def render(n):
    pixels = []
    r = int(n * 0.22)
    pad = int(n * 0.16)
    # نقاط شکست نمودار (x, y) در مختصات نرمال ۰..۱
    pts = [(0.16, 0.70), (0.32, 0.56), (0.44, 0.63), (0.60, 0.40), (0.76, 0.46), (0.88, 0.26)]
    pts = [(x * n, y * n) for x, y in pts]
    lw = max(1.5, n * 0.045)
    for y in range(n):
        row = bytearray()
        for x in range(n):
            if not rounded(x, y, n, r):
                row += bytes((0, 0, 0, 0))
                continue
            c = BG
            # خطوط افقی ظریف
            for k in range(5):
                gy = pad + int((n - 2 * pad) * k / 4)
                if abs(y - gy) <= max(0.5, n * 0.004):
                    c = GRID
            # خطوط نمودار
            d = min(seg_dist(x, y, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1))
            if d <= lw / 2:
                c = BLUE
            # نقطهٔ پایانی طلایی
            for px, py, col in ((pts[-1][0], pts[-1][1], GOLD),):
                if (x - px) ** 2 + (y - py) ** 2 <= (lw * 1.25) ** 2:
                    c = col
            row += bytes((c[0], c[1], c[2], 255))
        pixels.append(bytes(row))
    raw = b"".join(b"\x00" + p for p in pixels)
    comp = zlib.compress(raw, 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    for folder, size in (("mipmap-mdpi", 48), ("mipmap-hdpi", 72), ("mipmap-xhdpi", 96),
                         ("mipmap-xxhdpi", 144), ("mipmap-xxxhdpi", 192)):
        d = os.path.join(OUT, folder)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "ic_launcher.png"), "wb") as fh:
            fh.write(render(size))
        print(f"{folder}/ic_launcher.png")


if __name__ == "__main__":
    main()
