"""
tests/test_intel_feeds_extended.py

Unit tests for the new IntelFeeds sources added this session: security blog
RSS/Atom parsing, Reddit, OTX pulses, URLhaus, ThreatFox. All HTTP is mocked
via the class's own _get_json/_get_text/_post_json seams — no live network
calls, and no API keys needed to run these tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.intel_feeds import IntelFeeds

_SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Example Security Blog</title>
<item>
  <title>New ransomware group targets healthcare</title>
  <link>https://example.com/post1</link>
  <guid>https://example.com/post1</guid>
  <pubDate>Thu, 30 Jul 2026 12:00:00 GMT</pubDate>
  <description>&lt;p&gt;A new group has emerged, using a novel encryption scheme.&lt;/p&gt;</description>
</item>
</channel></rss>"""

_SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Example Atom Blog</title>
<entry>
  <title>Zero-day found in widely used library</title>
  <id>tag:example.com,2026:post2</id>
  <link href="https://example.com/post2" rel="alternate"/>
  <published>2026-07-30T10:00:00Z</published>
  <summary>Details of the zero-day and a proof of concept.</summary>
</entry>
</feed>"""

_SAMPLE_REDDIT = {
    "data": {
        "children": [
            {"data": {
                "id": "abc123", "title": "New CVE dropped for OpenSSH",
                "selftext": "Discussion thread about the new CVE.",
                "created_utc": 1785000000, "score": 250,
                "permalink": "/r/netsec/comments/abc123/new_cve/",
                "stickied": False,
            }},
            {"data": {
                "id": "sticky1", "title": "Rules of this subreddit",
                "selftext": "", "created_utc": 1700000000, "score": 10,
                "permalink": "/r/netsec/comments/sticky1/rules/",
                "stickied": True,
            }},
        ]
    }
}

_SAMPLE_OTX = {
    "results": [
        {"id": "pulse1", "name": "APT campaign targeting fintech",
         "description": "Cluster of indicators tied to a fintech-targeting campaign.",
         "created": "2026-07-29T00:00:00", "tags": ["apt", "fintech"]},
    ]
}

_SAMPLE_URLHAUS = {
    "query_status": "ok",
    "urls": [
        {"id": "1001", "url": "http://bad.example/payload.exe", "host": "bad.example",
         "url_status": "online", "date_added": "2026-07-30 09:00:00 UTC",
         "threat": "malware_download", "tags": ["exe", "trojan"],
         "urlhaus_reference": "https://urlhaus.abuse.ch/url/1001/"},
    ]
}

_SAMPLE_THREATFOX = {
    "query_status": "ok",
    "data": [
        {"id": "2001", "ioc": "1.2.3.4:8080", "ioc_type": "ip:port",
         "malware_printable": "AsyncRAT", "confidence_level": 90,
         "first_seen": "2026-07-30 08:00:00 UTC", "threat_type": "botnet_cc",
         "reference": "https://threatfox.abuse.ch/ioc/2001/"},
    ]
}


@pytest.mark.asyncio
async def test_fetch_security_blogs_parses_rss_and_atom() -> None:
    feeds = IntelFeeds()

    async def fake_get_text(url):
        # Only Project Zero's URL (blogspot.com) is the Atom sample; every
        # other configured blog URL contains "feed"/"rss" so a substring
        # check can't distinguish them — match the one known Atom source.
        return _SAMPLE_ATOM if "blogspot" in url.lower() else _SAMPLE_RSS

    with patch.object(feeds, "_get_text", side_effect=fake_get_text):
        items = await feeds.fetch_security_blogs()

    assert len(items) > 0
    titles = [i.title for i in items]
    assert any("ransomware" in t.lower() for t in titles)
    assert any("zero-day" in t.lower() for t in titles)
    for item in items:
        assert item.source
        assert "security-news" in item.tags


@pytest.mark.asyncio
async def test_fetch_reddit_skips_stickied_posts() -> None:
    feeds = IntelFeeds()
    with patch.object(feeds, "_get_json", new=AsyncMock(return_value=_SAMPLE_REDDIT)):
        items = await feeds.fetch_reddit("netsec")

    assert len(items) == 1
    assert items[0].item_id == "abc123"
    assert items[0].source == "r/netsec"
    assert "openssh" in items[0].title.lower()


@pytest.mark.asyncio
async def test_fetch_otx_pulses_noop_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OTX_API_KEY", raising=False)
    feeds = IntelFeeds()
    with patch.object(feeds, "_get_json", new=AsyncMock(return_value=_SAMPLE_OTX)) as mock_get:
        items = await feeds.fetch_otx_pulses()

    assert items == []
    mock_get.assert_not_called()  # must not hit the network without a key


@pytest.mark.asyncio
async def test_fetch_otx_pulses_with_key(monkeypatch) -> None:
    monkeypatch.setenv("OTX_API_KEY", "test-key")
    feeds = IntelFeeds()
    with patch.object(feeds, "_get_json", new=AsyncMock(return_value=_SAMPLE_OTX)):
        items = await feeds.fetch_otx_pulses()

    assert len(items) == 1
    assert items[0].source == "OTX"
    assert items[0].severity == "HIGH"
    assert "apt" in items[0].tags


@pytest.mark.asyncio
async def test_fetch_urlhaus_noop_without_key(monkeypatch) -> None:
    monkeypatch.delenv("ABUSECH_AUTH_KEY", raising=False)
    feeds = IntelFeeds()
    with patch.object(feeds, "_get_json", new=AsyncMock(return_value=_SAMPLE_URLHAUS)) as mock_get:
        items = await feeds.fetch_urlhaus()

    assert items == []
    mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_urlhaus_with_key(monkeypatch) -> None:
    monkeypatch.setenv("ABUSECH_AUTH_KEY", "test-key")
    feeds = IntelFeeds()
    with patch.object(feeds, "_get_json", new=AsyncMock(return_value=_SAMPLE_URLHAUS)):
        items = await feeds.fetch_urlhaus()

    assert len(items) == 1
    assert items[0].source == "URLhaus"
    assert "bad.example" in items[0].title


@pytest.mark.asyncio
async def test_fetch_threatfox_with_key(monkeypatch) -> None:
    monkeypatch.setenv("ABUSECH_AUTH_KEY", "test-key")
    feeds = IntelFeeds()
    with patch.object(feeds, "_post_json", new=AsyncMock(return_value=_SAMPLE_THREATFOX)):
        items = await feeds.fetch_threatfox()

    assert len(items) == 1
    assert items[0].source == "ThreatFox"
    assert items[0].severity == "HIGH"  # confidence_level 90 >= 75


@pytest.mark.asyncio
async def test_fetch_all_includes_new_no_auth_sources(monkeypatch) -> None:
    """fetch_all() should call the new no-auth sources without needing any keys."""
    monkeypatch.delenv("OTX_API_KEY", raising=False)
    feeds = IntelFeeds()
    with patch.object(feeds, "fetch_kev", new=AsyncMock(return_value=[])), \
         patch.object(feeds, "fetch_arxiv", new=AsyncMock(return_value=[])), \
         patch.object(feeds, "fetch_security_blogs", new=AsyncMock(return_value=[])) as mock_blogs, \
         patch.object(feeds, "fetch_reddit", new=AsyncMock(return_value=[])) as mock_reddit:
        await feeds.fetch_all()

    mock_blogs.assert_awaited()
    assert mock_reddit.await_count == 2  # netsec + cybersecurity
