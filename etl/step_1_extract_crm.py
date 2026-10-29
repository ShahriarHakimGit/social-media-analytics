"""ETL Step 1: Extract data from the synthetic CRM CSV file."""

import csv
from collections import Counter
from pathlib import Path

CSV_FILE = Path(__file__).parent / "generated" / "crm_leads_synthetic.csv"


def main():
    # Extract: read every CSV row into Python dictionaries.
    with CSV_FILE.open(encoding="utf-8-sig", newline="") as file:
        leads = list(csv.DictReader(file))

    # Print a simple summary so we can check the file before transforming it.
    statuses = Counter(lead["lead_status"] for lead in leads)
    print(f"File read: {CSV_FILE.name}")
    print(f"Number of leads extracted: {len(leads)}")
    print("Lead statuses:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")

    print("\nFirst lead extracted:")
    first_lead = leads[0]
    for field in ("source_lead_id", "agent_name", "property_id", "platform", "lead_status"):
        print(f"  {field}: {first_lead[field]}")


if __name__ == "__main__":
    main()
