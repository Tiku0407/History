#!/usr/bin/env python3
"""दोहराव-जाँच: python3 tools/check.py tools/src/setNN.txt

नए सेट के हर प्रश्न का मिलान वेबसाइट (index.html) के सभी प्रश्नों, रिपॉज़िटरी की सभी .docx फ़ाइलों
और tools/lists/*.md सूचियों से करता है। हर FLAG को स्वयं पढ़ें — यह स्क्रिप्ट केवल संकेत देती है;
उसी तथ्य को शब्द बदलकर या उलटकर पूछा गया प्रश्न भी दोहराव है, भले FLAG न आए।

FLAG प्रकार:
  समान-प्रश्न   — प्रश्न-पाठ बहुत मिलता है
  वही-उत्तर     — सही उत्तर वही है और प्रश्न के मुख्य शब्द मिलते हैं (वही तथ्य, नए शब्द)
  उलटा          — नया उत्तर पुराने प्रश्न में है और पुराना उत्तर नए प्रश्न में (तथ्य उलटकर पूछा)
  आंतरिक       — इसी सेट के दो प्रश्न आपस में मिलते हैं
अंत में "FLAG: 0" आना चाहिए, या हर बचे FLAG को पढ़कर पुष्टि करें कि तथ्य अलग है।
"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, LETTERS, parse_src, read_index, norm, words, grams, validate


def corpus(skip_no):
    out = []  # (स्रोत, प्रश्न, सही उत्तर या None)
    _, _, D = read_index()
    for q in D['q']:
        out.append((f'इतिहास बैंक सेट {q[0]}', q[2], q[3][q[4]]))
    for code, p in D.get('pools', {}).items():
        for q in p['q']:
            out.append((f'पूल {code}', q[1], q[2][q[3]]))
    for st in D.get('cg', {}).get('sets', []):
        if st['no'] == skip_no:
            continue
        name = st.get('badge') or f'CG सेट {st["no"]}'
        for k, q in enumerate(st['q'], 1):
            out.append((f'{name} प्र.{k}', q[1], q[2][q[3]]))
    for f in sorted(glob.glob(os.path.join(ROOT, 'tools', 'lists', '*.md'))):
        b = os.path.basename(f)
        if re.fullmatch(r'set0*%d\.md' % skip_no, b):
            continue
        for ln in open(f, encoding='utf-8'):
            m = re.match(r'^(\d+)\.\s+(.*?)\s+→\s+\(([ABCD])\)\s+(.*)$', ln.strip())
            if m:
                out.append((f'{b} प्र.{m.group(1)}', m.group(2), m.group(4)))
    try:
        import docx
        for f in sorted(glob.glob(os.path.join(ROOT, '*.docx'))):
            b = os.path.basename(f)
            if re.search(r'Set_0*%d_' % skip_no, b):
                continue
            for p in docx.Document(f).paragraphs:
                m = re.match(r'^(\d+)[\.\)]\s+(.{12,})$', p.text.strip())
                if m:
                    out.append((f'{b} प्र.{m.group(1)}', m.group(2), None))
    except ImportError:
        print('चेतावनी: python-docx नहीं है — .docx फ़ाइलों से मिलान नहीं हुआ (pip install python-docx)')
    # एक जैसे पाठ हटाएँ (उत्तर वाले को प्राथमिकता)
    seen, uniq = {}, []
    for src, q, a in out:
        k = norm(q)
        if k in seen:
            if a and not uniq[seen[k]][2]:
                uniq[seen[k]] = (src, q, a)
            continue
        seen[k] = len(uniq)
        uniq.append((src, q, a))
    return uniq


def cmp(nq, na, oq, oa, ng, nw):
    og = grams(oq)
    inter = len(ng & og)
    sim = inter / max(1, min(len(ng), len(og)))
    ow = words(oq)
    wo = len(nw & ow)
    wj = wo / max(1, len(nw | ow))
    nan, oan = norm(na), norm(oa) if oa else ''
    reasons = []
    if (sim >= 0.55 and wj >= 0.45) or (sim >= 0.6 and oa and nan == oan) or sim >= 0.9:
        reasons.append(f'समान-प्रश्न {sim:.2f}')
    if oa and nan and nan == oan and len(nan) >= 3 and wo >= 2:
        reasons.append(f'वही-उत्तर (+{wo} शब्द)')
    noq, nnq = norm(oq), norm(nq)
    if len(nan) >= 4 and nan in noq:
        if oa and len(oan) >= 4 and oan in nnq:
            reasons.append('उलटा')
        elif wo >= 3:
            reasons.append(f'उलटा? (नया उत्तर पुराने प्रश्न में, +{wo} शब्द)')
    return reasons, sim


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    m = re.search(r'set0*(\d+)\.txt$', path)
    no = int(m.group(1)) if m else -1
    qs, perr = parse_src(path)
    errs, warns = validate(qs, perr, strict=False)
    for e in errs:
        print('त्रुटि:', e)
    for w in warns:
        print('चेतावनी:', w)
    old = corpus(no)
    print(f'मिलान: {len(qs)} नए प्रश्न × {len(old)} पुराने प्रश्न\n')
    flags = 0
    pre = [(src, oq, oa) for src, oq, oa in old]
    for i, q in enumerate(qs, 1):
        if q['ans'] is None or not all(q['opts']):
            continue
        na = q['opts'][q['ans']]
        ng, nw = grams(q['q']), words(q['q'])
        hits = []
        for src, oq, oa in pre:
            r, sim = cmp(q['q'], na, oq, oa, ng, nw)
            if r:
                hits.append((sim, src, oq, oa, r))
        for j, p in enumerate(qs[:i - 1], 1):
            if p['ans'] is None or not all(p['opts']):
                continue
            r, sim = cmp(q['q'], na, p['q'], p['opts'][p['ans']], ng, nw)
            if r:
                hits.append((sim, f'आंतरिक: इसी सेट का प्र.{j}', p['q'], p['opts'][p['ans']], r))
        if hits:
            hits.sort(key=lambda h: -h[0])
            flags += 1
            print(f'FLAG प्र.{i} (पंक्ति {q["line"]}): {q["q"][:90]}  → ({LETTERS[q["ans"]]}) {na}')
            for sim, src, oq, oa, r in hits[:4]:
                print(f'    ↳ [{", ".join(r)}] {src}: {oq[:90]}' + (f'  → {oa}' if oa else ''))
            if len(hits) > 4:
                print(f'    ↳ … और {len(hits) - 4} मिलान')
    print(f'\nFLAG: {flags}' + ('' if flags else ' — कोई स्वचालित मिलान नहीं (फिर भी तथ्य-स्तर का दोहराव स्वयं जाँचें)'))
    print(f'त्रुटियाँ: {len(errs)}')
    sys.exit(1 if flags or errs else 0)


if __name__ == '__main__':
    main()
