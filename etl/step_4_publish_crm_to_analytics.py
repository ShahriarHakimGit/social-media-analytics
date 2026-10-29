"""ETL Step 4: Publish the latest staged CRM batch to analytics tables."""

import csv
import subprocess
from pathlib import Path


DATABASE = "zed_real_estate_analytics"
INPUT_FILE = Path(__file__).parent / "generated" / "crm_leads_cleaned.csv"


def sql_text(value: str) -> str:
    """Return a quoted SQL value, or NULL for an empty optional value."""
    return "NULL" if value == "" else "'" + value.replace("'", "''") + "'"


def unique_rows(rows: list[dict[str, str]], fields: tuple[str, ...]) -> list[dict[str, str]]:
    """Keep one row for each distinct combination of the selected fields."""
    seen = set()
    result = []
    for row in rows:
        key = tuple(row[field] for field in fields)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def main() -> None:
    with INPUT_FILE.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    statements = [f"USE {DATABASE};"]

    # Dimension tables describe the people, properties, campaigns and posts.
    for row in unique_rows(rows, ("agent_id",)):
        statements.append(
            "INSERT INTO dim_agent (source_agent_id, agent_name, email) VALUES "
            f"({sql_text(row['agent_id'])}, {sql_text(row['agent_name'])}, {sql_text(row['agent_email'])}) "
            "ON DUPLICATE KEY UPDATE agent_name = VALUES(agent_name), email = VALUES(email);"
        )

    for row in unique_rows(rows, ("property_id",)):
        statements.append(
            "INSERT INTO dim_property (source_property_id, property_type, suburb, state_code, postcode, bedrooms, listing_price) VALUES "
            f"({sql_text(row['property_id'])}, {sql_text(row['property_type'])}, {sql_text(row['suburb'])}, "
            f"{sql_text(row['state_code'])}, {sql_text(row['postcode'])}, {sql_text(row['bedrooms'])}, {sql_text(row['listing_price'])}) "
            "ON DUPLICATE KEY UPDATE property_type = VALUES(property_type), suburb = VALUES(suburb), "
            "state_code = VALUES(state_code), postcode = VALUES(postcode), bedrooms = VALUES(bedrooms), listing_price = VALUES(listing_price);"
        )

    for row in unique_rows(rows, ("campaign_id",)):
        statements.append(
            "INSERT INTO dim_campaign (source_campaign_id, campaign_name, platform_key, start_date_key, objective) "
            f"SELECT {sql_text(row['campaign_id'])}, {sql_text(row['campaign_name'])}, platform_key, 20260301, 'LeadGeneration' "
            f"FROM dim_platform WHERE platform_name = {sql_text(row['platform'])} "
            "ON DUPLICATE KEY UPDATE campaign_name = VALUES(campaign_name);"
        )

    for row in unique_rows(rows, ("post_id",)):
        published_date_key = row["published_date"].replace("-", "")
        statements.append(
            "INSERT INTO dim_post (source_post_id, platform_key, campaign_key, property_key, published_date_key, published_time, post_type, post_caption, post_url) "
            "SELECT "
            f"{sql_text(row['post_id'])}, p.platform_key, c.campaign_key, pr.property_key, {published_date_key}, "
            f"{sql_text(row['published_time'])}, {sql_text(row['post_type'])}, {sql_text(row['post_caption'])}, {sql_text(row['post_url'])} "
            "FROM dim_platform p "
            "JOIN dim_campaign c ON c.platform_key = p.platform_key "
            "JOIN dim_property pr ON pr.source_property_id = " + sql_text(row["property_id"]) + " "
            "WHERE p.platform_name = " + sql_text(row["platform"]) + " AND c.source_campaign_id = " + sql_text(row["campaign_id"]) + " "
            "ON DUPLICATE KEY UPDATE post_caption = VALUES(post_caption), post_url = VALUES(post_url);"
        )

    # Facts are the events we count and analyse. They are built from staging,
    # not directly from the raw CSV.
    statements.extend(
        [
            "SET @batch_id = (SELECT MAX(load_batch_id) FROM etl_load_batch "
            "WHERE source_system = 'CRM' AND source_file_name = 'crm_leads_cleaned.csv' AND status = 'Completed');",
            "INSERT INTO fact_lead (source_lead_id, enquiry_date_key, inspection_date_key, conversion_date_key, "
            "platform_key, campaign_key, post_key, property_key, agent_key, lead_status, conversion_type, revenue_amount, load_batch_id) "
            "SELECT s.source_lead_id, "
            "DATE_FORMAT(STR_TO_DATE(s.enquiry_date_text, '%Y-%m-%d'), '%Y%m%d') + 0, "
            "CASE WHEN s.inspection_date_text IS NULL THEN NULL ELSE DATE_FORMAT(STR_TO_DATE(s.inspection_date_text, '%Y-%m-%d'), '%Y%m%d') + 0 END, "
            "CASE WHEN s.conversion_date_text IS NULL THEN NULL ELSE DATE_FORMAT(STR_TO_DATE(s.conversion_date_text, '%Y-%m-%d'), '%Y%m%d') + 0 END, "
            "c.platform_key, c.campaign_key, po.post_key, pr.property_key, a.agent_key, s.lead_status_text, "
            "s.conversion_type_text, s.revenue_text, s.load_batch_id "
            "FROM stg_crm_lead s "
            "JOIN dim_campaign c ON c.source_campaign_id = s.campaign_id_text "
            "JOIN dim_post po ON po.source_post_id = s.post_id_text "
            "JOIN dim_property pr ON pr.source_property_id = s.property_id_text "
            "JOIN dim_agent a ON a.source_agent_id = s.agent_id_text "
            "WHERE s.load_batch_id = @batch_id "
            "ON DUPLICATE KEY UPDATE lead_status = VALUES(lead_status), inspection_date_key = VALUES(inspection_date_key), "
            "conversion_date_key = VALUES(conversion_date_key), conversion_type = VALUES(conversion_type), "
            "revenue_amount = VALUES(revenue_amount), updated_at_utc = CURRENT_TIMESTAMP;",
            "UPDATE stg_crm_lead SET is_processed = 1 WHERE load_batch_id = @batch_id;",
            "SELECT @batch_id AS published_batch_id;",
            "SELECT COUNT(*) AS fact_leads_from_synthetic_data FROM fact_lead WHERE source_lead_id LIKE 'CRM-%';",
            "SELECT lead_status, COUNT(*) AS leads FROM fact_lead WHERE source_lead_id LIKE 'CRM-%' GROUP BY lead_status ORDER BY lead_status;",
        ]
    )

    result = subprocess.run(
        ["mariadb", DATABASE], input="\n".join(statements), text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        print("Publishing did not complete. MariaDB said:")
        print(result.stderr)
        raise SystemExit(result.returncode)

    print("Publishing completed. MariaDB confirmation:")
    print(result.stdout)


if __name__ == "__main__":
    main()
