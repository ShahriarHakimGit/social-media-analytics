"""ETL Step 8: Publish staged Meta metrics to the analytics fact table."""

import subprocess


DATABASE = "zed_real_estate_analytics"


def main() -> None:
    # This query reads the latest completed Meta batch from staging, connects
    # it to its post dimension, and publishes daily metrics for reporting.
    sql = f"""
USE {DATABASE};
SET @batch_id = (
  SELECT MAX(load_batch_id)
  FROM etl_load_batch
  WHERE source_system = 'Meta'
    AND source_file_name = 'meta_post_performance_cleaned.csv'
    AND status = 'Completed'
);

INSERT INTO fact_post_performance_daily
  (post_key, date_key, impressions, reach, link_clicks, reactions, comments, shares, saves, ad_spend, load_batch_id)
SELECT
  p.post_key,
  DATE_FORMAT(STR_TO_DATE(s.report_date_text, '%Y-%m-%d'), '%Y%m%d') + 0,
  s.impressions_text + 0,
  s.reach_text + 0,
  s.link_clicks_text + 0,
  s.reactions_text + 0,
  s.comments_text + 0,
  s.shares_text + 0,
  s.saves_text + 0,
  s.ad_spend_text + 0,
  s.load_batch_id
FROM stg_meta_post_performance s
JOIN dim_post p ON p.source_post_id = s.source_post_id
WHERE s.load_batch_id = @batch_id
ON DUPLICATE KEY UPDATE
  impressions = VALUES(impressions), reach = VALUES(reach), link_clicks = VALUES(link_clicks),
  reactions = VALUES(reactions), comments = VALUES(comments), shares = VALUES(shares),
  saves = VALUES(saves), ad_spend = VALUES(ad_spend), load_batch_id = VALUES(load_batch_id);

UPDATE stg_meta_post_performance
SET is_processed = 1
WHERE load_batch_id = @batch_id;

SELECT @batch_id AS published_batch_id;
SELECT COUNT(*) AS performance_records_from_synthetic_data
FROM fact_post_performance_daily WHERE load_batch_id = @batch_id;
SELECT SUM(impressions) AS total_impressions, SUM(link_clicks) AS total_link_clicks,
       ROUND(SUM(ad_spend), 2) AS total_ad_spend
FROM fact_post_performance_daily WHERE load_batch_id = @batch_id;
"""

    result = subprocess.run(
        ["mariadb", DATABASE], input=sql, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        print("Publishing did not complete. MariaDB said:")
        print(result.stderr)
        raise SystemExit(result.returncode)

    print("Publishing completed. MariaDB confirmation:")
    print(result.stdout)


if __name__ == "__main__":
    main()
