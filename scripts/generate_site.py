#!/usr/bin/env python3
"""
Generate a GitHub Pages site for SGSS Songs (Simple English Psalms & Song of Solomon).

Features:
  - Strips verse-indicator numbers from displayed lyrics.
  - Splits chapters > 22 verses into multiple parts (<= 22 each).
  - Polished, responsive UI: sticky top nav with jump-to <select> + dark-mode
    toggle, Prev/Next reading buttons, per-part chip navigation, and an index
    page of clickable chapter cards grouped by book.
  - Generates index, per-chapter, per-part HTML pages + a JSON sitemap.

Usage:
  python3 scripts/generate_site.py
  python3 scripts/generate_site.py --songs-dir songs --output-dir docs
"""

import argparse
import json
import math
import os
import re
import html

SONGS_DEFAULT = "songs"
OUTPUT_DEFAULT = "docs"
MAX_VERSES_PER_PART = 22
SITE_TITLE = "SGSS Songs"

VERSE_RE = re.compile(r"^(\d{1,3})\s+(.*)$")


def parse_verses(text):
    """Parse a .txt song file into (title: str, verses: list[str])."""
    lines = text.split("\n")
    title = lines[0].strip() if lines else ""
    verses = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        m = VERSE_RE.match(ln.strip())
        verses.append(m.group(2) if m else ln.strip())
    return title, verses


MAX_PARTS = 3  # soft cap


def split_parts(verses):
    max_per = MAX_VERSES_PER_PART
    if not verses:
        return []
    n = len(verses)
    if n <= max_per:
        return [verses]
    if n <= max_per * 2:
        target = 2
    elif n <= max_per * 3:
        target = 3
    else:
        target = math.ceil(n / max_per)
    base, rem = divmod(n, target)
    sizes = [base + (1 if i < rem else 0) for i in range(target)]
    if any(s > max_per for s in sizes):
        sizes, i = [], 0
        while i < n:
            chunk = min(max_per, n - i)
            sizes.append(chunk)
            i += chunk
    parts_out, idx = [], 0
    for s in sizes:
        parts_out.append(verses[idx: idx + s])
        idx += s
    return parts_out


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)


def book_of(fname):
    return "Song of Solomon" if "SongOfSolomon" in fname else "Psalms"


# ---------- shared nav ----------

def topnav(current_href, all_pages):
    groups = {}
    for p in all_pages:
        groups.setdefault(p["book"], []).append(p)
    opts = []
    for book in ("Psalms", "Song of Solomon"):
        if book not in groups:
            continue
        og = [f'    <optgroup label="{html.escape(book)}">']
        for p in groups[book]:
            sel = " selected" if p["href"] == current_href else ""
            og.append(f'      <option value="{p["href"]}"{sel}>{html.escape(p["label"])}</option>')
        og.append("    </optgroup>")
        opts.append("\n".join(og))
    opts_html = "\n".join(opts)
    return f"""  <nav class="topnav">
    <a href="/" class="brand">🏠 {SITE_TITLE}</a>
    <div class="nav-right">
      <label class="jump">
        <span class="jump-label">Go to</span>
        <select onchange="if(this.value)location.href=this.value">
{opts_html}
        </select>
      </label>
      <button id="theme-toggle" class="theme-btn" type="button" aria-label="Toggle dark mode">🌓</button>
    </div>
  </nav>"""


def prevnext(current_href, all_pages):
    idx = next((i for i, p in enumerate(all_pages) if p["href"] == current_href), None)
    prev_a = next_a = ""
    if idx is not None:
        if idx > 0:
            p = all_pages[idx - 1]
            prev_a = f'<a class="navbtn" href="{p["href"]}">← {html.escape(p["label"])}</a>'
        if idx < len(all_pages) - 1:
            n = all_pages[idx + 1]
            next_a = f'<a class="navbtn" href="{n["href"]}">{html.escape(n["label"])} →</a>'
    if not prev_a:
        prev_a = '<span class="navbtn disabled">← Start</span>'
    if not next_a:
        next_a = '<span class="navbtn disabled">End →</span>'
    return f'  <div class="prevnext">{prev_a}{next_a}</div>'


def partnav(chap, current_part=0):
    if not chap["split"]:
        return ""
    links = []
    for i in range(1, len(chap["parts"]) + 1):
        cls = ' class="active"' if i == current_part else ""
        links.append(f'<a href="{chap["slug"]}-part{i}.html"{cls}>P{i}</a>')
    return '<nav class="partnav">Parts: ' + " ".join(links) + "</nav>"


def page_shell(title, body, current_href, all_pages):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {SITE_TITLE}</title>
<link rel="stylesheet" href="/assets/style.css">
<script src="/assets/theme.js" defer></script>
</head>
<body>
{topnav(current_href, all_pages)}
  <main>
{body}
  </main>
  <footer>Made from <a href="https://github.com/Walusimbi-Leon1/sgss-songs-lyrics">sgss-songs-lyrics</a> · Psalms &amp; Song of Solomon in simple English · verse numbers stripped for easy copying</footer>
