"""Load CRM and Meta CSV exports into MariaDB.

Run from the repository root, for example:
  python etl/run_import.py --crm etl/input_templates/crm_leads.csv --meta etl/input_templates/meta_post_performance.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
PLATFORMS = {"facebook": "Facebook", "instagram": "Instagram"}
POST_TYPES = {"image": "Image", "video": "Video", "carousel": "Carousel", "story": "Story", "reel": "Reel", "link": "Link", "other": "Other"}
PROPERTY_TYPES = {"house": "House", "apartment": "Apartment", "townhouse": "Townhouse", "unit": "Unit", "land": "Land", "commercial": "Commercial"}
LEAD_STATUSES = {"enquiry": "Enquiry", "inspectionbooked": "InspectionBooked", "converted": "Converted", "lost": "Lost"}


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def config() -> dict[str, Any]:
    load_dotenv()
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(f"Missing {', '.join(missing)}. Copy etl/.env.example to etl/.env and fill it in.")
    return {"host": os.environ["DB_HOST"], "port": int(os.environ["DB_PORT"]), "database": os.environ["DB_NAME"], "user": os.environ["DB_USER"], "password": os.environ["DB_PASSWORD"], "charset": "utf8mb4", "autocommit": False}


def value(row: dict[str, str], key: str) -> str | None:
    raw = row.get(key, "").strip()
    return raw or None


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date '{raw}'. Use YYYY-MM-DD.")


def parse_time(raw: str | None) -> str | None:
    if not raw:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M:%S")
        except ValueError:
            pass
    raise ValueError(f"Invalid time '{raw}'. Use HH:MM or HH:MM:SS.")


def parse_number(raw: str | None, integer: bool = False) -> int | Decimal | None:
    if raw is None:
        return None
    try:
        number = Decimal(raw.replace(",", "").replace("$", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid number '{raw}'.") from exc
    if number < 0:
        raise ValueError("Numbers cannot be negative.")
    if integer and number != number.to_integral_value():
        raise ValueError(f"'{raw}' must be a whole number.")
    return int(number) if integer else number


def normalized(raw: str | None, choices: dict[str, str], field: str) -> str | None:
    if raw is None:
        return None
    result = choices.get(raw.replace(" ", "").lower())
    if not result:
        raise ValueError(f"Unsupported {field} '{raw}'.")
    return result


def date_key(cursor: Any, day: date | None) -> int | None:
    if not day:
        return None
    key = int(day.strftime("%Y%m%d"))
    cursor.execute(
        """INSERT INTO dim_date (date_key, calendar_date, calendar_year, calendar_quarter, calendar_month, month_name, week_of_year, day_of_month, day_of_week, day_name, is_weekend)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE calendar_date=VALUES(calendar_date)""",
        (key, day, day.year, (day.month - 1) // 3 + 1, day.month, day.strftime("%B"), int(day.strftime("%V")), day.day, day.weekday() + 1, day.strftime("%A"), day.weekday() >= 5),
    )
    return key


def scalar(cursor: Any, sql: str, params: tuple[Any, ...]) -> Any:
    cursor.execute(sql, params)
    result = cursor.fetchone()
    return result[0] if result else None


def upsert_dimensions(cursor: Any, row: dict[str, str], require_post: bool) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    platform = normalized(value(row, "platform"), PLATFORMS, "platform")
    platform_key = None
    if platform:
        cursor.execute("INSERT INTO dim_platform (platform_name) VALUES (%s) ON DUPLICATE KEY UPDATE is_active=1", (platform,))
        platform_key = scalar(cursor, "SELECT platform_key FROM dim_platform WHERE platform_name=%s", (platform,))

    agent_key = None
    if value(row, "agent_id"):
        if not value(row, "agent_name"):
            raise ValueError("agent_name is required when agent_id is supplied.")
        cursor.execute("""INSERT INTO dim_agent (source_agent_id,agent_name,email) VALUES (%s,%s,%s)
                          ON DUPLICATE KEY UPDATE agent_name=VALUES(agent_name),email=VALUES(email),is_active=1""",
                       (value(row, "agent_id"), value(row, "agent_name"), value(row, "agent_email")))
        agent_key = scalar(cursor, "SELECT agent_key FROM dim_agent WHERE source_agent_id=%s", (value(row, "agent_id"),))

    property_key = None
    if value(row, "property_id"):
        kind = normalized(value(row, "property_type"), PROPERTY_TYPES, "property_type")
        suburb = value(row, "suburb")
        if not kind or not suburb:
            raise ValueError("property_type and suburb are required when property_id is supplied.")
        cursor.execute("""INSERT INTO dim_property (source_property_id,property_type,suburb,state_code,postcode,bedrooms,listing_price)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)
                          ON DUPLICATE KEY UPDATE property_type=VALUES(property_type),suburb=VALUES(suburb),state_code=VALUES(state_code),postcode=VALUES(postcode),bedrooms=VALUES(bedrooms),listing_price=VALUES(listing_price),is_active=1""",
                       (value(row, "property_id"), kind, suburb, value(row, "state_code") or "VIC", value(row, "postcode"), parse_number(value(row, "bedrooms"), True), parse_number(value(row, "listing_price"))))
        property_key = scalar(cursor, "SELECT property_key FROM dim_property WHERE source_property_id=%s", (value(row, "property_id"),))

    campaign_key = None
    if value(row, "campaign_id"):
        if not platform_key or not value(row, "campaign_name"):
            raise ValueError("platform and campaign_name are required when campaign_id is supplied.")
        cursor.execute("""INSERT INTO dim_campaign (source_campaign_id,campaign_name,platform_key,objective)
                          VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE campaign_name=VALUES(campaign_name),platform_key=VALUES(platform_key),is_active=1""",
                       (value(row, "campaign_id"), value(row, "campaign_name"), platform_key, "LeadGeneration"))
        campaign_key = scalar(cursor, "SELECT campaign_key FROM dim_campaign WHERE source_campaign_id=%s", (value(row, "campaign_id"),))

    post_key = None
    if value(row, "post_id"):
        published = parse_date(value(row, "published_date"))
        post_type = normalized(value(row, "post_type"), POST_TYPES, "post_type")
        if not platform_key or not published or not post_type:
            raise ValueError("platform, published_date and post_type are required when post_id is supplied.")
        cursor.execute("""INSERT INTO dim_post (source_post_id,platform_key,campaign_key,property_key,published_date_key,published_time,post_type,post_caption,post_url)
                          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                          ON DUPLICATE KEY UPDATE platform_key=VALUES(platform_key),campaign_key=VALUES(campaign_key),property_key=VALUES(property_key),published_date_key=VALUES(published_date_key),published_time=VALUES(published_time),post_type=VALUES(post_type),post_caption=VALUES(post_caption),post_url=VALUES(post_url)""",
                       (value(row, "post_id"), platform_key, campaign_key, property_key, date_key(cursor, published), parse_time(value(row, "published_time")) or "00:00:00", post_type, value(row, "post_caption"), value(row, "post_url")))
        post_key = scalar(cursor, "SELECT post_key FROM dim_post WHERE source_post_id=%s", (value(row, "post_id"),))
    elif require_post:
        raise ValueError("post_id is required for Meta performance data.")
    return platform_key, agent_key, property_key, campaign_key, post_key


def reject(cursor: Any, batch_id: int, row_no: int, entity: str, error: Exception, row: dict[str, str]) -> None:
    cursor.execute("INSERT INTO etl_rejected_record (load_batch_id,source_row_number,entity_name,error_message,raw_payload) VALUES (%s,%s,%s,%s,%s)", (batch_id, row_no, entity, str(error)[:1000], json.dumps(row)))


def stage_crm(cursor: Any, batch_id: int, row_no: int, row: dict[str, str]) -> int:
    fields = ("source_lead_id,enquiry_date_text,inspection_date_text,conversion_date_text,agent_id_text,property_id_text,campaign_id_text,post_id_text,lead_status_text,conversion_type_text,revenue_text,agent_name_text,agent_email_text,property_type_text,suburb_text,state_code_text,postcode_text,bedrooms_text,listing_price_text,platform_text,campaign_name_text,published_date_text,published_time_text,post_type_text,post_caption_text,post_url_text")
    values = (value(row,"source_lead_id"),value(row,"enquiry_date"),value(row,"inspection_date"),value(row,"conversion_date"),value(row,"agent_id"),value(row,"property_id"),value(row,"campaign_id"),value(row,"post_id"),value(row,"lead_status"),value(row,"conversion_type"),value(row,"revenue"),value(row,"agent_name"),value(row,"agent_email"),value(row,"property_type"),value(row,"suburb"),value(row,"state_code"),value(row,"postcode"),value(row,"bedrooms"),value(row,"listing_price"),value(row,"platform"),value(row,"campaign_name"),value(row,"published_date"),value(row,"published_time"),value(row,"post_type"),value(row,"post_caption"),value(row,"post_url"))
    cursor.execute(f"INSERT INTO stg_crm_lead (load_batch_id,source_row_number,{fields}) VALUES (%s,%s,{','.join(['%s']*26)})", (batch_id,row_no,*values))
    return cursor.lastrowid


def stage_meta(cursor: Any, batch_id: int, row_no: int, row: dict[str, str]) -> int:
    fields = ("source_post_id,report_date_text,impressions_text,reach_text,link_clicks_text,reactions_text,comments_text,shares_text,saves_text,ad_spend_text,platform_text,campaign_id_text,campaign_name_text,property_id_text,property_type_text,suburb_text,state_code_text,postcode_text,bedrooms_text,listing_price_text,published_date_text,published_time_text,post_type_text,post_caption_text,post_url_text")
    values = (value(row,"source_post_id"),value(row,"report_date"),value(row,"impressions"),value(row,"reach"),value(row,"link_clicks"),value(row,"reactions"),value(row,"comments"),value(row,"shares"),value(row,"saves"),value(row,"ad_spend"),value(row,"platform"),value(row,"campaign_id"),value(row,"campaign_name"),value(row,"property_id"),value(row,"property_type"),value(row,"suburb"),value(row,"state_code"),value(row,"postcode"),value(row,"bedrooms"),value(row,"listing_price"),value(row,"published_date"),value(row,"published_time"),value(row,"post_type"),value(row,"post_caption"),value(row,"post_url"))
    cursor.execute(f"INSERT INTO stg_meta_post_performance (load_batch_id,source_row_number,{fields}) VALUES (%s,%s,{','.join(['%s']*25)})", (batch_id,row_no,*values))
    return cursor.lastrowid


def process_crm(cursor: Any, batch_id: int, row_no: int, row: dict[str, str]) -> None:
    if not value(row, "source_lead_id") or not value(row, "enquiry_date") or not value(row, "lead_status"):
        raise ValueError("source_lead_id, enquiry_date and lead_status are required.")
    status = normalized(value(row, "lead_status"), LEAD_STATUSES, "lead_status")
    conversion_type = value(row, "conversion_type")
    conversion_day = parse_date(value(row, "conversion_date"))
    revenue = parse_number(value(row, "revenue"))
    if status == "Converted" and (not conversion_day or conversion_type not in ("Sale", "Lease") or revenue is None):
        raise ValueError("Converted leads need conversion_date, conversion_type (Sale or Lease), and revenue.")
    if status != "Converted" and (conversion_day or conversion_type or revenue is not None):
        raise ValueError("Only Converted leads can have conversion data.")
    staging_id = stage_crm(cursor, batch_id, row_no, row)
    platform_key, agent_key, property_key, campaign_key, post_key = upsert_dimensions(cursor, row, False)
    enquiry_key = date_key(cursor, parse_date(value(row, "enquiry_date")))
    inspection_key = date_key(cursor, parse_date(value(row, "inspection_date")))
    conversion_key = date_key(cursor, conversion_day)
    cursor.execute("""INSERT INTO fact_lead (source_lead_id,enquiry_date_key,inspection_date_key,conversion_date_key,platform_key,campaign_key,post_key,property_key,agent_key,lead_status,conversion_type,revenue_amount,load_batch_id)
                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON DUPLICATE KEY UPDATE enquiry_date_key=VALUES(enquiry_date_key),inspection_date_key=VALUES(inspection_date_key),conversion_date_key=VALUES(conversion_date_key),platform_key=VALUES(platform_key),campaign_key=VALUES(campaign_key),post_key=VALUES(post_key),property_key=VALUES(property_key),agent_key=VALUES(agent_key),lead_status=VALUES(lead_status),conversion_type=VALUES(conversion_type),revenue_amount=VALUES(revenue_amount),load_batch_id=VALUES(load_batch_id)""",
                   (value(row,"source_lead_id"),enquiry_key,inspection_key,conversion_key,platform_key,campaign_key,post_key,property_key,agent_key,status,conversion_type,revenue,batch_id))
    cursor.execute("UPDATE stg_crm_lead SET is_processed=1 WHERE staging_crm_lead_id=%s", (staging_id,))


def process_meta(cursor: Any, batch_id: int, row_no: int, row: dict[str, str]) -> None:
    required = ("source_post_id", "report_date", "platform", "published_date", "post_type")
    if any(not value(row, field) for field in required):
        raise ValueError(f"Meta rows require: {', '.join(required)}.")
    staging_id = stage_meta(cursor, batch_id, row_no, row)
    _, _, _, _, post_key = upsert_dimensions(cursor, row, True)
    metrics = tuple(parse_number(value(row, field), True) or 0 for field in ("impressions","reach","link_clicks","reactions","comments","shares","saves"))
    cursor.execute("""INSERT INTO fact_post_performance_daily (post_key,date_key,impressions,reach,link_clicks,reactions,comments,shares,saves,ad_spend,load_batch_id)
                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON DUPLICATE KEY UPDATE impressions=VALUES(impressions),reach=VALUES(reach),link_clicks=VALUES(link_clicks),reactions=VALUES(reactions),comments=VALUES(comments),shares=VALUES(shares),saves=VALUES(saves),ad_spend=VALUES(ad_spend),load_batch_id=VALUES(load_batch_id)""",
                   (post_key,date_key(cursor,parse_date(value(row,"report_date"))),*metrics,parse_number(value(row,"ad_spend")) or 0,batch_id))
    cursor.execute("UPDATE stg_meta_post_performance SET is_processed=1 WHERE staging_meta_post_performance_id=%s", (staging_id,))


def import_file(connection: Any, source: str, path: Path) -> None:
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO etl_load_batch (source_system,source_file_name,status) VALUES (%s,%s,'Started')", (source, path.name))
        batch_id = cursor.lastrowid
        connection.commit()
    read = loaded = rejected = 0
    with path.open(newline="", encoding="utf-8-sig") as file:
        for row_no, row in enumerate(csv.DictReader(file), start=2):
            read += 1
            try:
                with connection.cursor() as cursor:
                    (process_crm if source == "CRM" else process_meta)(cursor, batch_id, row_no, row)
                connection.commit()
                loaded += 1
            except Exception as exc:
                connection.rollback()
                with connection.cursor() as cursor:
                    reject(cursor, batch_id, row_no, "CRM lead" if source == "CRM" else "Meta performance", exc, row)
                connection.commit()
                rejected += 1
    with connection.cursor() as cursor:
        cursor.execute("UPDATE etl_load_batch SET completed_at_utc=UTC_TIMESTAMP(),status=%s,rows_read=%s,rows_loaded=%s,rows_rejected=%s WHERE load_batch_id=%s", ("Completed" if rejected == 0 else "CompletedWithErrors", read, loaded, rejected, batch_id))
    connection.commit()
    print(f"{source}: batch {batch_id}; read={read}, loaded={loaded}, rejected={rejected}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load CRM and Meta CSV exports into MariaDB.")
    parser.add_argument("--crm", type=Path, help="Path to a CRM leads CSV.")
    parser.add_argument("--meta", type=Path, help="Path to a Meta post-performance CSV.")
    args = parser.parse_args()
    if not args.crm and not args.meta:
        parser.error("provide --crm, --meta, or both")
    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise SystemExit("PyMySQL is not installed. Activate .venv and run: pip install -r etl/requirements.txt") from exc
    connection = pymysql.connect(**config())
    try:
        for source, path in (("CRM", args.crm), ("Meta", args.meta)):
            if path:
                if not path.is_file():
                    raise FileNotFoundError(path)
                import_file(connection, source, path)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
