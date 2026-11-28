"""Draw the icon of the app and write it as a PNG.

The icon is the shield of the ranks: a dark field, a gold rim and the
gold cross of the charge. The file is written without any library: the
pixels are made here and packed with zlib.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "flutter_app" / "assets" / "icons"

GOLD = (212, 167, 44)
GOLD_BRIGHT = (230, 192, 90)
INK = (232, 236, 244)
DARK = (10, 15, 24)
FIELD = (22, 30, 44)
SABLE = (23, 27, 36)


def png(width: int, height: int, pixels: bytearray) -> bytes:
    """Pack the pixels of a picture into a PNG file."""
    raw = bytearray()
    stride = width * 4
    for row in range(height):
        raw.append(0)
        raw.extend(pixels[row * stride:(row + 1) * stride])

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def blend(
    target: bytearray,
    index: int,
    colour: tuple[int, int, int],
    alpha: float,
) -> None:
    """Put a colour over a pixel, with the given opacity."""
    if alpha <= 0:
        return
    alpha = min(1.0, alpha)
    for channel in range(3):
        current = target[index + channel]
        target[index + channel] = int(current + (colour[channel] - current) * alpha)


def shield_alpha(x: float, y: float) -> float:
    """How much of the shield the point is in (the 100x120 shape)."""
    if y < 30 or y > 112:
        return 0.0
    if y <= 60:
        inside = 14 <= x <= 86
    else:
        # the curve of the bottom of the shield
        t = (y - 60) / 52
        half = 36 * math.sqrt(max(0.0, 1 - t * t)) + 2
        inside = 50 - half <= x <= 50 + half
    return 1.0 if inside else 0.0


def draw(size: int) -> bytearray:
    """Draw the icon at the given size."""
    pixels = bytearray(size * size * 4)
    scale = size / 100.0
    offset = (size - 120 * scale) / 2 if size > 120 * scale else 0.0
    for py in range(size):
        for px in range(size):
            index = (py * size + px) * 4
            # the field of the icon
            corner = min(px, py, size - 1 - px, size - 1 - py)
            if corner < size * 0.06:
                pixels[index + 3] = 0
                continue
            pixels[index] = DARK[0]
            pixels[index + 1] = DARK[1]
            pixels[index + 2] = DARK[2]
            pixels[index + 3] = 255

    # the shield
    for py in range(size):
        for px in range(size):
            index = (py * size + px) * 4
            sx = (px - 50 * scale - offset / scale) / scale + 50
            sy = (py - 6 * scale - offset / scale) / scale + 6
            inside = shield_alpha(sx, sy)
            if inside <= 0:
                continue
            # the rim
            rim = shield_alpha(sx + 0.9, sy) * shield_alpha(sx - 0.9, sy)
            rim *= shield_alpha(sx, sy + 0.9) * shield_alpha(sx, sy - 0.9)
            if rim <= 0:
                blend(pixels, index, GOLD, 1.0)
                continue
            blend(pixels, index, FIELD, 1.0)
            # the cross of the charge
            if (36 <= sx <= 64 and 68 <= sy <= 80) or (46 <= sx <= 54 and 44 <= sy <= 96):
                blend(pixels, index, GOLD_BRIGHT, 1.0)
    return pixels


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 48, 64, 72, 96, 128, 144, 192, 256, 512, 1024):
        pixels = draw(size)
        path = OUT / f"icon-{size}.png"
        path.write_bytes(png(size, size, pixels))
        print("wrote", path)


if __name__ == "__main__":
    main()