</body>
</html>
"""


def index_html(all_pages, chapters):
    books = {}
    for c in chapters:
        books.setdefault(c["book"], []).append(c)
    sections = []
    for book in ("Psalms", "Song of Solomon"):
        if book not in books:
            continue
        cards = []
        for c in books[book]:
            href = f"{c['slug']}-part1.html"
            badge = f' <span class="badge">⤵ {len(c["parts"])} parts</span>' if c["split"] else ""
            chips = ""
            if c["split"]:
                chip_links = "".join(
                    f'<a class="chip" href="{c["slug"]}-part{i}.html">P{i}</a>'
                    for i in range(1, len(c["parts"]) + 1)
                )
                chips = f'<div class="chips">{chip_links}</div>'
            cards.append(
                f'      <a class="chap" href="{href}"><span class="chapnum">{c["num"]}</span>'
                f'<span class="chaptitle">{html.escape(c["plain_title"])}</span>{badge}</a>{chips}'
            )
        grid = "\n".join(cards)
        sections.append(
            f'    <section class="book">\n      <h2>{html.escape(book)}</h2>\n'
            f'      <div class="grid">\n{grid}\n      </div>\n    </section>'
        )
    sections_html = "\n".join(sections)
    body = (
        f'    <h1>{SITE_TITLE} — Simple English Songs</h1>\n'
        f'    <p class="subhead">Simple-English Psalms and the Song of Solomon from the SGSS Bible. '
        f'Verse numbers are stripped from the lyrics so you can copy-paste cleanly. '
        f'Chapters with more than {MAX_VERSES_PER_PART} verses are split into parts — use the part chips to jump within a chapter.</p>\n'
        f'{sections_html}'
    )
    return page_shell(f"{SITE_TITLE}", body, "index.html", all_pages)


def chapter_page_html(chap, part_idx, verses, all_pages):
    label = chap["plain_title"] + (f" — Part {part_idx}" if chap["split"] else "")
    nav = partnav(chap, part_idx)
    verses_html = "\n".join(f"      <p>{html.escape(v)}</p>" for v in verses)
    body = f"""    <h1>{html.escape(label)}</h1>
{nav}
    <article class="lyrics">
{verses_html}
    </article>
{nav}
{prevnext(chap['slug'] + '-part' + str(part_idx) + '.html', all_pages)}"""
    return page_shell(label, body, f"{chap['slug']}-part{part_idx}.html", all_pages)


# ---------- main ----------

def generate(songs_dir, output_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    chapters = []
    files = sorted(f for f in os.listdir(songs_dir) if f.endswith("_simple.txt"))
    for fname in files:
        with open(os.path.join(songs_dir, fname), "r", encoding="utf-8") as f:
            raw = f.read()
        title, verses = parse_verses(raw)
        if not verses:
            continue
        parts = split_parts(verses)
        book = book_of(fname)
        if book == "Song of Solomon":
            num = fname.replace("SongOfSolomon_", "").replace("_simple.txt", "").lstrip("0") or "0"
            slug = safe_name(f"SongOfSolomon_{num}")
            plain = title or f"Song of Solomon {num}"
        else:
            num = fname.replace("Psalm_", "").replace("_simple.txt", "").lstrip("0") or "0"
            slug = safe_name(f"psalm_{num}")
            plain = title or f"Psalm {num}"
        chapters.append({
            "book": book,
            "num": int(num) if num.isdigit() else 0,
            "plain_title": plain,
            "slug": slug,
            "parts": parts,
            "split": len(parts) > 1,
        })

    chapters.sort(key=lambda c: (c["book"] != "Psalms", c["num"]))

    os.makedirs(output_dir, exist_ok=True)
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    all_pages = []
    for c in chapters:
        for i in range(1, len(c["parts"]) + 1):
            all_pages.append({
                "book": c["book"],
                "label": c["plain_title"] + (f" — Part {i}" if c["split"] else ""),
                "href": f"{c['slug']}-part{i}.html",
            })

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(all_pages, chapters))

    sitemap = []
    for chap in chapters:
        for part_idx, part_verses in enumerate(chap["parts"], start=1):
            page_path = os.path.join(output_dir, f"{chap['slug']}-part{part_idx}.html")
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(chapter_page_html(chap, part_idx, part_verses, all_pages))
            sitemap.append({
                "book": chap["book"],
                "label": chap["plain_title"],
                "part": part_idx,
                "href": f"{chap['slug']}-part{part_idx}.html",
                "verses": len(part_verses),
            })

    with open(os.path.join(assets_dir, "sitemap.json"), "w", encoding="utf-8") as f:
        json.dump({"pages": sitemap}, f, indent=2)

    # copy external assets (css/js live beside this script)
    for asset in ("site.css", "theme.js"):
        src = os.path.join(here, asset)
        dst = os.path.join(assets_dir, "style.css" if asset == "site.css" else "theme.js")
        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as f:
                data = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(data)

    print(f"Generated {len(sitemap)} page(s) across {len(chapters)} chapter(s) in {output_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs-dir", default=SONGS_DEFAULT)
    ap.add_argument("--output-dir", default=OUTPUT_DEFAULT)
    args = ap.parse_args()
    generate(args.songs_dir, args.output_dir)
