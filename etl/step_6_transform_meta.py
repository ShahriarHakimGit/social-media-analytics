"""ETL Step 6: Validate and clean synthetic Meta post-performance data."""

import csv
from datetime import date
from pathlib import Path


INPUT_FILE = Path(__file__).parent / "generated" / "meta_post_performance_synthetic.csv"
OUTPUT_FILE = Path(__file__).parent / "generated" / "meta_post_performance_cleaned.csv"
REQUIRED_FIELDS = ("source_post_id", "report_date", "platform", "campaign_id", "property_id", "impressions")
NUMBER_FIELDS = ("impressions", "reach", "link_clicks", "reactions", "comments", "shares", "saves", "ad_spend")


def clean_row(row: dict[str, str]) -> dict[str, str]:
    return {column: (value or "").strip() for column, value in row.items()}


def row_errors(row: dict[str, str]) -> list[str]:
    errors = [f"missing {field}" for field in REQUIRED_FIELDS if not row[field]]

    try:
        date.fromisoformat(row["report_date"])
    except ValueError:
        errors.append("invalid report_date")

    for field in NUMBER_FIELDS:
        try:
            if float(row[field]) < 0:
                errors.append(f"negative {field}")
        except ValueError:
            errors.append(f"invalid {field}")

    if row["impressions"].isdigit() and row["reach"].isdigit() and int(row["reach"]) > int(row["impressions"]):
        errors.append("reach is greater than impressions")

    return errors


def main() -> None:
    with INPUT_FILE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        clean_rows = []
        rejected_rows = []
        for row in reader:
            row = clean_row(row)
            errors = row_errors(row)
            if errors:
                rejected_rows.append((row["source_post_id"], "; ".join(errors)))
            else:
                clean_rows.append(row)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    print(f"Records checked: {len(clean_rows) + len(rejected_rows)}")
    print(f"Clean post records ready to load: {len(clean_rows)}")
    print(f"Rejected records: {len(rejected_rows)}")
    print(f"Clean file created: {OUTPUT_FILE.name}")

    if rejected_rows:
        print("\nRejected records:")
        for post_id, reason in rejected_rows:
            print(f"  {post_id}: {reason}")


if __name__ == "__main__":
    main()
