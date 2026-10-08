---
title: "Make a Font From Your Handwriting With a Coding Agent"
date: 2026-10-08T18:30:00+05:30
---

The text you are reading is set in HarshaFont, a font made from one phone photo of a handwritten alphabet. Codex built it in about forty minutes. It works, but getting there took a few rounds of me saying “that looks wrong”, and the font still has gaps.

This post is the cleaned up version of that process. There is a one page template you can print, and a skill that lets Claude Code or Codex turn the filled in page into a font.

-   [Download the template (PDF)](https://raw.githubusercontent.com/syllogismos/syllogismos.github.io/master/skills/handwriting-font/assets/handwriting-font-template.pdf)
-   [The skill, on GitHub](https://github.com/syllogismos/syllogismos.github.io/tree/master/skills/handwriting-font)

![HarshaFont: capitals, small letters and numbers](/images/handwriting-font/harshafont.png)

## How the first font was made

The input was a plain white sheet. The alphabet was written on it in blue ballpoint, capitals and small letters in pairs, four rows of them, then a row of numbers. No boxes, no lines. I took a photo and gave it to Codex.

Codex straightened the photo, separated the ink from the paper, cut out each letter, traced its outline and assembled a font file. All of it was Python: OpenCV for the image work and fontTools to build the font.

## What went wrong

**Letters got cropped.** The first attempt straightened the page using the corners of the paper, and that cut the tops off C, D, E, F and G in the first row. I had to point it out.

**The heights were all over the place.** This was the big one. On blank paper nobody writes every letter the same size, and there is nothing in the photo that says where a `g` should sit compared to an `a`. In the first version the `g` was about three times the height of the `q`, and the tails sat on the line instead of hanging below it. I asked for the letters to be normalised to where they are supposed to be on a line. The fix was to stretch every letter into a box for its kind (capitals, small letters, letters with tails). It looks much better, but it changes the proportions of letters that were written small on purpose.

**There is no punctuation.** The sheet only had letters and numbers. So every full stop, comma and bracket on this blog is borrowed from a different font.

**The edges are rough.** The outlines are made of short straight lines. At text sizes you can’t tell. In a big title you can.

**None of it can be reused.** Where the page corners are, where each letter is, which blob of ink belongs to which letter: all of it was worked out by looking at that one photo. A second person’s handwriting would mean starting again.

Some things are not mistakes. The small `r` looks like an `s` and the `2` looks like a `Z`, because that is how they were written.

## The template

Almost everything above comes from the sheet of paper, not from the code. So the fix is a better sheet of paper.

![The template: one box for each character, with four guide lines in every box](/images/handwriting-font/template.png)

-   One side of A4, with a box for each of 108 characters: capitals, small letters, numbers, punctuation and symbols.
-   Four guide lines in every box. Capitals and tall letters reach the top line, small letters reach the dashed line, everything sits on the dark line, and tails drop to the bottom line. The lines are light gray so they disappear when the page is scanned.
-   A black square in each corner. They let the software straighten a photo taken at an angle, and one of them tells it which way up the page is.
-   A second page, which is optional, with five sentences to copy at your normal size. That shows how you really space letters, which separate boxes can’t.
-   A third page that you don’t write on. It shows every character in a plain font on the same lines, so you can see where a comma, a quote mark or an asterisk is supposed to sit.

## The skill

A skill is a folder of instructions and scripts that a coding agent picks up when the task matches. This one has the template, a script that cuts a photo of the page into characters, a script that builds the font, and notes on everything that went wrong the first time so the agent doesn’t repeat it.

It needs [uv](https://docs.astral.sh/uv/) installed. To install the skill for both agents:

```bash
git clone --depth 1 https://github.com/syllogismos/syllogismos.github.io /tmp/syllogismos
cp -r /tmp/syllogismos/skills/handwriting-font ~/.claude/skills/
cp -r /tmp/syllogismos/skills/handwriting-font ~/.codex/skills/
```

## How to use it

1.  Print the template at 100% size.
2.  Fill it in with a black pen that makes a line of at least 0.5 mm. A thin ballpoint gives a thin, broken font.
3.  Scan it, or photograph it lying flat in even light with all four corner squares in the picture.
4.  Give the photo to Claude Code or Codex and say something like “make a font called Asha Hand from this”.

The agent cuts the page up and shows you a sheet of every character it found, with any that touch the edge of their box marked in red. If a letter came out badly, you write just that one again on a fresh print and photograph it. Then it builds the font and shows you a specimen before you install anything.

## What it does not do

-   No joined up cursive. We tried to get a cursive version out of the first sample and it was bad enough that I never used it.
-   No kerning, so pairs like “AV” are spaced like any other pair.
-   One drawing for each character, so every `e` is the same `e`.
-   No accented letters.

One more thing you should know: I have tested the template and the scripts on simulated photos of the page, at an angle and with shadows, but not yet with a real printed sheet. HarshaFont itself was made the old way. Rebuilding it from the template, with punctuation this time, is next.
