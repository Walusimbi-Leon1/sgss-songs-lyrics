#!/usr/bin/env python3
"""
Transform Psalms chapters into simple, easy-to-read English.

This script:
1. Reads Psalms from the SGSS Bible repo (or local files)
2. Transforms each chapter using an AI model
3. Saves each chapter individually
4. Optionally commits and pushes each chapter

Models:
  - oc/hy3-free (maps to tencent-tokenhub/hy3-preview via OpenRouter)
  - NVIDIA models (nvidia/nemotron-4-340b-reward, etc.)
  - Any OpenRouter model

Environment Variables:
  - OPENROUTER_API_KEY: *** API key (primary)
  - NVIDIA_API_KEY: *** API key (fallback)
  - MODEL: Model to use (default: oc/hy3-free)
  - COMMIT_AND_PUSH: Set to "true" to auto-commit and push after each chapter
"""

import argparse
import os
import re
import sys
import textwrap

import requests

# ─── Configuration ───

DEFAULT_MODEL = os.environ.get("MODEL", "oc/hy3-free")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2000"))
TEMPERATURE = 0.3

# ─── System Prompt ───

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a text simplification expert. Your job is to rewrite Psalms text from archaic/poetic English into very simple, modern English that is easy to understand and read — like a conversation with a friend.

    Key Guidelines:
    1. Replace archaic words: "thee"→"you", "thou"→"you", "thy"→"your", "thine"→"yours", "unto"→"to", "saying"→"say", "behold"→"look", "verily"→"truly", "the LORD"→"the Lord", "sons of men"→"people", "heathen"→" nations", "congregation"→"community", etc.
    2. Use short, simple sentences — break up long ones.
    3. Keep the core meaning and spiritual message intact — do not change theological content.
    4. Keep verse numbers at the start of each verse.
    5. Write a conversational tone — warm, like talking to a friend, not a formal church reading.
    6. DO NOT make it look like standard Bible versions (NIV, ESV, NKJV, etc.) — make it distinctively simple and fresh.
    7. Use everyday words: "help" not "succor", "sad" not "sorrowful", "hurt" not "afflicted", "angry" not "wrath", "talk" not "commandment", "rich" not "prosperity".
    8. You may keep "Selah" as a gentle pause marker or remove it if it doesn't flow naturally.

    Output Format: Keep each verse on its own line, starting with the verse number. No markdown, no extra commentary.

    Example transformation:
    Input: "1 Blessed is the man that walks not in the counsel of the ungodly"
    Output: "1 Happy are those who don't follow the advice of the wicked"
