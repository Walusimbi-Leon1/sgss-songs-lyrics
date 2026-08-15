#!/usr/bin/env python3
"""
Generate a GitHub Pages site for SGSS Songs (Simple English Psalms).

Features:
  - Strips verse-indicator numbers from displayed lyrics.
  - Splits chapters > 22 verses into multiple parts (2 parts if > 22, 3 parts if > 44).
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

# regex: a verse line like "1 ", "12 ", "123 " at the very start, followed by text
VERSE_RE = re.compile(r"^(\d{1,3})\s+(.*)$")


def parse_verses(text):
    """Parse a .txt song file into (title: str, verses: list[str])."""
    lines = text.split("\n")
    title = lines[0].strip() if lines else ""
    verse_lines = [l for l in lines[1:] if l.strip()]
    verses = []
    for ln in verse_lines:
        m = VERSE_RE.match(ln.strip())
        if m:
            num, body = m.group(1), m.group(2)
            verses.append(body)
        else:
            # continuation line (e.g., blank-numbered verses) — keep the body
            verses.append(ln.strip())
    return title, verses


MAX_PARTS = 3  # soft cap: exceptionally long chapters split into at most 3 parts

# NOTE: Psalm 119 (176 verses in the real Bible) exceeds 3*22 = 66, so it is
# allowed to use MORE than 3 parts to avoid dropping verses. The 3-part target
# applies to "exceptionally long" chapters in the 45-66 verse range (e.g.
# Chapter 18 with ~40-44 verses). Chapters > 66 verses get ceil(n/22) parts.


def split_parts(verses, max_per=MAX_VERSES_PER_PART, max_parts=MAX_PARTS):
    """
    Split verses into parts.

    Rules (from the SGSS Songs spec):
      - Each part must stay strictly under `max_per` verses (<= 22).
      - Chapters > 22 verses split into 2 parts.
      - Exceptionally long chapters (45-66 verses) split into 3 parts.
      - Psalm 119-style chapters (> 66 verses) get ceil(n/22) parts so no verses are lost.
    """
    if not verses:
        return []
    n = len(verses)
    if n <= max_per:
        return [verses]

    # Decide how many parts to aim for.
    if n <= max_per * 2:
        target = 2
    elif n <= max_per * 3:
        target = 3
    else:
        target = math.ceil(n / max_per)

    # Even distribution; if any part would exceed max_per, switch to greedy
    # chunking which always respects the limit (may yield one more part).
    base, rem = divmod(n, target)
    sizes = [base + (1 if i < rem else 0) for i in range(target)]
    if any(s > max_per for s in sizes):
        sizes = []
        i = 0
        while i < n:
            chunk = min(max_per, n - i)
            sizes.append(chunk)
            i += chunk

    parts_out, idx = [], 0
    for s in sizes:
        parts_out.append(verses[idx : idx + s])
        idx += s
    return parts_out


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)


# ---------- HTML pieces ----------

def page(title, body, extra_class=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <a href="/" class="home">🏠 SGSS Songs Home</a>
  <main class="{extra_class}">
{body}
  </main>
  <footer>Made from <a href="https://github.com/Walusimbi-Leon1/sgss-songs-lyrics">sgss-songs-lyrics</a> · Psalms in simple English · verse numbers stripped for easy copying</footer>
</body>
</html>
"""


def index_html(chapters_meta, total_parts):
    rows = []
    for c in chapters_meta:
        for part_idx, part in enumerate(c["parts"], start=1):
            href = f"{c['slug']}-part{part_idx}.html"
            label = c["label"]
            if c["split"]:
                label = f"{c['label']} — Part {part_idx}"
            rows.append(
                f'    <li><a href="{href}">{html.escape(label)}</a> '
                f'<span class="meta">{len(part)} verses</span></li>'
            )
    rows_html = "\n".join(rows)
    return page(
        "SGSS Songs — Simple English Psalms",
        f"""<h1>SGSS Songs — Simple English Psalms</h1>
<p class="subhead">Simple-English Psalms from the SGSS Bible. Numbers are stripped from the lyrics so you can copy-paste cleanly. Chapters with more than {MAX_VERSES_PER_PART} verses are split into parts.</p>
<ul class="index">
{rows_html}
</ul>""",
        extra_class="index",
    )


