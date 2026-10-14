// वेबसाइट की स्वचालित जाँच:  node tools/smoke_test.js NN
// index.html को हेडलेस ब्राउज़र में खोलकर सेट NN चुनती है, 100 प्रश्न, खंड, विकल्प, उत्तर-व्याख्या,
// परिणाम पृष्ठ और कंसोल त्रुटियाँ जाँचती है। अंत में "PASS" या "FAIL: कारण" छापती है।
// ब्राउज़र न मिले तो: PW_EXEC=/opt/pw-browsers/chromium node tools/smoke_test.js NN
const path = require('path'), fs = require('fs');
let pw;
for (const m of ['playwright', '/opt/npm-tools/node_modules/playwright', 'playwright-core']) {
  try { pw = require(m); break; } catch (e) {}
}
if (!pw) { console.log('FAIL: playwright नहीं मिला (npm i -g playwright)'); process.exit(2); }

const NO = Number(process.argv[2]);
if (!NO) { console.log('उपयोग: node tools/smoke_test.js NN'); process.exit(2); }
const ROOT = path.join(__dirname, '..');
const fail = (m) => { console.log('FAIL: ' + m); process.exit(1); };

(async () => {
  const opts = { headless: true };
  if (process.env.PW_EXEC) opts.executablePath = process.env.PW_EXEC;
  let browser;
  try { browser = await pw.chromium.launch(opts); }
  catch (e) {
    const guess = '/opt/pw-browsers/chromium';
    try { browser = await pw.chromium.launch({ headless: true, executablePath: fs.existsSync(guess + '/chrome') ? guess + '/chrome' : guess }); }
    catch (e2) { fail('ब्राउज़र शुरू नहीं हुआ: ' + e.message.split('\n')[0]); }
  }
  const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text() + (m.location().url || '')) && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + path.join(ROOT, 'index.html'));
  await page.waitForSelector('.set-card');
  if (errors.length) fail('पेज लोड पर त्रुटि: ' + errors[0]);

  const info = await page.evaluate((no) => {
    const st = (DATA.cg.sets || []).filter(s => s.no === no);
    if (st.length !== 1) return { err: `DATA.cg.sets में सेट ${no} की ${st.length} प्रविष्टियाँ हैं` };
    const s = st[0], secSum = (s.sections || []).reduce((a, x) => a + x[1], 0);
    const bad = s.q.findIndex(q => !(Array.isArray(q[2]) && q[2].length === 4 && q[3] >= 0 && q[3] < 4 && q[1] && q[4] && [0,1,2].includes(q[0])));
    return { n: s.q.length, secSum, bad };
  }, NO);
  if (info.err) fail(info.err);
  if (info.n !== 100) fail(`सेट ${NO} में ${info.n} प्रश्न हैं`);
  if (info.secSum !== 100) fail(`खंडों का योग ${info.secSum} है`);
  if (info.bad >= 0) fail(`प्रश्न ${info.bad + 1} का डेटा अधूरा है`);

  const card = page.locator('.set-card', { has: page.locator('.no', { hasText: new RegExp('^C' + NO + '$') }) });
  if (await card.count() !== 1) fail(`सेट-कार्ड C${NO} नहीं मिला`);
  await card.click();
  const sum = await page.textContent('#summary');
  if (!sum.includes('100')) fail('सारांश में 100 प्रश्न नहीं दिखे');
  await page.click('#start');
  await page.waitForSelector('#exam:not([hidden])');
  const qno = await page.textContent('#qno');
  if (!/1 \/ 100/.test(qno)) fail('पहला प्रश्न "1 / 100" नहीं दिखा: ' + qno);
  if (await page.locator('.choice').count() !== 4) fail('पहले प्रश्न में 4 विकल्प नहीं');
  await page.locator('.choice').first().click();
  if (!(await page.isVisible('#explain'))) fail('अभ्यास मोड में व्याख्या नहीं दिखी');
  if ((await page.locator('.choice.correct').count()) !== 1) fail('सही उत्तर चिह्नित नहीं हुआ');
  const pals = await page.locator('.pal').count();
  if (pals !== 100) fail(`प्रश्न-पैलेट में ${pals} बटन हैं`);
  if ((await page.locator('.pal-h').count()) !== 10) fail('पैलेट में 10 खंड-शीर्षक नहीं');
  await page.locator('.pal').nth(99).click();
  if (!/100 \/ 100/.test(await page.textContent('#qno'))) fail('अंतिम प्रश्न नहीं खुला');
  await page.click('#submit-btn'); await page.click('#cf-yes');
  await page.waitForSelector('#result:not([hidden])');
  const revs = await page.locator('.rev-item').count();
  if (revs !== 100) fail(`परिणाम में ${revs} प्रश्न दिखे`);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) fail('मोबाइल चौड़ाई पर पेज क्षैतिज रूप से बाहर जा रहा है');
  if (errors.length) fail('कंसोल त्रुटि: ' + errors[0]);
  await browser.close();
  console.log(`PASS — सेट ${NO}: 100 प्रश्न, 10 खंड, व्याख्या और परिणाम पृष्ठ ठीक हैं`);
})().catch(e => fail(e.message.split('\n')[0]));
