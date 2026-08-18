"""Command-line entry point for the PubMed first-round workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from scholarlead_agent.pubmed_models import (
    PUBMED_MAX_RESULTS_LIMIT,
    validate_pubmed_search_inputs,
)
from scholarlead_agent.pubmed_client import PubMedClient
from scholarlead_agent.services.pubmed_service import run_pubmed_search


def build_parser() -> argparse.ArgumentParser:
    """Build the PubMed command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Prepare a PubMed first-round collection task."
    )
    parser.add_argument("--query", required=True, help="PubMed search keyword.")
    parser.add_argument("--from-date", required=True, help="Start date in YYYY-MM-DD.")
    parser.add_argument("--to-date", required=True, help="End date in YYYY-MM-DD.")
    parser.add_argument(
        "--max-results",
        required=True,
        type=int,
        help=f"Maximum number of PubMed results, from 1 to {PUBMED_MAX_RESULTS_LIMIT}.",
    )
    parser.add_argument(
        "--country",
        help="Optional target country or region, for later filtering and export.",
    )
    parser.add_argument(
        "--service-type",
        help="Optional target service type, such as scRNA-seq or RNA-seq.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/pubmed"),
        help="Directory for raw PubMed API responses.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed/pubmed"),
        help="Directory for processed PubMed JSON and CSV output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PubMed first-round workflow."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        search_params = validate_pubmed_search_inputs(
            query=args.query,
            from_date=args.from_date,
            to_date=args.to_date,
            max_results=args.max_results,
            country=args.country,
            service_type=args.service_type,
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
        )
    except ValueError as error:
        parser.error(str(error))

    result = run_pubmed_search(search_params, client=PubMedClient())
    _print_run_summary(result)
    return 0 if result.status == "success" else 1


def _print_run_summary(result: object) -> None:
    print("ScholarLead Agent PubMed first-round run completed")
    print(f"Task ID: {result.task_id}")
    print(f"Status: {result.status}")
    print(f"PMIDs collected: {len(result.pmids)}")
    print(f"Papers parsed: {len(result.papers)}")
    print(f"Leads generated: {len(result.leads)}")
    print(
        "Leads with verified email: "
        f"{result.run_report['leads_with_verified_email_count']}"
    )
    print(
        "Leads needing review: "
        f"{result.run_report['leads_needing_review_count']}"
    )
    print(f"Unknown country: {result.run_report['unknown_country_count']}")
    print(f"Raw files: {result.run_report['raw_files']}")
    print(f"Papers CSV: {result.processed_paths.papers_csv}")
    print(f"Leads CSV: {result.processed_paths.leads_csv}")
    print(f"Run report: {result.run_report_path}")
    print("Scoring mode: PubMed single-source temporary scoring")
    print("LLM used: no")
    print("Agent enabled: no")


if __name__ == "__main__":
    raise SystemExit(main())
