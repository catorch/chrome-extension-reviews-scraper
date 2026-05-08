"""Module entrypoint so `python -m cwsreviews` works."""

import cwsreviews.cli

if __name__ == "__main__":
    raise SystemExit(cwsreviews.cli.main())
