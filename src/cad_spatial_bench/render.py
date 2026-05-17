"""Deterministic raster rendering for benchmark vision tasks.

The first renderer is intentionally simple: it creates a top-down PNG view of a
rectangular plate using only the Python standard library. Build123d remains the
source of CAD geometry; this module gives us stable image assets for VLM tests.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

from cad_spatial_bench.generators import hole_positions

Color = tuple[int, int, int]


def render_plate_top_view(
    parameters: dict[str, Any], output_path: Path, image_size: int = 512
) -> Path:
    """Render a deterministic top-down PNG image for a rectangular plate."""
    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])
    hole_count = int(parameters.get("hole_count", 0))

    canvas = _new_canvas(image_size, image_size, (245, 247, 250))
    margin = image_size * 0.14
    scale = min((image_size - 2 * margin) / length, (image_size - 2 * margin) / width)
    plate_width_px = int(round(length * scale))
    plate_height_px = int(round(width * scale))
    center_x = image_size // 2
    center_y = image_size // 2

    left = center_x - plate_width_px // 2
    top = center_y - plate_height_px // 2
    right = left + plate_width_px
    bottom = top + plate_height_px

    _draw_rect(canvas, image_size, left + 7, top + 7, right + 7, bottom + 7, (202, 209, 219))
    _draw_rect(canvas, image_size, left, top, right, bottom, (177, 186, 197))
    _draw_rect_outline(canvas, image_size, left, top, right, bottom, (56, 66, 82), thickness=3)

    hole_radius_px = max(6, int(round(min(length, width) * 0.06 * scale)))
    for x_position, y_position in hole_positions(length, width, hole_count):
        hole_x = int(round(center_x + x_position * scale))
        hole_y = int(round(center_y - y_position * scale))
        _draw_circle(canvas, image_size, hole_x, hole_y, hole_radius_px, (245, 247, 250))
        _draw_circle_outline(canvas, image_size, hole_x, hole_y, hole_radius_px, (56, 66, 82), 2)

    _write_png(output_path, image_size, image_size, canvas)
    return output_path


def _new_canvas(width: int, height: int, color: Color) -> list[Color]:
    """Create a flat RGB canvas."""
    return [color for _ in range(width * height)]


def _draw_rect(
    canvas: list[Color], canvas_width: int, left: int, top: int, right: int, bottom: int, color: Color
) -> None:
    """Draw a filled rectangle."""
    canvas_height = len(canvas) // canvas_width
    for y in range(max(0, top), min(canvas_height, bottom)):
        for x in range(max(0, left), min(canvas_width, right)):
            canvas[y * canvas_width + x] = color


def _draw_rect_outline(
    canvas: list[Color],
    canvas_width: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: Color,
    thickness: int,
) -> None:
    """Draw a rectangle outline."""
    _draw_rect(canvas, canvas_width, left, top, right, top + thickness, color)
    _draw_rect(canvas, canvas_width, left, bottom - thickness, right, bottom, color)
    _draw_rect(canvas, canvas_width, left, top, left + thickness, bottom, color)
    _draw_rect(canvas, canvas_width, right - thickness, top, right, bottom, color)


def _draw_circle(
    canvas: list[Color], canvas_width: int, center_x: int, center_y: int, radius: int, color: Color
) -> None:
    """Draw a filled circle."""
    canvas_height = len(canvas) // canvas_width
    radius_squared = radius * radius

    for y in range(max(0, center_y - radius), min(canvas_height, center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(canvas_width, center_x + radius + 1)):
            if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius_squared:
                canvas[y * canvas_width + x] = color


def _draw_circle_outline(
    canvas: list[Color],
    canvas_width: int,
    center_x: int,
    center_y: int,
    radius: int,
    color: Color,
    thickness: int,
) -> None:
    """Draw a circle outline."""
    outer = radius * radius
    inner_radius = max(0, radius - thickness)
    inner = inner_radius * inner_radius
    canvas_height = len(canvas) // canvas_width

    for y in range(max(0, center_y - radius), min(canvas_height, center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(canvas_width, center_x + radius + 1)):
            distance = (x - center_x) ** 2 + (y - center_y) ** 2
            if inner <= distance <= outer:
                canvas[y * canvas_width + x] = color


def _write_png(path: Path, width: int, height: int, pixels: list[Color]) -> None:
    """Write RGB pixels as a PNG file using the standard library."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_rows = []

    for y in range(height):
        row_start = y * width
        row = pixels[row_start : row_start + width]
        raw_rows.append(b"\x00" + b"".join(bytes(pixel) for pixel in row))

    compressed = zlib.compress(b"".join(raw_rows), level=9)

    with path.open("wb") as file:
        file.write(b"\x89PNG\r\n\x1a\n")
        file.write(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
        file.write(_png_chunk(b"IDAT", compressed))
        file.write(_png_chunk(b"IEND", b""))


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk."""
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)
