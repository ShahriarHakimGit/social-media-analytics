"""ETL Step 7: Load cleaned Meta performance records into MariaDB staging."""

import csv
import subprocess
from pathlib import Path


DATABASE = "zed_real_estate_analytics"
INPUT_FILE = Path(__file__).parent / "generated" / "meta_post_performance_cleaned.csv"
STAGING_COLUMNS = (
    "source_row_number", "source_post_id", "report_date_text", "impressions_text", "reach_text",
    "link_clicks_text", "reactions_text", "comments_text", "shares_text", "saves_text", "ad_spend_text",
)


def sql_text(value: str) -> str:
    return "NULL" if value == "" else "'" + value.replace("'", "''") + "'"


def main() -> None:
    with INPUT_FILE.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    values = []
    for row_number, row in enumerate(rows, start=2):
        row_values = (
            str(row_number), row["source_post_id"], row["report_date"], row["impressions"], row["reach"],
            row["link_clicks"], row["reactions"], row["comments"], row["shares"], row["saves"], row["ad_spend"],
        )
        values.append("(@batch_id, " + ", ".join(sql_text(value) for value in row_values) + ")")

    sql = f"""
USE {DATABASE};
INSERT INTO etl_load_batch (source_system, source_file_name, status, rows_read)
VALUES ('Meta', '{INPUT_FILE.name}', 'Started', {len(rows)});
SET @batch_id = LAST_INSERT_ID();

INSERT INTO stg_meta_post_performance (load_batch_id, {', '.join(STAGING_COLUMNS)})
VALUES
{',\n'.join(values)};

UPDATE etl_load_batch
SET status = 'Completed', completed_at_utc = CURRENT_TIMESTAMP, rows_loaded = {len(rows)}
WHERE load_batch_id = @batch_id;

SELECT load_batch_id, source_file_name, status, rows_read, rows_loaded
FROM etl_load_batch WHERE load_batch_id = @batch_id;
SELECT COUNT(*) AS staging_records_loaded
FROM stg_meta_post_performance WHERE load_batch_id = @batch_id;
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
