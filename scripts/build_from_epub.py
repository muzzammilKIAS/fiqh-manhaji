#!/usr/bin/env python3
"""Bina data/fiqh-data.json (bahagian Ibadat sahaja) daripada EPUB OCR archive.org (Encycloped405).

Guna:  python3 scripts/build_from_epub.py <fail.epub> [data/fiqh-data.json]

- Setiap halaman EPUB = satu مسألة; teks disalin apa adanya daripada OCR (tiada teks ditulis semula).
- Nombor halaman cetakan = indeks halaman EPUB + 1 (disemak pada banyak halaman: nombor kaki halaman).
- Sempadan bab/topik ialah halaman di mana tajuk itu dikesan dalam teks OCR (anggaran ±1 halaman).
"""
import html, json, re, sys, zipfile

EPUB, OUT = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else 'data/fiqh-data.json')

# (key, tajuk bab, halaman EPUB awal, akhir, [(halaman EPUB awal topik, tajuk topik)])
CHAPTERS = [
  ('taharah', 'الطهارة', 26, 96, [
    (26, 'معنى الطهارة وأهميتها'), (30, 'أقسام المياه'), (35, 'الأواني'), (44, 'الاستنجاء وآدابه'),
    (52, 'الوضوء'), (65, 'المسح على الخفين'), (67, 'الجبائر والعصائب'), (71, 'الغسل وأحكامه'),
    (72, 'الجنابة'), (78, 'الحيض'), (81, 'الولادة'), (83, 'الغسل المندوب'), (91, 'التيمم')]),
  ('salah', 'الصلاة', 98, 266, [
    (98, 'معنى الصلاة ومشروعيتها'), (113, 'الأذان والإقامة'), (124, 'شروط صحة الصلاة'), (156, 'أركان الصلاة'),
    (171, 'سجود السهو'), (175, 'سجدات التلاوة'), (177, 'صلاة الجماعة'), (184, 'صلاة المسافر'),
    (192, 'صلاة الخوف'), (199, 'صلاة الجمعة'), (212, 'صلاة النفل'), (223, 'صلاة العيدين'),
    (228, 'زكاة الفطر'), (232, 'الأضحية'), (237, 'صلاة التراويح'), (240, 'صلاة الخسوف والكسوف'),
    (245, 'صلاة الاستسقاء'), (247, 'الجنائز')]),
  ('zakah', 'الزكاة', 268, 329, [
    (268, 'تمهيد ومشروعية الزكاة'), (291, 'زكاة النقدين'), (293, 'زكاة الأنعام'),
    (298, 'زكاة الزروع والثمار'), (305, 'زكاة المعدن والركاز وما بعدها')]),
  ('siyam', 'الصيام', 330, 366, [
    (330, 'الصيام وأحكامه'), (354, 'صوم التطوع'), (358, 'الصوم المكروه والصوم المحرم'), (363, 'الاعتكاف')]),
  ('hajj', 'الحج والعمرة', 368, 443, [
    (368, 'الحج والعمرة: تعريفهما وحكمهما'), (382, 'شروط الحج'), (384, 'المواقيت والإحرام'),
    (394, 'أعمال الحج وما يتعلق بها')]),
]
SKIP = {367: 'صفحة فاصلة لم تُقرأ (دقة OCR 0%)'}

def page_texts(path):
    z, out = zipfile.ZipFile(path), {}
    for n in z.namelist():
        m = re.search(r'page_(\d+)\.html$', n)
        if not m: continue
        body = z.read(n).decode('utf-8')
        body = re.search(r'<body[^>]*>(.*)</body>', body, re.S).group(1)
        t = html.unescape(re.sub(r'<[^>]+>', ' ', body))
        out[int(m.group(1))] = re.sub(r'\s+', ' ', t).strip()
    return out

DIG = r'[0-9٠-٩۰-۹‏]'
def clean(t):
    t = re.sub(r'[A-Za-z][A-Za-z()|\s]{5,}', ' ', t)          # sisa hiasan bingkai yang dibaca OCR sebagai huruf Latin
    t = re.sub(r'\s*' + DIG + r'{1,4}\s*$', '', t)             # nombor kaki halaman
    return re.sub(r'\s+', ' ', t).strip()

