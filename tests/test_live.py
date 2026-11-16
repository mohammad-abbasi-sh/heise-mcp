"""Live tests — hit the real heise.de RSS feed, pages and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set HEISE_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from heise_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("HEISE_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="HEISE_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.heise_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_section_live(self):
        out = json.loads(srv.heise_news_by_section("security", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE security: {out['items'][0]['title']}")

    def test_all_sections_live(self):
        # Every section page must answer with at least one item.
        from heise_mcp import domain as dom
        for s in dom.SECTIONS:
            out = json.loads(srv.heise_news_by_section(s["section"], limit=1))
            self.assertNotIn("error", out, f"section {s['section']}")
            self.assertGreaterEqual(out["count"], 1, f"section {s['section']}")
        print(f"\nLIVE all {len(dom.SECTIONS)} sections OK")

    def test_search_live(self):
        out = json.loads(srv.heise_search_news("Microsoft", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(
            "microsoft" in (i["title"] + i["description"]).casefold()
            for i in out["items"]
        ))
        print(f"\nLIVE search 'Microsoft': {out['total_results']} hits")

    def test_top_stories_live(self):
        out = json.loads(srv.heise_top_stories(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE top stories: {out['items'][0]['title']}")

    def test_ct_live(self):
        out = json.loads(srv.heise_ct(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["link"] for i in out["items"]))
        print(f"\nLIVE c't: {out['items'][0]['title']}")

    def test_get_article_live(self):
        head = json.loads(srv.heise_headlines(limit=5))
        url = head["items"][0]["link"]
        out = json.loads(srv.heise_get_article(url))
        self.assertNotIn("error", out)
        self.assertTrue(out["headline"])
        # Free article: full body; paywalled: sample + flag, never fake text.
        if out["paywalled"]:
            self.assertTrue(out["description"])
            print(f"\nLIVE article (paywalled): {out['headline']}")
        else:
            self.assertGreater(out["body_chars"], 200)
            print(f"\nLIVE article: {out['headline']} ({out['body_chars']} chars)")

    def test_get_free_article_live(self):
        # A security-section article is free more often than not; accept
        # either outcome, but the result must be honest about it.
        out = json.loads(srv.heise_news_by_section("security", limit=5))
        self.assertNotIn("error", out)
        art = json.loads(srv.heise_get_article(out["items"][0]["link"]))
        self.assertNotIn("error", art)
        self.assertTrue(art["headline"])
        if not art["paywalled"]:
            self.assertGreater(art["body_chars"], 200)
        print(f"\nLIVE security article: paywalled={art['paywalled']}, "
              f"{art['body_chars']} chars")

    def test_health_live(self):
        out = json.loads(srv.heise_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
