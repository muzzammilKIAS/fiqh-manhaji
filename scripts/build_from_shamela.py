#!/usr/bin/env python3
"""Bina data/fiqh-data.json (bahagian Ibadat) daripada Shamela 4 setempat — kitab id 6369, jilid 1–2.

Guna:  python3 scripts/build_from_shamela.py [data/fiqh-data.json]

- Memerlukan Shamela 4 dipasang di Mac ini dengan kitab 6369 dimuat turun (dibaca secara baca-sahaja melalui shamela-mcp).
- Setiap halaman Shamela = satu مسألة; teks disalin apa adanya (tiada penulisan semula). Nota kaki diletakkan selepas pemisah.
- Sempadan bab/topik diambil terus daripada indeks Shamela (title_id), nombor halaman/jilid daripada printed_page.
- data/fiqh-data.json ada dalam .gitignore: teks kitab (hak cipta) kekal di mesin ini sahaja.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from shamela_client import Shm

BOOK = 6369
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'data', 'fiqh-data.json')
AR = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
LAST_PAGE_ID = 445  # akhir jilid 2 (Haji); jilid 3 dan seterusnya bukan Ibadat

# (key, tajuk, title_id awal, title_id akhir (eksklusif), mod topik)
#   'sib'  = topik ialah nod peringkat-2 dalam julat title_id
#   'child'= topik ialah anak (peringkat-3) bagi nod title_id awal
CHAPTERS = [
    ('taharah', 'الطهارة', 15, 114, 'sib'),
    ('salah', 'الصلاة', 114, 276, 'sib'),
    ('zakah', 'الزكاة', 278, 331, 'child'),
    ('siyam', 'الصيام', 331, 353, 'child'),
    ('hajj', 'الحج والعمرة', 353, 392, 'child'),
]

def parse_toc(text):
    nodes = []
    for l in text.split('\n'):
        m = re.match(r'^(\s*)- \*\*(.+?)\*\* \(title_id=(\d+), page=([٠-٩0-9]+)\)', l)
        if m:
            nodes.append({'depth': len(m[1]) // 2 + 1, 'title': m[2].strip().rstrip(':').rstrip(' -').strip(),
                          'id': int(m[3]), 'page_id': int(m[4].translate(AR))})
    return nodes

def nrm(t):
    """Normalisasi untuk memadankan tajuk fihrist dengan baris dalam teks halaman (tiada tashkil/tanda baca)."""
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t).replace('ة', 'ه').replace('ى', 'ي')
    t = re.sub(r'[^\w\s]|_', ' ', t)
    return ' '.join(t.split())

ORD = r'(?:اولا|ثانيا|ثالثا|رابعا|خامسا|سادسا|سابعا|ثامنا|تاسعا|عاشرا|الاول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|\d+)'
def strip_ord(n):
    """يحذف ترقيم العنوان في أول السطر: «أولاً ـ »، «١ـ »، «ثانيا»."""
    return re.sub(r'^' + ORD + r'\s+', '', n).strip()

def locate(body, title, start_line):
    """(offset aksara, indeks baris) bagi baris tajuk dalam body. Urutan: sama tepat → sama selepas buang nombor tertib →
    awalan → mengandungi (baris pendek sahaja). None jika tiada."""
    lines, pos, tn = body.split('\n'), 0, nrm(title)
    offs = []
    for l in lines: offs.append(pos); pos += len(l) + 1
    if not tn: return None
    tests = [lambda ln: ln == tn,
             lambda ln: strip_ord(ln) == tn,
             lambda ln: ln.startswith(tn) or strip_ord(ln).startswith(tn),
             lambda ln: tn in ln and len(ln) < len(tn) + 30]
    for test in tests:
        for i in range(start_line, len(lines)):
            if test(nrm(lines[i])): return offs[i], i
    return None

def label(pp):
    """'1/ 32' -> (1, '32'); '2/ 5' -> (2, '5')."""
    m = re.match(r'^\s*(\d+)\s*/\s*(\d+)', pp.translate(AR))
    return (int(m[1]), m[2]) if m else (None, pp)

def main():
    s = Shm()
    toc = parse_toc(s.call('shamela_get_toc', book_id=BOOK, depth=5))
    pages, nxt = {}, 1
    while nxt and nxt <= LAST_PAGE_ID:
        sc = s.rpc('tools/call', {'name': 'shamela_get_pages_range',
                   'arguments': {'book_id': BOOK, 'start_page_id': nxt, 'count': 20}})['result'].get('structuredContent') or {}
        for p in sc.get('pages', []): pages[int(p['page_id'])] = p
        nxt = max(pages) + 1 if sc.get('has_more') and pages else 0
    assert len(pages) >= LAST_PAGE_ID - 5, f'halaman tidak lengkap: {len(pages)}'

    d = {'meta': {'schema_version': '1.0', 'primary_book_id': 'b1',
                  'project': 'موسوعة الفقه المنهجي – قسم العبادات',
                  'source': f'المكتبة الشاملة ٤ — الفقه المنهجي على مذهب الإمام الشافعي (id={BOOK}); نص منسوخ كما هو.',
                  'page_note': 'رقم الصفحة = رقم الصفحة المطبوعة كما في الشاملة (يبدأ ترقيم كل مجلد من ١).'},
         'books': [{'book_id': 'b1', 'title': 'الفقه المنهجي على مذهب الإمام الشافعي', 'authors': ['مجموعة من المؤلفين'],
                    'publisher': 'دار القلم للطباعة والنشر والتوزيع', 'year': '١٤٢٩هـ'}],
         'volumes': [{'volume_id': 'v1', 'book_id': 'b1', 'number': 1, 'title': 'الجزء الأول'},
                     {'volume_id': 'v2', 'book_id': 'b1', 'number': 2, 'title': 'الجزء الثاني'}],
         'chapters': [], 'sections': [], 'topics': [], 'issues': [], 'evidences': [], 'references': []}
    empty = []
    d['headings'] = []
    pid2iid = {}
    for ci, (key, ctitle, a, b, mode) in enumerate(CHAPTERS, 1):
        cid = f'c{ci}'
        if mode == 'sib':
            tops = [n for n in toc if n['depth'] == 2 and a <= n['id'] < b]
        else:
            tops = [n for n in toc if n['depth'] == 3 and a < n['id'] < b]
        end_chapter = next(n['page_id'] for n in toc if n['id'] == b) - 1 if any(n['id'] == b for n in toc) else LAST_PAGE_ID
        first = tops[0]['page_id'] if mode == 'sib' else next(n for n in toc if n['id'] == a)['page_id']
        tops[0] = dict(tops[0], page_id=first)  # topik pertama bermula dari halaman tajuk bab
        d['chapters'].append({'chapter_id': cid, 'key': key, 'title': ctitle, 'order': ci,
                              'description': f'كتاب {ctitle} — من الصفحة {label(pages[first]["printed_page"])[1]} من المجلد {label(pages[first]["printed_page"])[0]}.'})
        for ti, t in enumerate(tops):
            lo = t['page_id']
            hi = (tops[ti + 1]['page_id'] - 1) if ti + 1 < len(tops) else end_chapter
            hi = max(hi, lo)  # topik yang bermula di halaman yang sama dengan topik seterusnya
            tid, rid = f't{ci}_{ti + 1}', f'r_t{ci}_{ti + 1}'
            vol_lo, pg_lo = label(pages[lo]['printed_page']); vol_hi, pg_hi = label(pages[hi]['printed_page'])
            d['references'].append({'reference_id': rid, 'book_id': 'b1', 'volume_id': f'v{vol_lo}', 'chapter_title': ctitle,
                                    'section_title': t['title'], 'page': pg_lo if lo == hi else f'{pg_lo}–{pg_hi}',
                                    'shamela_title_id': t['id'], 'source_type': 'book'})
            d['topics'].append({'topic_id': tid, 'chapter_id': cid, 'title': t['title'], 'order': ti + 1,
                                'reference_ids': [rid], 'evidence_ids': [], 'conditions': [], 'arkan': [],
                                'sunan': [], 'makruhat': [], 'mubtilat': []})
            for order, pid in enumerate(range(lo, hi + 1), 1):
                p = pages[pid]; vol, pg = label(p['printed_page'])
                text = p['body'].strip()
                if p.get('foot', '').strip(): text += '\n\n— الحواشي —\n' + p['foot'].strip()
                if not text: empty.append(f'{vol}/{pg}'); continue
                iid, prid = f'v{vol}p{pg}', f'r_v{vol}p{pg}'
                pid2iid[pid] = iid
                if any(i['issue_id'] == iid for i in d['issues'][-3:]): continue
                d['references'].append({'reference_id': prid, 'book_id': 'b1', 'volume_id': f'v{vol}', 'chapter_title': ctitle,
                                        'section_title': t['title'], 'page': pg, 'shamela_page_id': pid, 'source_type': 'book'})
                lead = ' '.join(text.split()[:8])
                d['issues'].append({'issue_id': iid, 'topic_id': tid, 'title': f'{t["title"]} — ص {pg}: {lead}…',
                                    'original_text': text, 'evidence_ids': [], 'reference_ids': [prid], 'related_issue_ids': [],
                                    'volume_id': f'v{vol}', 'page': pg, 'order': order, 'keywords': [ctitle, t['title']]})
            # ---- tajuk kecil (sub-topik, sub-sub-topik) daripada fihrist Shamela, dalam topik ini
            limit = tops[ti + 1]['id'] if ti + 1 < len(tops) else b
            sub = [n for n in toc if t['id'] < n['id'] < limit and n['depth'] > t['depth']]
            stack, last_page, last_line = [], None, 0
            for hi_, n in enumerate(sub, 1):
                while stack and stack[-1][0] >= n['depth']: stack.pop()
                parent = stack[-1][1] if stack else None
                hid = f'h{n["id"]}'
                pgid = n['page_id']
                body = pages[pgid]['body'].strip() if pgid in pages else ''
                if pgid != last_page: last_line = 0
                loc = locate(body, n['title'], last_line)
                if loc: last_line = loc[1]
                off = loc[0] if loc else (d['headings'][-1]['offset'] if d['headings'] and d['headings'][-1]['issue_id'] == pid2iid.get(pgid) else 0)
                vol_n, pg_n = label(pages[pgid]['printed_page']) if pgid in pages else (None, '')
                d['headings'].append({'heading_id': hid, 'topic_id': tid, 'parent_id': parent, 'level': n['depth'] - t['depth'],
                                      'title': n['title'], 'order': hi_, 'shamela_title_id': n['id'],
                                      'issue_id': pid2iid.get(pgid), 'offset': off, 'located': bool(loc),
                                      'volume_id': f'v{vol_n}' if vol_n else None, 'page': pg_n})
                last_page = pgid
                stack.append((n['depth'], hid))
    # kata kunci carian: tajuk kecil yang bermula pada halaman, dan tajuk yang sedang berjalan pada awal halaman
    by_issue = {}
    for h in d['headings']:
        if h['issue_id']: by_issue.setdefault(h['issue_id'], []).append(h)
    for t_ in d['topics']:
        cur = None
        for i in (x for x in d['issues'] if x['topic_id'] == t_['topic_id']):
            hs = by_issue.get(i['issue_id'], [])
            chain = []
            if cur:
                x = cur
                while x: chain.append(x['title']); x = next((y for y in d['headings'] if y['heading_id'] == x['parent_id']), None)
            for h in sorted(hs, key=lambda y: y['offset']): chain.append(h['title'])
            i['keywords'] = list(dict.fromkeys(i['keywords'] + chain))
            if hs: cur = sorted(hs, key=lambda y: y['offset'])[-1]
    # ringkasan bertanggungjawab (data/summaries.json, dihasilkan oleh scripts/check_summaries.py --merge) disimpan jika ada
    sp = os.path.join(os.path.dirname(os.path.abspath(OUT)), 'summaries.json')
    d['summaries'] = json.load(open(sp, encoding='utf-8')).get('summaries', []) if os.path.exists(sp) else []
    qp = os.path.join(os.path.dirname(os.path.abspath(OUT)), 'quizzes.json')  # soalan kuiz (scripts/check_quizzes.py --merge)
    d['quizzes'] = json.load(open(qp, encoding='utf-8')).get('quizzes', []) if os.path.exists(qp) else []
    d['meta']['empty_pages'] = empty
    d['meta']['headings_unlocated'] = [h['heading_id'] for h in d['headings'] if not h['located']]
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ids = [i['issue_id'] for i in d['issues']]
    print(f"headings={len(d['headings'])} unlocated={len(d['meta']['headings_unlocated'])}")
    print(f"chapters={len(d['chapters'])} topics={len(d['topics'])} issues={len(ids)} unique={len(set(ids))} empty={empty}")

if __name__ == '__main__':
    main()
