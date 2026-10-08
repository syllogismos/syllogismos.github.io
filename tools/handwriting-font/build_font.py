# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools>=4.50", "brotli", "opencv-python-headless>=4.8", "numpy", "pillow"]
# ///
"""Turn the extracted character images into an installable font.

    uv run build_font.py font-work --name "My Hand" [--version 1.000]

Reads font-work/glyphs.json and font-work/glyphs/*.png (from extract_glyphs.py)
and writes, under font-work/output:

    MyHand-Regular.ttf, MyHand-Regular.woff2
    specimen.png          LOOK AT this before calling the font done
    build-report.json     per-character measurements and every warning

Letters keep the size and position they were written at, relative to the
printed baseline. Three gentle corrections are applied, all of them optional:
one global scale so capitals are a standard height, a small nudge of each
letter onto the baseline, and pulling same-kind letters part-way towards a
common height. Use --regularise 0 --no-snap for the handwriting exactly as written.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.timeTools import timestampNow
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

import template_layout as L

UPM = 1000
CAP_HEIGHT = 700
UNITS_PER_MM = CAP_HEIGHT / (L.BASELINE_Y - L.ASCENDER_Y)  # before the global scale

CAPS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DIGITS = set("0123456789")
X_LOWER = set("acemnorsuvwxz")
TALL_LOWER = set("bdhkl")
# Characters whose lowest ink should rest exactly on the baseline.
SITTERS = (CAPS - set("JQ")) | DIGITS | X_LOWER | TALL_LOWER | set("it.!?:…")

# When a character was not written, show one of these instead (first one that exists).
STAND_INS = {
    0x2019: [0x0027],
    0x2018: [0x2019, 0x0027],
    0x0027: [0x2019],
    0x201D: [0x0022],
    0x201C: [0x201D, 0x0022],
    0x0022: [0x201D],
    0x2013: [0x002D],
    0x2014: [0x2013, 0x002D],
    0x002D: [0x2013],
    0x2212: [0x2013, 0x002D],  # minus sign
    0x0060: [0x2018, 0x0027],
    0x00A0: [0x0020],  # no-break space
    0x2010: [0x002D],
    0x2011: [0x002D],
}

Point = tuple[float, float, bool]  # x, y, on-curve


def glyph_name(code: int) -> str:
    from fontTools.agl import UV2AGL

    return UV2AGL.get(code, f"uni{code:04X}")


# ---------- image to outline ----------


def smooth_closed(points: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian-smooth a closed curve, wrapping around its ends."""
    radius = int(sigma * 3)
    if len(points) < 2 * radius + 1:
        return points
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.concatenate([points[-radius:], points, points[:radius]])
    return np.stack([np.convolve(padded[:, i], kernel, mode="valid") for i in range(2)], axis=1)


def trace(ink: np.ndarray, level: int, ppm: float, weight_px: float) -> list[tuple[np.ndarray, bool]]:
    """Outlines of one character as (points in image pixels, is_hole), smoothed and thinned.

    The ink image is enlarged before it is cut at `level`, so the outline follows
    the real edge of the stroke between pixels. Tracing a hard black-and-white
    mask instead leaves stair-steps, which is what made HarshaFont jagged.
    """
    up = 4
    big = cv2.resize(ink, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    big = cv2.GaussianBlur(big, (0, 0), up * 0.45)
    _, big = cv2.threshold(big, level, 255, cv2.THRESH_BINARY)
    if weight_px:
        size = 2 * round(abs(weight_px) * up) + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        big = cv2.dilate(big, kernel) if weight_px > 0 else cv2.erode(big, kernel)
    contours, hierarchy = cv2.findContours(big, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:
        return []
    out = []
    for contour, info in zip(contours, hierarchy[0]):
        is_hole = info[3] != -1
        area = cv2.contourArea(contour) / up**2
        if area < ((0.1 if is_hole else 0.2) * ppm) ** 2:
            continue
        points = smooth_closed(contour[:, 0, :].astype(np.float64), sigma=up * 0.8)
        thin = cv2.approxPolyDP(points.astype(np.float32).reshape(-1, 1, 2), up * 0.25, True)[:, 0, :]
        if len(thin) >= 3:
            out.append((thin.astype(np.float64) / up, is_hole))
    return out


def with_curves(points: np.ndarray) -> list[Point]:
    """Mark which outline points are corners; the rest become curve control points.

    A run of off-curve points is a smooth TrueType curve, so only real corners
    (the ends of a stroke, a sharp turn) need to be on the curve.
    """
    n = len(points)
    if n < 5:
        return [(x, y, True) for x, y in points]
    marked = []
    for i in range(n):
        a = points[i] - points[i - 1]
        b = points[(i + 1) % n] - points[i]
        cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        marked.append((points[i][0], points[i][1], cosine < 0.3))  # turn sharper than about 72 degrees
    return marked


def signed_area(points: list[Point]) -> float:
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1, _), (x2, y2, _) in zip(points, points[1:] + points[:1]))