def chapter_page_html(chap, part_idx, verses):
    slug = chap["slug"]
    label = chap["label"]
    if chap["split"]:
        label = f"{chap['label']} — Part {part_idx}"
    nav = ""
    if chap["split"]:
        links = []
        for i in range(1, len(chap["parts"]) + 1):
            cls = "current" if i == part_idx else ""
            links.append(f'<a href="{slug}-part{i}.html" class="{cls}">P{i}</a>')
        nav = '<nav class="part-nav">Parts: ' + " ".join(links) + "</nav>"

    verses_html = "\n".join(
        f"      <p>{html.escape(v)}</p>" for v in verses
    )
    return page(
        f"{label} — SGSS Songs",
        f"""<h1>{html.escape(label)}</h1>
{nav}
<article class="lyrics">
{verses_html}
</article>
{nav if chap["split"] else ""}""",
        extra_class="chapter",
    )


# ---------- main generation ----------

def generate(songs_dir, output_dir):
    chapters = []
    files = sorted(f for f in os.listdir(songs_dir) if f.endswith("_simple.txt"))
    for fname in files:
        path = os.path.join(songs_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        title, verses = parse_verses(raw)
        if not verses:
            # skip empty/stub files
            continue
        parts = split_parts(verses)
        num = fname.replace("Psalm_", "").replace("_simple.txt", "").lstrip("0") or "0"
        slug = safe_name(f"psalm_{num}")
        chapters.append(
            {
                "label": title or f"Psalm {num}",
                "slug": slug,
                "parts": parts,
                "split": len(parts) > 1,
                "num": int(num) if num.isdigit() else 0,
            }
        )

    # sort by chapter number
    chapters.sort(key=lambda c: c["num"])

    os.makedirs(output_dir, exist_ok=True)
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # index
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(chapters, None))

    # per-part chapter pages
    sitemap = []
    for chap in chapters:
        for part_idx, part_verses in enumerate(chap["parts"], start=1):
            page_path = os.path.join(output_dir, f"{chap['slug']}-part{part_idx}.html")
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(chapter_page_html(chap, part_idx, part_verses))
            rel = f"{chap['slug']}-part{part_idx}.html"
            sitemap.append({"label": chap["label"], "part": part_idx, "href": rel, "verses": len(part_verses)})

    # sitemap.json (handy for copying tools / future search)
    with open(os.path.join(assets_dir, "sitemap.json"), "w", encoding="utf-8") as f:
        json.dump({"chapters": chapters_meta(chapters), "pages": sitemap}, f, indent=2)

    # assets/style.css
    css = """body {
  max-width: 720px;
  margin: 2rem auto;
  padding: 0 1rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #222;
}
a { color: #096; }
a:hover { text-decoration: underline; }
footer { margin-top: 3rem; color:#777; font-size:.85rem; }
.home { display:inline-block; margin-bottom:1rem; }
.index ul, .chapter article { list-style:none; padding:0; }
.index li { margin:.4rem 0; }
.meta { color:#777; font-size:.8rem; }
.chapter article p { margin:.5rem 0; }
.part-nav { margin:1rem 0; }
.current { font-weight:700; text-decoration:underline; }
.subhead { color:#555; }
"""
    with open(os.path.join(assets_dir, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)

    print(f"Generated {len(sitemap)} page(s) across {len(chapters)} chapter(s) in {output_dir}")


def chapters_meta(chapters):
    return [{"label": c["label"], "parts": len(c["parts"]), "split": c["split"]} for c in chapters]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--songs-dir", default=SONGS_DEFAULT)
    ap.add_argument("--output-dir", default=OUTPUT_DEFAULT)
    args = ap.parse_args()
    generate(args.songs_dir, args.output_dir)
