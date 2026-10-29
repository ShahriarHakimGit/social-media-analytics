"""Small local dashboard server for the Zed Real Estate analytics project.

It uses the same local `mariadb` connection as the ETL scripts. No Python
packages or database passwords are required for this learning version.
"""

import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DATABASE = "zed_real_estate_analytics"
DIRECTORY = Path(__file__).parent


def query(sql: str, columns: list[str]) -> list[dict[str, str]]:
    """Run a read-only query and return MariaDB's tab-separated result as JSON-ready rows."""
    result = subprocess.run(
        ["mariadb", "--batch", "--skip-column-names", DATABASE, "-e", sql],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return [
        dict(zip(columns, line.split("\t")))
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def dashboard_data() -> dict:
    summary = query(
        "SELECT COUNT(*), SUM(lead_status = 'Converted'), COALESCE(SUM(revenue_amount), 0) FROM fact_lead;",
        ["leads", "converted", "revenue"],
    )[0]
    media = query(
        "SELECT COALESCE(SUM(impressions), 0), COALESCE(SUM(link_clicks), 0), COALESCE(SUM(ad_spend), 0) "
        "FROM fact_post_performance_daily;",
        ["impressions", "clicks", "spend"],
    )[0]
    statuses = query(
        "SELECT lead_status, COUNT(*) FROM fact_lead GROUP BY lead_status ORDER BY FIELD(lead_status, 'Enquiry', 'InspectionBooked', 'Converted', 'Lost');",
        ["status", "count"],
    )
    campaigns = query(
        "SELECT campaign_name, SUM(impressions), SUM(link_clicks), ROUND(SUM(ad_spend), 2) "
        "FROM rpt_post_performance GROUP BY campaign_name ORDER BY SUM(impressions) DESC;",
        ["campaign", "impressions", "clicks", "spend"],
    )
    posts = query(
        "SELECT source_post_id, platform_name, impressions, link_clicks, engagement_rate_pct "
        "FROM rpt_post_performance ORDER BY impressions DESC LIMIT 6;",
        ["post", "platform", "impressions", "clicks", "engagement"],
    )
    return {"summary": {**summary, **media}, "statuses": statuses, "campaigns": campaigns, "posts": posts}


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        if self.path == "/api/dashboard":
            try:
                body = json.dumps(dashboard_data()).encode()
                self.send_response(200)
            except RuntimeError as error:
                body = json.dumps({"error": str(error)}).encode()
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DashboardHandler)
    print("Dashboard available at http://127.0.0.1:8000")
    print("Keep this terminal running while using the dashboard. Press Control+C to stop it.")
    server.serve_forever()
