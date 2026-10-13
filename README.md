# sheets-sync

Every time a supplier sends a new price list: see **what changed since last time** (new products, removed products, price and stock changes) and **upload the table to a Google Sheet** that your team works in. Python standard library only; Google is reached through a small Apps Script web app, so there is no OAuth setup in Python.

## What it does
- Compares the new CSV with the previous run's snapshot by a key column (`sku` by default) and writes `changes.md`: added, removed, and changed values in the columns you watch (`price,stock` by default). Spaces around values are not a change.
- Empty keys and repeated keys are reported in the file, not silently dropped (the first row with a key wins).
- Uploads the whole table with `--webhook`: the first chunk replaces the sheet, the rest are appended (500 rows per request). Values starting with `=`, `+`, `-`, `@` get a leading `'`, so a supplier file cannot put formulas into your sheet.
- **The snapshot is saved only after a successful upload**, so a failed upload does not hide the next run's changes. The first run only creates the snapshot.
- The webhook secret comes from `SHEETS_SYNC_SECRET`; the URL must be `https`.

## Use
```bash
PYTHONPATH=src python3 -m sheets_sync prices.csv                 # first run: remembers the file
PYTHONPATH=src python3 -m sheets_sync prices-new.csv             # writes changes.md
SHEETS_SYNC_SECRET=... PYTHONPATH=src python3 -m sheets_sync prices-new.csv --webhook https://script.google.com/macros/s/.../exec --sheet prices
```
Google side: open the Sheet, Extensions > Apps Script, paste `apps_script/Code.gs`, add the Script property `SYNC_SECRET`, Deploy > New deployment > Web app (Execute as: Me, access: Anyone) and use the `/exec` URL. Tests: `python3 -m unittest discover -s tests` (the upload is tested against a local server).

## Limits (read this)
- **`apps_script/Code.gs` of this project has not been deployed on a live Google account yet.** The same pattern (JSON with a secret to a web app, refusal on a wrong secret, row appended) was verified live in my other repo, `telegram-orders-sheets-bot`; try this one on a test sheet first.
- Google Sheets turns text like `1250` into a number after upload. That is usually what you want for prices, but codes such as `00123` may lose leading zeros.
- Up to 1000 rows per request in the script; large lists go in chunks, so a failure in the middle can leave the sheet partly filled. Run again to replace it.
- The snapshot is a plain JSON file next to the program. Only CSV input.

MIT license.

---

# sheets-sync (українською)

Щоразу, коли постачальник надсилає новий прайс: бачите, **що змінилося** (нові й прибрані товари, зміни цін і залишків), і **завантажуєте таблицю в Google Таблицю**. Лише стандартна бібліотека Python; Google підключається через невеликий Apps Script.

**Запуск:** `python3 -m sheets_sync prices.csv` (перший раз запам'ятовує файл), наступного разу створює `changes.md`; з `--webhook` і `SHEETS_SYNC_SECRET` завантажує в таблицю.

**Важливо:** скрипт `Code.gs` саме цього проєкту ще не розгорнуто на живому акаунті Google; такий самий підхід перевірено наскрізно в `telegram-orders-sheets-bot`. Знімок оновлюється тільки після успішного завантаження.
