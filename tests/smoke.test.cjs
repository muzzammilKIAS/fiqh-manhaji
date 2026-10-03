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
    const f = D.getElementById('studioForm'); const ai = f.querySelector('input[name=mode][value=ai]');
    ai.checked = true; ai.dispatchEvent(new w.Event('change', { bubbles: true }));
    submit(w, f); await wait(150);
    ok(w.eval('DECKS[0].stats.dropped') === 1, 'AI deck drops uncited point');
    ok(errs.length === 0, 'studio without errors'); }

  console.log(failed ? `\n${failed} test(s) failed` : '\nAll tests passed');
  process.exit(failed ? 1 : 0);
})();
