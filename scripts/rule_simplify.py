#!/usr/bin/env python3
"""
Rule-based fallback simplifier for SGSS Psalms.

Used when the AI model returns empty or non-conforming output, so that NO
chapter is ever left as a permanent stub. It performs a conservative,
deterministic archaic-English -> simple-English replacement while keeping
verse numbers intact (verse numbers are stripped later on display).

This is intentionally simple and safe: it never invents theology, only
substitutes common archaic words with everyday equivalents and trims
stiff phrasing. Quality is lower than the AI version but guaranteed to
produce readable, complete content.
"""

import argparse
import re
import sys

# Ordered so longer phrases match before shorter fragments.
REPLACEMENTS = [
    (r"\bthee\b", "you"),
    (r"\bthou\b", "you"),
    (r"\bthy\b", "your"),
    (r"\bthine\b", "yours"),
    (r"\bthyself\b", "yourself"),
    (r"\bunto\b", "to"),
    (r"\bhast\b", "have"),
    (r"\bhath\b", "has"),
    (r"\bdoth\b", "does"),
    (r"\bdost\b", "do"),
    (r"\bshall\b", "will"),
    (r"\bwilt\b", "will"),
    (r"\bart\b", "are"),
    (r"\bbehold\b", "look"),
    (r"\bverily\b", "truly"),
    (r"\bwherefore\b", "why"),
    (r"\bwhither\b", "where"),
    (r"\bwhence\b", "from where"),
    (r"\bnigh\b", "near"),
    (r"\bbefall\b", "happen to"),
    (r"\bbespake\b", "spoke to"),
    (r"\bsaying\b", "say"),
    (r"\bsaith\b", "says"),
    (r"\bsaidst\b", "said"),
    (r"\bspake\b", "spoke"),
    (r"\bye\b", "you"),
    (r"\bo\b", "oh"),
    (r"\bLORD\b", "Lord"),
    (r"\bGOD\b", "God"),
    (r"\bSelah\b", ""),
    (r"\bheathen\b", "nations"),
    (r"\bungodly\b", "wicked"),
    (r"\brighteous\b", "good"),
    (r"\brighteousness\b", "goodness"),
    (r"\bwickedness\b", "evil"),
    (r"\bsinners\b", "those who do wrong"),
    (r"\bsin\b", "wrong"),
    (r"\btransgression\b", "wrongdoing"),
    (r"\bsaints\b", "God's people"),
    (r"\bcongregation\b", "community"),
    (r"\bsons of men\b", "people"),
    (r"\bchildren of men\b", "people"),
    (r"\bbenefit\b", "good"),
    (r"\bsuccor\b", "help"),
    (r"\bsorrowful\b", "sad"),
    (r"\bafflicted\b", "hurt"),
    (r"\bwrath\b", "anger"),
    (r"\bcommandment\b", "teaching"),
    (r"\bstatutes\b", "rules"),
    (r"\btestimonies\b", "promises"),
    (r"\bprecepts\b", "instructions"),
    (r"\bmercies\b", "kindness"),
    (r"\bmerciful\b", "kind"),
    (r"\blovingkindness\b", "love"),
    (r"\beverlasting\b", "eternal"),
    (r"\bforever\b", "always"),
    (r"\bfor ever\b", "always"),
    (r"\biniquities\b", "wrongs"),
    (r"\biniquity\b", "wrong"),
    (r"\bpraise\b", "thank"),
    (r"\bhallelujah\b", "praise the Lord"),
    (r"\bredeem\b", "save"),
    (r"\bredeemer\b", "savior"),
    (r"\brefuge\b", "safe place"),
    (r"\bstrength\b", "power"),
    (r"\bsalvation\b", "rescue"),
    (r"\bvengeance\b", "payback"),
    (r"\bvanity\b", "emptiness"),
    (r"\bvain\b", "useless"),
    (r"\bdiligently\b", "carefully"),
    (r"\bwrought\b", "did"),
    (r"\bwherein\b", "where"),
    (r"\bwhereof\b", "of which"),
    (r"\bthereof\b", "of it"),
    (r"\btherein\b", "in it"),
    (r"\bthereunto\b", "to it"),
    (r"\bherewith\b", "with this"),
    (r"\bperadventure\b", "maybe"),
    (r"\bnatheless\b", "still"),
    (r"\bnotwithstanding\b", "even so"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in REPLACEMENTS]


def simplify_line(line: str) -> str:
    # Preserve a leading verse number like "12 " or "12  ".
    m = re.match(r"^(\d+)\s+(.*)$", line)
    if not m:
        return line
    num, rest = m.group(1), m.group(2)
    for pat, rep in COMPILED:
        rest = pat.sub(rep, rest)
    # Collapse multiple spaces left by removed words (e.g. "Selah" -> "").
    rest = re.sub(r"\s{2,}", " ", rest).strip()
    # Drop a trailing leftover space before punctuation.
    rest = re.sub(r"\s+([.,;:!?])", r"\1", rest)
    return f"{num} {rest}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file")
    ap.add_argument("--output", "-o", required=True)
    args = ap.parse_args()

    with open(args.input_file, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    title = lines[0].strip() if lines else ""
    out_lines = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        out_lines.append(simplify_line(ln))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(title + "\n\n" + "\n".join(out_lines) + "\n")

    print(f"Rule-based fallback wrote: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
