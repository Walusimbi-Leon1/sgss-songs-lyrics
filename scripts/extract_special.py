#!/usr/bin/env python3
"""
Extract the special Song categories from the SGSS Bible tarball:
  - prayers/  : curated major prayers + every Psalm explicitly framed as a prayer
  - lamentations/ : the whole book of Lamentations (5 chapters)
  - songs/    : canonical biblical songs (Song of Moses, Hannah, Deborah,
                Song of the Sea, Habakkuk, Jonah, etc.)

Each extracted passage is written as  <category>/<slug>.txt  preserving the
source verse numbering line format: "N text" so downstream transform +
generate_site can strip numbers + split at <=22 verses.

Bible book files are expected at /tmp/sgss-bible/sgss/<NN>-<Name>.txt
where each chapter begins with a line "Chapter <n>".

Usage:
  python3 scripts/extract_special.py --bible /tmp/sgss-bible/sgss
"""

import argparse
import os
import re

VERSE_LINE = re.compile(r"^(\d+)\s+(.*)$")
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)\s*$", re.MULTILINE)
BOOK_TITLE_RE = re.compile(r"^(The Book of|Book of|The )\w", re.IGNORECASE)


def load_book(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    # drop leading book title line if present
    if lines and BOOK_TITLE_RE.match(lines[0].strip()):
        lines = lines[1:]
    return "\n".join(lines)


def chapters(content):
    """Return list of (num, body) where body is text after the Chapter header."""
    matches = list(CHAPTER_RE.finditer(content))
    out = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        out.append((num, content[start:end].strip()))
    return out


def verse_lines(chap_text):
    """Split a chapter body into (verse_num, text)."""
    out = []
    for ln in chap_text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        m = VERSE_LINE.match(ln)
        if m:
            out.append((int(m.group(1)), m.group(2)))
        else:
            # continuation / non-verse text: attach to previous or skip
            out.append((0, ln))
    return out


def chapter_range(content, start_ch, end_ch):
    return [(n, b) for n, b in chapters(content) if start_ch <= n <= end_ch]


def book_path(bible_dir, name):
    # name like "25-Lamentations" or "05-Deuteronomy"
    p = os.path.join(bible_dir, name + ".txt")
    return p if os.path.exists(p) else None


# ---- canonical song / prayer definitions ----
# (book_file_prefix, chapter, [verse_start, verse_end], slug, out_category)
SONGS = [
    ("02-Exodus",        15, 1, 21, "song-of-the-sea-exodus15",     "songs"),
    ("05-Deuteronomy",   32, 1, 43, "song-of-moses-deuteronomy32",   "songs"),
    ("09-1Samuel",       2, 1, 10, "hannah-song-1samuel-2",        "songs"),
    ("07-Judges",        5, 1, None, "deborah-song-judges-5",      "songs"),
    ("35-Habakkuk",      3, 1, None, "habakkuk-song-habakkuk-3",   "songs"),
    ("32-Jonah",         2, 1, None, "jonah-song-jonah-2",         "songs"),
    ("66-Revelation",    5, 1, 14, "new-song-revelation-5",        "songs"),
]

PRAYERS = [
    ("40-Matthew",       6, 9, 13, "lords-prayer-matthew-6",      "prayers"),
    ("42-Luke",         11, 2, 4,  "lords-prayer-luke-11",        "prayers"),
    ("16-Nehemiah",      1, 5, None, "nehemiah-prayer-neh-1",      "prayers"),
    ("27-Daniel",        6, 1, None, "darius-den-prayer-dan-6",   "prayers"),
    ("17-Esther",        4, 1, 17,   "ester-fast-prayer-esther-4", "prayers"),
    ("26-Ezekiel",       36, 24, 27, "ezekiel-valley-prayer-eze-36", "prayers"),
    ("24-Jeremiah",     33, 1, 6,   "jeremiah-confession-jer-33", "prayers"),
    ("10-2Samuel",       7, 25, 30,  "david-prayer-2sam-7",        "prayers"),
    ("13-1Chronicles",   17, 16, 22, "david-prayer-1chr-17",       "prayers"),
]
# Note: Psalms framed as prayers are pulled from Psalms.txt titles below.


PSALM_PRAYER_PREFIXES = (
    "A Psalm of David", "A Psalm for the dedication",
    "A Song of David the servant of the LORD",
    "A Psalm of Asaph", "A Song of Solomon", "A Psalm of Moses",
    "The LORD a n", "A Song of the sword",
)

# Psalms that are explicitly prayers / directly address God (no title in this Bible, so list them)
PSALM_PRAYER_NUMBERS = {
    4, 5, 6, 7, 8, 9, 10, 17, 26, 27, 28, 31, 35, 38, 41, 42, 43, 54, 55,
    61, 63, 64, 68, 70, 77, 84, 86, 88, 90, 91, 92, 99, 102, 104, 108, 109,
    130, 134, 139, 141, 143, 144, 145, 146, 147, 148, 149, 150,
}


def write_passage(out_dir, slug, lines):
    """lines: list[str] each 'N text'  -> file slug.txt"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bible", default="/tmp/sgss-bible/sgss")
    args = ap.parse_args()
    bd = args.bible

    created = []

    # 1. Lamentations — whole book
    la_path = book_path(bd, "25-Lamentations")
    if la_path:
        content = load_book(la_path)
        for num, body in chapters(content):
            lines = [f"{n} {t}" for n, t in verse_lines(body) if n > 0]
            if lines:
                created.append(write_passage("lamentations", "lamentation_%02d"%num, lines))
        print(f"Lamentations done -> {len(chapters(content))} chapters")

    # 2. Songs
    for book_prefix, ch, vs, ve, slug, cat in SONGS:
        bp = book_path(bd, book_prefix)
        if not bp:
            print("MISSING", book_prefix); continue
        content = load_book(bp)
        chaps = chapter_range(content, ch, ch)
        if not chaps:
            print("no ch", ch, "in", book_prefix); continue
        body = chaps[0][1]
        vlines = verse_lines(body)
        sel = [v for v in vlines if (v[0] >= vs and (ve is None or v[0] <= ve))]
        lines = [f"{n} {t}" for n, t in sel if n > 0]
        if lines:
            created.append(write_passage(cat, slug, lines))

    # 3. Prayers
    for book_prefix, ch, vs, ve, slug, cat in PRAYERS:
        bp = book_path(bd, book_prefix)
        if not bp:
            print("MISSING", book_prefix); continue
        content = load_book(bp)
        chaps = chapter_range(content, ch, ch)
        if not chaps:
            continue
        body = chaps[0][1]
        vlines = verse_lines(body)
        sel = [v for v in vlines if (v[0] >= vs and (ve is None or v[0] <= ve))]
        lines = [f"{n} {t}" for n, t in sel if n > 0]
        if lines:
            created.append(write_passage(cat, slug, lines))

    # 4. Psalms that are prayers (this Bible carries no psalm titles, so use an
    #    explicit set of psalm numbers that directly address God).
    ps_path = book_path(bd, "19-Psalms")
    if ps_path:
        content = load_book(ps_path)
        added = 0
        for num, body in chapters(content):
            if num not in PSALM_PRAYER_NUMBERS:
                continue
            lines = [f"{n} {t}" for n, t in verse_lines(body) if n > 0]
            if lines:
                created.append(write_passage("prayers", "psalm_%03d_prayer"%num, lines))
                added += 1
        print(f"Psalm-prayers done -> {added}")

    print(f"\nTotal files written: {len(created)}")
    for c in created[:30]:
        print("  ", c)


if __name__ == "__main__":
    main()
