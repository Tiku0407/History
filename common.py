"""साझा सहायक: index.html का DATA पढ़ना/लिखना, setNN.txt पार्स करना, पाठ सामान्यीकरण।"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
PREFIX = 'const DATA = '

SECTIONS = [
    ["प्राचीन भारतीय इतिहास", 15],
    ["मध्यकालीन भारत", 15],
    ["आधुनिक भारत का इतिहास", 20],
    ["यूरोपीय इतिहास", 10],
    ["शैक्षिक मनोविज्ञान, आकलन एवं मूल्यांकन, शिक्षणशास्त्र, शैक्षिक अभिवृत्ति", 15],
    ["सामान्य हिंदी", 5],
    ["General English", 5],
    ["सामान्य मानसिक योग्यता", 5],
    ["कंप्यूटर शिक्षा", 5],
    ["सामान्य ज्ञान", 5],
]
LETTERS = 'ABCD'
DIFF = {'E': 0, 'M': 1, 'H': 2}
DIFF_NAME = {'E': 'सरल', 'M': 'मध्यम', 'H': 'कठिन'}
MONTHS = {'जनवरी': (1, 'Jan'), 'फ़रवरी': (2, 'Feb'), 'फरवरी': (2, 'Feb'), 'मार्च': (3, 'Mar'),
          'अप्रैल': (4, 'Apr'), 'मई': (5, 'May'), 'जून': (6, 'Jun'), 'जुलाई': (7, 'Jul'),
          'अगस्त': (8, 'Aug'), 'सितंबर': (9, 'Sep'), 'सितम्बर': (9, 'Sep'), 'अक्टूबर': (10, 'Oct'),
          'अक्तूबर': (10, 'Oct'), 'नवंबर': (11, 'Nov'), 'नवम्बर': (11, 'Nov'), 'दिसंबर': (12, 'Dec'),
          'दिसम्बर': (12, 'Dec')}


def read_index():
    lines = open(INDEX, encoding='utf-8').read().split('\n')
    for i, ln in enumerate(lines):
        if ln.startswith(PREFIX):
            return lines, i, json.loads(ln[len(PREFIX):].rstrip().rstrip(';'))
    raise SystemExit('index.html में "const DATA = " पंक्ति नहीं मिली')


def write_index(lines, i, data):
    lines[i] = PREFIX + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';'
    open(INDEX, 'w', encoding='utf-8').write('\n'.join(lines))


def parse_src(path):
    """setNN.txt पार्स करें। प्रारूप tools/DAILY_SET.md में है।"""
    qs, sec, cur, field = [], None, None, None
    errors = []

    def close():
        nonlocal cur
        if cur:
            qs.append(cur)
        cur = None

    for n, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.rstrip('\n').rstrip()
        s = line.strip()
        if s.startswith('#') and not s.startswith('#!'):
            continue
        if s.startswith('@sec'):
            close()
            sec = s[4:].split('|')[0].strip()
            continue
        if not s:
            continue
        m = re.match(r'^(Q|प्र)\s*[:：]\s*(.*)$', s)
        if m:
            close()
            cur = {'sec': sec, 'q': m.group(2), 'opts': [None] * 4, 'ans': None, 'diff': None, 'exp': '', 'line': n}
            field = 'q'
            continue
        if cur is None:
            errors.append(f'पंक्ति {n}: प्रश्न (Q:) से पहले पाठ — {s[:40]}')
            continue
        m = re.match(r'^\(?([ABCD])[\)\.]\s*(.*)$', s)
        if m and field in ('q', 'opt'):
            cur['opts'][LETTERS.index(m.group(1))] = m.group(2).strip()
            field = 'opt'
            continue
        m = re.match(r'^ANS\s*[:：]\s*([ABCD])\s*$', s)
        if m:
            cur['ans'] = LETTERS.index(m.group(1)); field = None; continue
        m = re.match(r'^DIFF\s*[:：]\s*([ESMH])\s*$', s)
        if m:
            cur['diff'] = m.group(1).replace('S', 'E'); field = None; continue
        m = re.match(r'^EXP\s*[:：]\s*(.*)$', s)
        if m:
            cur['exp'] = m.group(1).strip(); field = 'exp'; continue
        if field == 'q':
            cur['q'] += '\n' + s
        elif field == 'exp':
            cur['exp'] += ' ' + s
        else:
            errors.append(f'पंक्ति {n}: अपरिचित पंक्ति — {s[:50]}')
    close()
    return qs, errors


def validate(qs, errors=None, strict=True):
    """त्रुटियाँ (errors) और चेतावनियाँ (warns) लौटाता है।"""
    errs = list(errors or [])
    warns = []
    if len(qs) != 100:
        errs.append(f'कुल प्रश्न {len(qs)} हैं, 100 होने चाहिए')
    names = [s for s, _ in SECTIONS]
    for i, q in enumerate(qs, 1):
        tag = f'प्रश्न {i} (पंक्ति {q["line"]})'
        if q['sec'] not in names:
            errs.append(f'{tag}: अज्ञात खंड "{q["sec"]}"')
        if any(o is None or not o for o in q['opts']):
            errs.append(f'{tag}: चारों विकल्प (A–D) नहीं हैं')
        elif len({norm(o) for o in q['opts']}) < 4:
            errs.append(f'{tag}: दो विकल्प एक जैसे हैं')
        if q['ans'] is None:
            errs.append(f'{tag}: ANS नहीं है')
        if q['diff'] is None:
            errs.append(f'{tag}: DIFF नहीं है')
        if not q['exp']:
            errs.append(f'{tag}: EXP (व्याख्या) नहीं है')
        if q['opts'][0] and q['ans'] is not None and all(q['opts']):
            lens = [len(o) for o in q['opts']]
            c = lens[q['ans']]
            others = sorted(l for k, l in enumerate(lens) if k != q['ans'])
            if c > 1.6 * others[-1] and c - others[-1] > 12:
                warns.append(f'{tag}: सही विकल्प बाकी सबसे बहुत लंबा है — लंबाई से पहचाना जा सकता है')
        low = ' '.join(q['opts']) if all(q['opts']) else ''
        if re.search(r'उपर्युक्त सभी|इनमें से कोई नहीं|All of the above|None of the above', low):
            warns.append(f'{tag}: "उपर्युक्त सभी/इनमें से कोई नहीं" विकल्प — सुनिश्चित करें कि केवल एक उत्तर सही है')
    # खंड क्रम और गिनती
    order = []
    for q in qs:
        if not order or order[-1][0] != q['sec']:
            order.append([q['sec'], 0])
        order[-1][1] += 1
    if order != [list(x) for x in SECTIONS]:
        errs.append('खंड-क्रम/गिनती गलत: ' + ', '.join(f'{a} {b}' for a, b in order) +
                    ' — अपेक्षित 15/15/20/10/15/5/5/5/5/5 इसी क्रम में')
    # उत्तर वितरण
    if all(q['ans'] is not None for q in qs) and qs:
        cnt = [sum(1 for q in qs if q['ans'] == k) for k in range(4)]
        if strict and (min(cnt) < 22 or max(cnt) > 28):
            errs.append('उत्तर-वितरण असंतुलित (A/B/C/D = %s) — प्रत्येक 22–28 रखें' % '/'.join(map(str, cnt)))
        run = 1
        for a, b in zip(qs, qs[1:]):
            run = run + 1 if a['ans'] == b['ans'] else 1
            if run > 3:
                errs.append(f'लगातार 4 या अधिक प्रश्नों का एक ही उत्तर ({LETTERS[b["ans"]]}) — क्रम बदलें (पंक्ति {b["line"]})')
                break
    if all(q['diff'] for q in qs) and qs:
        d = {k: sum(1 for q in qs if q['diff'] == k) for k in 'EMH'}
        if abs(d['E'] - 30) > 5 or abs(d['M'] - 50) > 5 or abs(d['H'] - 20) > 5:
            warns.append('कठिनाई %d/%d/%d है — लक्ष्य लगभग 30/50/20' % (d['E'], d['M'], d['H']))
    return errs, warns


_NUKTA = str.maketrans({'़': None})


def norm(s):
    s = unicodedata.normalize('NFC', s or '').lower()
    s = s.translate(_NUKTA)
    s = s.replace('ँ', 'ं').replace('ॉ', 'ा')
    s = re.sub(r'[\s\-–—_.,;:!?\'"‘’“”()\[\]{}।|/\\…]+', '', s)
    return s


STOP = set('का की के को में से है हैं था थे थी और या एवं तथा किस किसे किसने कौन कौनसा कौनसी कौनसे क्या कब कहाँ कहां '
           'किसको किसका किसकी किसके किन किया गया गई गए होता होती होते हुआ हुई हुए द्वारा लिए यह वह इस उस ने पर भी '
           'नहीं जो जिस जिसे जिसमें जिसकी जिसके एक प्रथम पहला पहली सबसे कहा जाता जाती जाते नाम सही गलत कथन '
           'निम्नलिखित निम्न विकल्प चुनिए चुनें बताइए किन्हीं इनमें उपर्युक्त सभी कोई ई ईपू शताब्दी वर्ष the of a an is '
           'to in and which who what was were by for on'.split())


def words(s):
    s = unicodedata.normalize('NFC', s or '').lower().translate(_NUKTA)
    toks = re.findall(r'[\wऀ-ॿ]+', s)
    return {t for t in toks if t not in STOP and len(t) > 1 and not t.isdigit()}


def grams(s, n=3):
    s = norm(s)
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def hindi_date(text):
    """'15 अक्टूबर 2026' → (iso, '15_Oct_2026')"""
    m = re.match(r'^\s*(\d{1,2})\s+(\S+)\s+(\d{4})\s*$', text)
    if not m or m.group(2) not in MONTHS:
        raise SystemExit(f'तारीख "{text}" समझ नहीं आई — उदाहरण: "15 अक्टूबर 2026"')
    d, (mo, en), y = int(m.group(1)), MONTHS[m.group(2)], int(m.group(3))
    return f'{y:04d}-{mo:02d}-{d:02d}', f'{d:02d}_{en}_{y}'
