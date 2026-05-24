# Marketing Intelligence Agent — Setup

Automated marketing intelligence for Burger Boy. The agent monitors a curated list of
18 Instagram brand-strategy accounts, downloads and transcribes any videos (AssemblyAI),
analyses each post with Claude, saves the insights to Notion, and assembles a weekly
Monday marketing brief.

## Files

- `marketing_agent.py` — the agent (daily monitoring + weekly brief generation).
- `requirements.txt` — Python dependencies (`anthropic`, `requests`).
- `.github/workflows/marketing-agent.yml` — schedules the daily run and the Monday brief, and allows manual runs.
- `SETUP.md` — this file.

## 1. Add the API keys as GitHub Secrets

In this repo, go to **Settings → Secrets and variables → Actions → New repository secret**
and add:

- `CLAUDE_API_KEY` — from console.anthropic.com
- `NOTION_API_KEY` — from notion.so/my-integrations
- `APIFY_API_KEY` — from apify.com (optional; see step 4)
- `ASSEMBLYAI_API_KEY` — from assemblyai.com (optional; free tier — used to transcribe video posts)

Never paste these keys into the code or commit them — this repo is public.

## 2. Connect the Notion integration

Create an internal integration at notion.so/my-integrations, copy its secret into the
`NOTION_API_KEY` secret above, then **share each target database with the integration**
(open the database → ••• menu → Connections → add your integration). The agent can only
read/write databases that have been shared with it.

## 3. Confirm the Notion database IDs

Open `marketing_agent.py` and check the two IDs near the top:

```python
INTELLIGENCE_FEED_DB = "69247ce1-fd74-41df-8b0d-17e16910e62c"  # House of AG Feed
MONDAY_BRIEFS_DB     = "4c95d2a5-497a-4576-bb32-c0baf94e8615"  # Monday Marketing Briefs
```

These are placeholders and must point at your real databases. They do **not** match the
"Marketing Brief Sources" database. The agent also expects specific property names in each
database (e.g. `Post Title`, `Themes`, `Include in Brief` in the feed; `Week Of`,
`Headline News`, etc. in the briefs) — make sure those columns exist with matching names.

## 4. Instagram scraping + video transcription

- **Without** `APIFY_API_KEY`: the script runs in manual-fallback mode and prints
  instructions instead of pulling posts automatically.
- **With** `APIFY_API_KEY`: it uses the Apify Instagram scraper to fetch posts automatically.
- **With** `ASSEMBLYAI_API_KEY`: video posts are downloaded and transcribed (AssemblyAI free
  tier), and the transcript is fed into the Claude analysis alongside the caption. Without the
  key, video posts are still analysed from their captions only.

Rough running cost with everything on: ~EUR 5–10/month (Apify + Claude API; AssemblyAI free tier).

## 5. Schedule

GitHub Actions cron runs in **UTC**:

- `0 7 * * *` — daily monitoring at 07:00 UTC (08:00 Irish time during summer / IST).
- `0 8 * * 1` — weekly brief every Monday at 08:00 UTC (09:00 Irish time during summer).

## 6. Run it manually

From the **Actions** tab → **Marketing Intelligence Agent** → **Run workflow**, pick
`daily` or `brief`.

To run locally:

```bash
pip install -r requirements.txt
export CLAUDE_API_KEY=...      # plus NOTION_API_KEY and (optionally) APIFY_API_KEY, ASSEMBLYAI_API_KEY
python marketing_agent.py          # daily monitoring across all 18 accounts
python marketing_agent.py --brief  # generate the weekly brief
```
