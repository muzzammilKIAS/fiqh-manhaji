#!/usr/bin/env python3
"""Semak soalan kuiz: petikan (quote) mesti salinan tepat daripada nas tajuk/topik; soalan + jawapan betul + penjelasan
mesti berlandaskan nas (perkataan tidak ditemui <= ambang); 4 pilihan berbeza; satu jawapan.

Guna:  python3 scripts/check_quizzes.py sections.json out_dir_or_files... [--strict 0.15] [--merge data/quizzes.json]
"""
import json, re, sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from check_summaries import score, nrm

FRAME = set('بحسب النص الكتاب الحديث ماذا يفعل يفعله لماذا كيف متي متى مما يلي ليس اي أي حكم الحكم حكمه حكمها وفق ذكره ذكر قرره نقله اورده أورده هل فهل رجل امراه امرأة شخص حالته حاله حالها الصحيح صحيح العباره العبارة الاتي الآتي التاليه التالية يعتبر تعتبر الكتاب السوال السؤال عبارة الحالة الحاله'.split())

def flat(t):  # untuk padanan petikan: tanpa tashkil, ruang dinormalkan
    return ' '.join(nrm(t).split())

def main():
    args = sys.argv[1:]
    thr = float(args[args.index('--strict') + 1]) if '--strict' in args else 0.15
    merge = args[args.index('--merge') + 1] if '--merge' in args else None
    skip = {x for i, x in enumerate(args) if i > 0 and args[i - 1] in ('--strict', '--merge')}
    pos = [a for a in args if not a.startswith('--') and a not in skip]
    sec = json.load(open(pos[0], encoding='utf-8'))
    files = []
    for p in pos[1:]: files += sorted(glob.glob(os.path.join(p, '*.json'))) if os.path.isdir(p) else [p]
    H, T, PRE = {}, {}, {}
    for t in sec['topics']:
        T[t['topic_id']] = '\n'.join(h['text'] + '\n' + h['notes'] for h in t['heads'])
        for h in t['heads']:
            if h['id']: H[h['id']] = (t['topic_id'], h['text'] + '\n' + h['notes'])
            else: PRE[t['topic_id']] = h['text'] + '\n' + h['notes']
    ok, bad, out = 0, [], []
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        for tid, qs in d.items():
            if tid not in T: bad.append((tid, '-', 'topik tidak dikenali')); continue
            for n, q in enumerate(qs, 1):
                why = []
                opts = [str(o).strip() for o in q.get('options', [])]
                a = q.get('answer')
                if len(opts) != 4 or len(set(flat(o) for o in opts)) != 4 or not all(opts): why.append('pilihan')
                if not isinstance(a, int) or not 0 <= a <= 3: why.append('jawapan')
                hid = q.get('heading_id') or None
                if hid and (hid not in H or H[hid][0] != tid): hid = None
                src = H[hid][1] if hid else PRE.get(tid, '')
                quote = str(q.get('quote', '')).strip().strip('«»"')
                if not (25 <= len(quote) <= 320): why.append('panjang petikan')
                elif flat(quote) not in flat(src):
                    if flat(quote) in flat(T[tid]): hid = None  # petikan sah dalam topik walaupun tajuk salah
                    else: why.append('petikan bukan salinan tepat')
                if not why:
                    # الجواب الصحيح والشرح: صارم. نص السؤال: تُهمل ألفاظ صياغة السؤال (بحسب النص، فماذا يفعل، مما يلي ليس...)
                    r, miss = score(' '.join([opts[a], q.get('explain', '')]), T[tid])
                    stem = ' '.join(w for w in re.findall(r'[\u0621-\u064A]+', nrm(q.get('q', ''))) if re.sub(r'^[وف]', '', w) not in FRAME)
                    r2, miss2 = score(stem, T[tid])
                    if r > thr: why.append(f'جواب/شرح غير مسند {r:.2f} {miss[:6]}')
                    elif r2 > 0.5 and len(miss2) >= 3: why.append(f'سؤال غير مسند {r2:.2f} {miss2[:6]}')
                if why: bad.append((tid, n, '; '.join(why))); continue
                ok += 1
                if hid is None:  # cari tajuk yang memuatkan petikan
                    hid = next((k for k, (tt, s) in H.items() if tt == tid and flat(quote) in flat(s)), None)
                out.append({'quiz_id': f'q_{tid}_{n}', 'topic_id': tid, 'heading_id': hid, 'q': q['q'].strip(), 'options': opts, 'answer': a,
                            'explain': q.get('explain', '').strip(), 'quote': quote, 'difficulty': 'medium', 'source': 'ai_from_source', 'ungrounded_ratio': round(r, 3)})
    print(f'lulus={ok} gagal={len(bad)}')
    for b in bad: print('  GAGAL', *b)
    if merge:
        old = json.load(open(merge, encoding='utf-8')) if os.path.exists(merge) else {'quizzes': []}
        keep = {x['quiz_id']: x for x in old.get('quizzes', [])}
        for x in out: keep[x['quiz_id']] = x
        json.dump({'quizzes': sorted(keep.values(), key=lambda x: (x['topic_id'], int(x['quiz_id'].rsplit('_', 1)[1])))}, open(merge, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('digabung ->', merge, len(keep))
if __name__ == '__main__': main()
