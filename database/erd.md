# Reporting database ERD

```mermaid
erDiagram
    LOAD_BATCH ||--o{ REJECTED_RECORD : records
    LOAD_BATCH ||--o{ STG_CRM_LEAD : contains
    LOAD_BATCH ||--o{ STG_META_POST_PERFORMANCE : contains
    LOAD_BATCH ||--o{ POST_PERFORMANCE_DAILY : loads
    LOAD_BATCH ||--o{ LEAD : loads

    PLATFORM ||--o{ CAMPAIGN : runs
    PLATFORM ||--o{ POST : hosts
    DATE ||--o{ CAMPAIGN : dates
    DATE ||--o{ POST : published
    CAMPAIGN ||--o{ POST : groups
    PROPERTY ||--o{ POST : promotes

    POST ||--o{ POST_PERFORMANCE_DAILY : measures
    DATE ||--o{ POST_PERFORMANCE_DAILY : reports

    DATE ||--o{ LEAD : enquiry_inspection_conversion_dates
    PLATFORM ||--o{ LEAD : attributes
    CAMPAIGN ||--o{ LEAD : attributes
    POST ||--o{ LEAD : attributes
    PROPERTY ||--o{ LEAD : concerns
    AGENT ||--o{ LEAD : assigned
```

Relationships pointing to `LEAD` from platform, campaign, post, property and agent are optional. This preserves CRM leads that cannot be reliably attributed to a social post while allowing dashboard users to distinguish attributed and unattributed outcomes.
