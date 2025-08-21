#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse key invoice fields from CSV invoices.

This utility scans CSV files that follow the Google invoice export format
and extracts a limited set of fields for bookkeeping.
"""

import argparse
import csv
import glob
import sys
from pathlib import Path


def extract_invoice(csv_path: str) -> dict:
    """Extract invoice data from a CSV file."""
    data = {
        "file": str(csv_path),
        "invoice_number": None,
        "invoice_date": None,
        "billing_id": None,
        "invoice_amount": None,
        "domain": None,
        "error": None,
    }

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            section = "meta"
            header = None
            for row in reader:
                # switch section at empty line
                if not row or all(not c.strip() for c in row):
                    section = "items"
                    header = None
                    continue

                if section == "meta":
                    key = row[0].strip().lower()
                    value = row[1].strip() if len(row) > 1 else ""
                    if key == "invoice number":
                        data["invoice_number"] = value
                    elif key == "invoice date":
                        data["invoice_date"] = value
                    elif key == "billing id":
                        data["billing_id"] = value
                    elif key == "invoice amount":
                        data["invoice_amount"] = value
                else:
                    if header is None:
                        header = row  # skip header row
                        continue
                    # first non-empty domain name
                    if row[0].strip():
                        data["domain"] = row[0].strip()
                        break
    except Exception as e:  # pragma: no cover
        data["error"] = f"parse_error: {e}"

    return data


def discover_csvs(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() == ".csv":
        return [input_path]
    pattern = "**/*.csv" if recursive else "*.csv"
    return [Path(p) for p in glob.glob(str(input_path / pattern), recursive=recursive)]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse invoice fields from CSV invoices"
    )
    ap.add_argument(
        "-i", "--input", required=True,
        help="Path to CSV file or directory",
    )
    ap.add_argument(
        "-o", "--out", default="csv_invoices_index.csv",
        help="Output CSV (default: csv_invoices_index.csv)",
    )
    ap.add_argument(
        "-r", "--recursive", action="store_true",
        help="Recursively search subdirectories",
    )
    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    csvs = discover_csvs(input_path, args.recursive)

    if not csvs:
        print(f"Geen CSV's gevonden in: {input_path}", file=sys.stderr)
        sys.exit(2)

    rows = [extract_invoice(str(p)) for p in csvs]

    fieldnames = [
        "file",
        "invoice_number",
        "invoice_date",
        "billing_id",
        "invoice_amount",
        "domain",
        "error",
    ]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if not r.get("error"))
    print(f"Geschreven: {args.out}  |  {ok}/{len(rows)} records zonder fouten")


if __name__ == "__main__":
    main()
