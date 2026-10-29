"""Create safe, repeatable CSV files that imitate CRM and Meta exports.

Run from the project folder:
    python3 etl/generate_synthetic_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RANDOM = random.Random(3018)  # Keeps the generated data the same each run.
OUTPUT = Path(__file__).parent / "generated"

AGENTS = [
    {"agent_id": "AG-001", "agent_name": "Ava Nguyen", "agent_email": "ava.nguyen@zedrealestate.example"},
    {"agent_id": "AG-002", "agent_name": "Noah Wilson", "agent_email": "noah.wilson@zedrealestate.example"},
]

PROPERTIES = [
    {"property_id": "PROP-001", "property_type": "House", "suburb": "Richmond", "state_code": "VIC", "postcode": "3121", "bedrooms": 3, "listing_price": 1250000},
    {"property_id": "PROP-002", "property_type": "Apartment", "suburb": "South Yarra", "state_code": "VIC", "postcode": "3141", "bedrooms": 2, "listing_price": 780000},
    {"property_id": "PROP-003", "property_type": "Townhouse", "suburb": "Prahran", "state_code": "VIC", "postcode": "3181", "bedrooms": 3, "listing_price": 980000},
]

POSTS = [
    {"source_post_id": "FB-POST-001", "platform": "Facebook", "campaign_id": "META-AUTUMN-26", "campaign_name": "Autumn Listings 2026", "property_id": "PROP-001", "published_date": "2026-03-05", "published_time": "10:30:00", "post_type": "Carousel", "post_caption": "Richmond family home inspection"},
    {"source_post_id": "IG-POST-001", "platform": "Instagram", "campaign_id": "IG-AUTUMN-26", "campaign_name": "Autumn Lifestyle 2026", "property_id": "PROP-002", "published_date": "2026-03-06", "published_time": "18:00:00", "post_type": "Reel", "post_caption": "South Yarra apartment tour"},
    {"source_post_id": "FB-POST-002", "platform": "Facebook", "campaign_id": "META-AUTUMN-26", "campaign_name": "Autumn Listings 2026", "property_id": "PROP-003", "published_date": "2026-03-10", "published_time": "12:00:00", "post_type": "Image", "post_caption": "Prahran townhouse now listed"},
    {"source_post_id": "IG-POST-002", "platform": "Instagram", "campaign_id": "IG-AUTUMN-26", "campaign_name": "Autumn Lifestyle 2026", "property_id": "PROP-001", "published_date": "2026-03-12", "published_time": "17:30:00", "post_type": "Reel", "post_caption": "Richmond home walkthrough"},
    {"source_post_id": "FB-POST-003", "platform": "Facebook", "campaign_id": "META-AUTUMN-26", "campaign_name": "Autumn Listings 2026", "property_id": "PROP-002", "published_date": "2026-03-15", "published_time": "09:00:00", "post_type": "Link", "post_caption": "South Yarra open inspection"},
    {"source_post_id": "IG-POST-003", "platform": "Instagram", "campaign_id": "IG-AUTUMN-26", "campaign_name": "Autumn Lifestyle 2026", "property_id": "PROP-003", "published_date": "2026-03-18", "published_time": "19:00:00", "post_type": "Carousel", "post_caption": "Prahran property highlights"},
]


def property_for(property_id):
    return next(item for item in PROPERTIES if item["property_id"] == property_id)


def write_meta_file():
    headers = ["source_post_id", "report_date", "platform", "campaign_id", "campaign_name", "property_id", "property_type", "suburb", "state_code", "postcode", "bedrooms", "listing_price", "published_date", "published_time", "post_type", "post_caption", "post_url", "impressions", "reach", "link_clicks", "reactions", "comments", "shares", "saves", "ad_spend"]
    with (OUTPUT / "meta_post_performance_synthetic.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for post in POSTS:
            property_data = property_for(post["property_id"])
            impressions = RANDOM.randint(2200, 9500)
            row = {**post, **property_data, "report_date": post["published_date"], "post_url": f"https://example.com/{post['source_post_id'].lower()}", "impressions": impressions, "reach": int(impressions * RANDOM.uniform(0.72, 0.88)), "link_clicks": RANDOM.randint(45, 300), "reactions": RANDOM.randint(80, 550), "comments": RANDOM.randint(5, 45), "shares": RANDOM.randint(5, 70), "saves": RANDOM.randint(4, 90), "ad_spend": round(RANDOM.uniform(70, 320), 2)}
            writer.writerow(row)


def write_crm_file():
    headers = ["source_lead_id", "enquiry_date", "inspection_date", "conversion_date", "agent_id", "agent_name", "agent_email", "property_id", "property_type", "suburb", "state_code", "postcode", "bedrooms", "listing_price", "platform", "campaign_id", "campaign_name", "post_id", "published_date", "published_time", "post_type", "post_caption", "post_url", "lead_status", "conversion_type", "revenue"]
    statuses = ["Converted", "InspectionBooked", "Enquiry", "Lost", "Enquiry", "InspectionBooked", "Converted", "Lost", "Enquiry", "InspectionBooked", "Enquiry", "Converted"]
    start = date(2026, 3, 6)
    with (OUTPUT / "crm_leads_synthetic.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for number, status in enumerate(statuses, start=1):
            post = POSTS[(number - 1) % len(POSTS)]
            property_data = property_for(post["property_id"])
            agent = AGENTS[(number - 1) % len(AGENTS)]
            enquiry = start + timedelta(days=number - 1)
            post_values = {key: item for key, item in post.items() if key != "source_post_id"}
            row = {**agent, **property_data, **post_values, "source_lead_id": f"CRM-{1000 + number}", "enquiry_date": enquiry.isoformat(), "inspection_date": "", "conversion_date": "", "conversion_type": "", "revenue": "", "post_id": post["source_post_id"], "post_url": f"https://example.com/{post['source_post_id'].lower()}", "lead_status": status}
            if status in ("InspectionBooked", "Converted"):
                row["inspection_date"] = (enquiry + timedelta(days=3)).isoformat()
            if status == "Converted":
                row["conversion_date"] = (enquiry + timedelta(days=12)).isoformat()
                row["conversion_type"] = "Sale" if property_data["property_type"] != "Apartment" else "Lease"
                row["revenue"] = property_data["listing_price"] if row["conversion_type"] == "Sale" else 2800
            writer.writerow(row)


def main():
    OUTPUT.mkdir(exist_ok=True)
    write_meta_file()
    write_crm_file()
    print("Created etl/generated/crm_leads_synthetic.csv (12 fake CRM leads)")
    print("Created etl/generated/meta_post_performance_synthetic.csv (6 fake Meta posts)")


if __name__ == "__main__":
    main()
