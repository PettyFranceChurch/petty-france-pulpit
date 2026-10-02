import json
import time
import urllib.request
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
RSS_FEED_URL = "https://anchor.fm/s/11798ff54/podcast/rss"
OUTPUT_FILE = "sermons.json"

NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'content': 'http://purl.org/rss/1.0/modules/content/'
}

# Standard Bible Books for Filter Extraction
BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation"
]

def fetch_rss_feed(url):
    # Cache buster ensures automated runs never get stuck on stale CDN cache
    cache_buster_url = f"{url}?cb={int(time.time())}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    req = urllib.request.Request(cache_buster_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read()

def clean_html_text(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return html.unescape(clean_text).strip()

def parse_item(item, index):
    title = (item.findtext("title") or "").strip()
    pub_date_str = (item.findtext("pubDate") or "").strip()
    link = (item.findtext("link") or "").strip()

    enclosure = item.find("enclosure")
    audio_url = enclosure.attrib.get("url", "").strip() if enclosure is not None else ""

    raw_desc = (item.findtext("description") or "").strip()
    content_encoded = (item.findtext(f"{{{NAMESPACES['content']}}}encoded") or "").strip()
    itunes_summary = (item.findtext(f"{{{NAMESPACES['itunes']}}}summary") or "").strip()

    # Full description string for rendering details in the accordion
    description_html = content_encoded if content_encoded else (raw_desc if raw_desc else itunes_summary)
    clean_desc = clean_html_text(description_html)

    itunes_author = (item.findtext(f"{{{NAMESPACES['itunes']}}}author") or "").strip()

    # Parse date
    formatted_date = pub_date_str
    year_str = "2026"
    timestamp = 0
    if pub_date_str:
        try:
            dt = parsedate_to_datetime(pub_date_str)
            timestamp = int(dt.timestamp())
            formatted_date = dt.strftime("%B %d, %Y")
            year_str = dt.strftime("%Y")
        except Exception:
            pass

    # Extract metadata fields from description string
    scripture = "Scripture Text"
    series = "General Archive"
    author = itunes_author or "Christopher Deaton"

    if clean_desc:
        parts = [p.strip() for p in clean_desc.split("|")]
        for part in parts:
            if "Scripture:" in part:
                scripture = part.replace("Scripture:", "").strip()
            elif "Series:" in part:
                series = part.replace("Series:", "").strip()
            elif "Speaker:" in part:
                author = part.replace("Speaker:", "").strip()

    # Determine Biblical Book filter category
    book = "General"
    for b in BIBLE_BOOKS:
        if re.search(r'\b' + re.escape(b) + r'\b', scripture, re.IGNORECASE):
            book = b
            break

    # ESV Scripture API / BibleGateway link generator
    esv_url = f"https://www.biblegateway.com/passage/?search={urllib.parse.quote(scripture)}&version=ESV" if scripture != "Scripture Text" else "#"

    # Generate persistent unique ID for share links
    sermon_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or f"sermon-{index}"

    return {
        "id": sermon_id,
        "title": title,
        "date": formatted_date,
        "pubDate": pub_date_str,
        "timestamp": timestamp,
        "author": author,
        "series": series,
        "passage": scripture,
        "book": book,
        "year": year_str,
        "esvUrl": esv_url,
        "description": description_html,
        "cleanDesc": clean_desc,
        "url": audio_url,
        "audioUrl": audio_url,
        "audio_url": audio_url,
        "link": link
    }

def main():
    print(f"Fetching feed from {RSS_FEED_URL}...")
    xml_data = fetch_rss_feed(RSS_FEED_URL)
    root = ET.fromstring(xml_data)
    channel = root.find("channel")

    if channel is None:
        print("Error: Could not parse channel.")
        return

    sermons = []
    items = channel.findall("item")
    for idx, item in enumerate(items):
        sermon = parse_item(item, idx)
        if sermon["title"] and sermon["url"]:
            sermons.append(sermon)

    # Sort newest first
    sermons.sort(key=lambda x: x["timestamp"], reverse=True)

    if not sermons:
        print("Warning: Parsed 0 sermons. Skipping overwrite.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {OUTPUT_FILE} with {len(sermons)} sermons matching website player specs.")

if __name__ == "__main__":
    main()
