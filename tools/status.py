#!/usr/bin/env python3
"""आज का सेट देय है या नहीं: python3 tools/status.py

आज की तारीख भारतीय समय (IST) में ली जाती है। tools/log.json और index.html से अंतिम सेट देखा जाता है।
अंतिम पंक्ति:  DUE NN "<तारीख>"   — आज का सेट देय है; NN अगला सेट-क्रमांक है
            NOT_DUE NN           — आज का सेट (NN) पहले से बन चुका है; कुछ न करें
"""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, read_index

HI = ['जनवरी', 'फ़रवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर']

today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).date()
today_hi = f'{today.day} {HI[today.month - 1]} {today.year}'
lp = os.path.join(ROOT, 'tools', 'log.json')
log = json.load(open(lp, encoding='utf-8')) if os.path.exists(lp) else {}
_, _, D = read_index()
site = sorted(s['no'] for s in D['cg']['sets'] if s['no'] < 100)
last = max(site + [int(k) for k in log])
print(f'आज (IST): {today_hi} ({today.isoformat()})')
print(f'वेबसाइट पर अंतिम CG सेट: {site[-1]}' + (f' · लॉग में अंतिम: {max(map(int, log))} ({log[max(log, key=int)]["date_hi"]})' if log else ''))
done = [k for k, v in log.items() if v.get('date') == today.isoformat()]
if done:
    print(f'NOT_DUE {done[0]}')
else:
    print(f'DUE {last + 1} "{today_hi}"')
