# Job Monitor

Checks Greenhouse and Ashby job boards daily for postings matching your
target titles and locations, and writes matches to `jobs.html`. No email —
you just open the file (or the file's raw GitHub link) to see what's new.

## What's covered right now

Confirmed on Greenhouse: Figma, Glossier, Vox Media, Squarespace, Duolingo,
Dropbox, Allbirds.
Confirmed on Ashby: Notion.

Not included yet: Patagonia, Netflix, Condé Nast, Shopify, REI, Canva.
Patagonia and Netflix are on Workday, which needs a tenant ID/site name I
couldn't verify without live internet access — send me their exact careers
URL and I'll wire it in properly. Shopify blocks scraping via robots.txt.
REI has no stable public API. Canva is a custom site.

## One-time setup (about 15 minutes)

### 1. Create a GitHub repo
- Go to github.com and sign in (create a free account if you don't have one).
- Click the "+" in the top right → "New repository."
- Name it something like `job-monitor`. Set it to **Private**. Don't add a
  README (you already have one). Click "Create repository."

### 2. Upload these files
- On your new repo's page, click "uploading an existing file."
- Drag in everything from this folder, **including the `.github` folder**
  (it's hidden in some file browsers — make sure it comes along; that's
  what tells GitHub to actually run the script on a schedule).
- Commit the files (the green button, straight to the `main` branch is fine).

### 3. Turn on Actions
- Click the "Actions" tab on your repo. GitHub sometimes asks you to
  confirm you want workflows enabled for this repo — click enable/allow.
- You should see "Job Monitor" listed as a workflow.

### 4. Run it once manually to confirm it works
- Still in the Actions tab, click "Job Monitor" on the left, then the
  "Run workflow" dropdown on the right, then the green "Run workflow" button.
- Wait about 30 seconds, refresh, click into the run. Green checkmark = it
  worked. Red X = something broke — copy the error text and send it to me.

### 5. Check the result
- Back in the main repo view, click `jobs.html`, then "raw" — this shows
  the actual page. Bookmark that raw URL; it updates every time the
  workflow runs.

After that first manual run, it's live: it'll run automatically every day
at 7am Pacific (adjust the cron line in
`.github/workflows/job-monitor.yml` if you want a different time — cron
times are in UTC).

## Running it locally instead (optional)

If you'd rather run it yourself instead of via GitHub Actions:

```
pip install -r requirements.txt
python job_monitor.py
```

Dry run (doesn't mark anything as seen, just shows what it would find):

```
python job_monitor.py --dry-run
```

## How dedup works

`seen_jobs.json` tracks every job ID already surfaced. Each run, the
workflow commits the updated file back to the repo, so the history
persists across days — you'll only see each posting flagged "NEW" once.
