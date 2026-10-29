"""ETL Step 5: Extract post-performance records from the synthetic Meta CSV."""

import csv
from collections import Counter
from pathlib import Path


CSV_FILE = Path(__file__).parent / "generated" / "meta_post_performance_synthetic.csv"


def main() -> None:
    # Extract: read each post-performance row into Python dictionaries.
    with CSV_FILE.open(encoding="utf-8-sig", newline="") as file:
        posts = list(csv.DictReader(file))

    platforms = Counter(post["platform"] for post in posts)
    total_impressions = sum(int(post["impressions"]) for post in posts)

    print(f"File read: {CSV_FILE.name}")
    print(f"Post-performance records extracted: {len(posts)}")
    print(f"Total impressions in the file: {total_impressions:,}")
    print("Posts by platform:")
    for platform, count in sorted(platforms.items()):
        print(f"  {platform}: {count}")

    print("\nFirst post extracted:")
    first_post = posts[0]
    for field in ("source_post_id", "report_date", "platform", "impressions", "link_clicks"):
        print(f"  {field}: {first_post[field]}")


if __name__ == "__main__":
    main()
