"""Domain logic: shape heise.de RSS feeds, section/home/c't pages and
article pages into compact dicts (stdlib only).

Data source: the official heise.de RSS feed
(https://www.heise.de/rss/heise.rdf) and the server-rendered section,
home and c't pages. No key, no login.

Article text comes from the ``div.article-content`` paragraphs of each
article page plus its NewsArticle JSON-LD (headline, publish date,
author, description). heise.de has no usable site search (the search
page renders no results server-side), so search filters the fetched
main feed client-side.

Paywall honesty: a large share of heise articles are heise+ — the
server-rendered page carries only the free sample ("Leseprobe", 3
intro paragraphs) and a "Das war die Leseprobe unseres
heise-Plus-Artikels" marker. extract_article therefore returns
``paywalled: true`` plus the free sample for those pages instead of
pretending the full text was read. Free articles return the full body
(verified live 2026-11-16: news article 291 words).
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

BASE = "https://www.heise.de"

# Ressort pages: /security and /developer are standalone paths; the
# rest live under /thema/<Name>. All 7 verified live 2026-11-16
# (14-32 article links each). German names accepted as aliases in
# normalise_section. NOTE: /thema/netzwelt is 404; the /tests/,
# /ratgeber/, /meinung/ and /hintergrund/ landing pages are 404 too.
SECTIONS = [
    {"section": "security", "name": "Security", "url": f"{BASE}/security"},
    {"section": "developer", "name": "Developer", "url": f"{BASE}/developer"},
    {"section": "ki", "name": "Künstliche Intelligenz",
     "url": f"{BASE}/thema/Kuenstliche-Intelligenz"},
    {"section": "it", "name": "IT", "url": f"{BASE}/thema/IT"},
    {"section": "wissenschaft", "name": "Wissenschaft",
     "url": f"{BASE}/thema/Wissenschaft"},
    {"section": "entertainment", "name": "Entertainment",
     "url": f"{BASE}/thema/Entertainment"},
    {"section": "digital-health", "name": "Digital Health",
     "url": f"{BASE}/thema/Digital-Health"},
]

HEADLINES_FEED = f"{BASE}/rss/heise.rdf"
HOME_URL = f"{BASE}/"
CT_URL = f"{BASE}/ct/"

_SECTION_BY_KEY = {}
for _s in SECTIONS:
    _SECTION_BY_KEY[_s["section"]] = _s
    _SECTION_BY_KEY[_s["name"].lower()] = _s
_SECTION_BY_KEY["kuenstliche intelligenz"] = _SECTION_BY_KEY["ki"]
_SECTION_BY_KEY["künstliche intelligenz"] = _SECTION_BY_KEY["ki"]

_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (feed carries 156 items)."""
    if not 1 <= limit <= 50:
        raise ValueError(f"limit out of range: {limit} (expected 1..50)")
    return limit