def load_glyph(folder: Path, entry: dict, weight: float) -> list[list[Point]]:
    """Contours of one character in font units, baseline at y = 0, as written."""
    ink = cv2.imread(str(folder / entry["file"]), cv2.IMREAD_GRAYSCALE)
    scale = UNITS_PER_MM / entry["ppm"]
    baseline = entry["rows"]["baseline"]
    contours = []
    for points, is_hole in trace(ink, entry["level"], entry["ppm"], weight / scale):
        contour = [(x * scale, (baseline - y) * scale, on) for x, y, on in with_curves(points)]
        # TrueType: filled shapes run clockwise, holes counter-clockwise.
        if (signed_area(contour) > 0) != is_hole:
            contour.reverse()
        contours.append(contour)
    return contours


def bounds(contours: list[list[Point]]) -> tuple[float, float, float, float]:
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def transform(contours: list[list[Point]], scale: float = 1.0, dx: float = 0.0, dy: float = 0.0) -> list[list[Point]]:
    return [[(x * scale + dx, y * scale + dy, on) for x, y, on in c] for c in contours]


def to_tt_glyph(contours: list[list[Point]]):
    pen = TTGlyphPointPen(None)
    for contour in contours:
        rounded = [(round(x), round(y), on) for x, y, on in contour]
        pen.beginPath()
        for i, (x, y, on) in enumerate(rounded):
            previous_on = rounded[i - 1][2]
            pen.addPoint((x, y), segmentType=("line" if previous_on else "qcurve") if on else None)
        pen.endPath()
    return pen.glyph()


# ---------- shaping the set ----------


def normalise(glyphs: dict[int, list[list[Point]]], regularise: float, snap: bool, report: dict) -> float:
    """Apply the global scale, baseline snap and height regularisation in place. Returns the x-height."""
    cap_tops = [bounds(glyphs[ord(c)])[3] for c in CAPS if ord(c) in glyphs]
    scale = 1.0
    if len(cap_tops) >= 8:
        scale = min(1.6, max(0.7, CAP_HEIGHT / statistics.median(cap_tops)))
    report["global_scale"] = round(scale, 3)
    for code in glyphs:
        glyphs[code] = transform(glyphs[code], scale=scale)

    if snap:
        for code, contours in glyphs.items():
            if chr(code) not in SITTERS:
                continue
            bottom = bounds(contours)[1]
            if abs(bottom) <= 0.13 * CAP_HEIGHT:
                glyphs[code] = transform(contours, dy=-bottom)
            else:
                report["warnings"].append(f"{chr(code)!r} sits {bottom:+.0f} units off the baseline, too far to correct; rewrite it or accept it")

    for label, members in (("capitals", CAPS), ("digits", DIGITS), ("small letters", X_LOWER), ("tall small letters", TALL_LOWER)):
        present = [ord(c) for c in members if ord(c) in glyphs]
        if len(present) < 4:
            continue
        target = statistics.median(bounds(glyphs[code])[3] for code in present)
        for code in present:
            height = bounds(glyphs[code])[3]
            if height <= 0:
                continue
            if abs(height / target - 1) > 0.3:
                report["warnings"].append(f"{chr(code)!r} is {height / target:.0%} of the usual height for {label}; check it against the specimen")
            if regularise > 0:
                factor = min(1.25, max(0.8, 1 + regularise * (target / height - 1)))
                glyphs[code] = transform(glyphs[code], scale=factor)

    xs = [bounds(glyphs[ord(c)])[3] for c in X_LOWER if ord(c) in glyphs]
    return statistics.median(xs) if xs else 0.56 * CAP_HEIGHT


