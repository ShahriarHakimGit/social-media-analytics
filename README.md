# Zed Real Estate Social Media Analytics

This project combines synthetic CRM lead data and synthetic Meta post-performance data in MariaDB, then displays the results in a local dashboard. It runs on macOS without SQL Server or a password-based `root` login.

## What has been built

```text
Synthetic CSV files → Extract → Transform → Staging tables → Analytics facts → Reporting views → Local dashboard
```

- `stg_` tables temporarily store raw imported rows.
- `fact_` tables store measurable events: leads and daily post performance.
- `dim_` tables describe dates, platforms, agents, properties, campaigns and posts.
- `rpt_` views prepare joined data for dashboard pages.

## First-time database setup on macOS

1. Install and start MariaDB:

   ```bash
   brew install mariadb
   brew services start mariadb
   ```

2. Test the local connection:

   ```bash
   mariadb
   ```

   If you see a `MariaDB` prompt, type `exit`. Do not use `-u root -p` for this Homebrew setup.

3. From the project folder, create the database and its reporting views:

   ```bash
   mariadb < database/00_create_database.sql
   mariadb zed_real_estate_analytics < database/01_create_schema.sql
   mariadb zed_real_estate_analytics < database/02_seed_sample_data.sql
   mariadb zed_real_estate_analytics < database/03_reporting_views.sql
   ```

## Guided ETL workflow used in this project

The generator creates fake, non-personal data. Run these commands from the project folder in this order.

```bash
python3 etl/generate_synthetic_data.py

python3 etl/step_1_extract_crm.py
python3 etl/step_2_transform_crm.py
python3 etl/step_3_load_crm_to_staging.py
python3 etl/step_4_publish_crm_to_analytics.py

python3 etl/step_5_extract_meta.py
python3 etl/step_6_transform_meta.py
python3 etl/step_7_load_meta_to_staging.py
python3 etl/step_8_publish_meta_to_analytics.py
```

The first two stages of each source only read and validate CSV data. The load stages add a traceable batch to `etl_load_batch`, then store raw rows in a staging table. The publish stages create/update dimensions and populate the final fact tables.

## Run the local dashboard

After the ETL workflow completes, start the local dashboard:

```bash
python3 dashboard/server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser. Keep the terminal running while using the dashboard. It includes an executive overview, lead funnel, campaign performance and post performance.

## Verify the data

Open MariaDB:

```bash
mariadb zed_real_estate_analytics
```

Then run:

```sql
SELECT * FROM rpt_lead_funnel;
SELECT * FROM rpt_post_performance;
SELECT * FROM rpt_campaign_performance;
```

## Advanced importer (optional)

`etl/run_import.py` is a more production-like single-command importer. It requires the staging-table migration, a Python virtual environment, PyMySQL and a password-based `zed_etl` MariaDB user. It is not required for the guided workflow above.

## Team ownership suggestion

| Area | Responsibility |
| --- | --- |
| Database developer | Schema, indexes, data dictionary and migrations |
| ETL developer | CSV validation, batch logging, staging and publishing |
| BI developer | Reporting views, dashboard layout and measures |
| QA / project lead | Test data, reconciliation checks and project documentation |

## Key files

- `database/` — MariaDB schema, seed data, views, validation queries and documentation.
- `etl/` — synthetic data generator, CSV templates and ETL scripts.
- `etl/generated/` — generated raw and cleaned synthetic CSV files.
- `dashboard/` — local browser dashboard.