def normalise_section(section: str) -> dict:
    """Canonical section entry; accepts slug ("security") or German name."""
    key = (section or "").strip().lower()
    if not key:
        raise ValueError("section must not be empty")
    entry = _SECTION_BY_KEY.get(key)
    if entry is None:
        raise ValueError(
            f"unknown section: {section!r} "
            f"(expected one of {', '.join(s['section'] for s in SECTIONS)})"
        )
    return entry


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    try:
        dt = parsedate_to_datetime(date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def compact_item(item: ET.Element) -> dict:
    """One RSS <item>, compact: title, link, description, publish time.

    The description is the CDATA teaser; content:encoded (same teaser
    with an image) is the fallback. heise+ items carry a "heise+ | "
    title prefix, kept as-is.
    """
    description = _text(item, "description")
    if not description:
        encoded = item.find(f"{_CONTENT_NS}encoded")
        if encoded is not None and encoded.text:
            description = _strip_tags(encoded.text)
    return {
        "title": _text(item, "title"),
        "link": _text(item, "link"),
        "description": description,
        "published": _iso(_text(item, "pubDate")),
        "category": _text(item, "category"),
    }


def parse_rss(xml_text: str) -> dict:
    """Parse the heise.de RSS feed into {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document (e.g. a
    404 error page saved as text).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = [compact_item(it) for it in channel.findall("item")]
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description.

    The site search page renders no results server-side, so search
    filters the fetched main feed client-side.
    """
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


_ARTICLE_LINK_RE = re.compile(r"^/(news|hintergrund)/[^\"?]+\.html")


def _clean_link(href: str) -> str:
    """Absolute article URL without tracking query/fragment."""
    abs_url = urljoin(BASE, href)
    parts = urlsplit(abs_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class _LinkListParser(HTMLParser):
    """Article links of a heise.de list page (section, home, c't).

    Headlines come from the ``data-upscore-title`` span inside each
    teaser anchor (100% coverage on all three page types, verified
    2026-11-16); image-only anchors for the same URL carry no title
    and are merged by link. Publish time comes from the <time
    dateTime> inside the anchor when present.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors: list[dict] = []
        self._cur: dict | None = None
        self._depth = 0
        self._in_upscore = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and self._cur is None:
            href = d.get("href", "")
            if _ARTICLE_LINK_RE.match(href):
                self._cur = {
                    "href": href, "title": [], "time": None,
                }
                self._depth = 1
                return
        if self._cur is not None:
            self._depth += 1
            if tag == "span" and d.get("data-upscore-title") == "true":
                self._in_upscore += 1
            if tag == "time" and d.get("datetime"):
                self._cur["time"] = d["datetime"]

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag == "span" and self._in_upscore > 0:
            self._in_upscore -= 1
        self._depth -= 1
        if self._depth == 0 and tag == "a":
            title = re.sub(r"\s+", " ", "".join(self._cur["title"])).strip()
            self.anchors.append({
                "link": _clean_link(self._cur["href"]),
                "title": title,
                "published": self._cur["time"] or "",
            })
            self._cur = None
            self._in_upscore = 0

    def handle_data(self, data):
        if self._cur is not None and self._in_upscore > 0:
            self._cur["title"].append(data)


def parse_link_list(page_html: str) -> list[dict]:
    """Article links of a heise.de list page, in page order, de-duplicated.

    For a URL seen twice (image-only anchor + headline anchor) the
    entry with a title wins.
    """
    parser = _LinkListParser()
    parser.feed(page_html)
    by_link: dict[str, dict] = {}
    order: list[str] = []
    for anchor in parser.anchors:
        link = anchor["link"]
        if link not in by_link:
            by_link[link] = anchor
            order.append(link)
        elif not by_link[link]["title"] and anchor["title"]:
            by_link[link] = anchor
        elif by_link[link]["title"] and not anchor["title"]:
            pass
        elif not by_link[link]["published"] and anchor["published"]:
            by_link[link]["published"] = anchor["published"]
    return [by_link[link] for link in order]


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)

# The screen-reader line that ends every heise+ free sample — the one
# reliable paywall marker (the layout curtain class also appears on
# free pages, e.g. for gift-curtains).
_PAYWALL_MARKER = "Das war die Leseprobe unseres heise-Plus-Artikels"

# Paragraphs inside div.article-content that are UI/boilerplate, not
# article text: newsletter promos, the topic-follow prompt, the
# author mark "(mho)".
_AUTHOR_MARK_RE = re.compile(r"^\([a-z]{2,4}\)$")
_BOILERPLATE = (
    "keine news verpassen",
    "immer informiert bleiben",
    "ausführliche informationen zum versandverfahren",
)


def _is_boilerplate(text: str) -> bool:
    low = text.casefold()
    if _AUTHOR_MARK_RE.match(low):
        return True
    return any(marker in low for marker in _BOILERPLATE)


class _ArticleParser(HTMLParser):
    """Paragraphs + subheadings of div.article-content, in order.

    Stops at the "Lesen Sie auch" related-articles heading (everything
    after it is footer/promo) and skips paragraphs inside ad containers.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._stack: list[tuple[str, str]] = []
        self._in_content = False
        self._content_depth: int | None = None
        self._in_ad = 0
        self._cur: tuple[str, list[str]] | None = None
        self._stopped = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        cls = d.get("class", "")
        self._stack.append((tag, cls))
        if (
            tag == "div"
            and "article-content" in cls.split()
            and not self._in_content
        ):
            self._in_content = True
            self._content_depth = len(self._stack)
        if self._in_content and not self._stopped:
            if tag == "div" and "ad" in cls:
                self._in_ad += 1
            if tag in ("p", "h3") and self._in_ad == 0:
                self._cur = (tag, [])

    def handle_endtag(self, tag):
        if self._in_content and tag in ("p", "h3") and self._cur is not None:
            if self._cur[0] == tag:
                text = re.sub(r"\s+", " ", "".join(self._cur[1])).strip()
                if text:
                    if tag == "h3" and text == "Lesen Sie auch":
                        self._stopped = True
                    elif not self._stopped:
                        self.blocks.append((tag, text))
                self._cur = None
        if self._stack:
            popped_tag, popped_cls = self._stack.pop()
            if self._in_content and popped_tag == "div" and "ad" in popped_cls:
                self._in_ad = max(0, self._in_ad - 1)
            if (
                self._in_content
                and popped_tag == "div"
                and len(self._stack) + 1 == self._content_depth
                and "article-content" in popped_cls.split()
            ):
                self._in_content = False

    def handle_data(self, data):
        if self._cur is not None:
            self._cur[1].append(data)


def _news_article_node(page_html: str) -> dict:
    """The NewsArticle node of the page's JSON-LD.

    Scans every ld+json block: news items use "NewsArticle", long-form
    Hintergrund pieces use "BackgroundNewsArticle".
    """
    for match in _LD_JSON_RE.finditer(page_html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and str(
                node.get("@type", "")
            ).endswith("NewsArticle"):
                return node
    return {}


def extract_article(page_html: str) -> dict:
    """Headline, description, author, publish date and body text of one
    heise.de article page.

    Headline/author/date/description come from the NewsArticle JSON-LD;
    body from the ``div.article-content`` paragraphs with newsletter /
    topic-follow boilerplate removed, stopping at "Lesen Sie auch".

    heise+ (paywalled) articles carry only the free sample ("Leseprobe",
    3 intro paragraphs) in the SSR page: ``paywalled`` is true and
    ``body`` holds that sample plus a note — never fabricated text.
    Free articles return the full body. Raises ValueError when the page
    has neither JSON-LD nor an article-content block (not an article
    page).
    """
    node = _news_article_node(page_html)
    title_m = _TITLE_RE.search(page_html)
    title = html.unescape(title_m.group(1)).strip() if title_m else ""
    title = re.sub(r"\s+", " ", title)
    if title.endswith(" | heise online"):
        title = title[: -len(" | heise online")]
    headline = (node.get("headline") or "").strip() or title

    description = (node.get("description") or "").strip()

    author = node.get("author")
    names: list[str] = []
    if isinstance(author, list):
        names = [a.get("name", "") for a in author
                 if isinstance(a, dict) and a.get("name")]
    elif isinstance(author, dict):
        names = [author.get("name", "")] if author.get("name") else []
    elif isinstance(author, str):
        names = [author]

    parser = _ArticleParser()
    parser.feed(page_html)
    has_content = bool(parser.blocks) or "article-content" in page_html
    if not node and not has_content:
        raise ValueError(
            "no JSON-LD data and no article-content block on this page "
            "(not a heise.de article page?)"
        )
    body_parts: list[str] = []
    for kind, text in parser.blocks:
        if kind == "h3":
            body_parts.append(f"## {text}")
        elif not _is_boilerplate(text):
            body_parts.append(text)
    body = "\n\n".join(body_parts)
    words = len(body.split())
    paywalled = _PAYWALL_MARKER in page_html
    return {
        "headline": headline,
        "description": description,
        "section": (node.get("articleSection") or "").strip(),
        "published": node.get("datePublished") or "",
        "modified": node.get("dateModified") or "",
        "author": ", ".join(names),
        "body": body,
        "body_chars": len(body),
        "body_words": words,
        "paywalled": paywalled,
        "note": (
            "Only the free sample (Leseprobe) is shown; the full text is "
            "behind the heise+ paywall."
            if paywalled
            else ""
        ),
    }
