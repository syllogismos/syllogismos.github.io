"""Geometry and character set of the handwriting template.

This module is the single source of truth: make_template.py draws the PDF from it,
and the extraction step reads the same numbers to find each box in a scan.
All measurements are millimetres, measured from the top-left corner of the page.
"""

from __future__ import annotations

PAGE_W, PAGE_H = 210.0, 297.0  # A4. Everything sits inside the area US Letter also prints.

# The content box. Fiducial marks sit in its four corners.
LEFT, TOP = 12.0, 18.0
CONTENT_W, CONTENT_H = 186.0, 258.5

HEADER_H = 16.0  # title and instructions, between the two top marks
FOOTER_H = 8.0  # between the two bottom marks

COLS, ROWS = 6, 7
CELL_W = CONTENT_W / COLS  # 31.0
CELL_H = (CONTENT_H - HEADER_H - FOOTER_H) / ROWS  # 33.5
GRID_TOP = TOP + HEADER_H

# Guide lines inside a cell, as offsets from the top edge of the cell.
LABEL_H = 5.0  # strip holding the printed reference character
ASCENDER_Y = 8.0  # capitals and tall letters reach this line
XHEIGHT_Y = 14.8  # small letters reach this dashed line
BASELINE_Y = 23.5  # every letter sits on this line
DESCENDER_Y = 30.0  # tails of g j p q y reach this line

MARK = 6.0  # side of each square corner mark
ID_BIT = 3.0  # side of each page-number bit, to the right of the top-left mark
ID_BITS = 3

# Handwriting lines on the last page, at a natural writing size.
LINE_BLOCK_H = 28.0
LINE_ASCENDER_Y = 7.5
LINE_XHEIGHT_Y = 11.3
LINE_BASELINE_Y = 16.0
LINE_DESCENDER_Y = 19.6

SENTENCES = [
    "Sphinx of black quartz, judge my vow.",
    "Pack my box with five dozen liquor jugs!",
    "\u201cWait,\u201d they\u2019ll say \u2014 it\u2019s 10:45 already?",
]

# (character, name printed beside it). A name is given wherever the character
# could be mistaken for another one.
UPPER = [(c, "capital O" if c == "O" else "capital i" if c == "I" else "") for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
LOWER = [(c, "small L" if c == "l" else "") for c in "abcdefghijklmnopqrstuvwxyz"]
DIGITS = [(c, {"0": "zero", "1": "one"}.get(c, "")) for c in "0123456789"]

PUNCT_1 = [
    (".", "full stop"),
    (",", "comma"),
    ("!", "exclamation"),
    ("?", "question"),
    ("'", "straight quote"),
    ('"', "straight double"),
]
PUNCT_2 = [
    (":", "colon"),
    (";", "semicolon"),
    ("-", "hyphen"),
    ("\u2013", "en dash"),
    ("\u2014", "em dash"),
    ("_", "underscore"),
    ("(", "bracket"),
    (")", "bracket"),
    ("[", "square"),
    ("]", "square"),
    ("{", "brace"),
    ("}", "brace"),
    ("/", "slash"),
    ("\\", "backslash"),
    ("|", "bar"),
    ("\u2026", "ellipsis"),
]
SYMBOLS = [
    ("@", "at"),
    ("#", "hash"),
    ("$", "dollar"),
    ("%", "percent"),
    ("^", "caret"),
    ("&", "and"),
    ("*", "asterisk"),
    ("+", "plus"),
    ("=", "equals"),
    ("<", "less than"),
    (">", "greater than"),
    ("~", "tilde"),
    ("`", "backtick"),
    ("\u2018", "opening quote"),
    ("\u2019", "apostrophe"),
    ("\u201c", "opening double"),
    ("\u201d", "closing double"),
    ("\u2022", "bullet"),
    ("\u00b0", "degree"),
    ("\u20b9", "rupee"),
    ("\u20ac", "euro"),
    ("\u00a3", "pound"),
    ("\u00d7", "times"),
    ("\u00f7", "divide"),
]

PAGES = [
    {"title": "Capitals, numbers", "cells": UPPER + DIGITS + PUNCT_1, "sentences": False},
    {"title": "Small letters, punctuation", "cells": LOWER + PUNCT_2, "sentences": False},
    {"title": "Symbols, sentences", "cells": SYMBOLS, "sentences": True},
]


def cell_origin(index: int) -> tuple[float, float]:
    """Top-left corner of the index-th cell on a page (cells fill rows left to right)."""
    row, col = divmod(index, COLS)
    return LEFT + col * CELL_W, GRID_TOP + row * CELL_H


def mark_origins() -> dict[str, tuple[float, float]]:
    """Top-left corner of each corner mark."""
    right = LEFT + CONTENT_W - MARK
    bottom = TOP + CONTENT_H - MARK
    return {"tl": (LEFT, TOP), "tr": (right, TOP), "bl": (LEFT, bottom), "br": (right, bottom)}


def sentences_top(page: dict) -> float:
    """Top edge of the handwriting lines, just under the last row of cells."""
    rows_used = -(-len(page["cells"]) // COLS)
    return GRID_TOP + rows_used * CELL_H + 7.0


def as_dict() -> dict:
    """The whole layout as plain data, for tools that are not written in Python."""
    pages = []
    for number, page in enumerate(PAGES, start=1):
        cells = []
        for index, (char, name) in enumerate(page["cells"]):
            x, y = cell_origin(index)
            cells.append({"char": char, "codepoint": f"U+{ord(char):04X}", "name": name, "x": x, "y": y})
        entry = {"page": number, "title": page["title"], "cells": cells}
        if page["sentences"]:
            top = sentences_top(page)
            entry["sentences"] = [
                {"text": text, "x": LEFT, "y": top + i * LINE_BLOCK_H, "w": CONTENT_W, "h": LINE_BLOCK_H}
                for i, text in enumerate(SENTENCES)
            ]
        pages.append(entry)
    return {
        "units": "mm, origin at the top-left corner of the page",
        "page": {"w": PAGE_W, "h": PAGE_H},
        "content": {"x": LEFT, "y": TOP, "w": CONTENT_W, "h": CONTENT_H},
        "marks": {k: {"x": x, "y": y, "size": MARK} for k, (x, y) in mark_origins().items()},
        "page_id": {"x": LEFT + MARK + ID_BIT, "y": TOP, "bit": ID_BIT, "bits": ID_BITS, "order": "most significant first"},
        "cell": {
            "w": CELL_W,
            "h": CELL_H,
            "label_h": LABEL_H,
            "ascender_y": ASCENDER_Y,
            "xheight_y": XHEIGHT_Y,
            "baseline_y": BASELINE_Y,
            "descender_y": DESCENDER_Y,
        },
        "line": {
            "ascender_y": LINE_ASCENDER_Y,
            "xheight_y": LINE_XHEIGHT_Y,
            "baseline_y": LINE_BASELINE_Y,
            "descender_y": LINE_DESCENDER_Y,
        },
        "pages": pages,
    }
