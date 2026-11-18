# heise-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/heise-mcp

Unofficial **read-only** MCP server for **[heise.de](https://www.heise.de)** — heise online, Germany's #1 IT news portal (c't, iX, heise security) — via its official RSS feed and server-rendered pages. Top headlines, news by section (7 Ressorts), keyword search, front-page top stories, c't magazine articles and article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with heise.de or Heise Medien.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "heise": {
      "command": "uvx",
      "args": ["heise-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m heise_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `heise_headlines` | Top headlines (main RSS feed, 156 items), newest first — `limit` 1..50 |
| `heise_search_news` | Search news by keyword (title + description) — `query` (e.g. "KI"), `limit` 1..50 |
| `heise_news_by_section` | Newest news of one section — `section`: "security", "developer", "ki", "it", "wissenschaft", "entertainment" or "digital-health" (German names work too, e.g. "Künstliche Intelligenz"), `limit` 1..50 |
| `heise_top_stories` | The front-page top stories curated on heise.de right now, in page order — `limit` 1..50 |
| `heise_ct` | Latest articles from c't, heise's flagship computer magazine — `limit` 1..50 |
| `heise_get_article` | Text of one article: headline, description, section, publish date, author, body — `url` (a heise.de article link). Free articles return the full body; heise+ (paywalled) articles return `paywalled: true` with only the freely available sample (Leseprobe) |
| `heise_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`heise_headlines`, `limit` 2):

```json
{"feed_title": "heise online News", "total_results": 156, "count": 2,
 "items": [
  {"title": "heise+ | Software-Nachbau mit KI: Wie Craft-Apps entstehen",
   "link": "https://www.heise.de/hintergrund/Software-Nachbau-mit-KI-Wie-Craft-Apps-entstehen-11518918.html?wt_mc=rss.red.ho.ho.rdf.beitrag_plus.beitrag_plus",
   "description": "16 Programme in wenigen Wochen: Repositorys hinter Nachbauten von Photoshop, Word oder Excel zeigen, wie KI-Agenten und eine CI-Pipeline zusammenspielen.",
   "published": "2026-11-16T09:30:00+00:00", "category": ""},
  {"title": "Nach Terroranschlag: Jordanien lässt Telegram sperren",
   "link": "https://www.heise.de/news/Nach-Terroranschlag-Jordanien-laesst-Telegram-sperren-11525885.html?wt_mc=rss.red.ho.ho.rdf.beitrag.beitrag",
   "description": "Eine jordanische Strafverfolgungsbehörde hat Telegram landesweit sperren lassen. Dem ist ein islamistischer Anschlag mit mehreren Toten vorausgegangen.",
   "published": "2026-11-16T09:27:00+00:00", "category": ""},
  ...]}
```

Notes:
- The server reads the **official RSS feed** (156 items, verified live 2026-11-16) plus the server-rendered section pages (7 sections, 14–32 articles each), the home page (73 top stories) and the c't hub (19 articles). There are no per-section RSS feeds — the section feeds (`heise-top`, `security/rss`, `newsticker/rss`) are all 404, so sections come from the HTML pages. Search filters the main feed client-side (the site search page renders no results server-side).
- `heise_get_article` reads the NewsArticle JSON-LD (headline, publish date, author, description — Hintergrund pieces use `BackgroundNewsArticle`) plus the `div.article-content` paragraphs, stopping at "Lesen Sie auch". Only `www.heise.de` URLs are fetched.
- **Paywall honesty:** many heise articles are heise+ — their server-rendered pages carry only the free sample (Leseprobe, 3 intro paragraphs). For those, the tool returns `paywalled: true`, the headline, the teaser/description and a note — never fabricated text. Free articles return the full body (verified live: news article 296 words).
- Data: heise.de public RSS feed and pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured RSS feed, section / home / c't pages and two article pages (free + paywalled)
- `tests/test_live.py` — cautious live requests against heise.de

Tests: 41/41 green (32 offline + 9 live, 2026-11-16).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
