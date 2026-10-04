// Data tests: loads data/fiqh-data.json through the app's own fetch path and checks integrity + rendering.
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace(/<script src="https:\/\/cdnjs[^>]+><\/script>/, '');
const DATA = fs.readFileSync(path.join(ROOT, 'data', 'fiqh-data.json'), 'utf8');
const wait = ms => new Promise(r => setTimeout(r, ms));
let failed = 0;
const ok = (cond, msg) => { console.log((cond ? '✓ ' : '✗ ') + msg); if (!cond) failed++; };

function boot(hash) {
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously', url: 'https://local.test/' + hash,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false }); w.scrollTo = () => {};
      w.fetch = async () => ({ ok: true, status: 200, json: async () => JSON.parse(DATA), text: async () => DATA });
      w.Element.prototype.scrollIntoView = () => {}; w.console.info = () => {}; w.console.warn = () => {};
    }
  });
  const errs = []; dom.window.addEventListener('error', e => errs.push(e.message));
  return { w: dom.window, D: dom.window.document, errs };
}
const text = D => D.getElementById('view').textContent.replace(/\s+/g, ' ');

(async () => {
  const d = JSON.parse(DATA);
  if (!d.issues.length) { console.log('- data tests skipped: data/fiqh-data.json is empty (run scripts/build_from_shamela.py)'); return; }
  ok(d.chapters.map(c => c.key).join() === 'taharah,salah,zakah,siyam,hajj', 'only the five ibadat chapters');
  ok(d.issues.length > 400 && d.issues.every(i => i.original_text && i.page), 'every issue has original text and a page');

  const { w, D, errs } = boot('#/'); await wait(400);
  ok(w.eval('DB.mode') === 'remote', 'data loaded via DATA_URL');
  const W = w.eval('validate()').filter(x => x.startsWith('تحذير'));
  ok(W.length === 0, 'validate() reports no broken relations' + (W.length ? ': ' + W.slice(0, 3).join(' | ') : ''));
  for (const h of ['#/bab/salah', '#/topic/t1_2', '#/issue/v1p33', '#/search?q=' + encodeURIComponent('الوضوء'), '#/refs']) {
    w.location.hash = h; await wait(150);
    ok(text(D).length > 50, 'renders ' + h);
  }
  w.location.hash = '#/issue/v1p33'; await wait(150);
  ok(text(D).includes('ودليل كونه غير مطهر'), 'issue v1p33 shows verbatim text');
  ok(errs.length === 0, 'no runtime errors' + (errs.length ? ': ' + errs[0] : ''));
  console.log(failed ? `\n${failed} failed` : '\nAll data tests passed');
  process.exit(failed ? 1 : 0);
})();
