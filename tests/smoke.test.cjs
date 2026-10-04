// Smoke tests: run with `npm test`. Loads index.html in jsdom (no network).
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const JSZip = require('jszip');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8')
  .replace(/<script src="https:\/\/cdnjs[^>]+><\/script>/, '');
const wait = ms => new Promise(r => setTimeout(r, ms));
let failed = 0;
const ok = (cond, msg) => { console.log((cond ? '✓ ' : '✗ ') + msg); if (!cond) failed++; };

function boot(hash, withSample = false) {
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously', url: 'https://local.test/' + hash,
    beforeParse(w) {
      w.JSZip = JSZip; w.matchMedia = () => ({ matches: false }); w.scrollTo = () => {};
      w.fetch = () => Promise.reject(new Error('offline')); w.confirm = () => true;
      w.Element.prototype.scrollIntoView = () => {}; w.console.info = () => {}; w.console.warn = () => {};
      if (withSample) {
        const sample = async () => ({ text: '' });
        sample.json = async prompt => {
          const ids = [...prompt.matchAll(/<source id="([^"]+)"/g)].map(m => m[1]);
          return { slides: [{ type: 'points', title: 'T', points: [{ text: 'ok', cite: [ids[0]] }, { text: 'bad', cite: ['nope'] }] }] };
        };
        w.claude = { use: async n => (n === 'sample' ? sample : null) };
      }
    }
  });
  const errs = []; dom.window.addEventListener('error', e => errs.push(e.message));
  return { w: dom.window, D: dom.window.document, errs };
}
const submit = (w, f) => f.dispatchEvent(new w.Event('submit', { bubbles: true, cancelable: true }));
const text = D => D.getElementById('view').textContent.replace(/\s+/g, ' ');

