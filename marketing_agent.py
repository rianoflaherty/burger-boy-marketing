#!/usr/bin/env python3
"""
House of AG Marketing Intelligence Agent
Monitors a curated list of Instagram brand-strategy accounts for insights
Generates weekly marketing briefs for Burger Boy
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta
from anthropic import Anthropic

# ============================================================================
# CONFIGURATION
# ============================================================================

# Instagram accounts to monitor
INSTAGRAM_ACCOUNTS = [
    {"username": "house.of.ag", "name": "House of AG"},
    {"username": "shwinnabegobrand", "name": "Shwinna Begobrand"},
    {"username": "thebrandblueprint_", "name": "The Brand Blueprint"},
    {"username": "thebestmarketingnewsletterever", "name": "Best Marketing Newsletter"},
    {"username": "tatumbrandt", "name": "Tatum Brandt"},
    {"username": "orenmeetsworld", "name": "Oren Meets World"},
    {"username": "brian_blum", "name": "Brian Blum"},
    {"username": "jdomito_", "name": "J Domito"},
    {"username": "lukas.mullen", "name": "Lukas Mullen"},
    {"username": "eugbrandstrat", "name": "Eug Brand Strat"},
    {"username": "jason_swet", "name": "Jason Swet"},
    {"username": "fakeplasticbrands", "name": "Fake Plastic Brands"},
    {"username": "becauseofmarketing", "name": "Because of Marketing"},
    {"username": "shotbysammy_", "name": "Shot by Sammy"},
    {"username": "founderspodcast", "name": "Founders Podcast"},
    {"username": "calebralston", "name": "Caleb Ralston"},
    {"username": "jtbarnett", "name": "JT Barnett"},
    {"username": "rico.incarnati", "name": "Rico Incarnati"}
]

# Notion Database IDs (collection:// URLs from the databases we created)
# TODO: CONFIRM THESE IDs. They do NOT match the "Marketing Brief Sources"
#       data source built earlier (36a9a834-5c6f-8012-b6da-000b3fdf03ba).
#       Replace with the real IDs for your "House of AG Feed" and
#       "Monday Marketing Briefs" databases before running in production.
INTELLIGENCE_FEED_DB = "69247ce1-fd74-41df-8b0d-17e16910e62c"  # House of AG Feed
MONDAY_BRIEFS_DB = "4c95d2a5-497a-4576-bb32-c0baf94e8615"  # Monday Marketing Briefs

# API Keys (set these as environment variables / GitHub Secrets)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")  # Get from console.anthropic.com
NOTION_API_KEY = os.getenv("NOTION_API_KEY")  # Get from notion.so/my-integrations
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")  # Optional - for Instagram scraping
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")  # Optional - for video transcription (free tier)

# AssemblyAI endpoints
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com/v2"


# ============================================================================
# INSTAGRAM SCRAPING
# ============================================================================
def scrape_instagram_posts(username, days_back=7):
    """
    Scrapes recent Instagram posts from the specified username.

    For FREE version (no Apify): Uses public Instagram RSS/web scraping
    For PAID version: Uses Apify Instagram scraper

    Args:
        username: Instagram handle without @
        days_back: How many days of posts to fetch

    Returns:
        List of post dictionaries with: url, caption, date, media_type
    """

    if APIFY_API_KEY:
        # PAID VERSION: Use Apify Instagram Scraper
        # This is the most reliable method
        return _scrape_with_apify(username, days_back)
    else:
        # FREE VERSION: Basic scraping
        # Note: Instagram blocks most scraping - this is a placeholder
        # In practice, you'd need to manually check or use a free RSS service
        print(f"WARNING: No Apify API key found. Using manual fallback...")
        return _scrape_instagram_free(username, days_back)


def _scrape_with_apify(username, days_back):
    """Scrape Instagram using Apify (paid service, ~EUR 20/month)"""

    url = "https://api.apify.com/v2/acts/apify~instagram-scraper/runs"

    payload = {
        "username": [username],
        "resultsLimit": 10,
        "addParentData": False
    }

    headers = {
        "Content-Type": "application/json"
    }

    # Start the scraper
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        params={"token": APIFY_API_KEY}
    )

    if response.status_code != 201:
        print(f"ERROR: Apify scraper failed: {response.status_code}")
        return []

    run_id = response.json()["data"]["id"]

    # Wait for results
    dataset_url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/runs/{run_id}/dataset/items"

    import time
    for _ in range(30):  # Wait up to 5 minutes
        time.sleep(10)
        result = requests.get(dataset_url, params={"token": APIFY_API_KEY})

        if result.status_code == 200:
            data = result.json()
            if data:
                return _parse_apify_results(data, days_back)

    print("ERROR: Apify scraper timed out")
    return []


def _parse_apify_results(data, days_back):
    """Parse Apify results into our standard format"""

    posts = []
    cutoff_date = datetime.now() - timedelta(days=days_back)

    for item in data:
        # Parse timestamp
        timestamp = item.get("timestamp")
        if timestamp:
            post_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            if post_date < cutoff_date:
                continue

            posts.append({
                "url": item.get("url", ""),
                "caption": item.get("caption", ""),
                "date": post_date.strftime("%Y-%m-%d"),
                "media_type": _determine_media_type(item),
                "video_url": item.get("videoUrl", ""),
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0)
            })

    return posts


def _determine_media_type(item):
    """Determine if post is image, carousel, video, or reel"""

    if item.get("type") == "Video":
        return "Video"
    elif item.get("type") == "Sidecar":
        return "Carousel"
    else:
        return "Single Image"


def _scrape_instagram_free(username, days_back):
    """
    FREE fallback - returns empty list with instructions

    For a truly free solution, you would need to:
    1. Manually check the Instagram account
    2. Copy post URLs and captions
    3. Run this script with a JSON file of posts

    OR use a free Instagram RSS service
    """

    print(f"""
    MANUAL INSTAGRAM CHECK REQUIRED

    Go to: https://www.instagram.com/{username}/

    Look for new posts from the last {days_back} days.
    For each post, note:
    - Post URL
    - Caption text
    - Post date
    - Type (image, carousel, video)

    To automate this, add an Apify API key to environment variables.
    Cost: ~EUR 15-30/month depending on usage.
    """)

    # Return empty - manual workflow
    return []


# ============================================================================
# VIDEO DOWNLOAD + TRANSCRIPTION (AssemblyAI)
# ============================================================================
def download_video(video_url, dest_dir="/tmp"):
    """
    Download a video to a local temp file.

    Args:
        video_url: Direct URL to the video file
        dest_dir: Directory to save the temp file into

    Returns:
        Local file path, or None if the download failed / no URL.
    """

    if not video_url:
        return None

    local_path = os.path.join(dest_dir, f"ig_video_{int(time.time() * 1000)}.mp4")

    try:
        with requests.get(video_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return local_path

    except Exception as e:
        print(f"ERROR: Video download failed: {e}")
        return None


def transcribe_with_assemblyai(file_path):
    """
    Upload a local media file to AssemblyAI and return the transcript text.

    Uses the AssemblyAI free tier. Returns an empty string if no API key is
    set, the file is missing, or transcription fails.

    Args:
        file_path: Path to a local audio/video file

    Returns:
        Transcript text (str), empty if unavailable.
    """

    if not ASSEMBLYAI_API_KEY or not file_path or not os.path.exists(file_path):
        return ""

    headers = {"authorization": ASSEMBLYAI_API_KEY}

    try:
        # 1. Upload the local file to AssemblyAI
        with open(file_path, "rb") as f:
            upload_resp = requests.post(
                f"{ASSEMBLYAI_BASE_URL}/upload",
                headers=headers,
                data=f
            )

        if upload_resp.status_code != 200:
            print(f"ERROR: AssemblyAI upload failed: {upload_resp.status_code}")
            return ""

        upload_url = upload_resp.json()["upload_url"]

        # 2. Request transcription
        transcript_resp = requests.post(
            f"{ASSEMBLYAI_BASE_URL}/transcript",
            headers=headers,
            json={"audio_url": upload_url}
        )

        if transcript_resp.status_code != 200:
            print(f"ERROR: AssemblyAI transcript request failed: {transcript_resp.status_code}")
            return ""

        transcript_id = transcript_resp.json()["id"]

        # 3. Poll for completion (up to ~5 minutes)
        polling_url = f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}"

        for _ in range(60):
            poll = requests.get(polling_url, headers=headers).json()
            status = poll.get("status")

            if status == "completed":
                return poll.get("text", "") or ""
            if status == "error":
                print(f"ERROR: AssemblyAI transcription error: {poll.get('error')}")
                return ""

            time.sleep(5)

        print("ERROR: AssemblyAI transcription timed out")
        return ""

    except Exception as e:
        print(f"ERROR: AssemblyAI transcription failed: {e}")
        return ""


def transcribe_video_post(post):
    """
    For a video post, download the video and transcribe its audio.
    Returns the transcript text (empty string for non-video posts or on failure).
    """

    if post.get("media_type") != "Video" or not post.get("video_url"):
        return ""

    print("   Downloading + transcribing video...")
    video_path = download_video(post["video_url"])

    if not video_path:
        return ""

    transcript = transcribe_with_assemblyai(video_path)

    # Clean up the temp file
    try:
        os.remove(video_path)
    except OSError:
        pass

    return transcript


# ============================================================================
# CLAUDE AI ANALYSIS
# ============================================================================
def analyze_post_with_claude(post, account=None):
    """
    Sends Instagram post to Claude for brand strategy analysis.

    Args:
        post: Dictionary with url, caption, date, media_type, transcript
        account: Optional dict with the source account's "name" and "username"

    Returns:
        Dictionary with analysis results:
        - key_insights: What Burger Boy can learn
        - themes: List of applicable themes
        - burger_boy_application: Specific actionable ideas
        - excitement_level: How valuable this insight is
    """

    client = Anthropic(api_key=CLAUDE_API_KEY)

    # Build a source label from the account (falls back to a generic description)
    if account:
        source_label = f"{account.get('name', 'a brand-strategy account')} (@{account.get('username', '')})"
    else:
        source_label = "a brand-strategy / marketing account"

    transcript = post.get("transcript", "")
    transcript_block = transcript if transcript else "(no video / no transcript)"

    prompt = f"""You are a brand strategist analyzing Instagram content from {source_label},
