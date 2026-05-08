# Chrome Extension Reviews Scraper

**Chrome Extension Reviews Scraper** is a Python CLI for exporting Chrome Web Store extension reviews to `JSONL`, `CSV`, and metadata files. Use it to collect public Chrome extension reviews for product research, competitor analysis, app store monitoring, sentiment analysis, and review datasets.

The package installs a descriptive command, `chrome-extension-reviews-scraper`, plus the shorter alias `cwsreviews`.

## Important Disclaimer

This is an unofficial open source tool and is not affiliated with, endorsed by, sponsored by, or supported by Google, Chrome, or the Chrome Web Store. You are responsible for using it lawfully and in compliance with the Chrome Web Store terms, Google policies, privacy rules, and any other obligations that apply to you.

Read the full [Disclaimer and Responsible Use Policy](DISCLAIMER.md) before using this scraper.

## Features

- Scrape public Chrome Web Store reviews from extension URLs or raw extension IDs.
- Export normalized review data to newline-delimited JSON and CSV.
- Save per-extension metadata, including reported totals, fetched count, locale, sort order, and fetch time.
- Filter reviews by star rating and sort by recent or helpful.
- Read many extension IDs or URLs from stdin for batch review exports.
- Use a configurable delay between extension requests for more responsible batch collection.
- Retry transient Chrome Web Store request failures with backoff.

## Install

Install from this GitHub repository:

```bash
python -m pip install git+https://github.com/catorch/chrome-extension-reviews-scraper.git
```

For isolated CLI usage:

```bash
pipx install git+https://github.com/catorch/chrome-extension-reviews-scraper.git
```

For local development:

```bash
git clone https://github.com/catorch/chrome-extension-reviews-scraper.git
cd chrome-extension-reviews-scraper
python -m pip install -e .
```

## Quick Start

Scrape reviews for one or more Chrome extensions:

```bash
chrome-extension-reviews-scraper --out cws_reviews \
  https://chromewebstore.google.com/detail/onetab/chphlpgkkbolifaimnlloiipkdnihall \
  https://chromewebstore.google.com/detail/session-buddy-tab-bookmar/edacconmaakjimmfgnblocblbcdcpbko
```

Scrape Chrome Web Store reviews by extension ID:

```bash
chrome-extension-reviews-scraper chphlpgkkbolifaimnlloiipkdnihall
```

Read extension IDs and URLs from a file:

```bash
chrome-extension-reviews-scraper --out cws_reviews < extensions.txt
```

The short alias works the same way:

```bash
cwsreviews --stars 5 --sort recent chphlpgkkbolifaimnlloiipkdnihall
```

## CLI Options

```bash
chrome-extension-reviews-scraper --help
```

Common options:

- `--out`: Output directory. Defaults to `cws_reviews`.
- `--hl`: Chrome Web Store UI locale. Defaults to `en`.
- `--sort`: Review sort order, `recent` or `helpful`.
- `--stars`: Filter to one star rating, `1` through `5`.
- `--delay`: Seconds to wait between extensions in batch mode. Defaults to `1.0`.
- `--include-raw`: Include the raw Chrome Web Store review payload in JSONL output.
- `--strict`: Fail if the number of returned reviews differs from the reported total.

## Output Files

For each Chrome extension, the scraper writes three files:

- `*.reviews.jsonl`: One normalized review object per line.
- `*.reviews.csv`: Spreadsheet-friendly review export.
- `*.meta.json`: Fetch metadata and count reconciliation details.

Example JSONL fields:

```json
{
  "extension_id": "chphlpgkkbolifaimnlloiipkdnihall",
  "extension_slug": "onetab",
  "review_id": "...",
  "author_name": "...",
  "rating": 5,
  "text": "...",
  "created_at_utc": "2026-05-08T00:00:00+00:00",
  "updated_at_utc": "2026-05-08T00:00:00+00:00",
  "developer_reply_text": null,
  "developer_reply_created_at_utc": null,
  "lang": "en"
}
```

## Python API

```python
import cwsreviews.scraper

results = cwsreviews.scraper.scrape_reviews(
    ["chphlpgkkbolifaimnlloiipkdnihall"],
    out_dir="cws_reviews",
    sort="recent",
)
```

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## Responsible Use

This project reads publicly accessible review data through Chrome Web Store web UI behavior. That behavior may change, break, throttle, or become unavailable at any time.

Do not use this tool to bypass authentication, access controls, CAPTCHAs, rate limits, technical restrictions, or private/non-public data. Do not use it for spam, harassment, review manipulation, user profiling, or any activity that violates platform rules or user privacy.

Reviews may contain user-generated content and personal information. Handle exported data carefully, minimize retention where possible, and avoid republishing review text, author names, profile photos, or other user data without a valid legal basis.

Review the full [Disclaimer and Responsible Use Policy](DISCLAIMER.md), plus the official Google and Chrome Web Store policies that may apply to your use:

- [Chrome Web Store Developer Agreement](https://developer.chrome.com/docs/webstore/terms/)
- [Chrome Web Store Program Policies](https://developer.chrome.com/docs/webstore/program-policies/policies)
- [Chrome Web Store reviews help](https://support.google.com/chrome_webstore/answer/12225786?hl=en)

Some extensions may report a `total` that is slightly larger than the number of reviews returned by the UI endpoint. In that case, `meta.json` records the mismatch. Use `--strict` to fail on mismatches.

## License

MIT
