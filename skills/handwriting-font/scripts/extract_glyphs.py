# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.8", "numpy", "pillow", "pypdfium2"]
# ///
"""Cut photos or scans of the filled-in template into one image per character.

    uv run extract_glyphs.py page1.jpg [page2.jpg] --out font-work

Each input may be a photo, a scan, or a PDF of scans, in any order and any
rotation. For every page the script finds the four corner marks, straightens
the page, reads which page it is, and lifts the ink out of every box.

Outputs, under --out:
    glyphs/U+0041.png      ink mask of one box (white ink on black), not cropped
    glyphs.json            where the guide lines fall in each mask, plus warnings
    check-page1.png        contact sheet to LOOK AT before building the font
    rectified-page1.jpg    the straightened page
    sentences.png          the handwritten sentences, for judging spacing later

Running it again on a re-shot page replaces only that page's characters.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

import template_layout as L

PPM = 16  # pixels per millimetre in the straightened page (about 400 dpi)
INSET = 0.6  # mm kept clear of each box edge
MIN_SPECK = 0.25  # mm; ink blobs smaller than this square are dust


def load(path: Path) -> list[np.ndarray]:
    """Read an image or every page of a PDF as BGR arrays, upright per EXIF."""
    if path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        return [cv2.cvtColor(np.array(page.render(scale=300 / 72).to_pil().convert("RGB")), cv2.COLOR_RGB2BGR) for page in pdf]
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return [cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)]


def darkness(bgr: np.ndarray) -> np.ndarray:
    """How much darker each pixel is than the paper around it (0-255).

    Uses the darkest colour channel, so blue or red ink counts as fully dark,
    and subtracts a local estimate of the paper, so shadows and uneven light
    from a phone photo do not read as ink.
    """
    low = bgr.min(axis=2)
    k = int(3.2 * PPM) | 1
    paper = cv2.morphologyEx(low, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    paper = cv2.GaussianBlur(paper, (0, 0), PPM)
    return cv2.subtract(paper, low)


# ---------- finding and straightening the page ----------


def square_candidates(dark: np.ndarray, threshold: float) -> list[dict]:
    """Solid, roughly square dark blobs of a plausible size for a corner mark."""
    bw = (dark < threshold).astype(np.uint8)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    total = dark.shape[0] * dark.shape[1]
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not 0.00002 * total < area < 0.004 * total:
            continue
        (cx, cy), (w, h), _ = cv2.minAreaRect(contour)
        if min(w, h) < 4 or max(w, h) / min(w, h) > 1.8 or area / (w * h) < 0.72:
            continue
        found.append({"centre": (cx, cy), "area": area, "side": (w * h) ** 0.5})
    return sorted(found, key=lambda c: -c["area"])[:14]


def quad_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])))


def clockwise(points: list[tuple[float, float]]) -> list[int]:
    """Indices of the points in clockwise order as seen on screen."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(range(len(points)), key=lambda i: np.arctan2(points[i][1] - cy, points[i][0] - cx))