a brand strategy / marketing source, to extract insights for Burger Boy - a neighbourhood smash burger
restaurant in Bray, Ireland.

INSTAGRAM POST:
URL: {post['url']}
Date: {post['date']}
Caption: {post['caption']}
Video Transcript: {transcript_block}

YOUR TASK:
Analyze this post and extract actionable brand strategy insights specifically for Burger Boy.

Consider:
1. **Brand Direction**: What strategic moves could this inspire?
2. **Content Ideas**: What content formats or storytelling approaches could we adapt?
3. **Community Building**: How could this help build deeper customer relationships?
4. **Trends**: What cultural moments or trends is House of AG identifying?
5. **Big Ideas**: Are there bold concepts here (like "start a social show") that could transform BB's marketing?

Return your analysis as JSON with these exact fields:
{{
  "post_title": "Short catchy title (5-8 words)",
  "key_insights": "2-3 sentence summary of what Burger Boy can learn",
  "themes": ["Theme1", "Theme2"], // Choose from: Brand Strategy, Content Ideas, Community Building, Storytelling, Trend Analysis, Social Media Tactics, Cultural Moments
  "burger_boy_application": "Specific, actionable ideas for how BB can use this (3-5 sentences with concrete examples)",
  "excitement_level": "Mind-Blowing" | "Very Interesting" | "Worth Noting" | "Reference"
}}

