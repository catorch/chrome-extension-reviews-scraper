from __future__ import annotations

"""Parsing utilities for Chrome Web Store HTML token extraction."""

import json
import re
from typing import Any, Dict


def parse_wiz_global_data(html: str) -> Dict[str, Any]:
    """
    Extract `window.WIZ_global_data = {...};` from CWS HTML and return as dict.

    We bracket-match the JSON object to avoid brittle regex across nested braces.
    """
    idx = html.find("WIZ_global_data")
    if idx == -1:
        raise ValueError("Could not find WIZ_global_data in HTML")

    eq = html.find("=", idx)
    if eq == -1:
        raise ValueError("Could not find '=' after WIZ_global_data")
    start = html.find("{", eq)
    if start == -1:
        raise ValueError("Could not find '{' after WIZ_global_data=")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = html[start : i + 1]
                return json.loads(blob)

    raise ValueError("Could not bracket-match WIZ_global_data JSON object")


_AF_DSR_RE = re.compile(r"AF_dataServiceRequests\s*=\s*(\{.*?\})\s*;", re.S)
_DS1_ID_RE = re.compile(r"'ds:1'\s*:\s*\{id:'([^']+)'")


def parse_ds1_rpcid(html: str) -> str:
    """
    Extract the rpcid for the reviews list RPC from AF_dataServiceRequests (ds:1).
    Typically `x1DgCd` at time of writing, but we treat it as dynamic.
    """
    m = _AF_DSR_RE.search(html)
    if not m:
        raise ValueError("Could not find AF_dataServiceRequests in HTML")
    blob = m.group(1)
    mm = _DS1_ID_RE.search(blob)
    if not mm:
        raise ValueError("Could not find ds:1 id in AF_dataServiceRequests")
    return mm.group(1)
