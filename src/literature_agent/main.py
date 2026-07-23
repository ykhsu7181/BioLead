"""Command-line entry point for Literature Agent."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from literature_agent.config import load_config
from literature_agent.openalex_client import OpenAlexClient
from literature_agent.storage import (
    build_output_paths,
    save_processed_records,
    save_raw_response,
)
from literature_agent.works import clean_works_response, validate_search_inputs


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(description="Collect papers from OpenAlex Works.")
    parser.add_argument("--query", required=True, help="Search keyword.")
    parser.add_argument("--from-date", required=True, help="Start date in YYYY-MM-DD.")
    parser.add_argument("--to-date", required=True, help="End date in YYYY-MM-DD.")
    parser.add_argument(
        "--max-results",
        required=True,
        type=int,
        help="Maximum number of results, from 1 to 20.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory for raw API responses.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory for cleaned JSON and CSV output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OpenAlex collection command."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        search_params = validate_search_inputs(
            query=args.query,
            from_date=args.from_date,
            to_date=args.to_date,
            max_results=args.max_results,
        )
    except ValueError as error:
        parser.error(str(error))

    config = load_config()
    client = OpenAlexClient(config=config)
    raw_response = client.fetch_works(search_params)
    output_paths = build_output_paths(
        query=search_params.query,
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
    )
    save_raw_response(raw_response, output_paths.raw_json)

    records = clean_works_response(raw_response)
    save_processed_records(records, output_paths)

    print(f"Collected {len(records)} records")
    print(f"Raw JSON: {output_paths.raw_json}")
    print(f"Processed JSON: {output_paths.processed_json}")
    print(f"Processed CSV: {output_paths.processed_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
