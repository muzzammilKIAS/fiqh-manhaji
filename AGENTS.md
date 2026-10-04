# AGENTS.md — موسوعة الفقه المنهجي – قسم العبادات

> Mirror of `CLAUDE.md` for other coding agents (Codex, etc.). Keep both files identical in content; when you change one, update the other.

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
- Text of *al-Fiqh al-Manhaji* (Dar al-Qalam, 1429H; Shamela id 6369): the project owner confirmed on 2026-10-04 that publication permission was obtained, so the ibadat data is committed and published with the site. Do not add other books or other parts of this book without the same confirmation; keep the source credited.
- Demo/placeholder data must be bracketed and obviously fake: `[بيانات تجريبية – …]`.
- Priorities: correctness > citation accuracy > data integrity > search > UX > speed > looks.

## Layout
- `index.html` — the whole app (single file, sections marked `CSS / HTML / DATA / JAVASCRIPT`).
- `data/fiqh-data.json` — the published ibadat data (committed; permission confirmed, see above); regenerate with `python3 scripts/build_from_shamela.py` (Shamela 4 + kitab id 6369 mesti ada di Mac). When served over http the app fetches it if the
  embedded `<script id="fiqh-data">` block is empty (see `CONFIG.DATA_URL`).
- `scripts/build_from_epub.py` — **lapuk**: OCR archive.org ~18% perkataan salah dan pemetaan halaman cetakan tersasar (hanya betul hal. 26–97). Guna build_from_shamela.py.
- `tests/smoke.test.cjs` — jsdom smoke tests (`npm install && npm test`).

## Run
`npm start` → http://localhost:8080 (any static server works; `file://` works but skips fetch).

## Data model (ids are strings, relations by id)
books → volumes → chapters (`key`: taharah|salah|zakah|siyam|hajj) → sections → topics → issues
→ evidences (type quran|hadith|other) / references (book_id, volume_id, page, url…).
`headings` = sub-topic hierarchy taken from the book's own TOC (Shamela title tree): `{heading_id, topic_id, parent_id, level 1..3, title, issue_id (page where it starts), offset (char index of its line inside that page's text), located}`. A heading's text = the verbatim slice from its offset to the next heading's offset (`topicBlocks()`); footnotes follow the segment that cites their number. Never invent headings — they come only from `build_from_shamela.py` (TOC depth 5) or a user's import.
Full template: `SCHEMA_EXAMPLE` in index.html. `validate()` reports broken relations.

## Architecture (inside index.html)
- Data layer: `setData()`, `buildIndexes()`, `issueCtx()`, `validate()`, `buildSearchRows()`.
- API facade `FiqhApi` (getBooks…searchIssues). Swap these bodies for `fetch(CONFIG.API_BASE…)`
  when a backend exists; never put DB credentials in the browser.
- Search: `norm()` (أ/إ/آ→ا، ى→ي، ة→ه، strips tashkeel), `runSearch()`, `highlight()`.
- Router: hash routes in `render()` — `#/`, `#/bab/:key`, `#/topic/:id`, `#/issue/:id`,
  `#/search?q=`, `#/refs`, `#/favs`, `#/recent`, `#/about`, `#/data`, `#/edit[/:id]`,
  `#/section/:headingId`, `#/tree[/bab|topic|section/:id]` (tasyjir SVG, collapsible), `#/cards/{bab|topic|section}/:id` (flashcards: title → verbatim text), `#/studio`, `#/deck/:id`, `#/slides/{section|bab|topic|issue}/:id[?s=N]` (temporary deck, nothing saved until "حفظ في عروضي"). "ملخص" blocks show TOC structure + verbatim excerpts, plus grounded summaries when present (see Summaries).
- Storage: user data + decks in IndexedDB (`idb`), small prefs in localStorage (`store`).
- Importer: `parseBookText()`, `extractPage()`, `epubToText()` (JSZip from cdnjs).
- Slides: `buildExtractDeck()` splits each Shamela page into verbatim chunks (`chunkText()`; body and `— الحواشي —` footnotes via `splitFoot()` become separate slides) — `tests/data.test.cjs` checks every page survives unchanged. `slideHtml()` renders title/section/quote/points/sources slides in cq-units (fixed light palette so print/export match); per-bab accent comes from `.ab-<key>` (`--a`, `--a-deep`). Viewer = canvas + filmstrip; thumbs are `div role=button` (never nest `<button>` inside — the HTML parser would close the outer one).
- Studio: `buildExtractDeck()` (verbatim, no AI), `buildAiDeck()` + `validateAiSlides()`
  (drops points whose `cite` is not a real issue id; non-verbatim quotes become points).
- claude.ai-only features: `window.claude.use('sample')` (AI slides) and `window.claude.use('downloads')`
  exist only when the page is published as a claude.ai artifact. Elsewhere `CAP.*` is null and the UI
  hides them. To enable AI slides elsewhere, add a small backend that calls an LLM API and implement
  the same `sample.json(prompt)` contract.

## Conventions
- UI text in Arabic; `dir="rtl"`; fonts Cairo (UI) + Amiri (sacred text).
- Colors are CSS tokens on `:root` with dark-mode overrides; keep it calm (emerald/gold/parchment).
- Escape all data with `esc()` before inserting into HTML.
- After any change run `npm test`.

## Suggested next tasks
1. Split into `/css/style.css`, `/js/data.js`, `/js/app.js`, `/js/search.js` (brief §37) and update tests.
2. "اسأل مصادرك": grounded Q&A chat over selected issues with numbered citations.
3. Optional backend (SQL/API) behind `FiqhApi`.

