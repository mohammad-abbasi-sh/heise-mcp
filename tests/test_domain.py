"""Offline tests — parse the real captured heise.de RSS feed, section /
home / c't pages and two article pages (one free, one heise+ paywalled),
no network."""
import json
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from heise_mcp import domain as dom
from heise_mcp import server as srv

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _rss(name):
    return dom.parse_rss((FIX / name).read_text(encoding="utf-8"))


class TestHeadlinesFixture(unittest.TestCase):
    def test_headlines_shape(self):
        out = _rss("headlines.rdf")
        self.assertEqual(out["feed_title"], "heise online News")
        self.assertEqual(out["count"], 156)
        self.assertEqual(len(out["items"]), 156)

    def test_headlines_first_item(self):
        item = _rss("headlines.rdf")["items"][0]
        self.assertEqual(
            item["title"],
            "heise+ | Software-Nachbau mit KI: Wie Craft-Apps entstehen",
        )
        self.assertTrue(item["link"].startswith("https://www.heise.de/hintergrund/"))
        self.assertEqual(item["published"], "2026-11-16T09:30:00+00:00")
        self.assertTrue(item["description"].startswith("16 Programme in wenigen Wochen"))

    def test_headlines_all_items_complete(self):
        items = _rss("headlines.rdf")["items"]
        self.assertTrue(all(i["title"] and i["link"] and i["published"] for i in items))
        self.assertTrue(all(i["description"] for i in items))
        self.assertTrue(all(i["link"].startswith("https://www.heise.de/") for i in items))


class TestLinkListFixtures(unittest.TestCase):
    def test_section_security(self):
        items = dom.parse_link_list((FIX / "section-security.html").read_text(encoding="utf-8"))
        self.assertEqual(len(items), 27)
        self.assertEqual(
            items[0]["title"],
            "Microsoft-Cloud-Ausfall führte zu 15 Verletzten im Phantasialand",
        )
        self.assertTrue(items[0]["link"].startswith("https://www.heise.de/news/"))
        self.assertTrue(all(i["title"] for i in items))
        self.assertTrue(all(i["link"].startswith("https://www.heise.de/") for i in items))

    def test_top_stories(self):
        items = dom.parse_link_list((FIX / "top-stories.html").read_text(encoding="utf-8"))
        self.assertEqual(len(items), 73)
        self.assertEqual(
            items[0]["title"],
            "ConnectWise ScreenConnect: Angreifer installieren Malware "
            "über RMM+-Erweiterung",
        )
        self.assertEqual(items[0]["published"], "2026-11-16T10:15:00.000Z")
        self.assertTrue(all(i["title"] for i in items))

    def test_ct(self):
        items = dom.parse_link_list((FIX / "ct.html").read_text(encoding="utf-8"))
        self.assertEqual(len(items), 19)
        self.assertEqual(
            items[0]["title"],
            "Face Swap und Voice Cloning: So entlarvt ein Detektor "
            "Deepfake-Anrufer",
        )
        self.assertTrue(all(i["title"] for i in items))

    def test_link_list_dedupes(self):
        # The security page links each article twice (image anchor +
        # headline anchor); the list is de-duplicated by link.
        items = dom.parse_link_list((FIX / "section-security.html").read_text(encoding="utf-8"))
        links = [i["link"] for i in items]
        self.assertEqual(len(links), len(set(links)))

    def test_link_list_strips_tracking(self):
        items = dom.parse_link_list((FIX / "top-stories.html").read_text(encoding="utf-8"))
        self.assertTrue(all("wt_mc" not in i["link"] and "?" not in i["link"] for i in items))


