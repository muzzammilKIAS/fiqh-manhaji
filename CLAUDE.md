# CLAUDE.md — موسوعة الفقه المنهجي – قسم العبادات

Arabic RTL, database-driven encyclopedia for Shafi'i fiqh of worship (عبادات), with a content
editor, TXT/EPUB importer and a NotebookLM-style slide studio.

## Non-negotiable content rules (from the project brief)
- **DATABASE FIRST / SOURCE FIRST / ACCURACY FIRST.** The database is the single source of truth.
- Never invent or write from model memory: rulings, Quran verses, hadith, scholars' opinions,
  page/volume/hadith numbers, publication data, chapter names, or sources.
- Missing data → show `هذه المعلومة غير متوفرة في قاعدة البيانات الحالية.`
  Incomplete reference → `بيانات المرجع غير مكتملة في قاعدة البيانات.`
- Keep original text (📖 النص الأصلي) visually separate from explanation (💡 شرح وتوضيح).
- Scope: only الطهارة، الصلاة، الزكاة، الصيام، الحج والعمرة. Shafi'i madhhab only.
- Do not add the text of *al-Fiqh al-Manhaji* (copyrighted). Users import their own licensed text.
- Demo/placeholder data must be bracketed and obviously fake: `[بيانات تجريبية – …]`.
- Priorities: correctness > citation accuracy > data integrity > search > UX > speed > looks.

## Layout
- `index.html` — the whole app (single file, sections marked `CSS / HTML / DATA / JAVASCRIPT`).
- `data/fiqh-data.json` — empty schema; when served over http the app fetches it if the
  embedded `<script id="fiqh-data">` block is empty (see `CONFIG.DATA_URL`).
- `tests/smoke.test.cjs` — jsdom smoke tests (`npm install && npm test`).

## Run
`npm start` → http://localhost:8080 (any static server works; `file://` works but skips fetch).

## Data model (ids are strings, relations by id)
books → volumes → chapters (`key`: taharah|salah|zakah|siyam|hajj) → sections → topics → issues
→ evidences (type quran|hadith|other) / references (book_id, volume_id, page, url…).
Full template: `SCHEMA_EXAMPLE` in index.html. `validate()` reports broken relations.

## Architecture (inside index.html)
- Data layer: `setData()`, `buildIndexes()`, `issueCtx()`, `validate()`, `buildSearchRows()`.
- API facade `FiqhApi` (getBooks…searchIssues). Swap these bodies for `fetch(CONFIG.API_BASE…)`
  when a backend exists; never put DB credentials in the browser.
- Search: `norm()` (أ/إ/آ→ا، ى→ي، ة→ه، strips tashkeel), `runSearch()`, `highlight()`.
- Router: hash routes in `render()` — `#/`, `#/bab/:key`, `#/topic/:id`, `#/issue/:id`,
  `#/search?q=`, `#/refs`, `#/favs`, `#/recent`, `#/about`, `#/data`, `#/edit[/:id]`,
  `#/studio`, `#/deck/:id`.
- Storage: user data + decks in IndexedDB (`idb`), small prefs in localStorage (`store`).
- Importer: `parseBookText()`, `extractPage()`, `epubToText()` (JSZip from cdnjs).
- Studio: `buildExtractDeck()` (verbatim, no AI), `buildAiDeck()` + `validateAiSlides()`
  (drops points whose `cite` is not a real issue id; non-verbatim quotes become points).
- Claude-only features: `claude.use('sample')` (AI slides) and `claude.use('downloads')` exist
  only when published as a claude.ai artifact. Elsewhere `CAP.*` is null and the UI hides them.
  To enable AI slides outside claude.ai, add a small backend that calls the Anthropic API and
  implement the same `sample.json(prompt)` contract.

## Conventions
- UI text in Arabic; `dir="rtl"`; fonts Cairo (UI) + Amiri (sacred text).
- Colors are CSS tokens on `:root` with dark-mode overrides; keep it calm (emerald/gold/parchment).
- Escape all data with `esc()` before inserting into HTML.
- After any change run `npm test`.

## Suggested next tasks
1. Split into `/css/style.css`, `/js/data.js`, `/js/app.js`, `/js/search.js` (brief §37) and update tests.
2. "اسأل مصادرك": grounded Q&A chat over selected issues with numbered citations.
3. Optional backend (SQL/API) behind `FiqhApi`.
