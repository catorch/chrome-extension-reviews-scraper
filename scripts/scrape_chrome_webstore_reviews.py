#!/usr/bin/env python3
"""
Backwards-compatible shim.

Prefer using the installed CLI:
  chrome-extension-reviews-scraper ...
"""

from __future__ import annotations

import os
import sys

try:
    import cwsreviews.cli
except ModuleNotFoundError:
    # Allow running from a source checkout without installing.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src = os.path.join(repo_root, "src")
    sys.path.insert(0, src)
    import cwsreviews.cli  # type: ignore


if __name__ == "__main__":
    raise SystemExit(cwsreviews.cli.main())