(async () => {
  // 1. Empty database: no invented content
  { const { D, errs } = boot('#/'); await wait(200);
    ok(text(D).includes('لم يتم ربط قاعدة البيانات بعد'), 'empty DB shows "not connected" notice');
    ok(errs.length === 0, 'no runtime errors on home'); }

  // 2. Demo data + all routes
  { const { w, D, errs } = boot('#/data'); await wait(200);
    D.querySelector('[data-act=load-demo]').click(); await wait(50);
    for (const h of ['#/', '#/bab/taharah', '#/topic/demo-t1-1', '#/issue/demo-i1', '#/refs', '#/favs', '#/recent', '#/about', '#/studio', '#/edit']) {
      w.location.hash = h; await wait(30);
    }
    w.location.hash = '#/search?q=' + encodeURIComponent('تجريبيه'); await wait(30);
    ok(/عرض ١–/.test(text(D)) && D.querySelectorAll('mark').length > 0, 'Arabic-normalized search + highlight');
    ok(errs.length === 0, 'all routes render without errors'); }

  // 3. Editor create / edit / delete
  { const { w, D, errs } = boot('#/edit?bab=salah'); await wait(200);
    const f = D.querySelector('[data-form=edit]');
    f.elements.topic.value = 'موضوع'; f.elements.title.value = 'مسألة'; f.elements.original_text.value = 'نص'; f.elements.page.value = '7'; f.elements.volume.value = '1';
    submit(w, f); await wait(60);
    ok(w.location.hash.startsWith('#/issue/') && text(D).includes('صـ 7'), 'editor saves issue with page');
    const id = decodeURIComponent(w.location.hash.split('/')[2]);
    w.location.hash = '#/edit/' + id; await wait(40);
    D.querySelector('[data-act=del-issue]').click(); await wait(60);
    ok(w.eval('DB.raw.issues.length') === 0, 'delete removes issue');
    ok(errs.length === 0, 'editor without errors'); }

  // 4. EPUB/text importer
  { const { w, D, errs } = boot('#/data'); await wait(200);
    const f = D.getElementById('importForm');
    f.elements.raw.value = '# كتاب الطهارة\n## باب المياه\n### مسألة: أ\nنص ﴿آية﴾ [البقرة: 5]\n[ص 12]\n### مسألة: ب\nنص\n# كتاب البيوع\nخارج';
    submit(w, f); await wait(30);
    D.querySelector('[data-act=commit-import]').click(); await wait(60);
    const R = w.eval('DB.raw');
    ok(R.issues.length === 2, 'importer splits issues and skips non-ibadat');
    ok(R.evidences.length === 1 && R.evidences[0].surah === 'البقرة', 'importer extracts Quran evidence');
    ok(errs.length === 0, 'importer without errors'); }

  // 5. Studio (extract + AI with citation validation)
  { const { w, D, errs } = boot('#/data', true); await wait(250);
    D.querySelector('[data-act=load-demo]').click(); await wait(50);
    w.location.hash = '#/studio?bab=taharah'; await wait(50);
    submit(w, D.getElementById('studioForm')); await wait(80);
    ok(w.location.hash.startsWith('#/deck/') && w.eval('DECKS[0].slides.length') > 3, 'extract deck created');
    w.location.hash = '#/studio'; await wait(50);
    { const f0 = D.getElementById('studioForm'), le = f0.querySelector('input[name=mode][value=lesson]');
      le.checked = true; le.dispatchEvent(new w.Event('change', { bubbles: true })); submit(w, f0); await wait(80);
      ok(w.eval('DECKS[0].lesson') === true && w.eval('DECKS[0].slides[0].type') === 'title' && D.querySelector('#stage .slide'), 'lesson (PdP) deck created from studio');
      w.eval("studioSel.mode = 'extract'"); }
    w.location.hash = '#/studio'; await wait(50);
    const f = D.getElementById('studioForm'); const ai = f.querySelector('input[name=mode][value=ai]');
    ai.checked = true; ai.dispatchEvent(new w.Event('change', { bubbles: true }));
    submit(w, f); await wait(150);
    ok(w.eval('DECKS[0].stats.dropped') === 1, 'AI deck drops uncited point');
    ok(errs.length === 0, 'studio without errors'); }

  // 6. Slide themes (settings) — every theme renders every slide type, choice persists
  { const { w, D, errs } = boot('#/data'); await wait(200);
    D.querySelector('[data-act=load-demo]').click(); await wait(50);
    w.location.hash = '#/settings'; await wait(50);
    ok(D.querySelectorAll('.th-card').length === 5, 'settings shows 5 slide themes');
    D.querySelector('.th-card[data-th=lail]').click(); await wait(50);
    ok(w.eval("store.get('slideTheme')") === 'lail', 'theme choice saved');
    w.location.hash = '#/slides/topic/demo-t1-1'; await wait(80);
    ok(D.querySelector('#stage .slide.th-lail'), 'slides use the chosen theme');
    const bad = w.eval(`(() => { const t = DB.raw.topics[0], r = buildLessonDeck('topic', t.title, [t], 'taharah'), f = buildExtractDeck(t.title, [t], 'taharah'); const deck = { title: 'x', mode: 'extract', bab: 'taharah', sources: [], slides: r.slides };
      const extra = [{ type: 'agenda', title: 'x', items: [{ t: 'a', n: 1 }] }, { type: 'summary', title: 'x', lead: 'a', items: ['b'], ai: true }, { type: 'dalil', title: 'x', items: [{ kind: 'quran', text: 'a', ref: 'b' }] }, { type: 'recap', title: 'x', items: [{ t: 'a', r: 'b' }] }, { type: 'review', title: 'x', items: [{ q: 'a', n: 1 }] }, { type: 'points', mlk: true, title: 'x', points: [{ text: 'a', cite: [] }] }];
      const out = []; SLIDE_THEMES.forEach(th => [...r.slides, ...f.slides, ...extra].forEach((s, k) => { const h = slideHtml(deck, s, k, th.key); if (!h.includes('th-' + th.key) || h === '<div class="slide th-' + th.key + '"></div>') out.push(th.key + ':' + s.type); })); return out; })()`);
    ok(bad.length === 0, 'all 5 themes render every slide type' + (bad.length ? ': ' + bad.slice(0, 4).join() : ''));
    for (const th of ['classic', 'mushaf', 'lail', 'asri', 'zakhrafa']) { w.location.hash = '#/themes/' + th; await wait(40); if (D.querySelectorAll('.gal .slide.th-' + th).length < 4) bad.push('gallery:' + th); }
    ok(!bad.some(x => x.startsWith('gallery')), 'theme galleries render');
    w.eval("store.set('slideTheme','classic')");
    ok(errs.length === 0, 'themes without errors'); }

  // 7. Copyright notice
  { const { w, D } = boot('#/about'); await wait(200);
    const C = '© Muzzammil Najib 2026 | FPIB-KIAS';
    ok(D.querySelector('.site-foot').textContent.includes(C) && D.getElementById('sideFoot').textContent.includes(C) && text(D).includes(C), 'copyright shown in footer, sidebar and about page'); }

  console.log(failed ? `\n${failed} test(s) failed` : '\nAll tests passed');
  process.exit(failed ? 1 : 0);
})();
