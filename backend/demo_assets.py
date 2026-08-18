"""
Synthetic demo asset generators for seed.py: turns plain-text demo documents
into real PDF bytes, and produces small placeholder "CT scan" PNGs (a grayscale
gradient with a circular density standing in for a nodule — not real imaging
data). Used to demonstrate the ingestion pipeline's PDF text-extraction path
and IMAGE-artifact storage/embedding path against real binary files.
"""
from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw


def make_pdf_bytes(title: str, body_text: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, height - 1 * inch, title)

    c.setFont("Helvetica", 10)
    y = height - 1.4 * inch
    for line in body_text.strip().splitlines():
        if y < 1 * inch:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 1 * inch
        c.drawString(1 * inch, y, line)
        y -= 14

    c.showPage()
    c.save()
    return buf.getvalue()


def make_ct_scan_png(nodule_position: tuple[float, float] = (0.62, 0.45), size: int = 512) -> bytes:
    """A schematic axial-slice placeholder: a soft grayscale disc (torso
    cross-section) with a brighter circular density at ``nodule_position``
    (fractional x, y). Purely illustrative, not derived from real imaging."""
    img = Image.new("L", (size, size), color=10)
    draw = ImageDraw.Draw(img)

    cx, cy, r = size // 2, size // 2, int(size * 0.42)
    for i in range(r, 0, -1):
        shade = 40 + int(60 * (1 - i / r))
        draw.ellipse((cx - i, cy - i, cx + i, cy + i), fill=shade)

    lung_r = int(size * 0.16)
    for lx in (cx - int(size * 0.2), cx + int(size * 0.2)):
        draw.ellipse((lx - lung_r, cy - lung_r, lx + lung_r, cy + lung_r), fill=15)

    nx, ny = int(size * nodule_position[0]), int(size * nodule_position[1])
    nr = max(4, int(size * 0.02))
    draw.ellipse((nx - nr, ny - nr, nx + nr, ny + nr), fill=200)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
