from __future__ import annotations

"""Core scraper implementation and output writers for cwsreviews."""

import csv
import datetime as dt
import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
import urllib.parse

import cwsreviews
import cwsreviews.http
import cwsreviews.models
import cwsreviews.parsing


_EXT_ID_RE = re.compile(r"^[a-p]{32}$")


def _utc_iso(ts: Any) -> Optional[str]:
    if not isinstance(ts, list) or not ts:
        return None
    try:
        sec = int(ts[0])
    except Exception:
        return None
    return dt.datetime.fromtimestamp(sec, dt.timezone.utc).isoformat()


def _safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "extension"


def _parse_slug_and_id_from_detail_url(url: str) -> Tuple[str, str]:
    """Parse `(/detail/<slug>/<id>)` from a chromewebstore.google.com URL."""
    u = urllib.parse.urlparse(url)
    parts = [p for p in u.path.split("/") if p]
    # /detail/<slug>/<id>/...
    if "detail" not in parts:
        raise ValueError(f"Not a CWS detail URL: {url}")
    i = parts.index("detail")
    if len(parts) < i + 3:
        raise ValueError(f"Not a CWS detail URL: {url}")
    slug = parts[i + 1]
    ext_id = parts[i + 2]
    if not _EXT_ID_RE.match(ext_id):
        raise ValueError(f"Invalid extension id in URL: {ext_id}")
    return slug, ext_id


def resolve_input_to_reviews_url(input_ref: str, *, hl: str) -> str:
    """
    Convert a user input (CWS URL or raw extension ID) into a reviews-page URL.

    Inputs:
    - Raw extension id: 32 chars in [a-p]
    - chromewebstore.google.com detail/reviews URL
    """
    s = input_ref.strip()
    if _EXT_ID_RE.match(s):
        # slug is ignored by CWS (redirects to canonical), but is required in the URL path.
        return f"https://chromewebstore.google.com/detail/extension/{s}/reviews?hl={hl}"

    u = urllib.parse.urlparse(s)
    if u.scheme != "https":
        raise ValueError(f"Only https URLs are supported: {input_ref}")
    if u.netloc != "chromewebstore.google.com":
        raise ValueError(f"Not a chromewebstore.google.com URL: {input_ref}")

    slug, ext_id = _parse_slug_and_id_from_detail_url(s)
    return f"https://chromewebstore.google.com/detail/{slug}/{ext_id}/reviews?hl={hl}"


def normalize_review(
    ext: cwsreviews.models.ExtensionRef, raw: List[Any], *, include_raw: bool
) -> Dict[str, Any]:
    """Normalize a raw CWS review array into a stable dict suitable for JSONL/CSV export."""
    review_id = raw[0] if len(raw) > 0 else None
    author = raw[1] if len(raw) > 1 else None
    author_name = author[0] if isinstance(author, list) and len(author) > 0 else None
    author_photo = author[1] if isinstance(author, list) and len(author) > 1 else None
    rating = raw[2] if len(raw) > 2 else None
    body = raw[3] if len(raw) > 3 else None
    created = raw[4] if len(raw) > 4 else None
    updated = raw[5] if len(raw) > 5 else None

    dev_reply = raw[8] if len(raw) > 8 else None
    dev_reply_text = None
    dev_reply_created = None
    if isinstance(dev_reply, list) and len(dev_reply) > 2:
        dev_reply_text = dev_reply[2]
        dev_reply_created = dev_reply[3] if len(dev_reply) > 3 else None

    lang = (
        raw[-2]
        if len(raw) >= 2 and isinstance(raw[-2], str) and len(raw[-2]) <= 12
        else None
    )

    obj: Dict[str, Any] = {
        "extension_id": ext.extension_id,
        "extension_slug": ext.slug,
        "review_id": review_id,
        "author_name": author_name,
        "author_photo_url": author_photo,
        "rating": rating,
        "text": body,
        "created_at_utc": _utc_iso(created),
        "updated_at_utc": _utc_iso(updated),
        "developer_reply_text": dev_reply_text,
        "developer_reply_created_at_utc": _utc_iso(dev_reply_created),
        "lang": lang,
    }
    if include_raw:
        obj["raw"] = raw
    return obj


def _extract_wrb_fr(batch: Any, rpcid: str) -> Any:
    if not isinstance(batch, list):
        raise ValueError("batchexecute payload is not a list")
    for item in batch:
        if (
            isinstance(item, list)
            and len(item) >= 3
            and item[0] == "wrb.fr"
            and item[1] == rpcid
        ):
            if item[2] is None:
                # Common transient: error code list like [3]
                raise cwsreviews.http.RetryableError(
                    f"RPC {rpcid} returned no data; error={item[5] if len(item) > 5 else None}"
                )
            return json.loads(item[2])
    raise ValueError(f"Could not find wrb.fr response for rpcid={rpcid}")


def _batchexecute_url(wiz: Dict[str, Any], rpcid: str, *, hl: str, reqid: int) -> str:
    im6 = wiz["Im6cmf"]
    fsid = wiz["FdrFJe"]
    bl = wiz["cfb2h"]
    params = {
        "rpcids": rpcid,
        "f.sid": fsid,
        "bl": bl,
        "hl": hl,
        "soc-app": "1",
        "soc-platform": "1",
        "soc-device": "1",
        "_reqid": str(reqid),
    }
    return (
        "https://chromewebstore.google.com"
        + im6
        + "/data/batchexecute?"
        + urllib.parse.urlencode(params)
    )