def side_bearing(char: str, tracking: float) -> float:
    if char in CAPS or char in DIGITS:
        base = 52
    elif char.isalpha():
        base = 42
    else:
        base = 46
    return base * tracking


def build(work: Path, family: str, version: str, regularise: float, snap: bool, tracking: float, weight: float) -> Path:
    record = json.loads((work / "glyphs.json").read_text(encoding="utf-8"))
    report: dict = {"family": family, "version": version, "warnings": [], "glyphs": {}}

    glyphs: dict[int, list[list[Point]]] = {}
    for key, entry in record["glyphs"].items():
        if "file" not in entry:
            continue
        contours = load_glyph(work, entry, weight)
        if contours:
            glyphs[int(key[2:], 16)] = contours
        if "touches-edge" in entry["flags"]:
            report["warnings"].append(f"{entry['char']!r} touched the edge of its box and may be cut off")
    if not glyphs:
        sys.exit("no characters found; run extract_glyphs.py first")

    x_height = normalise(glyphs, regularise, snap, report)

    # An ellipsis that was not written is three of the writer's own full stops.
    if 0x2026 not in glyphs and 0x2E in glyphs:
        dot = glyphs[0x2E]
        left, _, right, _ = bounds(dot)
        step = (right - left) + 2.2 * side_bearing(".", tracking)
        glyphs[0x2026] = [c for i in range(3) for c in transform(dot, dx=i * step)]
        report["warnings"].append("'…' was not written; made from three full stops")

    order = [".notdef", "space"]
    cmap = {0x20: "space"}
    tt_glyphs = {".notdef": to_tt_glyph([[(60, 0, True), (60, 700, True), (440, 700, True), (440, 0, True)], [(110, 50, True), (390, 50, True), (390, 650, True), (110, 650, True)]]), "space": to_tt_glyph([])}
    advances = {".notdef": 500, "space": round(300 * tracking)}
    top, bottom = CAP_HEIGHT, 0.0

    for code in sorted(glyphs):
        char, name = chr(code), glyph_name(code)
        bearing = side_bearing(char, tracking)
        left, low, right, high = bounds(glyphs[code])
        contours = transform(glyphs[code], dx=bearing - left)
        tt_glyphs[name] = to_tt_glyph(contours)
        advances[name] = max(160, round(right - left + 2 * bearing))
        order.append(name)
        cmap[code] = name
        top, bottom = max(top, high), min(bottom, low)
        report["glyphs"][f"U+{code:04X}"] = {"char": char, "advance": advances[name], "top": round(high), "bottom": round(low), "ink_width": round(right - left)}

    for code, options in STAND_INS.items():
        if code in cmap:
            continue
        source = next((o for o in options if o in cmap), None)
        if source is not None:
            cmap[code] = cmap[source]
            if code in {ord(c) for page in L.PAGES for c, _ in page["cells"]}:
                report["warnings"].append(f"{chr(code)!r} was not written; it will show as {chr(source)!r}")

    wanted = [c for page in L.PAGES for c, _ in page["cells"]]
    report["missing"] = [c for c in wanted if ord(c) not in cmap]

    # Vertical metrics follow the tallest and deepest ink, so nothing is clipped.
    ascent = max(850, int(-(-top // 10) * 10) + 40)
    descent = min(-250, int(bottom // 10 * 10) - 40)
    report["metrics"] = {"ascent": ascent, "descent": descent, "cap_height": CAP_HEIGHT, "x_height": round(x_height)}

    ps_name = "".join(ch for ch in family if ch.isalnum()) + "-Regular"
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(tt_glyphs)
    glyf = fb.font["glyf"]
    fb.setupHorizontalMetrics({name: (advances[name], getattr(glyf[name], "xMin", 0) or 0) for name in order})
    fb.setupHorizontalHeader(ascent=ascent, descent=descent)
    fb.setupNameTable(
        {
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"{ps_name};{version}",
            "fullName": f"{family} Regular",
            "version": f"Version {version}",
            "psName": ps_name,
            "copyright": "Digitized from an original handwriting sample.",
        }
    )
    fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0, usWinAscent=ascent, usWinDescent=-descent, sxHeight=round(x_height), sCapHeight=CAP_HEIGHT, achVendID="HAND", fsType=0)
    fb.setupPost()
    # Real timestamps: a head table dated 1904 makes some tools reject the font.
    fb.updateHead(created=timestampNow(), modified=timestampNow(), fontRevision=float(version))

    out = work / "output"
    out.mkdir(exist_ok=True)
    ttf = out / f"{ps_name}.ttf"
    fb.save(str(ttf))
    font = TTFont(str(ttf))
    font.flavor = "woff2"
    font.save(str(out / f"{ps_name}.woff2"))
    TTFont(str(out / f"{ps_name}.woff2")).getGlyphOrder()  # reopen it to prove the file is readable

    specimen(ttf, out / "specimen.png", wanted, cmap, report["metrics"])
    (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"wrote {ttf} ({len(order) - 2} characters, version {version})")
    if report["missing"]:
        print("not in the font: " + " ".join(report["missing"]))
    for warning in report["warnings"]:
        print("warning: " + warning)
    print(f"now look at {out / 'specimen.png'}")
    return ttf


# ---------- proof ----------


def specimen(ttf: Path, path: Path, wanted: list[str], cmap: dict[int, str], metrics: dict) -> None:
    """A proof sheet: every character on guide lines, then running text at three sizes."""
    width, margin = 1800, 60
    image = Image.new("RGB", (width, 100), "white")
    blocks = []

    have = "".join(c for c in wanted if ord(c) in cmap)
    rows = [have[i : i + 27] for i in range(0, len(have), 27)]
    blocks.append(("guides", 64, rows))
    blocks.append(("text", 54, L.SENTENCES))
    blocks.append(("text", 34, ["Handgloves & minimum: the quick brown fox jumps over the lazy dog, 1234567890 times.", "It's a \"test\" (really) - of every-day punctuation; isn't it? Yes! 50% off @ $9.99 #now"]))
    blocks.append(("text", 22, ["When in the course of writing a font it becomes necessary to check small sizes, this line and the next do that job;", "words should hold together, spaces should read as spaces, and no letter should jump above or sink below its neighbours."]))

    height = margin
    for kind, size, lines in blocks:
        height += int(len(lines) * size * 1.75) + 40
    image = Image.new("RGB", (width, height + margin), "white")
    draw = ImageDraw.Draw(image)
    y = margin
    for kind, size, lines in blocks:
        font = ImageFont.truetype(str(ttf), size)
        for line in lines:
            base = y + int(size * 1.15)
            if kind == "guides":
                for value, colour in ((metrics["cap_height"], (170, 200, 255)), (metrics["x_height"], (170, 200, 255)), (0, (255, 120, 120)), (-220, (225, 225, 225))):
                    gy = base - int(value * size / UPM)
                    draw.line([(margin, gy), (width - margin, gy)], fill=colour, width=1)
            draw.text((margin, base), line, font=font, fill="black", anchor="ls")
            y += int(size * 1.75)
        y += 40
    image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("work", type=Path, help="the folder extract_glyphs.py wrote to")
    parser.add_argument("--name", required=True, help='font family name, e.g. "Asha Hand"')
    parser.add_argument("--version", default="1.000", help="raise this on every rebuild, or the old font stays cached")
    parser.add_argument("--regularise", type=float, default=0.5, help="0 keeps each letter's written height, 1 forces same-kind letters to one height")
    parser.add_argument("--no-snap", action="store_true", help="do not nudge letters onto the baseline")
    parser.add_argument("--tracking", type=float, default=1.0, help="multiplies the space around every character")
    parser.add_argument("--weight", type=float, default=0.0, help="font units added to every stroke edge (negative thins); 0 keeps the pen's own weight")
    args = parser.parse_args()
    build(args.work, args.name, args.version, args.regularise, not args.no_snap, args.tracking, args.weight)


if __name__ == "__main__":
    main()
