"""MCP server: unofficial read-only access to heise.de — Germany's
#1 IT news portal — via its official RSS feed and server-rendered
pages. No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for heise.de — Germany's #1 IT news
portal (c't, iX, heise security) — via its official RSS feed and
server-rendered pages (no key, no login). Top headlines, news by
section (Security, Developer, KI, IT, Wissenschaft, Entertainment,
Digital Health), keyword search across the main feed, front-page top
stories, c't magazine articles and article text. NOTE: many heise
articles are heise+ (paywalled) — their pages carry only the free
sample (Leseprobe), so heise_get_article reports paywalled: true and
returns only that sample for those; free articles return the full
body. Search filters the fetched main feed client-side (the site
search page renders no results server-side).
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "heise.de"
_DISCLAIMER = "Unofficial read-only data from heise.de; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("heise-mcp", instructions=INSTRUCTIONS)


def _feed(url: str, limit: int) -> dict:
    """Fetch one RSS feed and return its items, newest first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(url))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


def _list_page(url: str, limit: int) -> dict:
    """Fetch one heise.de list page and return its articles, capped."""
    items = _dom.parse_link_list(_http.fetch_page(url))
    return {
        "total_results": len(items),
        "count": min(limit, len(items)),
        "items": items[:limit],
    }


@mcp.tool()
def heise_headlines(limit: int = 10) -> str:
    """Top headlines from heise.de (main RSS feed), newest first.
limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(_dom.HEADLINES_FEED, lim)
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def heise_search_news(query: str, limit: int = 10) -> str:
    """Search heise.de news by keyword (title + description).
query: free text, e.g. "KI" or "Microsoft". limit: 1..50
(default 10). Searches the main feed (156 items) client-side
(the site search page renders no results server-side), newest
first, de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.search_items(parsed["items"], query.strip())
        seen: set[str] = set()
        unique: list[dict] = []
        for item in found:
            if item["link"] in seen:
                continue
            seen.add(item["link"])
            unique.append(item)
        unique.sort(key=lambda it: it.get("published") or "", reverse=True)
        out = {
            "query": query.strip(),
            "total_results": len(unique),
            "count": min(lim, len(unique)),
            "items": unique[:lim],
        }
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def heise_news_by_section(section: str, limit: int = 10) -> str:
    """Newest news of one heise section, in page order. section:
"security", "developer", "ki", "it", "wissenschaft",
"entertainment" or "digital-health" (German names work too, e.g.
"Künstliche Intelligenz"). limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        entry = _dom.normalise_section(section)
        out = _list_page(entry["url"], lim)
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok({"section": entry["section"], "section_name": entry["name"], **out})


@mcp.tool()
def heise_top_stories(limit: int = 10) -> str:
    """The heise.de front page: the top stories curated on the home
page right now, in page order. limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        out = _list_page(_dom.HOME_URL, lim)
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def heise_ct(limit: int = 10) -> str:
    """Latest articles from c't — heise's flagship computer magazine
— via the c't hub page, in page order. limit: 1..50 (default 10)."""
    try:
        lim = _dom.validate_limit(limit)
        out = _list_page(_dom.CT_URL, lim)
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def heise_get_article(url: str) -> str:
    """Text of one heise.de article: headline, description, section,
publish date, author and the article body. url: a heise.de article
link, e.g. from heise_headlines. Free articles return the full body;
heise+ (paywalled) articles return paywalled: true with only the
freely available sample (Leseprobe) — the full text stays behind the
paywall and is never fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        article = _dom.extract_article(_http.fetch_article(url.strip()))
    except (_http.HeiseError, ValueError) as e:
        return _err(e)
    return _ok({"url": url.strip(), **article})


@mcp.tool()
def heise_health() -> str:
    """Check whether heise.de is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