def scrape_reviews(
    inputs: Sequence[str],
    *,
    out_dir: str,
    hl: str = "en",
    sort: str = "recent",
    stars: Optional[int] = None,
    page_size: int = 100000,
    include_raw: bool = False,
    get_timeout_s: int = 60,
    post_timeout_s: int = 240,
    retries: int = 5,
    strict: bool = False,
) -> List[cwsreviews.models.ScrapeResult]:
    """
    Scrape Chrome Web Store reviews and write per-extension JSONL/CSV/meta files.

    Side effects:
    - Creates `out_dir` if needed.
    - Writes 3 files per extension: `*.reviews.jsonl`, `*.reviews.csv`, `*.meta.json`.
    """
    if sort not in ("recent", "helpful"):
        raise ValueError("sort must be 'recent' or 'helpful'")
    if stars is not None and stars not in (1, 2, 3, 4, 5):
        raise ValueError("stars must be one of 1..5")

    sort_int = 2 if sort == "recent" else 1
    retry_cfg = cwsreviews.http.RetryConfig(retries=retries)

    os.makedirs(out_dir, exist_ok=True)
    session = cwsreviews.http.make_session()

    results: List[cwsreviews.models.ScrapeResult] = []
    for input_ref in inputs:
        # 1) Resolve to reviews URL and fetch HTML (follow redirects).
        reviews_url = resolve_input_to_reviews_url(input_ref, hl=hl)
        html, final_url = cwsreviews.http.get_text(
            session, reviews_url, timeout_s=get_timeout_s, retry_cfg=retry_cfg
        )

        slug, ext_id = _parse_slug_and_id_from_detail_url(final_url)
        slug = _safe_slug(slug)
        ext = cwsreviews.models.ExtensionRef(
            input_ref=input_ref,
            extension_id=ext_id,
            slug=slug,
            reviews_url=final_url,
        )

        # 2) Parse dynamic tokens + rpcid.
        wiz = cwsreviews.parsing.parse_wiz_global_data(html)
        rpcid = cwsreviews.parsing.parse_ds1_rpcid(html)

        # 3) Call batchexecute.
        args = [ext_id, [page_size], sort_int, stars, None, None, 0]
        f_req = json.dumps([[[rpcid, json.dumps(args), None, "generic"]]])

        def _do_post_once() -> Any:
            # _reqid seems to influence certain transient failures; refresh it on each retry.
            url = _batchexecute_url(wiz, rpcid, hl=hl, reqid=random.randint(1000, 9999))
            text = cwsreviews.http.post_form_text(
                session,
                url,
                data={"f.req": f_req},
                timeout_s=post_timeout_s,
                retry_cfg=cwsreviews.http.RetryConfig(retries=0),
            )
            if not text.startswith(")]}'"):
                raise cwsreviews.http.RetryableError("Unexpected batchexecute prefix")
            payload = text.split("\n", 2)[2]
            return json.loads(payload)

        batch = cwsreviews.http.with_retries(_do_post_once, retry_cfg)
        resp = _extract_wrb_fr(batch, rpcid)
        if not (
            isinstance(resp, list)
            and len(resp) >= 3
            and isinstance(resp[1], list)
            and isinstance(resp[2], int)
        ):
            raise ValueError(f"Unexpected RPC response shape for {ext_id}")

        token_list = resp[0] if isinstance(resp[0], list) else []
        token = token_list[0] if token_list else None
        raw_items: List[Any] = resp[1]
        total_reported: int = resp[2]

        # 4) Normalize + dedupe.
        seen: set[Tuple[str, str]] = set()
        normalized: List[Dict[str, Any]] = []
        for it in raw_items:
            if not isinstance(it, list) or not it:
                continue
            obj = normalize_review(ext, it, include_raw=include_raw)
            key = (str(obj["review_id"]), str(obj["created_at_utc"]))
            if key in seen:
                continue
            seen.add(key)
            normalized.append(obj)

        # 5) Write outputs.
        base = f"{ext.slug}__{ext.extension_id}"
        jsonl_path = os.path.join(out_dir, f"{base}.reviews.jsonl")
        csv_path = os.path.join(out_dir, f"{base}.reviews.csv")
        meta_path = os.path.join(out_dir, f"{base}.meta.json")

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for obj in normalized:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "extension_id",
                    "extension_slug",
                    "review_id",
                    "rating",
                    "created_at_utc",
                    "updated_at_utc",
                    "author_name",
                    "text",
                    "developer_reply_text",
                    "developer_reply_created_at_utc",
                    "lang",
                ],
            )
            w.writeheader()
            for obj in normalized:
                w.writerow({k: obj[k] for k in w.fieldnames})

        meta = {
            "version": cwsreviews.__version__,
            "input_ref": input_ref,
            "reviews_url": ext.reviews_url,
            "hl": hl,
            "sort": sort,
            "stars": stars,
            "rpcid": rpcid,
            "page_size": page_size,
            "total_reported": total_reported,
            "returned": len(raw_items),
            "written_deduped": len(normalized),
            "mismatch": max(0, total_reported - len(raw_items)),
            "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            # Helps debugging if CWS changes:
            "token_present": bool(token),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        counts = cwsreviews.models.ScrapeCounts(
            total_reported=total_reported,
            returned=len(raw_items),
            written_deduped=len(normalized),
        )
        outputs = cwsreviews.models.OutputPaths(
            jsonl_path=jsonl_path, csv_path=csv_path, meta_path=meta_path
        )
        results.append(
            cwsreviews.models.ScrapeResult(ext=ext, counts=counts, outputs=outputs)
        )

        if strict and len(raw_items) != total_reported:
            raise RuntimeError(
                f"Strict mode: {ext.extension_id} reported total={total_reported} but returned={len(raw_items)}"
            )

    return results
