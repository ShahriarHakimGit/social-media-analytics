"""ETL Step 2: Validate and clean the extracted synthetic CRM data."""

import csv
from datetime import date
from pathlib import Path


INPUT_FILE = Path(__file__).parent / "generated" / "crm_leads_synthetic.csv"
OUTPUT_FILE = Path(__file__).parent / "generated" / "crm_leads_cleaned.csv"
ALLOWED_STATUSES = {"Enquiry", "InspectionBooked", "Converted", "Lost"}
REQUIRED_FIELDS = ("source_lead_id", "enquiry_date", "agent_id", "property_id", "platform", "lead_status")


def valid_date(value: str) -> bool:
    """Return True for an empty optional date or a YYYY-MM-DD date."""
    if not value:
        return True
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def clean_row(row: dict[str, str]) -> dict[str, str]:
    """Remove extra spaces from every value in one CRM record."""
    return {column: (value or "").strip() for column, value in row.items()}


def row_errors(row: dict[str, str]) -> list[str]:
    """Return human-readable reasons why a record should not be loaded."""
    errors = [f"missing {field}" for field in REQUIRED_FIELDS if not row[field]]

    if row["lead_status"] and row["lead_status"] not in ALLOWED_STATUSES:
        errors.append("unknown lead_status")

    for field in ("enquiry_date", "inspection_date", "conversion_date"):
        if not valid_date(row[field]):
            errors.append(f"invalid {field}")

    if row["lead_status"] == "Converted" and not row["conversion_date"]:
        errors.append("converted lead has no conversion_date")

    return errors


def main() -> None:
    with INPUT_FILE.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        cleaned_rows = []
        rejected_rows = []

        for row in reader:
            cleaned_row = clean_row(row)
            errors = row_errors(cleaned_row)
            if errors:
                rejected_rows.append((cleaned_row["source_lead_id"], "; ".join(errors)))
            else:
                cleaned_rows.append(cleaned_row)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"Records checked: {len(cleaned_rows) + len(rejected_rows)}")
    print(f"Clean records ready to load: {len(cleaned_rows)}")
    print(f"Rejected records: {len(rejected_rows)}")
    print(f"Clean file created: {OUTPUT_FILE.name}")

    if rejected_rows:
        print("\nRejected records:")
        for lead_id, reason in rejected_rows:
            print(f"  {lead_id}: {reason}")


if __name__ == "__main__":
    main()
