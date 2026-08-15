# SGSS Songs — Simple English Psalms

Simple English Psalms rewritten from the SGSS Bible.  
🌐 **[View the website →](https://<USERNAME>.github.io/sgss-songs-lyrics/)** (replace `<USERNAME>` with your GitHub username after enabling Pages).

## What's here
- `songs/` — all 150 Psalms, each verse on its own line with its number.
- `docs/` — generated GitHub Pages site (built by the workflow). Lyrics have **verse numbers stripped** and **long chapters split into parts** of ≤ 22 verses each.
- `scripts/generate_site.py` — builds the `docs/` site from `songs/`.
- `.github/workflows/build-and-deploy.yml` — GitHub Action that builds & deploys the site, and re-populates any missing Psalms.

## Local dev
```bash
python3 scripts/generate_site.py   # writes to docs/
```
