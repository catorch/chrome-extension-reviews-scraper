from __future__ import annotations

"""Command-line interface for cwsreviews (implemented with Click)."""

import sys
from typing import List, Optional, Sequence, Tuple

import click

import cwsreviews.scraper


def _read_stdin_lines() -> List[str]:
    out: List[str] = []
    for line in click.get_text_stream("stdin"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("inputs", nargs=-1)
@click.option(
    "--out",
    "out_dir",
    default="cws_reviews",
    show_default=True,
    help="Output directory.",
)
@click.option("--hl", default="en", show_default=True, help="UI locale for requests.")
@click.option(
    "--sort",
    type=click.Choice(["recent", "helpful"], case_sensitive=False),
    default="recent",
    show_default=True,
    help="Review sort order.",
)
@click.option(
    "--stars",
    type=click.Choice(["1", "2", "3", "4", "5"]),
    help="Filter to a single star rating.",
)
@click.option(
    "--page-size",
    type=int,
    default=100000,
    show_default=True,
    help="Requested page size.",
)
@click.option(
    "--include-raw", is_flag=True, help="Include raw payload per review in JSONL."
)
@click.option(
    "--timeout",
    "get_timeout_s",
    type=int,
    default=60,
    show_default=True,
    help="GET timeout seconds.",
)
@click.option(
    "--post-timeout",
    "post_timeout_s",
    type=int,
    default=240,
    show_default=True,
    help="POST timeout seconds.",
)
@click.option(
    "--retries",
    type=int,
    default=5,
    show_default=True,
    help="Retries for transient failures.",
)
@click.option(
    "--strict", is_flag=True, help="Fail if returned review count != reported total."
)
def cli(
    inputs: Tuple[str, ...],
    out_dir: str,
    hl: str,
    sort: str,
    stars: Optional[str],
    page_size: int,
    include_raw: bool,
    get_timeout_s: int,
    post_timeout_s: int,
    retries: int,
    strict: bool,
) -> None:
    """
    Export Chrome Web Store extension reviews to JSONL/CSV.

    Pass extension URLs or raw extension IDs. If no INPUTS are provided, inputs
    are read from stdin (one per line). Blank lines and lines starting with '#'
    are ignored.
    """
    input_list: List[str] = list(inputs)
    if not input_list:
        input_list = _read_stdin_lines()
    if not input_list:
        raise click.UsageError(
            "No inputs provided (pass URLs/IDs or pipe them via stdin)."
        )

    stars_int = int(stars) if stars is not None else None
    results = cwsreviews.scraper.scrape_reviews(
        input_list,
        out_dir=out_dir,
        hl=hl,
        sort=sort.lower(),
        stars=stars_int,
        page_size=page_size,
        include_raw=include_raw,
        get_timeout_s=get_timeout_s,
        post_timeout_s=post_timeout_s,
        retries=retries,
        strict=strict,
    )

    for r in results:
        click.echo(
            f"{r.ext.extension_id} ({r.ext.slug}): "
            f"total={r.counts.total_reported} returned={r.counts.returned} written={r.counts.written_deduped}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Programmatic entrypoint.

    Returns an integer exit code instead of calling sys.exit.
    """
    try:
        cli.main(args=list(argv) if argv is not None else None, standalone_mode=False)
        return 0
    except click.ClickException as e:
        e.show()
        return 2
