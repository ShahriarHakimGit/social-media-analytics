"""ETL Step 3: Load cleaned CRM records into MariaDB's staging table.

This uses the local `mariadb` command, so it works with the same macOS
connection used earlier in the terminal.
"""

import csv
import subprocess
from pathlib import Path


DATABASE = "zed_real_estate_analytics"
INPUT_FILE = Path(__file__).parent / "generated" / "crm_leads_cleaned.csv"

STAGING_COLUMNS = (
    "source_row_number", "source_lead_id", "enquiry_date_text", "inspection_date_text",
    "conversion_date_text", "agent_id_text", "property_id_text", "campaign_id_text",
    "post_id_text", "lead_status_text", "conversion_type_text", "revenue_text",
)


def sql_text(value: str) -> str:
    """Turn a CSV value into safe SQL text for this local learning project."""
    return "NULL" if value == "" else "'" + value.replace("'", "''") + "'"


def main() -> None:
    with INPUT_FILE.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    values = []
    for row_number, row in enumerate(rows, start=2):  # Row 1 is the CSV header.
        row_values = (
            str(row_number), row["source_lead_id"], row["enquiry_date"], row["inspection_date"],
            row["conversion_date"], row["agent_id"], row["property_id"], row["campaign_id"],
            row["post_id"], row["lead_status"], row["conversion_type"], row["revenue"],
        )
        # @batch_id links every raw row to the import batch created above.
        values.append("(@batch_id, " + ", ".join(sql_text(value) for value in row_values) + ")")

    sql = f"""
USE {DATABASE};
INSERT INTO etl_load_batch (source_system, source_file_name, status, rows_read)
VALUES ('CRM', '{INPUT_FILE.name}', 'Started', {len(rows)});
SET @batch_id = LAST_INSERT_ID();

INSERT INTO stg_crm_lead (load_batch_id, {', '.join(STAGING_COLUMNS)})
VALUES
{',\n'.join(values)};

UPDATE etl_load_batch
SET status = 'Completed', completed_at_utc = CURRENT_TIMESTAMP, rows_loaded = {len(rows)}
WHERE load_batch_id = @batch_id;

SELECT load_batch_id, source_file_name, status, rows_read, rows_loaded
FROM etl_load_batch
WHERE load_batch_id = @batch_id;

SELECT COUNT(*) AS staging_records_loaded
FROM stg_crm_lead
WHERE load_batch_id = @batch_id;
"""

    result = subprocess.run(
        ["mariadb", DATABASE], input=sql, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        print("Load did not complete. MariaDB said:")
        print(result.stderr)
        raise SystemExit(result.returncode)

    print("Load completed. MariaDB confirmation:")
    print(result.stdout)


if __name__ == "__main__":
    main()