""").strip()

# ─── Model Ref Mapping ───

# Map oc/ prefixed models to OpenRouter-compatible model IDs
OC_MODEL_MAP = {
    "oc/hy3-free": "tencent-tokenhub/hy3-preview",
}

# NVIDIA model mapping
NVIDIA_MODEL_MAP = {
    "nvidia/nemotron-4-340b-reward": "nvidia/nemotron-4-340b-reward",
    "nvidia/nemotron-4-340b-base": "nvidia/nemotron-4-340b-base",
    "nvidia/llama-3-8b": "nvidia/llama-3-8b",
}


def get_model_config(model):
    """Determine the provider, model ID, and API endpoint for a given model ref."""
    if model.startswith("oc/"):
        openrouter_model = OC_MODEL_MAP.get(model, model.replace("oc/", "openai/"))
        return "openrouter", openrouter_model
    elif model.startswith("nvidia/"):
        return "nvidia", model.replace("nvidia/", "")
    elif model.startswith("openrouter/"):
        return "openrouter", model.replace("openrouter/", "")
    else:
        # Default to OpenRouter
        return "openrouter", model


def call_openrouter(api_key, model_id, system_prompt, user_prompt):
    """Call OpenRouter API."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Walusimbi-Leon1/sgss-songs-lyrics",
        "X-Title": "SGSS Songs Lyrics Simplifier",
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    if response.status_code != 200:
        raise Exception(f"OpenRouter API error {response.status_code}: {response.text[:500]}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def call_nvidia(api_key, model_id, system_prompt, user_prompt):
    """Call NVIDIA API."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    if response.status_code != 200:
        raise Exception(f"NVIDIA API error {response.status_code}: {response.text[:500]}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def simplify_chapter(chapter_text, model=None):
    """
    Simplify a single chapter of Psalms text into simple English.
    Tries available models in order of preference.
    """
    model = model or DEFAULT_MODEL
    provider, model_id = get_model_config(model)

    print(f"  Using provider: {provider}, model: {model_id}", file=sys.stderr)

    # Try the preferred provider first
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    nvidia_key = os.environ.get("NVIDIA_API_KEY")

    if provider == "openrouter" and openrouter_key:
        return call_openrouter(openrouter_key, model_id, SYSTEM_PROMPT, chapter_text)
    elif provider == "nvidia" and nvidia_key:
        return call_nvidia(nvidia_key, model_id, SYSTEM_PROMPT, chapter_text)

    # Fallback to whatever key is available
    if openrouter_key:
        return call_openrouter(openrouter_key, model_id, SYSTEM_PROMPT, chapter_text)
    elif nvidia_key:
        return call_nvidia(nvidia_key, model_id, SYSTEM_PROMPT, chapter_text)

    raise Exception(
        "No API key found. Set OPENROUTER_API_KEY or NVIDIA_API_KEY environment variable."
    )


def extract_chapter_title(text):
    """Extract the chapter title (e.g., 'Psalm 23') from file content."""
    lines = text.strip().split("\n")
    if lines and lines[0].strip():
        return lines[0].strip()
    return ""


def extract_verses(text):
    """Extract verse content (without the title line) from the Psalm file."""
    lines = text.strip().split("\n")
    # Skip the title line (e.g., "Psalm 23")
    if lines and lines[0].strip().lower().startswith("psalm"):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Transform Psalms chapters into simple English"
    )
    parser.add_argument(
        "chapter_file", help="Path to the chapter file to transform"
    )
    parser.add_argument(
        "--output", "-o", help="Output file path (default: same dir, _simple suffix)"
    )
    parser.add_argument(
        "--model", help="Model to use (default: ${MODEL} or oc/hy3-free)"
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Commit the result (requires git repo and COMMIT_AND_PUSH=true)"
    )
    parser.add_argument(
        "--push", action="store_true",
        help="Push after commit (requires --commit)"
    )

    args = parser.parse_args()

    # Read input file
    with open(args.chapter_file, "r", encoding="utf-8") as f:
        content = f.read()

    chapter_title = extract_chapter_title(content)
    chapter_text = extract_verses(content)

    print(f"Transforming: {chapter_title}", file=sys.stderr)
    print(f"  Source: {args.chapter_file}", file=sys.stderr)

    # Transform the chapter
    simplified = simplify_chapter(chapter_text, args.model or DEFAULT_MODEL)

    # Build output content with title preserved
    output_content = f"{chapter_title}\n\n{simplified}\n"

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.chapter_file)
        output_path = f"{base}_simple{ext}"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"  Written to: {output_path}", file=sys.stderr)
    print(f"  Done!", file=sys.stderr)

    # Commit if requested
    if args.commit:
        import subprocess
        commit_and_push = os.environ.get("COMMIT_AND_PUSH", "false").lower() == "true"
        if commit_and_push:
            # Add the file
            subprocess.run(["git", "add", output_path], check=True)

            # Commit
            subprocess.run(
                ["git", "commit", "-m", f"Transform {chapter_title} to simple English"],
                check=True,
            )
            print(f"  Committed: {chapter_title}", file=sys.stderr)

            # Push if requested
            if args.push:
                branch = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, check=True
                ).stdout.strip()
                subprocess.run(["git", "push", "origin", branch], check=True)
                print(f"  Pushed: {chapter_title}", file=sys.stderr)

    # Print result to stdout
    print(output_path)


if __name__ == "__main__":
    main()
