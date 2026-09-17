# Zed Real Estate Analytics Database

This folder contains the MariaDB database foundation for the Social Media Lead Analytics Dashboard. MariaDB is free and runs on macOS and Windows.

## Database model

The reporting layer uses a star schema. `dim_` tables are stable filters (date, platform, campaign, agent, property and post). `fact_` tables hold daily post performance and individual CRM leads. `stg_` tables receive raw CSV/Excel data; `etl_` tables log load batches and rejected rows.

## Setup on macOS

1. Install Homebrew if required, then run `brew install mariadb`.
2. Start MariaDB with `brew services start mariadb`.
3. From the project folder, run:

   ```bash
   mariadb -u root < database/00_create_database.sql
   mariadb -u root zed_real_estate_analytics < database/01_create_schema.sql
   mariadb -u root zed_real_estate_analytics < database/02_seed_sample_data.sql
   mariadb -u root zed_real_estate_analytics < database/03_reporting_views.sql
   ```

If your MariaDB root account has a password, add `-p` after `root`; it will prompt securely. For a graphical tool, install DBeaver Community and connect to `localhost` on port `3306`.

## Setup on Windows

Install MariaDB Community Server, then run these same scripts through DBeaver Community, HeidiSQL, or the `mariadb` command-line client. Script `00` creates `zed_real_estate_analytics`; run the remaining scripts while connected to it.

## Run order

1. `database/00_create_database.sql` — creates the MariaDB database.
2. `database/01_create_schema.sql` — creates dimensions, facts, staging and ETL tables.
3. `database/02_seed_sample_data.sql` — optional repeatable demo data.
4. `database/03_reporting_views.sql` — dashboard-ready reporting views.
5. `database/04_validation_queries.sql` — checks after an ETL load.

The schema is for a new development database. The seed script uses `INSERT IGNORE`, so it can be re-run without duplicating its sample data.

## Team ownership suggestion

| Area | Responsibility |
| --- | --- |
| Database developer | Schema changes, indexes, data dictionary and migration review |
| ETL developer | CSV/Excel validation, staging loads, dimension/fact upserts and batch/reject logging |
| BI developer | Dashboard connection, reporting views and visual measures |
| QA / project lead | Test data, reconciliation checks, user acceptance tests and release notes |

Do not use `stg_` tables directly in a dashboard. Use `rpt_` views or the dimensions and facts.

## Key rules

- Preserve source-system IDs in `source_*_id` columns.
- One `fact_lead` row is one CRM lead; update it as the lead progresses.
- One `fact_post_performance_daily` row measures one post on one date.
- Create an `etl_load_batch` record before each import and put rejected rows in `etl_rejected_record`.

## Files

- `database/00_create_database.sql` — creates the MariaDB database.
- `database/01_create_schema.sql` — dimensions, facts, staging and ETL tables.
- `database/02_seed_sample_data.sql` — small repeatable demo dataset.
- `database/03_reporting_views.sql` — dashboard-ready reporting views.
- `database/04_validation_queries.sql` — reconciliation and data-quality checks.
- `database/data_dictionary.md` — field-level ETL and dashboard guidance.
- `database/erd.md` — relationship diagram for team discussion and documentation.
