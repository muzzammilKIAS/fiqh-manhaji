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
  // slides: nothing lost or altered when a page is split across slides (verbatim, in order)
  { const bad = w.eval(`(() => {
      const ws = t => String(t).replace(/\\s+/g, ' ').trim(), bad = [];
      DB.raw.issues.forEach(is => {
        const c = issueCtx(is), { body, foot } = splitFoot(is.original_text);
        const r = buildExtractDeck(c.topic.title, [c.topic], c.babKey, [is]);
        const q = k => r.slides.filter(s => s.type === 'quote' && s.kind === k).map(s => s.text).join(' ');
        if (ws(q('nass')) !== ws(body) || ws(q('foot')) !== ws(foot)) bad.push(is.issue_id);
        if (r.slides.some(s => s.type === 'quote' && s.text.length > 520)) bad.push(is.issue_id + ':long');
      });
      return bad;
    })()`);
    ok(bad.length === 0, 'slides keep every page verbatim (' + w.eval('DB.raw.issues.length') + ' pages)' + (bad.length ? ': ' + bad.slice(0, 5).join() : '')); }
  for (const h of ['#/slides/bab/hajj', '#/slides/topic/t1_3', '#/slides/issue/v1p67?s=1']) {
    w.location.hash = h; await wait(250);
    ok(D.querySelectorAll('.film .thumb').length > 2 && D.querySelector('#stage .slide'), 'renders ' + h);
  }
  // hierarchy: headings come from the book's own TOC; the per-heading text partitions each topic exactly
  ok(d.headings.length > 250 && d.headings.every(h => d.topics.some(t => t.topic_id === h.topic_id)), 'headings loaded: ' + d.headings.length);
  ok(d.headings.filter(h => h.located).length / d.headings.length > 0.97, 'headings located inside page text (>97%)');
  { const bad = w.eval(`(() => {
      const ws = t => String(t).replace(/\\s+/g, ' ').trim(), bad = [];
      DB.raw.topics.forEach(t => {
        const iss = topicIssues(t), bl = topicBlocks(t);
        const bodies = ws(iss.map(is => splitFoot(is.original_text).body).join(' ')), got = ws(bl.map(b => b.segs.map(s => s.text).join(' ')).join(' '));
        if (bodies !== got) bad.push(t.topic_id + ':body');
        const wd = x => x.split(/\\s+/).filter(Boolean).sort().join(' ');
        const foots = wd(iss.map(is => splitFoot(is.original_text).foot).join(' ')), gotF = wd(bl.map(b => b.segs.map(s => s.notes.join(' ')).join(' ')).join(' '));
        if (foots !== gotF) bad.push(t.topic_id + ':foot');
        // slides of the whole topic carry the same body text, in order
        const r = buildExtractDeck(t.title, [t], 'x');
        const q = r.slides.filter(s => s.type === 'quote' && s.kind === 'nass').map(s => s.text).join(' ');
        const kept = ws(bl.filter(b => !isBareTitle(b, t)).map(b => b.segs.map(s => s.text).join(' ')).join(' '));
        if (bl.some(b => isBareTitle(b, t) && blockText(b).length > 60)) bad.push(t.topic_id + ':skip');
        if (!r.stats && ws(q) !== kept) bad.push(t.topic_id + ':slides');
      });
      return bad;
    })()`);
    ok(bad.length === 0, 'every topic: sections + slides keep body and footnotes verbatim' + (bad.length ? ': ' + bad.slice(0, 6).join() : '')); }
  if (d.summaries && d.summaries.length) {
    const hid = new Set(d.headings.map(x => x.heading_id)), tid = new Set(d.topics.map(x => x.topic_id));
    ok(d.summaries.every(x => (x.level === 'heading' ? hid : tid).has(x.target_id) && x.ringkas && x.ringkas.length < 420 && x.ungrounded_ratio <= 0.1 && x.source === 'ai_from_source'), 'summaries: ' + d.summaries.length + ' valid, grounded (<=10% unmatched words), flagged ai_from_source');
    ok(d.topics.every(t => d.summaries.some(x => x.level === 'topic' && x.target_id === t.topic_id)), 'every topic has a summary');
    const dl = w.eval(`(() => { const o = []; DB.raw.headings.forEach(h => { const b = sectionBlocks(h, false)[0]; if (!b) return; const own = blockText(b); extractDalil(ownText(b)).forEach(x => { if (!norm(own).includes(norm(x.text.replace(/ …$/, '').slice(0, 40)))) o.push(h.heading_id); }); }); return [o, DB.raw.headings.reduce((n, h) => n + extractDalil(ownText(sectionBlocks(h, false)[0] || { h: null, segs: [] })).length, 0)]; })()`);
    ok(dl[0].length === 0 && dl[1] > 100, 'extracted dalil is verbatim from the book text (' + dl[1] + ' items)');
  }
  { const res = w.eval(`(() => { const bad = [], counts = []; const ok = s => s && s.type && has(s.title);
      DB.raw.topics.forEach(t => { const r = buildLessonDeck('topic', t.title, [t], babOfTopic(t)); counts.push(r.slides.length); if (!r.slides.every(ok) || r.slides[0].type !== 'title' || r.slides[r.slides.length - 1].type !== 'sources') bad.push(t.topic_id);
        r.slides.filter(s => s.type === 'dalil').forEach(s => s.items.forEach(d => { const src = norm(topicIssues(t).map(i => i.original_text).join(' ')); if (!src.includes(norm(d.text.replace(/ …$/, '').slice(0, 40)))) bad.push(t.topic_id + ':dalil'); })); });
      BABS.forEach(b => { const r = buildLessonDeck('bab', b.title, babTopicsOrdered(b.key).map(x => x.t), b.key); if (!r.slides.every(ok)) bad.push(b.key); counts.push(r.slides.length); });
      DB.raw.headings.slice(0, 80).forEach(h => { const r = buildLessonDeck('section', h.title, [Api.getTopicById(h.topic_id)], 'x', h); if (!r.slides.every(ok)) bad.push(h.heading_id); });
      return { bad, max: Math.max(...counts) }; })()`);
    ok(res.bad.length === 0, 'lesson (PdP) decks well-formed, dalil verbatim; longest ' + res.max + ' slides' + (res.bad.length ? ': ' + res.bad.slice(0, 5).join() : '')); }
  if (d.quizzes && d.quizzes.length) {
    const qb = w.eval(`(() => { const ws = t => norm(t).replace(/\\s+/g, ' ').trim(), bad = [];
      DB.raw.quizzes.forEach(q => { const t = Api.getTopicById(q.topic_id); if (!t) { bad.push(q.quiz_id + ':topic'); return; }
        const src = ws(topicIssues(t).map(i => i.original_text).join(' '));
        if (!src.includes(ws(q.quote))) bad.push(q.quiz_id + ':quote');
        if (!Array.isArray(q.options) || q.options.length !== 4 || new Set(q.options).size !== 4 || !(q.answer >= 0 && q.answer <= 3)) bad.push(q.quiz_id + ':shape');
        if (has(q.heading_id) && !Api.getHeadingById(q.heading_id)) bad.push(q.quiz_id + ':heading'); });
      return bad; })()`);
    ok(qb.length === 0, 'quizzes: ' + d.quizzes.length + ' questions, 4 options each, quote verbatim from the book' + (qb.length ? ': ' + qb.slice(0, 5).join() : ''));
    const tq = d.quizzes[0].topic_id;
    w.location.hash = '#/quiz/topic/' + tq; await wait(150);
    const ans = w.eval('QZ.list[QZ.order[0]].answer'), wrongK = (ans + 1) % 4;
    D.querySelector('.qz-opt[data-k="' + wrongK + '"]').click(); await wait(30);
    ok(D.querySelector('.qz-opt.bad') && D.querySelector('.qz-opt.ok') && D.querySelector('.qz-src .qz-quote'), 'quiz: wrong pick marked, correct shown, explanation + verbatim quote');
    w.location.hash = '#/quiz'; await wait(100);
    ok(text(D).includes('الاختبارات') && D.querySelectorAll('.tcard').length > 0, 'quiz index renders');
  }
  for (const h of ['#/slides/topic/t1_3?m=nas', '#/tree/topic/t1_3', '#/section/h20', '#/tree', '#/tree/bab/salah', '#/tree/topic/t1_3', '#/tree/section/h20', '#/cards/topic/t1_3', '#/cards/bab/zakah', '#/slides/section/h20', '#/search?q=' + encodeURIComponent('أقسام المياه')]) {
    w.location.hash = h; await wait(250);
    ok(text(D).length > 80 && !/تعذّر عرض/.test(text(D)), 'renders ' + h);
  }
  w.location.hash = '#/tree/bab/salah'; await wait(200);
  { const n1 = D.querySelectorAll('.trn').length; D.querySelector('[data-act=tr-all]').click(); await wait(50);
    ok(D.querySelectorAll('.trn').length > n1, 'tree expands (' + n1 + ' → ' + D.querySelectorAll('.trn').length + ' nodes)'); }
  ok(errs.length === 0, 'no runtime errors' + (errs.length ? ': ' + errs[0] : ''));
  console.log(failed ? `\n${failed} failed` : '\nAll data tests passed');
  process.exit(failed ? 1 : 0);
})();