def find_marks(bgr: np.ndarray) -> list[tuple[float, float]]:
    """Centres of the four corner marks in the photo, ordered TL, TR, BR, BL."""
    scale = min(1.0, 1800 / max(bgr.shape[:2]))
    small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else bgr
    dark = cv2.GaussianBlur(small.min(axis=2), (5, 5), 0)
    otsu, _ = cv2.threshold(dark, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    best = None
    for threshold in (otsu, otsu * 0.8, otsu * 0.6, otsu * 1.15, 110, 80, 60):
        candidates = square_candidates(dark, threshold)
        for group in combinations(candidates, 4):
            areas = [c["area"] for c in group]
            if max(areas) / min(areas) > 3:
                continue
            centres = [c["centre"] for c in group]
            ring = [centres[i] for i in clockwise(centres)]
            sides = [np.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(ring, ring[1:] + ring[:1])]
            if min(sides) < 12 * group[0]["side"]:
                continue  # marks are far apart; the page-number bits are not
            if max(sides[0], sides[2]) / min(sides[0], sides[2]) > 1.45 or max(sides[1], sides[3]) / min(sides[1], sides[3]) > 1.45:
                continue
            ratio = (sides[0] + sides[2]) / (sides[1] + sides[3])
            if not 1.1 < max(ratio, 1 / ratio) < 1.8:
                continue
            area = quad_area(ring)
            if best is None or area > best[0]:
                best = (area, ring, [group[i] for i in clockwise(centres)])
        if best:
            break
    if best is None:
        raise ValueError("could not find the four black corner squares; retake the photo with all four in view, flat and evenly lit")

    _, ring, group = best
    # The top-left mark has a white centre. Find it to learn which way up the page is.
    centre_light = []
    for (cx, cy), mark in zip(ring, group):
        r = max(1, int(mark["side"] / 8))
        centre_light.append(float(dark[int(cy) - r : int(cy) + r + 1, int(cx) - r : int(cx) + r + 1].mean()))
    ranked = sorted(centre_light, reverse=True)
    if ranked[0] - ranked[1] < 40:
        raise ValueError("found four corner squares but not the one with the white centre (top-left); is that corner covered or blurred?")
    start = centre_light.index(ranked[0])
    ordered = ring[start:] + ring[:start]
    return [(x / scale, y / scale) for x, y in ordered]


def straighten(bgr: np.ndarray) -> np.ndarray:
    """Warp the photo so the page fills the frame at PPM pixels per millimetre."""
    marks = L.mark_origins()
    half = L.MARK / 2
    target = [[(marks[k][0] + half) * PPM, (marks[k][1] + half) * PPM] for k in ("tl", "tr", "br", "bl")]
    matrix = cv2.getPerspectiveTransform(np.float32(find_marks(bgr)), np.float32(target))
    size = (round(L.PAGE_W * PPM), round(L.PAGE_H * PPM))
    return cv2.warpPerspective(bgr, matrix, size, flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def page_number(dark: np.ndarray) -> int:
    """Read the binary page number printed beside the top-left mark."""
    number = 0
    for bit in range(L.ID_BITS):
        x = (L.LEFT + L.MARK + L.ID_BIT + bit * L.ID_BIT + L.ID_BIT / 2) * PPM
        y = (L.TOP + L.ID_BIT / 2) * PPM
        r = int(L.ID_BIT * PPM / 4)
        filled = dark[int(y) - r : int(y) + r, int(x) - r : int(x) + r].mean() > 70
        number = number << 1 | int(filled)
    return number


# ---------- lifting ink out of the boxes ----------


def snap_edge(dark: np.ndarray, expected: float, lo: float, hi: float, vertical: bool) -> float:
    """Find a printed box edge near its expected place (all in mm) and return where it really is."""
    reach = 1.5
    a, b = int((expected - reach) * PPM), int((expected + reach) * PPM)
    lo_px, hi_px = int(lo * PPM), int(hi * PPM)
    strip = dark[lo_px:hi_px, a:b] if vertical else dark[a:b, lo_px:hi_px]
    profile = strip.mean(axis=0 if vertical else 1)
    if profile.size == 0 or profile.max() < 25:
        return expected
    return (a + int(profile.argmax()) + 0.5) / PPM


def ink_threshold(dark: np.ndarray, cells: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Pick the darkness above which a pixel is pen, not printed guide line.

    The level of the printed baseline is measured on the page itself (it is the
    darkest guide), and the pen level from the darkest pixels inside the boxes.
    """
    guide_samples, inner = [], []
    for x, y in cells:
        x0, x1 = int((x + 2) * PPM), int((x + L.CELL_W - 2) * PPM)
        band = dark[int((y + L.BASELINE_Y - 0.6) * PPM) : int((y + L.BASELINE_Y + 0.6) * PPM), x0:x1]
        guide_samples.append(band.max(axis=0))
        inner.append(dark[int((y + L.LABEL_H + 0.5) * PPM) : int((y + L.CELL_H - 1.2) * PPM), x0:x1].ravel())
    guide = float(np.median(np.concatenate(guide_samples)))
    pen = float(np.percentile(np.concatenate(inner), 99.9))
    threshold = max(guide + 0.5 * (pen - guide), guide * 1.2 + 10)
    return threshold, guide, pen


def clean(mask: np.ndarray) -> np.ndarray:
    """Drop dust: blobs that are tiny, both in absolute size and next to the main stroke."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    floor = max((MIN_SPECK * PPM) ** 2, 0.025 * areas.max())
    keep = np.zeros_like(mask)
    for i, area in enumerate(areas, start=1):
        if area >= floor:
            keep[labels == i] = 255
    return keep


def extract_page(bgr: np.ndarray, out: Path, record: dict) -> int:
    page = straighten(bgr)
    dark = darkness(page)
    number = page_number(dark)
    if not 1 <= number <= len(L.PAGES):
        raise ValueError(f"read page number {number}, which this template does not have; the top-left corner may be smudged")
    spec = L.PAGES[number - 1]
    origins = [L.cell_origin(i) for i in range(len(spec["cells"]))]
    threshold, guide, pen = ink_threshold(dark, origins) if origins else (0.0, 0.0, 255.0)
    if pen - guide < 30:
        record["warnings"].append(f"page {number}: the pen is barely darker than the printed lines; use a darker pen or better light")

    sheet_cells = []
    for (char, name), (x, y) in zip(spec["cells"], origins):
        left = snap_edge(dark, x, y + L.LABEL_H, y + L.CELL_H - 1.5, vertical=True)
        right = snap_edge(dark, x + L.CELL_W, y + L.LABEL_H, y + L.CELL_H - 1.5, vertical=True)
        top = snap_edge(dark, y, x + 2, x + L.CELL_W - 2, vertical=False)
        bottom = snap_edge(dark, y + L.CELL_H, x + 2, x + L.CELL_W - 2, vertical=False)
        # Trust the printed spacing between the lines more than either edge alone.
        top = (top + bottom - L.CELL_H) / 2
        x0, x1 = round((left + INSET) * PPM), round((right - INSET) * PPM)
        y0, y1 = round((top + L.LABEL_H) * PPM), round((top + L.CELL_H - INSET) * PPM)
        mask = clean(((dark[y0:y1, x0:x1] > threshold) * 255).astype(np.uint8))

        key = f"U+{ord(char):04X}"
        rows = {k: round((top + v) * PPM) - y0 for k, v in (("ascender", L.ASCENDER_Y), ("xheight", L.XHEIGHT_Y), ("baseline", L.BASELINE_Y), ("descender", L.DESCENDER_Y))}
        entry = {"char": char, "name": name, "page": number, "ppm": PPM, "rows": rows, "flags": []}
        ys, xs = np.nonzero(mask)
        if len(xs) < (0.5 * PPM) ** 2:
            entry["flags"].append("empty")
            (out / "glyphs" / f"{key}.png").unlink(missing_ok=True)
        else:
            edge = 2
            if xs.min() < edge or xs.max() >= mask.shape[1] - edge or ys.min() < edge or ys.max() >= mask.shape[0] - edge:
                entry["flags"].append("touches-edge")
            entry["ink"] = {
                "left": int(xs.min()),
                "right": int(xs.max()),
                "top_above_baseline_mm": round((rows["baseline"] - int(ys.min())) / PPM, 2),
                "bottom_below_baseline_mm": round((int(ys.max()) - rows["baseline"]) / PPM, 2),
            }
            entry["file"] = f"glyphs/{key}.png"
            cv2.imwrite(str(out / entry["file"]), mask)
        record["glyphs"][key] = entry
        sheet_cells.append((key, entry, mask))

    cv2.imwrite(str(out / f"rectified-page{number}.jpg"), cv2.resize(page, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    if sheet_cells:
        contact_sheet(sheet_cells, number).save(out / f"check-page{number}.png")
    if spec["sentences"]:
        top = L.sentences_top(spec)
        crop = page[int((top - 1) * PPM) : int((top + len(L.SENTENCES) * L.LINE_BLOCK_H) * PPM), int(L.LEFT * PPM) : int((L.LEFT + L.CONTENT_W) * PPM)]
        cv2.imwrite(str(out / "sentences.png"), crop)
        print(f"page {number} ({spec['title']}): saved the handwritten sentences")
        return number
    filled = sum("empty" not in e["flags"] for _, e, _ in sheet_cells)
    print(f"page {number} ({spec['title']}): {filled}/{len(sheet_cells)} boxes filled; guide level {guide:.0f}, pen level {pen:.0f}, threshold {threshold:.0f}")
    return number


def contact_sheet(cells: list, number: int) -> Image.Image:
    """Every box of a page as extracted, with the guide lines drawn back in colour."""
    scale = 0.6
    cw = max(m.shape[1] for _, _, m in cells)
    ch = max(m.shape[0] for _, _, m in cells)
    tile_w, tile_h = int(cw * scale) + 8, int(ch * scale) + 22
    rows = -(-len(cells) // L.COLS)
    sheet = Image.new("RGB", (tile_w * L.COLS, tile_h * rows + 22), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((6, 5), f"page {number}: black = ink kept. red box = ink touches the box edge. grey box = empty.", fill=(60, 60, 60))
    colours = {"ascender": (120, 170, 255), "xheight": (120, 170, 255), "baseline": (255, 80, 80), "descender": (120, 170, 255)}
    for i, (key, entry, mask) in enumerate(cells):
        ox, oy = (i % L.COLS) * tile_w + 4, (i // L.COLS) * tile_h + 22 + 16
        tile = Image.fromarray(255 - mask).resize((int(mask.shape[1] * scale), int(mask.shape[0] * scale)), Image.LANCZOS).convert("RGB")
        sheet.paste(tile, (ox, oy))
        for line, row in entry["rows"].items():
            ry = oy + int(row * scale)
            draw.line([(ox, ry), (ox + tile.width, ry)], fill=colours[line], width=1)
        outline = (220, 0, 0) if "touches-edge" in entry["flags"] else (170, 170, 170) if "empty" in entry["flags"] else (225, 225, 225)
        draw.rectangle([ox - 1, oy - 1, ox + tile.width, oy + tile.height], outline=outline, width=2 if outline[0] == 220 else 1)
        label = entry["char"] if entry["char"].isascii() else entry["name"]
        draw.text((ox, oy - 14), f"{key}  {label}  {entry['name'] if entry['char'].isascii() else ''}".rstrip(), fill=(40, 40, 40))
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path, help="photos, scans or PDFs of the filled-in pages")
    parser.add_argument("--out", type=Path, default=Path("font-work"))
    args = parser.parse_args()

    (args.out / "glyphs").mkdir(parents=True, exist_ok=True)
    record_path = args.out / "glyphs.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {"glyphs": {}}
    record["warnings"] = []

    seen, failed = set(), False
    for path in args.inputs:
        for index, image in enumerate(load(path)):
            where = f"{path.name}" + (f" (page {index + 1})" if path.suffix.lower() == ".pdf" else "")
            try:
                number = extract_page(image, args.out, record)
            except ValueError as error:
                print(f"{where}: {error}", file=sys.stderr)
                failed = True
                continue
            if number in seen:
                print(f"{where}: this is template page {number} again; it replaced the earlier one", file=sys.stderr)
            seen.add(number)

    glyphs = record["glyphs"]
    expected = {f"U+{ord(c):04X}" for page in L.PAGES for c, _ in page["cells"]}
    missing = sorted(k for k in expected if k not in glyphs or "empty" in glyphs[k]["flags"])
    touching = sorted(k for k, g in glyphs.items() if "touches-edge" in g["flags"])
    record["missing"] = missing
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\n{len(expected) - len(missing)} of {len(expected)} characters extracted into {args.out}/glyphs")
    if missing:
        print("not written or not yet scanned: " + " ".join(chr(int(k[2:], 16)) for k in missing))
    if touching:
        print("ink touches the box edge (may be cut off): " + " ".join(chr(int(k[2:], 16)) for k in touching))
    for warning in record["warnings"]:
        print("warning: " + warning)
    print(f"now look at {args.out}/check-page*.png before building the font")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
