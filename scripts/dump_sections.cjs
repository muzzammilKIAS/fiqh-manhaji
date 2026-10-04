// Mengeluarkan teks tiap tajuk (kitab sendiri, tiada tambahan) ke JSON untuk penulisan/semakan ringkasan.
// Guna: node scripts/dump_sections.cjs [out.json]   (memuat index.html + data/fiqh-data.json dalam jsdom)
const { JSDOM } = require('jsdom'); const fs = require('fs'); const path = require('path');
const ROOT = path.join(__dirname, '..'), OUT = process.argv[2] || path.join(ROOT, 'data', 'sections.json');
const H = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace(/<script src="https:\/\/cdnjs[^>]+><\/script>/, '');
const D = fs.readFileSync(path.join(ROOT, 'data', 'fiqh-data.json'), 'utf8');
const dom = new JSDOM(H, { runScripts: 'dangerously', url: 'https://l.test/#/', beforeParse(w) { w.matchMedia = () => ({ matches: false }); w.scrollTo = () => {}; w.fetch = async () => ({ ok: true, status: 200, json: async () => JSON.parse(D) }); w.console.info = () => {}; w.console.warn = () => {}; } });
setTimeout(() => {
  const out = dom.window.eval(`(() => ({ topics: DB.raw.topics.map(t => ({ topic_id: t.topic_id, title: t.title, bab: babOfTopic(t),
    heads: topicBlocks(t).map(b => ({ id: b.h ? b.h.heading_id : null, title: b.h ? b.h.title : null, level: b.h ? b.h.level : 0, parent: b.h ? b.h.parent_id : null,
      text: blockText(b), notes: b.segs.flatMap(s => s.notes).join('\\n'), pages: [...new Set(b.segs.map(s => s.is.page))] })) })) }))()`);
  fs.writeFileSync(OUT, JSON.stringify(out)); console.log('sections ->', OUT);
}, 600);
