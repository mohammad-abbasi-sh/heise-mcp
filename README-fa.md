# heise-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/heise-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[heise.de](https://www.heise.de)** — هایزه آنلاین، پورتال خبری شمارهٔ ۱ فناوری اطلاعات آلمان (c't، iX، heise security) — از طریق فید رسمی RSS و صفحه‌های رندرشدهٔ سمت سرور. تیترهای برتر، اخبار ۷ بخش، جست‌وجوی کلیدواژه، خبرهای برتر صفحهٔ اصلی، مقاله‌های مجلهٔ c't و متن مقاله‌ها. بدون کلید، بدون ورود.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (مدل سپهر). وابسته به heise.de یا Heise Medien نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی MCP Client اضافه کنید (stdio):

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

یا اجرای محلی: `python -m heise_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `heise_headlines` | تیترهای برتر (فید اصلی RSS، ۱۵۶ مورد)، جدیدترین اول — `limit` بین ۱ تا ۵۰ |
| `heise_search_news` | جست‌وجوی اخبار با کلیدواژه (عنوان + توضیح) — `query` (مثلاً «KI»)، `limit` بین ۱ تا ۵۰ |
| `heise_news_by_section` | جدیدترین اخبار یک بخش — `section`: «security»، «developer»، «ki»، «it»، «wissenschaft»، «entertainment» یا «digital-health» (نام آلمانی هم کار می‌کند، مثلاً «Künstliche Intelligenz»)، `limit` بین ۱ تا ۵۰ |
| `heise_top_stories` | خبرهای برتر صفحهٔ اصلی هایزه در حال حاضر، به ترتیب صفحه — `limit` بین ۱ تا ۵۰ |
| `heise_ct` | جدیدترین مقاله‌های c't، مجلهٔ پرچم‌دار کامپیوتر هایزه — `limit` بین ۱ تا ۵۰ |
| `heise_get_article` | متن یک مقاله: تیتر، توضیح، بخش، تاریخ انتشار، نویسنده و متن — `url` (لینک مقالهٔ heise.de). مقاله‌های رایگان متن کامل را برمی‌گردانند؛ مقاله‌های heise+ (پولی) مقدار `paywalled: true` را با فقط نمونهٔ رایگان (Leseprobe) برمی‌گردانند |
| `heise_health` | بررسی در دسترس بودن سایت (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`heise_headlines` با `limit` برابر ۲):

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

نکته‌ها:
- سرور **فید رسمی RSS** را می‌خواند (۱۵۶ مورد، بررسی زنده در ۱۶ نوامبر ۲۰۲۶) به‌علاوهٔ صفحه‌های رندرشدهٔ بخش‌ها (۷ بخش، هر کدام ۱۴ تا ۳۲ مقاله)، صفحهٔ اصلی (۷۳ خبر برتر) و هاب c't (۱۹ مقاله). فید RSS جداگانه برای بخش‌ها وجود ندارد — فیدهای بخش (`heise-top`، `security/rss`، `newsticker/rss`) همه ۴۰۴ هستند، پس بخش‌ها از صفحه‌های HTML خوانده می‌شوند. جست‌وجو فید اصلی را سمت کلاینت فیلتر می‌کند (جست‌وجوی سایت سمت سرور نتیجه‌ای رندر نمی‌کند).
- `heise_get_article` داده‌های NewsArticle در JSON-LD (تیتر، تاریخ انتشار، نویسنده، توضیح — مقاله‌های Hintergrund از `BackgroundNewsArticle` استفاده می‌کنند) به‌علاوهٔ پاراگراف‌های `div.article-content` را می‌خواند و در «Lesen Sie auch» متوقف می‌شود. فقط آدرس‌های `www.heise.de` واکشی می‌شوند.
- **صداقت دربارهٔ پی‌وال:** بسیاری از مقاله‌های هایزه heise+ هستند — صفحه‌های رندرشدهٔ سمت سرور آن‌ها فقط نمونهٔ رایگان (Leseprobe، ۳ پاراگراف اول) را دارند. برای این مقاله‌ها ابزار مقدار `paywalled: true`، تیتر، تیزر/توضیح و یک یادداشت برمی‌گرداند — هرگز متن ساختگی. مقاله‌های رایگان متن کامل را برمی‌گردانند (بررسی زنده: مقالهٔ خبری ۲۹۶ کلمه).
- داده‌ها: فید عمومی RSS و صفحه‌های heise.de — بدون کلید، بدون ورود، فقط خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین، با فید RSS واقعی ضبط‌شده، صفحه‌های بخش / اصلی / c't و دو صفحهٔ مقاله (رایگان + پولی)
- `tests/test_live.py` — چند درخواست زندهٔ محتاطانه به heise.de

تست‌ها: ۴۱ از ۴۱ سبز (۳۲ آفلاین + ۹ زنده، ۱۶ نوامبر ۲۰۲۶).

## مجوز

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