def main():
    P = page_texts(EPUB)
    d = {'meta': {'schema_version': '1.0', 'primary_book_id': 'b1',
                  'project': 'موسوعة الفقه المنهجي – قسم العبادات',
                  'source': 'نص مستخرج آليًا (OCR) من نسخة archive.org: Encycloped405 — قد يحتوي أخطاء تعرّف ضوئي؛ راجع صورة الصفحة عند الاقتباس.',
                  'page_note': 'رقم الصفحة = رقم صفحة الطبعة المطبوعة (الثالثة عشرة، دار القلم 2012).'},
         'books': [{'book_id': 'b1', 'title': 'الفقه المنهجي على مذهب الإمام الشافعي',
                    'authors': ['د. مصطفى الخن', 'د. مصطفى البغا', 'علي الشربجي'],
                    'publisher': 'دار القلم – دمشق؛ الدار الشامية – بيروت', 'edition': 'الطبعة الثالثة عشرة',
                    'year': '2012', 'source_url': 'https://archive.org/details/Encycloped405'}],
         'volumes': [{'volume_id': 'v1', 'book_id': 'b1', 'number': 1, 'title': 'المجلد الأول'}],
         'chapters': [], 'sections': [], 'topics': [], 'issues': [], 'evidences': [], 'references': []}
    missing = []
    for ci, (key, ctitle, a, b, topics) in enumerate(CHAPTERS, 1):
        cid = f'c{ci}'
        d['chapters'].append({'chapter_id': cid, 'key': key, 'title': ctitle, 'order': ci,
                              'description': f'كتاب {ctitle} — الصفحات {a + 1}–{b + 1} من المجلد الأول.'})
        for ti, (start, ttitle) in enumerate(topics):
            end = topics[ti + 1][0] - 1 if ti + 1 < len(topics) else b
            tid = f't{ci}_{ti + 1}'
            rid = f'r_{tid}'
            d['references'].append({'reference_id': rid, 'book_id': 'b1', 'volume_id': 'v1', 'chapter_title': ctitle,
                                    'section_title': ttitle, 'page': f'{start + 1}–{end + 1}',
                                    'url': 'https://archive.org/details/Encycloped405', 'source_type': 'book'})
            d['topics'].append({'topic_id': tid, 'chapter_id': cid, 'title': ttitle, 'order': ti + 1,
                                'reference_ids': [rid], 'evidence_ids': [], 'conditions': [], 'arkan': [],
                                'sunan': [], 'makruhat': [], 'mubtilat': []})
            for order, n in enumerate(range(start, end + 1), 1):
                if n in SKIP or n not in P:
                    missing.append(n + 1); continue
                text = clean(P[n])
                if len(text) < 40:
                    missing.append(n + 1); continue
                pg = str(n + 1)
                prid = f'r_p{pg}'
                d['references'].append({'reference_id': prid, 'book_id': 'b1', 'volume_id': 'v1', 'chapter_title': ctitle,
                                        'section_title': ttitle, 'page': pg,
                                        'url': f'https://archive.org/details/Encycloped405/page/n{n}',
                                        'source_type': 'book'})
                lead = ' '.join(text.split()[:8])
                d['issues'].append({'issue_id': f'p{pg}', 'topic_id': tid, 'title': f'{ttitle} — ص {pg}: {lead}…',
                                    'original_text': text, 'evidence_ids': [], 'reference_ids': [prid],
                                    'related_issue_ids': [], 'volume_id': 'v1', 'page': pg, 'order': order,
                                    'keywords': [ctitle, ttitle], 'notes': 'نص OCR آلي — قد يحتوي أخطاء في الحروف.'})
    d['meta']['missing_pages'] = sorted(set(missing))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"chapters={len(d['chapters'])} topics={len(d['topics'])} issues={len(d['issues'])} missing={d['meta']['missing_pages']}")

if __name__ == '__main__':
    main()
