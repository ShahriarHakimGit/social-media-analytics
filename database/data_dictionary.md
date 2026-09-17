# Database data dictionary

## Reporting grain

| Table | One row means | Main source |
| --- | --- | --- |
| `fact_post_performance_daily` | One Meta post measured on one calendar day | Meta Business Suite export |
| `fact_lead` | One CRM lead, updated as it moves through the funnel | CRM export |

## Dimensions

| Table | Purpose | Natural key |
| --- | --- | --- |
| `dim_date` | Calendar filters and reporting dates | `calendar_date` |
| `dim_platform` | Supported social platforms | `platform_name` |
| `dim_agent` | CRM agent assigned to a lead | `source_agent_id` |
| `dim_property` | Advertised/listed property | `source_property_id` |
| `dim_campaign` | Meta campaign and objective | `source_campaign_id` |
| `dim_post` | Published social item | `source_post_id` |

## Required source fields

CRM rows require a unique lead ID and enquiry date. Agent, property, campaign and post IDs may be blank when attribution is unavailable. A conversion requires a conversion date, a conversion type of `Sale` or `Lease`, and a non-negative revenue amount.

Meta performance rows require a unique post ID and report date. All metric fields must be whole non-negative numbers except ad spend, which is a non-negative decimal.

## Important ETL mappings

| Source concept | Target |
| --- | --- |
| CRM lead identifier | `fact_lead.source_lead_id` |
| CRM enquiry / inspection / conversion dates | date keys in `fact_lead` |
| CRM status | `fact_lead.lead_status` |
| Meta post identifier | `dim_post.source_post_id` |
| Meta daily impressions, reach, clicks, engagements, spend | `fact_post_performance_daily` |
| Invalid row and reason | `etl_rejected_record` |

The ETL should validate dates with `STR_TO_DATE` and numeric values before conversion, send invalid rows to `etl_rejected_record`, then mark valid staging rows as processed only after dimension and fact upserts succeed.
