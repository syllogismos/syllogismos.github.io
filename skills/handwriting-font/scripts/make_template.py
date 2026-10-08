# /// script
# requires-python = ">=3.10"
# dependencies = ["reportlab>=4"]
# ///
"""Draw the printable handwriting template.

    uv run make_template.py [output.pdf] [--layout layout.json]

One box per character, each with four guide lines, plus corner marks that let a
photo or scan of the page be straightened and cut up automatically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import template_layout as L

# Typefaces for the printed labels, in order of preference. No single system
# font has every character (the rupee sign is the usual gap), so each label
# uses the first one that contains it.
LABEL_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]

BLACK = 0.0
BOX = 0.30  # box outlines: dark, so the boxes read clearly
BASELINE = 0.64  # the line letters sit on: the strongest guide
GUIDE = 0.80  # the other guides: light, so they drop out of a scan
LABEL = 0.42
TEXT = 0.25


FONTS: list[tuple[str, set[int]]] = []  # (registered name, code points it covers)


def register_fonts() -> None:
    for i, path in enumerate(f for f in LABEL_FONTS if Path(f).exists()):
        font = TTFont(f"Label{i}", path)
        pdfmetrics.registerFont(font)
        FONTS.append((f"Label{i}", set(font.face.charToGlyph)))
    if not FONTS:
        sys.exit("No label font found. Add the path of a Unicode TrueType font to LABEL_FONTS.")


def font_for(char: str) -> str:
    """The first label font that has this character."""
    for name, covered in FONTS:
        if ord(char) in covered:
            return name
    sys.exit(f"No label font has {char!r} (U+{ord(char):04X}). Add one to LABEL_FONTS.")


def y(top_mm: float) -> float:
    """Convert a distance from the top of the page into PDF coordinates."""
    return (L.PAGE_H - top_mm) * mm


def hline(c: canvas.Canvas, x: float, top: float, w: float, gray: float, width: float, dash=None) -> None:
    c.setStrokeGray(gray)
    c.setLineWidth(width)
    c.setDash(dash or [])
    c.line(x * mm, y(top), (x + w) * mm, y(top))
    c.setDash([])


def guides(c: canvas.Canvas, x: float, top: float, w: float, asc: float, xh: float, base: float, desc: float) -> None:
    hline(c, x, top + asc, w, GUIDE, 0.45)
    hline(c, x, top + xh, w, GUIDE, 0.45, dash=[1.4, 1.4])
    hline(c, x, top + desc, w, GUIDE, 0.45)
    hline(c, x, top + base, w, BASELINE, 0.8)


def draw_marks(c: canvas.Canvas, page_number: int) -> None:
    c.setFillGray(BLACK)
    for x, top in L.mark_origins().values():
        c.rect(x * mm, y(top + L.MARK), L.MARK * mm, L.MARK * mm, stroke=0, fill=1)
    # The top-left mark has a white centre, so an upside-down scan can be told apart.
    hole = L.MARK / 3
    c.setFillGray(1)
    c.rect((L.LEFT + hole) * mm, y(L.TOP + 2 * hole), hole * mm, hole * mm, stroke=0, fill=1)
    # The page number in binary, most significant bit first, right of the top-left mark.
    c.setFillGray(BLACK)
    for bit in range(L.ID_BITS):
        if page_number >> (L.ID_BITS - 1 - bit) & 1:
            bx = L.LEFT + L.MARK + L.ID_BIT + bit * L.ID_BIT
            c.rect(bx * mm, y(L.TOP + L.ID_BIT), L.ID_BIT * mm, L.ID_BIT * mm, stroke=0, fill=1)


def draw_header(c: canvas.Canvas, font: str, page_number: int, page: dict) -> None:
    x = L.LEFT + L.MARK + L.ID_BIT * (L.ID_BITS + 2)
    right = L.LEFT + L.CONTENT_W - L.MARK - 3
    c.setFillGray(BLACK)
    c.setFont(font, 12)
    c.drawString(x * mm, y(L.TOP + 4.4), "Handwriting font template")
    c.setFont(font, 8.5)
    c.setFillGray(TEXT)
    c.drawRightString(right * mm, y(L.TOP + 4.4), f"{page['title']}    page {page_number} of {len(L.PAGES)}")
    c.setFont(font, 7.6)
    if page["cells"]:
        lines = [
            "Use a black pen and write each character once, in its box. Sit every letter on the dark line. Capitals and tall",
            "letters reach the top line, small letters reach the dashed line, and tails (g j p q y) drop to the bottom line.",
        ]
    else:
        lines = [
            "Optional, but it makes a better font. Copy each sentence on the lines below it in a black pen, at your normal",
            "size and speed. It shows how you really space letters and words, which single boxes cannot.",
        ]
    for i, text in enumerate(lines):
        c.drawString(x * mm, y(L.TOP + 8.7 + i * 3.4), text)


def draw_footer(c: canvas.Canvas, font: str) -> None:
    c.setFont(font, 7.6)
    c.setFillGray(TEXT)
    top = L.TOP + L.CONTENT_H - 2.0
    c.drawCentredString(
        (L.LEFT + L.CONTENT_W / 2) * mm,
        y(top),
        "Scan at 300 dpi or more, or photograph the page flat in even light with all four black corner squares in view.",
    )


def draw_cell(c: canvas.Canvas, font: str, index: int, char: str, name: str) -> None:
    x, top = L.cell_origin(index)
    guides(c, x, top, L.CELL_W, L.ASCENDER_Y, L.XHEIGHT_Y, L.BASELINE_Y, L.DESCENDER_Y)
    c.setStrokeGray(BOX)
    c.setLineWidth(0.8)
    c.rect(x * mm, y(top + L.CELL_H), L.CELL_W * mm, L.CELL_H * mm, stroke=1, fill=0)
    c.setFillGray(LABEL)
    c.setFont(font_for(char), 8)
    c.drawString((x + 1.3) * mm, y(top + L.LABEL_BASELINE_Y), char)
    if name:
        c.setFont(font, 5.2)
        c.drawRightString((x + L.CELL_W - 1.3) * mm, y(top + L.LABEL_BASELINE_Y - 0.1), name)


def draw_sentences(c: canvas.Canvas, font: str, page: dict) -> None:
    top = L.sentences_top(page)
    for i, text in enumerate(L.SENTENCES):
        block = top + i * L.LINE_BLOCK_H
        c.setFillGray(LABEL)
        c.setFont(font, 9.5)
        c.drawString(L.LEFT * mm, y(block + 4.4), text)
        guides(c, L.LEFT, block, L.CONTENT_W, L.LINE_ASCENDER_Y, L.LINE_XHEIGHT_Y, L.LINE_BASELINE_Y, L.LINE_DESCENDER_Y)


def main() -> None:
    args = sys.argv[1:]
    layout_path = None
    if "--layout" in args:
        i = args.index("--layout")
        layout_path = Path(args[i + 1])
        del args[i : i + 2]
    out = Path(args[0] if args else "handwriting-font-template.pdf")

    register_fonts()
    text_font = FONTS[0][0]

    c = canvas.Canvas(str(out), pagesize=(L.PAGE_W * mm, L.PAGE_H * mm))
    c.setTitle("Handwriting font template")
    c.setAuthor("syllogismos")
    c.setSubject("Print, fill in by hand, then scan to make a font of your handwriting.")
    for number, page in enumerate(L.PAGES, start=1):
        draw_marks(c, number)
        draw_header(c, text_font, number, page)
        for index, (char, name) in enumerate(page["cells"]):
            draw_cell(c, text_font, index, char, name)
        if page["sentences"]:
            draw_sentences(c, text_font, page)
        draw_footer(c, text_font)
        c.showPage()
    c.save()
    print(f"wrote {out} ({len(L.PAGES)} pages, {sum(len(p['cells']) for p in L.PAGES)} characters)")

    if layout_path:
        layout_path.write_text(json.dumps(L.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {layout_path}")


if __name__ == "__main__":
    main()
