"""Generate synthetic test images for sandbox workflow testing.

Creates two PNG images in sandbox/assets/:
  food_test.png  — a plate with identifiable food items (egg, salmon, greens, cucumber, bread)
  cgm_test.png   — a CGM glucose chart similar to LibreLink / Dexcom output

No external dependencies — uses only struct, zlib, and math.

Run once (or after deleting the assets):
    python -m sandbox.generate_test_images
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"


# ── PNG primitives ─────────────────────────────────────────────────────────────


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _make_png(width: int, height: int, pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """Encode a 2-D list of (R, G, B) tuples as a valid PNG file."""
    raw = b""
    for row in pixels:
        raw += b"\x00"  # filter type 0 (None)
        for r, g, b in row:
            raw += bytes([r, g, b])
    compressed = zlib.compress(raw, level=6)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _dist(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ── Food plate image ───────────────────────────────────────────────────────────


def _food_pixels(w: int = 400, h: int = 300) -> list[list[tuple[int, int, int]]]:
    """
    A round white plate on a warm-gray surface with:
      - Golden scrambled egg / omelette (bottom centre-left)
      - Salmon fillet (upper right)
      - Arugula / rocket leaves (upper centre)
      - Cucumber slices (right side)
      - Rye cracker (upper left)
    """
    img: list[list[tuple[int, int, int]]] = [[(205, 198, 188)] * w for _ in range(h)]
    cx, cy = w // 2, h // 2
    pr = min(w, h) // 2 - 12  # plate radius

    # White plate disc
    for y in range(h):
        for x in range(w):
            if _dist(x, y, cx, cy) <= pr:
                img[y][x] = (252, 252, 252)

    food_r = pr - 14  # usable food area radius

    # Scrambled egg / omelette — golden yellow, lower half
    egg_cx, egg_cy = cx - pr // 7, cy + pr // 6
    for y in range(h):
        for x in range(w):
            if _dist(x, y, cx, cy) <= food_r:
                rx = (x - egg_cx) / (food_r * 0.72)
                ry = (y - egg_cy) / (food_r * 0.52)
                if rx**2 + ry**2 <= 1.0 and (y - cy) > -pr // 8:
                    t = 1.0 - rx**2 - ry**2
                    img[y][x] = (
                        min(255, int(228 + 18 * t)),
                        min(255, int(172 + 22 * t)),
                        45,
                    )

    # Salmon fillet — orange-pink, upper right
    sal_cx, sal_cy = cx + pr // 3, cy - pr // 3
    for y in range(h):
        for x in range(w):
            if _dist(x, y, cx, cy) <= food_r:
                rx = (x - sal_cx) / (food_r * 0.38)
                ry = (y - sal_cy) / (food_r * 0.27)
                if rx**2 + ry**2 <= 1.0 and (y - cy) < pr // 6:
                    t = 1.0 - rx**2 - ry**2
                    img[y][x] = (
                        min(255, int(208 + 18 * t)),
                        min(210, int(100 + 12 * t)),
                        82,
                    )

    # Arugula / greens — dark green, upper centre
    for i in range(14):
        gx = cx + int((i - 7) * pr // 9) + (i % 3) * 4
        gy = cy - pr // 4 + (i % 5) * 5
        gr = 11 + (i % 4) * 2
        for y in range(h):
            for x in range(w):
                if _dist(x, y, cx, cy) <= food_r and _dist(x, y, gx, gy) <= gr:
                    shade = (i + abs(x - gx) + abs(y - gy)) % 4
                    img[y][x] = (32 + shade * 6, min(185, 108 + shade * 16), 28 + shade * 6)

    # Cucumber slices — bright green circles, right side
    for dx, dy in [(pr // 2, -pr // 9), (pr * 3 // 5, pr // 7), (pr // 2, pr // 3)]:
        scx, scy = cx + dx, cy + dy
        for y in range(h):
            for x in range(w):
                if _dist(x, y, cx, cy) <= food_r:
                    d = _dist(x, y, scx, scy)
                    if d <= 17:
                        img[y][x] = (88, 178, 68) if d <= 13 else (48, 128, 38)

    # Rye cracker — brown rounded rectangle, upper left
    br_cx, br_cy = cx - pr * 9 // 18, cy - pr // 3
    for y in range(h):
        for x in range(w):
            if _dist(x, y, cx, cy) <= food_r:
                if abs(x - br_cx) <= pr // 5 and abs(y - br_cy) <= pr // 8:
                    tx = abs((x - br_cx) % 9 - 4)
                    ty = abs((y - br_cy) % 7 - 3)
                    img[y][x] = (min(185, 118 + tx * 3), min(130, 82 + ty * 2), 48)

    return img


# ── CGM glucose chart image ────────────────────────────────────────────────────


def _cgm_pixels(w: int = 400, h: int = 500) -> list[list[tuple[int, int, int]]]:
    """
    Synthetic LibreLink-style CGM chart:
      - Green header band (current reading: 79 mg/dL)
      - White chart area with light-green target band (70–140 mg/dL)
      - Black stable glucose curve (~72–82 mg/dL) with brief dip below 70 (red)
      - Green dot at the latest reading point
      - Horizontal grid lines at 50, 100, 150, 200, 250, 300, 350 mg/dL
      - Dashed red hypo threshold line at 70 mg/dL
    """
    img: list[list[tuple[int, int, int]]] = [[(255, 255, 255)] * w for _ in range(h)]

    # Green header band
    header_h = h * 30 // 100
    for y in range(header_h):
        for x in range(w):
            img[y][x] = (128, 185, 72)

    # Darker "reading" block inside header
    for y in range(header_h // 4, header_h * 3 // 4):
        for x in range(w // 5, w * 4 // 5):
            if 0 <= y < header_h:
                img[y][x] = (18, 78, 18)

    # Chart geometry
    chart_top = header_h + 8
    chart_bottom = h - 42
    chart_left = 52
    chart_right = w - 12
    chart_h = chart_bottom - chart_top
    chart_w = chart_right - chart_left

    y_min_val, y_max_val = 50, 350

    def val_to_y(val: float) -> int:
        ratio = (val - y_min_val) / (y_max_val - y_min_val)
        return int(chart_bottom - ratio * chart_h)

    # Target range band: light green (70–140 mg/dL)
    y_140 = val_to_y(140)
    y_70 = val_to_y(70)
    for y in range(y_140, y_70 + 1):
        for x in range(chart_left, chart_right):
            if chart_top <= y <= chart_bottom:
                img[y][x] = (228, 246, 208)

    # Horizontal grid lines
    for grid_val in [50, 100, 150, 200, 250, 300, 350]:
        gy = val_to_y(grid_val)
        if chart_top <= gy <= chart_bottom:
            for x in range(chart_left, chart_right):
                img[gy][x] = (215, 215, 215)

    # Dashed red hypo threshold at 70 mg/dL
    for x in range(chart_left, chart_right):
        if x % 10 < 5:
            gy = val_to_y(70)
            if chart_top <= gy <= chart_bottom:
                img[gy][x] = (218, 48, 48)

    # Glucose curve: stable ~72–82 mg/dL with one dip below 70
    n_pts = 120
    curve: list[float] = []
    for i in range(n_pts):
        t = i / n_pts
        base = 77.0
        wave = 5 * math.sin(t * 22) + 3 * math.cos(t * 37)
        # Brief hypo dip around t = 0.64
        dip = -17 * math.sin((t - 0.60) * math.pi / 0.10) if 0.60 <= t <= 0.70 else 0.0
        curve.append(max(52.0, min(100.0, base + wave + dip)))

    def _draw_point(px: int, py: int, color: tuple[int, int, int]) -> None:
        for dy2 in range(-1, 2):
            for dx2 in range(-1, 2):
                nx, ny = px + dx2, py + dy2
                if chart_left <= nx < chart_right and chart_top <= ny <= chart_bottom:
                    img[ny][nx] = color

    for i in range(n_pts - 1):
        x1 = chart_left + i * chart_w // (n_pts - 1)
        y1 = val_to_y(curve[i])
        x2 = chart_left + (i + 1) * chart_w // (n_pts - 1)
        y2 = val_to_y(curve[i + 1])
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        color = (218, 48, 48) if curve[i] < 70 else (22, 22, 22)
        for step in range(steps + 1):
            t = step / steps
            _draw_point(
                int(x1 + (x2 - x1) * t),
                int(y1 + (y2 - y1) * t),
                color,
            )

    # Green dot at last reading
    last_x = chart_right - 4
    last_y = val_to_y(curve[-1])
    for dy2 in range(-7, 8):
        for dx2 in range(-7, 8):
            if dx2**2 + dy2**2 <= 42:
                nx, ny = last_x + dx2, last_y + dy2
                if 0 <= nx < w and 0 <= ny < h:
                    img[ny][nx] = (78, 198, 78)

    # Simple tick marks on x-axis
    for tick_i in range(3):
        tx = chart_left + (tick_i + 1) * chart_w // 4
        for ty in range(chart_bottom, min(h, chart_bottom + 6)):
            if 0 <= tx < w:
                img[ty][tx] = (150, 150, 150)

    return img


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    food_path = ASSETS_DIR / "food_test.png"
    food_png = _make_png(400, 300, _food_pixels(400, 300))
    food_path.write_bytes(food_png)
    print(f"Generated {food_path}  ({len(food_png):,} bytes)")

    cgm_path = ASSETS_DIR / "cgm_test.png"
    cgm_png = _make_png(400, 500, _cgm_pixels(400, 500))
    cgm_path.write_bytes(cgm_png)
    print(f"Generated {cgm_path}  ({len(cgm_png):,} bytes)")


if __name__ == "__main__":
    main()