Be specific. Think like a brand strategist who knows Burger Boy's neighbourhood vibe and wants to help
them punch above their weight in marketing."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract JSON from response
        content = response.content[0].text

        # Try to parse JSON (handle if Claude wraps it in markdown)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        analysis = json.loads(content)
        return analysis

    except Exception as e:
        print(f"ERROR: Claude analysis failed: {e}")
        return {
            "post_title": "Analysis Failed",
            "key_insights": f"Error analyzing post: {str(e)}",
            "themes": ["Reference"],
            "burger_boy_application": "Manual review required",
            "excitement_level": "Reference"
        }


# ============================================================================
# NOTION INTEGRATION
# ============================================================================
def save_to_notion_intelligence_feed(post, analysis):
    """
    Saves analyzed post to Notion Intelligence Feed database.

    Args:
        post: Original post dictionary
        analysis: Claude's analysis results
    """

    url = "https://api.notion.com/v1/pages"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Map themes to match Notion options exactly
    theme_mapping = {
        "Brand Strategy": "Brand Strategy",
        "Content Ideas": "Content Ideas",
        "Community Building": "Community Building",
        "Storytelling": "Storytelling",
        "Trend Analysis": "Trend Analysis",
        "Social Media Tactics": "Social Media Tactics",
        "Cultural Moments": "Cultural Moments"
    }

    mapped_themes = [theme_mapping.get(t, t) for t in analysis.get("themes", [])]

    payload = {
        "parent": {"database_id": INTELLIGENCE_FEED_DB.replace("-", "")},
        "properties": {
            "Post Title": {
                "title": [{"text": {"content": analysis.get("post_title", "Untitled")}}]
            },
            "Post Date": {
                "date": {"start": post["date"]}
            },
            "Content Type": {
                "select": {"name": post.get("media_type", "Single Image")}
            },
            "Caption": {
                "rich_text": [{"text": {"content": post.get("caption", "")[:2000]}}]  # Notion limit
            },
            "Key Insights": {
                "rich_text": [{"text": {"content": analysis.get("key_insights", "")}}]
            },
            "Themes": {
                "multi_select": [{"name": theme} for theme in mapped_themes]
            },
            "BB Application": {
                "rich_text": [{"text": {"content": analysis.get("burger_boy_application", "")}}]
            },
            "Priority": {
                "select": {"name": analysis.get("excitement_level", "Worth Noting")}
            },
            "Instagram URL": {
                "url": post.get("url", "")
            },
            "Include in Brief": {
                "checkbox": analysis.get("excitement_level") in ["Mind-Blowing", "Very Interesting"]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"OK: Saved to Notion: {analysis.get('post_title')}")
            return True
        else:
            print(f"ERROR: Notion save failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: Notion API error: {e}")
        return False


# ============================================================================
# WEEKLY BRIEF GENERATION
# ============================================================================
def generate_weekly_brief():
    """
    Pulls last week's intelligence and generates Monday marketing brief.

    This should run every Monday morning.
    """

    print("\nGENERATING WEEKLY BRIEF...")

    # 1. Query Notion for last week's posts marked "Include in Brief"
    posts_data = _fetch_last_week_intelligence()

    if not posts_data:
        print("WARNING: No intelligence collected this week. Skipping brief generation.")
        return

    # 2. Send to Claude for synthesis
    brief_content = _synthesize_weekly_brief_with_claude(posts_data)

    # 3. Save to Notion
    _save_brief_to_notion(brief_content)

    print("OK: Weekly brief generated!")


def _fetch_last_week_intelligence():
    """Query Notion for last 7 days of intelligence"""

    # This would use Notion API to query the Intelligence Feed
    # For now, return placeholder
    # In production, implement Notion query API

    print("Fetching last week's intelligence from Notion...")

    # Placeholder - implement Notion query
    return []


def _synthesize_weekly_brief_with_claude(posts_data):
    """Send week's data to Claude for synthesis into marketing brief"""

    client = Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""You are creating the MONDAY MARKETING BRIEF for Burger Boy based on intelligence
gathered from 18 leading brand-strategy and marketing accounts on Instagram over the past week.

INTELLIGENCE COLLECTED:
{json.dumps(posts_data, indent=2)}

YOUR TASK:
Create a clear, actionable marketing brief. NO jargon. NO bullshit. Just insights Burger Boy can actually use.

Structure:
1. **HEADLINE NEWS** (The ONE key lesson)
   Most crucial insight from the week - summarised simply
2. **BRAND DIRECTION** (Strategic moves)
   How should Burger Boy evolve based on these insights?
3. **CONTENT HYPE** (What's working now)
   Formats, styles, topics getting traction
4. **BIG IDEAS** (Transformative concepts)
   Bold moves like "Why Burger Boy should start a social show"
5. **COMMUNITY** (Relationship building)
   Ways to deepen customer connections
6. **REAL-WORLD CONTEXT** (Cultural moments)
   Events, trends happening now BB can tap into
7. **OPPORTUNITIES** (Commercial & strategic)
   Menu innovation, marketing tactics, revenue ideas
8. **COMPETITIVE INTELLIGENCE** (Market context)
   What competitors are doing + gaps to exploit

Make it:
- **Simple** - no marketing jargon
- **Actionable** - things they can actually do
- **Specific** - concrete examples for Burger Boy
- **Grounded** - based on the House of AG insights
- **Inspiring** but **actionable**
- **Bold** - push them to think bigger

Return as JSON with these exact keys:
{{
  "headline_news": "...",
  "brand_direction": "...",
  "content_hype": "...",
  "big_ideas": "...",
  "community": "...",
  "real_world_context": "...",
  "opportunities": "...",
  "competitive_intelligence": "..."
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        brief = json.loads(content)
        return brief

    except Exception as e:
        print(f"ERROR: Brief generation failed: {e}")
        return None


def _save_brief_to_notion(brief_content):
    """Save generated brief to Notion Monday Briefs database"""

    if not brief_content:
        return

    url = "https://api.notion.com/v1/pages"

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Get Monday's date
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_label = f"Week of {monday.strftime('%B %d, %Y')}"

    payload = {
        "parent": {"database_id": MONDAY_BRIEFS_DB.replace("-", "")},
        "properties": {
            "Week Of": {
                "title": [{"text": {"content": week_label}}]
            },
            "Brief Date": {
                "date": {"start": monday.strftime("%Y-%m-%d")}
            },
            "Status": {
                "select": {"name": "Ready"}
            },
            "Executive Summary": {
                "rich_text": [{"text": {"content": brief_content.get("headline_news", "")[:2000]}}]
            },
            "Headline News": {
                "rich_text": [{"text": {"content": brief_content.get("headline_news", "")[:2000]}}]
            },
            "Brand Direction": {
                "rich_text": [{"text": {"content": brief_content.get("brand_direction", "")[:2000]}}]
            },
            "Content Hype": {
                "rich_text": [{"text": {"content": brief_content.get("content_hype", "")[:2000]}}]
            },
            "Big Ideas": {
                "rich_text": [{"text": {"content": brief_content.get("big_ideas", "")[:2000]}}]
            },
            "Community": {
                "rich_text": [{"text": {"content": brief_content.get("community", "")[:2000]}}]
            },
            "Real-World Context": {
                "rich_text": [{"text": {"content": brief_content.get("real_world_context", "")[:2000]}}]
            },
            "Opportunities": {
                "rich_text": [{"text": {"content": brief_content.get("opportunities", "")[:2000]}}]
            },
            "Competitive Intelligence": {
                "rich_text": [{"text": {"content": brief_content.get("competitive_intelligence", "")[:2000]}}]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"OK: Brief saved to Notion: {week_label}")
        else:
            print(f"ERROR: Failed to save brief: {response.status_code}")

    except Exception as e:
        print(f"ERROR: Notion error: {e}")


# ============================================================================
# DAILY MONITORING (all accounts)
# ============================================================================
def run_daily_monitoring(days_back=2):
    """
    Scrape + analyze recent posts for every account in INSTAGRAM_ACCOUNTS,
    then save the results to the Notion Intelligence Feed.
    """

    total_processed = 0

    for account in INSTAGRAM_ACCOUNTS:
        username = account["username"]
        name = account["name"]

        print(f"\nMONITORING @{username} ({name})...\n")

        # 1. Scrape Instagram
        posts = scrape_instagram_posts(username, days_back=days_back)

        if not posts:
            print(f"No new posts found for @{username}.")
            continue

        print(f"Found {len(posts)} new posts for @{username}\n")

        # 2. For each post: transcribe video (if any), analyze with Claude, save to Notion
        for i, post in enumerate(posts, 1):
            print(f"[{i}/{len(posts)}] Analyzing @{username} post from {post['date']}...")
            post["transcript"] = transcribe_video_post(post)
            analysis = analyze_post_with_claude(post, account=account)
            save_to_notion_intelligence_feed(post, analysis)
            total_processed += 1

    print(f"\nOK: Complete! Processed {total_processed} posts across {len(INSTAGRAM_ACCOUNTS)} accounts.")


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    """Main execution function"""

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--brief":
        # Generate weekly brief (run on Mondays)
        generate_weekly_brief()
    else:
        # Daily scrape and analyze across all monitored accounts (run daily)
        run_daily_monitoring(days_back=2)


if __name__ == "__main__":
    main()
