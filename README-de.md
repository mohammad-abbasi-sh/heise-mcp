# heise-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/heise-mcp

Inoffizieller **Read-only**-MCP-Server für **[heise.de](https://www.heise.de)** — heise online, Deutschlands #1-IT-Nachrichtenportal (c't, iX, heise security) — über den offiziellen RSS-Feed und serverseitig gerenderte Seiten. Top-Schlagzeilen, Nachrichten nach Ressort (7 Ressorts), Stichwortsuche, Top-Meldungen der Startseite, c't-Artikel und Artikeltexte. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi im Rahmen der „Germany MCP factory" (Sepehr-Modell). Nicht mit heise.de oder Heise Medien verbunden.

## Für KI-Agenten

Zur MCP-Client-Konfiguration hinzufügen (stdio):

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

Oder lokal starten: `python -m heise_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|--------------|
| `heise_headlines` | Top-Schlagzeilen (Haupt-RSS-Feed, 156 Einträge), neueste zuerst — `limit` 1..50 |
| `heise_search_news` | Nachrichtensuche nach Stichwort (Titel + Beschreibung) — `query` (z. B. „KI"), `limit` 1..50 |
| `heise_news_by_section` | Neueste Nachrichten eines Ressorts — `section`: „security", „developer", „ki", „it", „wissenschaft", „entertainment" oder „digital-health" (deutsche Namen funktionieren auch, z. B. „Künstliche Intelligenz"), `limit` 1..50 |
| `heise_top_stories` | Die Top-Meldungen, die gerade auf der heise.de-Startseite kuratiert werden, in Seitenreihenfolge — `limit` 1..50 |
| `heise_ct` | Neueste Artikel aus der c't, dem Flaggschiff-Computermagazin von heise — `limit` 1..50 |
| `heise_get_article` | Text eines Artikels: Schlagzeile, Beschreibung, Ressort, Veröffentlichungsdatum, Autor, Text — `url` (ein heise.de-Artikellink). Freie Artikel liefern den Volltext; heise+-Artikel (Paywall) liefern `paywalled: true` mit nur der frei verfügbaren Leseprobe |
| `heise_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`heise_headlines`, `limit` 2):

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

Hinweise:
- Der Server liest den **offiziellen RSS-Feed** (156 Einträge, live geprüft am 16.11.2026) plus die serverseitig gerenderten Ressort-Seiten (7 Ressorts, je 14–32 Artikel), die Startseite (73 Top-Meldungen) und den c't-Hub (19 Artikel). Es gibt keine Ressort-RSS-Feeds — die Ressort-Feeds (`heise-top`, `security/rss`, `newsticker/rss`) sind alle 404, daher kommen die Ressorts aus den HTML-Seiten. Die Suche filtert den Haupt-Feed clientseitig (die Website-Suche rendert serverseitig keine Ergebnisse).
- `heise_get_article` liest das NewsArticle-JSON-LD (Schlagzeile, Veröffentlichungsdatum, Autor, Beschreibung — Hintergrund-Artikel nutzen `BackgroundNewsArticle`) plus die Absätze aus `div.article-content`, und stoppt bei „Lesen Sie auch". Nur `www.heise.de`-URLs werden abgerufen.
- **Paywall-Ehrlichkeit:** Viele heise-Artikel sind heise+ — ihre serverseitig gerenderten Seiten enthalten nur die kostenlose Leseprobe (3 Einleitungsabsätze). Für diese liefert das Tool `paywalled: true`, die Schlagzeile, den Teaser/die Beschreibung und einen Hinweis — niemals erfundenen Text. Freie Artikel liefern den Volltext (live geprüft: Nachrichtenartikel 296 Wörter).
- Daten: öffentlicher RSS-Feed und Seiten von heise.de — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, mit dem echten aufgezeichneten RSS-Feed, Ressort-/Start-/c't-Seiten und zwei Artikelseiten (frei + Paywall)
- `tests/test_live.py` — wenige vorsichtige Live-Anfragen an heise.de

Tests: 41/41 grün (32 offline + 9 live, 16.11.2026).

## Lizenz

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
