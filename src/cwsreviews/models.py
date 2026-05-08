from __future__ import annotations

"""Datamodels for cwsreviews."""

from typing import Optional

import dataclasses


@dataclasses.dataclass(frozen=True)
class ExtensionRef:
    """
    Canonicalized reference to a Chrome Web Store extension.

    `input_ref` is what the user provided (URL or raw ID) for traceability.
    `reviews_url` is the exact reviews-page URL we fetched (after resolving redirects).
    """

    input_ref: str
    extension_id: str
    slug: str
    reviews_url: str


@dataclasses.dataclass(frozen=True)
class ScrapeCounts:
    total_reported: int
    returned: int
    written_deduped: int


@dataclasses.dataclass(frozen=True)
class OutputPaths:
    jsonl_path: str
    csv_path: str
    meta_path: str


@dataclasses.dataclass(frozen=True)
class ScrapeResult:
    ext: ExtensionRef
    counts: ScrapeCounts
    outputs: OutputPaths
