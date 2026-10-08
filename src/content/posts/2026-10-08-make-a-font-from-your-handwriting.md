---
title: "Make a Font From Your Handwriting With a Coding Agent"
date: 2026-10-08T18:30:00+05:30
---

The text you are reading is set in HarshaFont, a font made from a photo of a handwritten alphabet. Here is how to make one of your own handwriting. You print a page, fill it in, take a photo, and Claude Code or Codex does the rest.

## 1. Print the template

[Download the template (PDF)](https://raw.githubusercontent.com/syllogismos/syllogismos.github.io/master/skills/handwriting-font/assets/handwriting-font-template.pdf)

Print page 1 on A4 or Letter paper at 100% size. Page 2 is optional and page 3 is only a reference, so you can leave them on the screen.

![The template: one box for each character, with four guide lines in every box](/images/handwriting-font/template.png)

## 2. Fill it in

-   Use a black pen that makes a line of at least 0.5 mm. A gel pen or a fineliner works. A thin ballpoint gives a thin, broken font.
-   Write one character in each box. The small gray character in the corner tells you which one.
-   Sit every letter on the dark line.
-   Capitals and tall letters like `b d h k l` reach the top line.
-   Small letters like `a c e n o` reach the dashed line.
-   Tails of `g j p q y` drop to the bottom line.
-   Don’t touch the edges of the box.
-   If you are not sure where a comma or a quote mark should sit, look at page 3 of the PDF.
-   Skip any character you don’t want. It will be left out of the font.

Page 2 has five sentences to copy at your normal size. It is optional, but it helps get the spacing between letters right.

## 3. Take a photo

Lay the page flat in even light and photograph it from straight above. All four black corner squares have to be in the picture. A scan at 300 dpi or more is even better.

## 4. Give it to your coding agent

You need [uv](https://docs.astral.sh/uv/) installed. Open Claude Code or Codex in any folder, attach your photo, and paste this. Change the font name in the first line.

````markdown
Make a font called "My Hand" from the attached photo, following these instructions.

---
name: handwriting-font
description: Make an installable font (TTF and WOFF2) from someone's handwriting, using a printable one-page template that they fill in and photograph or scan. Use when the user wants a font of their own or someone else's handwriting, hands over a photo or scan of the filled-in template, asks for the blank template, or wants to fix or rebuild a font made this way.
---

# Handwriting font

Turn a filled-in template into a font. The person prints one A4 page, writes 108
characters in boxes (A-Z, a-z, 0-9, punctuation, symbols), and photographs or
scans it. Two scripts do the rest: one cuts the page into characters, one builds
the font. Your job is to run them, **look at what they produce**, and get bad
characters rewritten instead of patching them.

Everything runs through `uv`, which fetches the Python packages each script
names. The scripts sit in `scripts/` next to this file; run them from there, or
give their full path.

## 0. Get the scripts

If `scripts/` and `assets/` are not beside this file (for example, these
instructions were pasted into a chat), fetch them first and work from that
folder. `uv` must be installed (https://docs.astral.sh/uv/).

```sh
git clone --depth 1 https://github.com/syllogismos/syllogismos.github.io /tmp/syllogismos
cd /tmp/syllogismos/skills/handwriting-font
```

## 1. Give them the template

`assets/handwriting-font-template.pdf` is ready to print. Page 1 holds every
character. Page 2 is optional: five sentences to copy at normal size, which you
later use to judge spacing. Page 3 is a reference to look at, not to fill in: it
shows every character in a plain typeface on the same lines, so the writer can
see where a comma, a quote mark or an asterisk sits.

Pass these on with the file:

- Print at 100% ("actual size") on A4 or US Letter.
- Use a **black pen with a line of 0.5 mm or more** (gel pen or fineliner). A
  thin ballpoint gives a spindly font and strokes that break up.
- Every letter sits on the dark line. Capitals and tall letters reach the top
  line, small letters reach the dashed line, tails drop to the bottom line.
- Keep clear of the box edges. A box left empty is simply left out of the font.
- Scan at 300 dpi or more, or photograph the page lying flat, in even light,
  filling the frame, with all four black corner squares visible.

To change the template (box size, characters, line shades), edit
`scripts/template_layout.py` and rerun `uv run make_template.py
../assets/handwriting-font-template.pdf --layout ../assets/layout.json`. The
extraction reads the same layout, so the two cannot drift apart. A sheet printed
from an older layout will no longer extract.

## 2. Cut the page into characters

```sh
uv run scripts/extract_glyphs.py photo.jpg [page2.jpg] --out font-work
```

Inputs can be photos, scans or PDFs, in any order and any rotation. Then open
`font-work/check-page1.png` and actually look at it. It shows every box as
extracted, with the guide lines drawn back in colour. Check for:

- **Red boxes**: ink reaches the box edge, so the letter may be cut off.
- **Wrong character in a box**: O and 0, l and I and 1, the three dashes, and
  straight versus curly quotes are the usual mix-ups.
- **Stray marks**: a speck, a bit of a neighbouring letter, a line fragment.
- **Broken strokes**: gaps in a letter mean the pen was too thin or too faint.
- **Letters far off the red baseline**, or far smaller than their neighbours.

If the script cannot find the corner squares, or reads an impossible page
number, the photo is the problem (a corner cropped, covered, or blurred). Ask
for a new photo. Do not hand-pick coordinates to rescue it.

## 3. Fix problems at the source

For anything wrong with a character, the fix is for the person to **rewrite it
and re-shoot**: print the page again, fill in only the boxes that need redoing,
and run the extraction on the new photo into the same `--out` folder. Only the
boxes with ink in them are replaced.

Do not redraw, retouch or "improve" a letter yourself. Odd letterforms are the
handwriting. Show the person what you see and let them decide; they may well
want their strange lowercase r kept.

## 4. Build the font

```sh
uv run scripts/build_font.py font-work --name "Asha Hand" --version 1.000
```

Writes `font-work/output/`: the `.ttf`, a `.woff2`, `specimen.png` and
`build-report.json`. Open `specimen.png` and look at it:

- The first rows show every character on guide lines. Letters should sit on the
  red line, and small letters should reach a common height.
- The sentences are the same five as on page 2 of the template. If the person
  filled that page in, compare with `font-work/sentences.png`: the font should
  have about the same rhythm and spacing as their real writing.
- The small text at the bottom shows whether words hold together.

Relay every warning the script prints. Then show the person the specimen before
calling it done.

Adjustments, in the order to reach for them:

| Problem | Option |
| --- | --- |
| Letters too tight or too loose | `--tracking 1.15` (or `0.9`) |
| Heights look uneven | `--regularise 0.8` (default 0.5; 1 forces one height) |
| It looks too tidy, not like the writing | `--regularise 0 --no-snap` |
| Strokes too thin, and they asked for heavier | `--weight 8` (font units per edge) |

Only change the weight if the person asks. A font faked heavier than the pen
looks blobby, and a rewrite with a thicker pen is better.

## 5. Hand it over

- **Raise `--version` on every rebuild** (1.000, 1.100, ...). Operating systems
  and apps cache fonts by name and version, and will keep showing the old one.
  Tell the person to remove the old install before installing the new file.
- To install: open the `.ttf` and choose Install (Font Book on macOS;
  right-click, Install on Windows). Use the `.woff2` on websites.
- State what the font does not contain. `build-report.json` lists `missing`
  characters, and the stand-ins used (for example a straight quote shown where
  a curly one was not written).

## Things that have gone wrong before

This skill exists because a first font was built from a freehand sheet with no
template. Each of these cost a rebuild:

- **Letters cropped at the page edge.** The straightening used the paper's own
  corners and cut the tops off the first row. The template's corner squares sit
  well inside the page, and the red boxes flag any ink at a box edge.
- **Heights all over the place.** Without guide lines there was no way to know
  where a g should sit relative to an a, so every letter was stretched to fill
  a guessed box, which distorted proportions. Here letters keep their written
  size and position; do not "normalise" by stretching individual letters.
- **The paper edge and desk read as ink.** Solved here by measuring darkness
  against the local paper and reading only inside the boxes.
- **Fixed box positions split letters.** Never assume where a box is in the
  photo; the script locates each printed box edge.
- **Jagged outlines at large sizes.** Outlines are now cut from the ink's real
  darkness between pixels and smoothed. If a font still looks rough, the scan
  was too small: ask for a higher-resolution scan, not more smoothing.
- **No punctuation.** The first font had letters and digits only, so every
  sentence borrowed full stops and commas from another typeface. Encourage the
  person to fill in the whole sheet.
- **A build that silently did not run.** In a sandbox, `uv` can fail to open
  its cache ("Operation not permitted") and the old files stay in place. If a
  result does not change, check that the command actually ran; allow `uv` its
  cache, or set `UV_CACHE_DIR` to a writable folder.
- **A fake bold.** Thickening the font by outlining it in a PDF was asked for
  and then rejected on sight. Keep the pen's weight unless told otherwise.
- **A separate "cursive" version** built from the same sample was rejected
  outright. Joined-up writing needs its own sample and its own approach; do not
  offer to derive it from this template.

## What this does not do

No kerning pairs, no joined-up cursive, no accented letters, and one drawing per
character (so repeated letters are identical). Say so if asked.
````

The agent shows you every character it found before it builds anything. If a letter came out badly, write just that one again on a fresh print and send the new photo.

## 5. Install the font

The agent gives you a `.ttf` file. Open it and click Install. On Windows, right click it and choose Install.

A note: I have tested this on simulated photos of the page, not yet on a real printed sheet. If it breaks for you, tell me.
