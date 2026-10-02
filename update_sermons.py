import json
import time
import urllib.request
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Your official Anchor/Spotify RSS Feed URL
RSS_FEED_URL = "https://anchor.fm/s/11798ff54/podcast/rss"
OUTPUT_FILE = "sermons.json"

# ---------------------------------------------------------------------------
# FETCH FEED WITH CACHE-BUSTING HEADERS
# ---------------------------------------------------------------------------
def fetch_rss_feed(url):
    # Append a unique timestamp query parameter to bypass CDN/edge caches
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

# ---------------------------------------------------------------------------
# PARSE RSS & CONVERT TO JSON
# ---------------------------------------------------------------------------
def main():
    print(f"Fetching RSS feed from: {RSS_FEED_URL}")
    xml_data = fetch_rss_feed(RSS_FEED_URL)

    root = ET.fromstring(xml_data)
    channel = root.find("channel")

    # XML Namespaces commonly found in podcast feeds
    itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

    sermons = []

    for item in channel.findall("item"):
        title = item.findtext("title", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        description = item.findtext("description", default="").strip()
        link = item.findtext("link", default="").strip()

        # Extract audio enclosure URL
        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url", "") if enclosure is not None else ""

        # Extract iTunes specific metadata if present
        speaker = item.findtext(f"{itunes_ns}author", default="").strip()
        duration = item.findtext(f"{itunes_ns}duration", default="").strip()

        sermons.append({
            "title": title,
            "pubDate": pub_date,
            "description": description,
            "link": link,
            "audioUrl": audio_url,
            "speaker": speaker,
            "duration": duration
        })

    # Safeguard: Do not overwrite if 0 sermons were returned
    if not sermons:
        print("Warning: Parsed 0 sermons. Skipping file overwrite to protect existing data.")
        return

    # Write out formatted JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated {OUTPUT_FILE} with {len(sermons)} sermons.")

if __name__ == "__main__":
    main()
