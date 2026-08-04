"""
Job monitor: checks Greenhouse and Ashby job boards for target companies,
filters by title and location, and writes any new matches to jobs.html.

Run manually:
    python job_monitor.py

Dry run (doesn't update seen_jobs.json, just prints what it would find):
    python job_monitor.py --dry-run
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

STATE_FILE = Path(__file__).parent / "seen_jobs.json"
OUTPUT_FILE = Path(__file__).parent / "jobs.html"

# --- Companies to check -----------------------------------------------

# Greenhouse boards: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
GREENHOUSE_COMPANIES = {
    "figma": "Figma",
    "glossier": "Glossier",
    "voxmedia": "Vox Media",
    "squarespace": "Squarespace",
    "duolingo": "Duolingo",
    "dropbox": "Dropbox",
    "allbirds": "Allbirds",
    "reformation": "Reformation",
    "renttherunway": "Rent the Runway",
    "warbyparker": "Warby Parker",
    "everlane": "Everlane",
    "olaplexcareers": "Olaplex",
    "klaviyojobs": "Klaviyo",
    "faire": "Faire",
    "robinhood": "Robinhood",
    "doordashusa": "DoorDash",
}

# Ashby boards: https://api.ashbyhq.com/posting-api/job-board/{slug}
ASHBY_COMPANIES = {
    "notion": "Notion",
}

# Lever boards: https://api.lever.co/v0/postings/{slug}?mode=json
LEVER_COMPANIES = {
    "elfbeauty": "e.l.f. Beauty",
}

# Workday tenants need their own tenant/site ID and a POST request rather
# than a simple GET, so they're handled separately and are more fragile.
# Confirm the tenant/site values below still work before relying on this;
# Workday configs can change without notice.
WORKDAY_COMPANIES = {
    # "patagonia": {"tenant": "patagonia", "site": "External"},
}

# --- Filtering rules -----------------------------------------------

INCLUDE_KEYWORDS = [
    "program manager",
    "project manager",
    "creative operations",
    "creative ops",
    "design operations",
    "design ops",
    "creative producer",
    "marketing manager",
]

EXCLUDE_KEYWORDS = [
    "engineering",
    "technical",
]

LOCATION_KEYWORDS = [
    "new york",
    "nyc",
    "san francisco",
    "remote",
]

# Reject if location contains one of these, even if it also matched
# LOCATION_KEYWORDS (e.g. "Remote - Philippines" contains "remote" but
# also "philippines"). Bare "Remote" with no country named stays in.
LOCATION_EXCLUDE = [
    "philippines", "india", "canada", "uk", "united kingdom", "germany",
    "france", "spain", "poland", "brazil", "mexico", "australia",
    "singapore", "japan", "ireland", "netherlands", "emea", "apac",
]


def title_matches(title: str) -> bool:
    t = title.lower()
    if any(bad in t for bad in EXCLUDE_KEYWORDS):
        return False
    return any(good in t for good in INCLUDE_KEYWORDS)


def location_matches(location: str) -> bool:
    loc = (location or "").lower()
    if not loc:
        return True  # keep unlisted locations for manual review
    if any(bad in loc for bad in LOCATION_EXCLUDE):
        return False
    return any(good in loc for good in LOCATION_KEYWORDS)


def fetch_greenhouse(slug: str, company_name: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] Greenhouse fetch failed for {company_name}: {e}", file=sys.stderr)
        return []

    jobs = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        location = (job.get("location") or {}).get("name", "")
        if title_matches(title) and location_matches(location):
            jobs.append({
                "id": f"greenhouse-{slug}-{job['id']}",
                "company": company_name,
                "title": title,
                "location": location,
                "url": job.get("absolute_url", ""),
            })
    return jobs


def fetch_ashby(slug: str, company_name: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] Ashby fetch failed for {company_name}: {e}", file=sys.stderr)
        return []

    jobs = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        location = job.get("location", "")
        if title_matches(title) and location_matches(location):
            jobs.append({
                "id": f"ashby-{slug}-{job.get('id')}",
                "company": company_name,
                "title": title,
                "location": location,
                "url": job.get("jobUrl", ""),
            })
    return jobs


def fetch_lever(slug: str, company_name: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [warn] Lever fetch failed for {company_name}: {e}", file=sys.stderr)
        return []

    jobs = []
    for job in resp.json():
        title = job.get("text", "")
        location = (job.get("categories") or {}).get("location", "")
        if title_matches(title) and location_matches(location):
            jobs.append({
                "id": f"lever-{slug}-{job.get('id')}",
                "company": company_name,
                "title": title,
                "location": location,
                "url": job.get("hostedUrl", ""),
            })
    return jobs


def load_seen() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_seen(seen: dict) -> None:
    STATE_FILE.write_text(json.dumps(seen, indent=2))


def write_html(new_jobs: list[dict], all_seen_jobs: list[dict]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def row(job, is_new):
        badge = '<span style="background:#1a7f37;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-right:8px;">NEW</span>' if is_new else ""
        return f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">{badge}{job['company']}</td>
          <td style="padding:10px;border-bottom:1px solid #eee;"><a href="{job['url']}" target="_blank">{job['title']}</a></td>
          <td style="padding:10px;border-bottom:1px solid #eee;color:#666;">{job['location']}</td>
        </tr>"""

    new_rows = "".join(row(j, True) for j in new_jobs)
    old_rows = "".join(row(j, False) for j in all_seen_jobs if j["id"] not in {n["id"] for n in new_jobs})

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Job Monitor</title></head>
<body style="font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px;">
<h1>Job Monitor</h1>
<p style="color:#666;">Last checked: {now}</p>
<h2>New since last check ({len(new_jobs)})</h2>
<table style="width:100%;border-collapse:collapse;">{new_rows or '<tr><td style="padding:10px;color:#999;">Nothing new.</td></tr>'}</table>
<h2 style="margin-top:40px;">All open matches ({len(all_seen_jobs)})</h2>
<table style="width:100%;border-collapse:collapse;">{new_rows}{old_rows}</table>
</body></html>"""
    OUTPUT_FILE.write_text(html)


def main():
    dry_run = "--dry-run" in sys.argv
    seen = load_seen()

    all_jobs = []
    print("Checking Greenhouse companies...")
    for slug, name in GREENHOUSE_COMPANIES.items():
        jobs = fetch_greenhouse(slug, name)
        print(f"  {name}: {len(jobs)} matching")
        all_jobs.extend(jobs)

    print("Checking Ashby companies...")
    for slug, name in ASHBY_COMPANIES.items():
        jobs = fetch_ashby(slug, name)
        print(f"  {name}: {len(jobs)} matching")
        all_jobs.extend(jobs)

    print("Checking Lever companies...")
    for slug, name in LEVER_COMPANIES.items():
        jobs = fetch_lever(slug, name)
        print(f"  {name}: {len(jobs)} matching")
        all_jobs.extend(jobs)

    new_jobs = [j for j in all_jobs if j["id"] not in seen]

    print(f"\n{len(new_jobs)} new job(s) found out of {len(all_jobs)} total matches.")
    for j in new_jobs:
        print(f"  NEW: {j['company']} — {j['title']} ({j['location']})")

    write_html(new_jobs, all_jobs)
    print(f"Wrote {OUTPUT_FILE}")

    if not dry_run:
        for j in all_jobs:
            seen[j["id"]] = {"company": j["company"], "title": j["title"], "first_seen": datetime.now(timezone.utc).isoformat()}
        save_seen(seen)
    else:
        print("[dry run] seen_jobs.json not updated.")


if __name__ == "__main__":
    main()
