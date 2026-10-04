#!/usr/bin/env python3
"""Semak keterlandasan ringkasan: setiap perkataan bermakna dalam ringkasan mesti wujud dalam nas sumber tajuk/topik itu.

Guna:  python3 scripts/check_summaries.py sections.json out_dir_or_file... [--merge data/summaries.json] [--strict 0.12]
Keluaran: laporan ringkasan gagal (nisbah perkataan tidak ditemui > ambang). --merge menulis hanya yang lulus.
"""
import json, re, sys, os, glob

def nrm(t):
    t = re.sub(r'[ً-ْٰـ]', '', t)
    t = re.sub(r'[أإآٱ]', 'ا', t).replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    return t
def words(t): return re.findall(r'[ء-ي]+', nrm(t))
STOP = set('هذا هذه ذلك تلك التي الذي الذين اللذان في من الي على عن مع او ثم قد لا ما لم لن ان انه انها اذا اذ كل بعض غير هو هي هم هن ذا هناك كما حيث اي ايضا فقط بل لكن كان يكون تكون كانت اما الا انما هنا بين عند عليه عليها فيه فيها منه منها به بها له لها'.split())
PRE = ('وال', 'فال', 'بال', 'كال', 'لل', 'ال', 'و', 'ف', 'ب', 'ل', 'ك', 'س')
SUF = ('هما', 'هم', 'هن', 'ها', 'ان', 'ين', 'ون', 'ات', 'ه', 'ا', 'ي', 'ك', 'ت')
def variants(w):
    out = {w}; cur = [w]
    for p in PRE:
        if w.startswith(p) and len(w) - len(p) >= 2: cur.append(w[len(p):])
    for c in list(cur):
        out.add(c)
        for s in SUF:
            if c.endswith(s) and len(c) - len(s) >= 2: out.add(c[:-len(s)])
    return out
def stems(ws):
    s = set()
    for w in ws: s |= variants(w)
    return s
def score(summary, source):
    src = stems(words(source)); toks = [w for w in words(summary) if len(w) >= 3 and w not in STOP]
    if not toks: return 0.0, []
    miss = [w for w in toks if not (variants(w) & src)]
    return len(miss) / len(toks), miss

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    thr = float(sys.argv[sys.argv.index('--strict') + 1]) if '--strict' in sys.argv else 0.12
    merge = sys.argv[sys.argv.index('--merge') + 1] if '--merge' in sys.argv else None
    if merge and merge in a: a.remove(merge)
    if '--strict' in sys.argv: a = [x for x in a if x != sys.argv[sys.argv.index('--strict') + 1]]
    sec = json.load(open(a[0], encoding='utf-8'))
    files = []
    for p in a[1:]: files += sorted(glob.glob(os.path.join(p, '*.json'))) if os.path.isdir(p) else [p]
    H = {}; T = {}
    for t in sec['topics']:
        T[t['topic_id']] = ' '.join(h['text'] + ' ' + h['notes'] for h in t['heads'])
        for h in t['heads']:
            if h['id']: H[h['id']] = h['text'] + ' ' + h['notes']
    ok, bad, summ = 0, [], []
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        for kind, src, level in (('headings', H, 'heading'), ('topics', T, 'topic')):
            for k, v in d.get(kind, {}).items():
                if k not in src: bad.append((level, k, 'id tidak dikenali', [])); continue
                txt = ' '.join([v.get('ringkas', '')] + v.get('masail', []))
                r, miss = score(txt, src[k])
                limit = thr
                if r > limit or not v.get('ringkas'): bad.append((level, k, round(r, 2), miss[:10])); continue
                ok += 1
                summ.append({'summary_id': f's_{k}', 'level': level, 'target_id': k, 'ringkas': v['ringkas'].strip(),
                             'masail': [m.strip() for m in v.get('masail', []) if m.strip()], 'source': 'ai_from_source', 'ungrounded_ratio': round(r, 3)})
    print(f'lulus={ok} gagal={len(bad)}')
    for b in bad: print('  GAGAL', *b)
    if merge:
        old = json.load(open(merge, encoding='utf-8')) if os.path.exists(merge) else {'summaries': []}
        keep = {s['summary_id']: s for s in old.get('summaries', [])}
        for s in summ: keep[s['summary_id']] = s
        json.dump({'summaries': list(keep.values())}, open(merge, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('digabung ->', merge, len(keep))
    json.dump([{'level': l, 'id': k, 'ratio': r, 'miss': m} for l, k, r, m in bad], open(os.path.join(os.path.dirname(a[0]) or '.', 'failed.json'), 'w', encoding='utf-8'), ensure_ascii=False)
if __name__ == '__main__': main()