## Summaries (ملخص مصوغ) — grounded, never from memory
- `data/summaries.json` (committed) → embedded as `summaries` by `build_from_shamela.py`: `{summary_id, level: heading|topic, target_id, ringkas, masail[], source:'ai_from_source', ungrounded_ratio}`.
- Pipeline: `node scripts/dump_sections.cjs` → agents write `ringkas`/`masail` using ONLY the section text → `python3 scripts/check_summaries.py sections.json out/*.json --strict 0.10 --merge data/summaries.json`. The checker rejects any summary where >10% of its words do not occur in the source section (lexical grounding only: **spot-check rulings by eye** — it cannot catch a reversed ruling).
- UI always labels them (`AI_NOTE`, tag «ملخص آلي»). Dalil shown in summaries/tasyjir is NOT generated: `extractDalil()` copies verses (﴿ ﴾ + ref) and «روى/رواه/أخرجه» lines verbatim; tests assert they occur in the book text.
- Tasyjir detailed view (`#/tree/topic|section/:id`, toggle on bab/overview) = per node: ringkas · first dalil · up to 3 masail.

## Slide flow (PdP)
- `#/slides/{bab|topic|section}/:id` opens **وضع الدرس** by default (`buildLessonDeck()`); `?m=nas` = full verbatim text deck (`buildExtractDeck()`); issue decks are always verbatim. Studio has the same «🎓 درس» option.
- Lesson flow: title → agenda (محاور) → overview + أهم المسائل → per unit (level-1 heading): divider (ringkas) → المسائل → الأدلة (verbatim `extractDalil`, ≤4) → تفصيل (sub-headings) → خلاصة الدرس → أسئلة المراجعة (template questions built from heading titles only) → sources. Full unit text sits in presenter notes (key **N**). Anything taken from `summaries` is tagged «ملخص آلي». Summary slides (`t-summary`, `t-recap`) use their own honey-gold palette and `--mlk` font (Amiri → Lotus fallback) so they never look like verbatim text (cream) or dalil (green). The same applies inside `?m=nas` decks and Studio AI decks (`points` slides flagged `mlk` → class `t-mlk`).
- Lists are split with `evenChunks()` (no 6+1 orphan slides); full mode skips bare heading-line blocks (`isBareTitle`) and merges short tail chunks in `chunkText()`.

## Slide themes (⚙️ #/settings)
- `SLIDE_THEMES` = classic · mushaf (مخطوطة) · lail (ليلي) · asri (عصري) · zakhrafa (زخرفة); chosen in `#/settings` (live previews) or the 🎨 picker in the deck viewer; stored as `store('slideTheme')`, overridable per link with `?th=`. `slideHtml(deck, s, k, th)` adds `th-<key>` to every slide (stage, thumbs, print, HTML export).
- Themes differ in **layout**, not just colour («تخطيطات الأنماط» block): mushaf = book (centred rubric titles, agenda as a dotted-leader فهرس, boxless text with a margin rule); lail = stage (glowing timeline agenda, single big centred dalil, chat-bubble review); asri = bento/split (coloured title column beside text/dalil, big-number tiles; first tile spans by item count via `.n<count>` classes); zakhrafa = symmetry (zig-zag agenda on a central axis, arch-topped tiles, verse in a cartouche). Theme selectors that target the slide's own type must be compound (`.th-lail.k-foot`, not `.th-lail .k-foot`). Gallery of every slide type per theme: `#/themes/:key`.
- Theme colour CSS («أنماط الشرائح» block) overrides tokens (`--sbg --sink --smut --sline --card --sa --sd --sg`) plus title/section/summary backgrounds. Every theme must keep the three-way distinction: verbatim text · summary (own colour, `--mlk` font) · dalil.
- `#/settings` also sets the default deck mode (`store('deckMode')`: dars | nas); the viewer toggle passes `?m=dars|nas` explicitly.

## Deploy
- GitHub Pages from `main` (repo public): https://muzzammilkias.github.io/fiqh-manhaji/ — the app loads `data/fiqh-data.json` automatically. Push to `main` redeploys (~1 min).

## Quizzes (📝 #/quiz)
- `data/quizzes.json` → embedded as `quizzes` by `build_from_shamela.py`: `{quiz_id, topic_id, heading_id, q, options[4], answer, explain, quote, difficulty:'medium', source:'ai_from_source'}`. 477 questions, 4–12 per topic.
- Pipeline: agents write questions from `sections.json` only → `python3 scripts/check_quizzes.py sections.json quiz/*.json --merge data/quizzes.json`. Rejects: quote not an exact substring of the book text; correct answer + explanation with >15% words not in the source; stems mostly ungrounded (question-framing words like «بحسب النص/فماذا يفعل» are ignored). Tests re-verify every quote.
- Routes: `#/quiz` (index + best scores), `#/quiz/{topic|bab|section}/:id`. Keys 1–4 answer, Enter next. Always labelled as machine-generated with the verbatim proof under each answer.

## Slide text fitting
- `fitSlide(stage)` shrinks fonts (in `cqh`, so fullscreen stays right) until every text box fits — book text is never clipped. Called for the main stage, galleries/settings previews, print (offscreen pass) and the HTML export; thumbnails are not fitted.
- Do not use `font-size … !important` in slide CSS (it blocks fitting); raise selector specificity instead. Titles use line-height ≥1.6 so Amiri marks are not cut.
- Check: `npm start`, open http://localhost:8080/tests/overflow.html — renders every slide of every topic in all 5 themes and lists clipped elements (expect all empty).
