import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
RSS_FEED_URL = "https://anchor.fm/s/11798ff54/podcast/rss"
OUTPUT_FILE = "sermons.json"

# XML Namespaces
NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

def fetch_rss_feed(url):
    # Cache-buster URL parameter forces fresh fetch on automated server runs
    cache_buster_url = f"{url}?cb={int(time.time())}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    req = urllib.request.Request(cache_buster_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read()

def parse_sermon_item(item):
    # Basic text extraction
    title = (item.findtext("title") or "").strip()
    pub_date_str = (item.findtext("pubDate") or "").strip()
    link = (item.findtext("link") or "").strip()
    
    # Extract audio enclosure URL
    enclosure = item.find("enclosure")
    audio_url = enclosure.attrib.get("url", "").strip() if enclosure is not None else ""

    # Capture Full Descriptions across standard RSS and extended tags
    raw_desc = (item.findtext("description") or "").strip()
    content_encoded = (item.findtext(f"{{{NAMESPACES['content']}}}encoded") or "").strip()
    itunes_summary = (item.findtext(f"{{{NAMESPACES['itunes']}}}summary") or "").strip()
    
    # Priority for full description
    full_description = content_encoded if content_encoded else (raw_desc if raw_desc else itunes_summary)

    # iTunes Specific Metadata
    speaker = (item.findtext(f"{{{NAMESPACES['itunes']}}}author") or "").strip()
    duration = (item.findtext(f"{{{NAMESPACES['itunes']}}}duration") or "").strip()
    image_tag = item.find(f"{{{NAMESPACES['itunes']}}}image")
    image_url = image_tag.attrib.get("href", "") if image_tag is not None else ""

    # Parse date for accurate chronological sorting
    timestamp = 0
    formatted_date = pub_date_str
    if pub_date_str:
        try:
            dt = parsedate_to_datetime(pub_date_str)
            timestamp = int(dt.timestamp())
            formatted_date = dt.strftime("%B %d, %Y")
        except Exception:
            pass

    # Extract metadata embedded inside description text if present
    scripture = ""
    series = ""
    if full_description:
        parts = [p.strip() for p in full_description.split("|")]
        for part in parts:
            if "Scripture:" in part:
                scripture = part.replace("Scripture:", "").strip()
            elif "Series:" in part:
                series = part.replace("Series:", "").strip()
            elif "Speaker:" in part and not speaker:
                speaker = part.replace("Speaker:", "").strip()

    # Dictionary containing standard and fallback keys for maximum compatibility
    return {
        "title": title,
        "pubDate": pub_date_str,
        "date": formatted_date,
        "timestamp": timestamp,
        "description": full_description,
        "content": content_encoded,
        "summary": itunes_summary or raw_desc,
        "link": link,
        "audioUrl": audio_url,
        "audio_url": audio_url,
        "enclosure": audio_url,
        "speaker": speaker or "Christopher Deaton",
        "scripture": scripture,
        "series": series,
        "duration": duration,
        "image": image_url
    }

def main():
    print(f"Fetching RSS feed from: {RSS_FEED_URL}")
    xml_data = fetch_rss_feed(RSS_FEED_URL)

    root = ET.fromstring(xml_data)
    channel = root.find("channel")

    if channel is None:
        print("Error: Invalid RSS feed structure.")
        return

    sermons = []
    for item in channel.findall("item"):
        sermon = parse_sermon_item(item)
        if sermon["title"]:
            sermons.append(sermon)

    # Sort strictly by timestamp (Newest sermon first)
    sermons.sort(key=lambda x: x["timestamp"], reverse=True)

    # Safeguard against overwriting with empty data
    if not sermons:
        print("Warning: 0 sermons parsed. Skipping write to protect live data.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {OUTPUT_FILE} with {len(sermons)} sermons.")

if __name__ == "__main__":
    main()