class TestParseErrors(unittest.TestCase):
    def test_malformed_xml(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<rss><channel><item>oops")

    def test_non_rss_document(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("<html><head><title>404</title></head></html>")

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            dom.parse_rss("")


class TestValidation(unittest.TestCase):
    def test_limit_bounds(self):
        self.assertEqual(dom.validate_limit(1), 1)
        self.assertEqual(dom.validate_limit(50), 50)
        with self.assertRaises(ValueError):
            dom.validate_limit(0)
        with self.assertRaises(ValueError):
            dom.validate_limit(51)

    def test_normalise_section(self):
        self.assertEqual(dom.normalise_section("security")["section"], "security")
        self.assertEqual(dom.normalise_section("Security")["name"], "Security")
        self.assertEqual(dom.normalise_section("ki")["section"], "ki")
        self.assertEqual(dom.normalise_section("Künstliche Intelligenz")["section"], "ki")
        self.assertEqual(dom.normalise_section("KÜNSTLICHE INTELLIGENZ")["section"], "ki")
        self.assertEqual(dom.normalise_section("Digital Health")["section"], "digital-health")
        with self.assertRaises(ValueError):
            dom.normalise_section("netzwelt")
        with self.assertRaises(ValueError):
            dom.normalise_section("dax")
        with self.assertRaises(ValueError):
            dom.normalise_section("")

    def test_sections_all_have_urls(self):
        self.assertEqual(len(dom.SECTIONS), 7)
        for s in dom.SECTIONS:
            self.assertTrue(s["url"].startswith("https://www.heise.de/"))


class TestSearch(unittest.TestCase):
    def test_search_case_insensitive(self):
        items = _rss("headlines.rdf")["items"]
        self.assertEqual(len(dom.search_items(items, "Telegram")), 1)
        self.assertEqual(len(dom.search_items(items, "telegram")), 1)

    def test_search_counts(self):
        items = _rss("headlines.rdf")["items"]
        self.assertEqual(len(dom.search_items(items, "KI")), 45)
        self.assertEqual(len(dom.search_items(items, "Microsoft")), 12)

    def test_search_no_hits(self):
        items = _rss("headlines.rdf")["items"]
        self.assertEqual(dom.search_items(items, "zzzzqqq"), [])

    def test_search_empty_raises(self):
        with self.assertRaises(ValueError):
            dom.search_items([], "  ")


class TestArticleExtraction(unittest.TestCase):
    def test_free_article_fixture(self):
        html_text = (FIX / "article-free.html").read_text(encoding="utf-8")
        out = dom.extract_article(html_text)
        self.assertEqual(
            out["headline"],
            "Nach Terroranschlag: Jordanien lässt Telegram sperren",
        )
        self.assertEqual(out["section"], "Mobiles")
        self.assertEqual(out["published"], "2026-11-16T10:27:00+01:00")
        self.assertEqual(out["author"], "Martin Holland")
        self.assertEqual(out["body_chars"], 2198)
        self.assertEqual(out["body_words"], 296)
        self.assertFalse(out["paywalled"])
        self.assertEqual(out["note"], "")
        self.assertTrue(out["body"].startswith("Die Regierung in Jordanien"))
        self.assertTrue(out["description"].startswith("Eine jordanische Strafverfolgungsbehörde"))
        self.assertIn("## Appell an die Bevölkerung", out["body"])

    def test_paywalled_article_fixture(self):
        html_text = (FIX / "article-paywalled.html").read_text(encoding="utf-8")
        out = dom.extract_article(html_text)
        self.assertEqual(
            out["headline"],
            "Software-Nachbau mit KI: Wie Craft-Apps entstehen",
        )
        self.assertEqual(out["section"], "IT")
        self.assertEqual(out["published"], "2026-11-13T07:00:00+01:00")
        self.assertEqual(out["author"], "Ulrich Wolf")
        self.assertTrue(out["paywalled"])
        self.assertEqual(out["body_words"], 144)
        self.assertIn("heise+ paywall", out["note"])
        # The free sample (Leseprobe) is still returned — never empty.
        self.assertTrue(out["body"].startswith("Ende September veröffentlichte"))
        self.assertTrue(out["description"].startswith("16 Programme in wenigen Wochen"))

    def test_article_no_data(self):
        with self.assertRaises(ValueError):
            dom.extract_article("<html><body>no data here</body></html>")


class TestServerOffline(unittest.TestCase):
    """Tool functions with the HTTP layer mocked to the fixtures."""

    def test_headlines_tool(self):
        xml = (FIX / "headlines.rdf").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.heise_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["total_results"], 156)
        self.assertEqual(out["source"], "heise.de")
        self.assertIn("fetched_at", out)

    def test_section_tool(self):
        html_text = (FIX / "section-security.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_page", return_value=html_text):
            out = json.loads(srv.heise_news_by_section("security", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["section"], "security")
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["total_results"], 27)

    def test_section_tool_unknown(self):
        out = json.loads(srv.heise_news_by_section("netzwelt", limit=2))
        self.assertIn("error", out)
        self.assertIn("unknown section", out["error"])

    def test_search_tool(self):
        xml = (FIX / "headlines.rdf").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_feed", return_value=xml):
            out = json.loads(srv.heise_search_news("Telegram", limit=10))
        self.assertNotIn("error", out)
        self.assertEqual(out["query"], "Telegram")
        self.assertEqual(out["total_results"], 1)
        self.assertEqual(out["count"], 1)

    def test_search_tool_empty_query(self):
        out = json.loads(srv.heise_search_news("   "))
        self.assertIn("error", out)

    def test_top_stories_tool(self):
        html_text = (FIX / "top-stories.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_page", return_value=html_text):
            out = json.loads(srv.heise_top_stories(limit=5))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 5)
        self.assertEqual(out["total_results"], 73)

    def test_ct_tool(self):
        html_text = (FIX / "ct.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_page", return_value=html_text):
            out = json.loads(srv.heise_ct(limit=5))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 5)
        self.assertEqual(out["total_results"], 19)

    def test_get_article_tool_free(self):
        html_text = (FIX / "article-free.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(
                srv.heise_get_article(
                    "https://www.heise.de/news/Nach-Terroranschlag-Jordanien-laesst-Telegram-sperren-11525885.html"
                )
            )
        self.assertNotIn("error", out)
        self.assertEqual(out["body_chars"], 2198)
        self.assertFalse(out["paywalled"])
        self.assertIn("Telegram", out["headline"])

    def test_get_article_tool_paywalled(self):
        html_text = (FIX / "article-paywalled.html").read_text(encoding="utf-8")
        with mock.patch.object(srv._http, "fetch_article", return_value=html_text):
            out = json.loads(
                srv.heise_get_article(
                    "https://www.heise.de/hintergrund/Software-Nachbau-mit-KI-Wie-Craft-Apps-entstehen-11518918.html"
                )
            )
        self.assertNotIn("error", out)
        self.assertTrue(out["paywalled"])
        self.assertIn("heise+ paywall", out["note"])

    def test_get_article_tool_rejects_other_hosts(self):
        out = json.loads(srv.heise_get_article("https://example.com/news.html"))
        self.assertIn("error", out)

    def test_health_tool(self):
        with mock.patch.object(srv._http, "health_check", return_value={"status": "ok", "http_status": 200, "url": dom.HEADLINES_FEED}):
            out = json.loads(srv.heise_health())
        self.assertEqual(out["status"], "ok")


if __name__ == "__main__":
    unittest.main()
