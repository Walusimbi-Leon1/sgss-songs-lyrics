# SGSS Songs Lyrics

Simple English Psalms from the SGSS Bible — rewritten for everyday understanding.

## Overview

This repo transforms the [SGSS Bible](https://github.com/Walusimbi-Leon1/sgss-bible) Psalms (150 chapters, archaic/poetic English) into **simple, easy-to-read English** that's distinct from any published Bible translation.

## Structure

```
sgss-songs-lyrics/
├── psalms/                    # Original SGSS Psalm chapters
│   ├── Psalm_001.txt
│   ├── Psalm_002.txt
│   └── ...
├── songs/                     # Simplified (simple English) versions
│   ├── Psalm_001_simple.txt
│   ├── Psalm_002_simple.txt
│   └── ...
├── transform_psalms.py        # Transformation script
└── .github/workflows/
    └── transform-psalms.yml   # GitHub Action
```

## How the Transformation Works

The GitHub Action:
1. **Fetches** the SGSS Bible repo and extracts Psalms
2. **Splits** into 150 individual chapter files
3. **Transforms** each chapter using AI models:
   - Primary: `oc/hy3-free` (OpenRouter → Tencent TokenHub `hy3-preview`)
   - Fallback: NVIDIA models (`nvidia/nemotron-4-340b-reward`)
4. **Commits and pushes** each chapter individually (not all at once)

### The Simple English Style

- Replaces archaic words: "thee"→"you", "thou"→"you", "unto"→"to", etc.
- Uses short, conversational sentences
- Warm, friend-to-friend tone
- Everyday vocabulary throughout

## Running Locally

```bash
# Set your API key
export OPENROUTER_API_KEY=your-key-here
export MODEL=oc/hy3-free  # or any OpenRouter model

# Transform a single chapter
python3 transform_psalms.py psalms/Psalm_001.txt --output songs/Psalm_001_simple.txt
```

## GitHub Action

Run manually from the Actions tab, or it runs automatically daily at 6 AM UTC.

### Inputs
- `start_chapter`: Starting chapter (1-150, default: 1)
- `end_chapter`: Ending chapter (1-150, default: 150)
- `model`: AI model to use (default: `oc/hy3-free`)

### Secrets Needed
- `OPENROUTER_API_KEY` — *** API key
- `NVIDIA_API_KEY` — NVIDIA API key (optional, fallback)

## License

MIT
