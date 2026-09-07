// Real Chromium smoke/regression test. No npm packages or real GitHub mutations.
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createServer } from 'node:http';
import assert from 'node:assert/strict';

const root = resolve(import.meta.dirname, '..');
const server = createServer(async (req, res) => {
  try {
    const file = resolve(root, '.' + new URL(req.url, 'http://localhost').pathname);
    if (!file.startsWith(root + '/')) throw Error('outside root');
    res.setHeader('Content-Type', file.endsWith('.html') ? 'text/html' : file.endsWith('.js') ? 'text/javascript' : 'application/json');
    res.end(await readFile(file));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const profile = await mkdtemp(join(tmpdir(), 'sentinel-browser-'));
const chrome = spawn(process.env.CHROMIUM || 'chromium', ['--headless', '--disable-gpu', '--no-sandbox', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
let ws;
try {
  const endpoint = await new Promise((resolve, reject) => {
    let log = '';
    const timeout = setTimeout(() => reject(Error('Chromium startup timeout: ' + log.slice(-1000))), 15000);
    chrome.on('error', reject);
    chrome.stderr.on('data', data => {
      log += data;
      const match = log.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timeout); resolve(match[1]); }
    });
  });
  const targets = await fetch(endpoint.replace('ws:', 'http:').replace(/\/devtools\/.*/, '/json')).then(r => r.json());
  ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', ({ data }) => {
    const msg = JSON.parse(data);
    if (pending.has(msg.id)) {
      const { resolve, reject, timer } = pending.get(msg.id);
      clearTimeout(timer); pending.delete(msg.id);
      msg.error ? reject(Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  });
  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const key = ++id;
      const timer = setTimeout(() => { pending.delete(key); reject(Error('CDP timeout: ' + method)); }, 20000);
      pending.set(key, { resolve, reject, timer });
      ws.send(JSON.stringify({ id: key, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  await send('Page.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `
    localStorage.setItem('sentinel_pat', 'legacy-test-token');
    localStorage.setItem('sentinel_repo', 'legacy/target');
    window.__apiCalls = [];
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (url, options) => {
      if (String(url).startsWith('https://api.github.com/')) {
        window.__apiCalls.push({url, options});
        throw new Error('The dashboard must not call the GitHub API');
      }
      return originalFetch(url, options);
    };
  ` });
  await send('Page.navigate', { url: process.env.SENTINEL_URL || `http://127.0.0.1:${server.address().port}/docs/index.html` });
  await evaluate(`new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      if (typeof localeData !== 'undefined' && localeData.app_title && typeof radarData !== 'undefined' && radarData && typeof site !== 'undefined' && site) { clearInterval(timer); resolve(true); }
      if (Date.now() - started > 15000) {clearInterval(timer); reject(Error('App failed to load'));}
    }, 50);
  })`);
  const locales = ['en', 'zh', 'hi', 'es', 'fr', 'ar', 'bn', 'pt', 'ru', 'ur'];
  const keys = Object.keys(JSON.parse(await readFile(join(root, 'docs/locales/en.json')))).sort();
  for (const lang of locales) {
    const dictionary = JSON.parse(await readFile(join(root, `docs/locales/${lang}.json`)));
    assert.deepEqual(Object.keys(dictionary).sort(), keys);
    assert.ok(Object.values(dictionary).every(x => typeof x === 'string' && x.length));
    const state = await evaluate(`(async () => {await loadLocale('${lang}'); return {lang: document.documentElement.lang, dir: document.documentElement.dir, button: document.getElementById('btn-refresh-text').textContent, next: document.getElementById('btn-guide-next').textContent};})()`);
    assert.equal(state.lang, lang);
    assert.equal(state.dir, ['ar', 'ur'].includes(lang) ? 'rtl' : 'ltr');
    assert.equal(state.button, dictionary.btn_refresh);
    assert.equal(state.next, dictionary.next_btn);
  }
  assert.equal(await evaluate(`(async () => {await loadLocale('../../invalid'); return document.documentElement.lang;})()`), 'en');
  const theme = await evaluate(`(() => {const before = document.documentElement.classList.contains('dark'); document.getElementById('theme-toggle').click(); return {changed: before !== document.documentElement.classList.contains('dark'), saved: localStorage.getItem('sentinel_theme')};})()`);
  assert.ok(theme.changed); assert.ok(['dark', 'light'].includes(theme.saved));
  assert.deepEqual(await evaluate(`({token:localStorage.getItem('sentinel_pat'), repo:localStorage.getItem('sentinel_repo'), input:!!document.getElementById('input-token')})`), {token:null,repo:null,input:false});
  await evaluate(`document.getElementById('btn-open-settings').click()`);
  assert.equal(await evaluate(`document.getElementById('modal-settings').open`), true);
  assert.equal(await evaluate(`document.getElementById('guide-progress').textContent`), '1 / 3');
  await evaluate(`document.getElementById('btn-guide-next').click()`);
  assert.equal(await evaluate(`document.getElementById('guide-progress').textContent`), '2 / 3');
  assert.match(await evaluate(`document.getElementById('guide-action').href`), /github\.com\/iberi22\/github-sentinel-radar\/settings\/pages$/);
  await evaluate(`document.getElementById('btn-guide-back').click(); document.getElementById('btn-guide-next').click(); document.getElementById('btn-guide-next').click()`);
  assert.equal(await evaluate(`document.getElementById('guide-progress').textContent`), '3 / 3');
  assert.match(await evaluate(`document.getElementById('guide-action').href`), /actions\/workflows\/radar\.yml$/);
  await evaluate(`document.getElementById('btn-guide-next').click()`);
  assert.equal(await evaluate(`document.getElementById('modal-settings').open`), false);
  const fork = await evaluate(`(async () => {
    const original = window.fetch;
    window.fetch = async () => new Response(JSON.stringify({repository:'example/my-radar',default_branch:'dev/next'}));
    await loadSite(); window.fetch = original;
    return {url:document.getElementById('btn-dispatch-radar').href, repo:document.getElementById('guide-repository').textContent, help:document.getElementById('btn-sentinel-setup').href};
  })()`);
  assert.equal(fork.url, 'https://github.com/example/my-radar/actions/workflows/radar.yml');
  assert.equal(fork.repo, 'example/my-radar');
  assert.ok(fork.help.includes('dev%2Fnext'));
  await evaluate(`loadSite()`);
  await evaluate(`document.getElementById('btn-dispatch-radar').addEventListener('click', e => e.preventDefault()); document.getElementById('btn-dispatch-radar').click();`);
  assert.equal(await evaluate(`!!pendingRefresh && !!sessionStorage.getItem('sentinel_refresh')`), true);
  assert.equal(await evaluate(`document.getElementById('feed-status').textContent`), JSON.parse(await readFile(join(root,'docs/locales/en.json'))).waiting_feed);
  // An unchanged feed must not be called an updated feed.
  await evaluate(`checkFeedUpdate()`);
  assert.equal(await evaluate(`!!pendingRefresh`), true);
  // Visibility suspends polling; returning checks again.
  await evaluate(`Object.defineProperty(document, 'hidden', {configurable:true,value:true}); document.dispatchEvent(new Event('visibilitychange'));`);
  assert.equal(await evaluate(`refreshTimer`), null);
  await evaluate(`delete document.hidden;`);
  const received = await evaluate(`(async () => {
    const original = window.fetch;
    window.fetch = async () => new Response(JSON.stringify({last_updated:'2099-01-01T00:00:00Z',profile_dna:{},releases:[],discoveries:[]}));
    await checkFeedUpdate(); window.fetch = original;
    return {pending:pendingRefresh, timestamp:radarData.last_updated, persisted:sessionStorage.getItem('sentinel_refresh')};
  })()`);
  assert.deepEqual(received, {pending:null,timestamp:'2099-01-01T00:00:00Z',persisted:null});
  await evaluate(`document.getElementById('btn-dispatch-radar').click(); pendingRefresh.until = Date.now()-1; checkFeedUpdate();`);
  assert.equal(await evaluate(`pendingRefresh`), null);
  assert.equal(await evaluate(`document.getElementById('feed-status').textContent`), JSON.parse(await readFile(join(root,'docs/locales/en.json'))).wait_finished);
  assert.equal(await evaluate(`window.__apiCalls.length`), 0);
  await evaluate(`(async () => {
    const original = window.fetch;
    window.fetch = async () => new Response('', {status:503});
    await fetchLocalData(); window.fetch = original;
  })()`);
  assert.equal(await evaluate(`document.getElementById('feed-status').textContent`), JSON.parse(await readFile(join(root,'docs/locales/en.json'))).load_error);
  await send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate(`loadLocale('es')`);
  await evaluate(`document.getElementById('btn-open-settings').click()`);
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= window.innerWidth`), true);
  await evaluate(`document.getElementById('btn-close-modal').click()`);
  await send('Emulation.clearDeviceMetricsOverride');

  const injection = await evaluate(`(() => {
    radarData = {profile_dna:{top_languages:['<img src=x onerror="window.pwned=1">']}, releases:[{repo:'bad', html_url:'javascript:alert(1)', tag_name:'<script>bad<\/script>',body_snippet:'<img src=x onerror="window.pwned=1">',published_at:'2026-01-01'}]};
    renderRadar();
    verifiedData = {projects:[{name:'<img src=x>',description:'<svg onload=alert(1)>',stack:['<img>'],owner:'<img>',pages_url:'javascript:alert(1)',repo_url:'https://github.com/a/b'}]}; renderDirectory();
    return {images:document.querySelectorAll('#releases-list img, #dna-languages img, #projects-grid img, #projects-grid svg').length, badLinks:document.querySelectorAll('a[href^="javascript:"]').length};
  })()`);
  assert.deepEqual(injection, {images:0,badLinks:0});
  await evaluate(`new Promise(r => setTimeout(r, 400))`);
  const style = await evaluate(`({background:getComputedStyle(document.body).backgroundColor, border:getComputedStyle(document.getElementById('btn-dispatch-radar')).borderTopWidth})`);
  assert.equal(style.border, '0px');
  assert.ok(['rgb(9, 10, 15)', 'rgb(248, 249, 250)'].includes(style.background), 'Tailwind theme styles loaded');
  console.log('PASS: 10 locales/RTL, theme, token migration, wizard, fork metadata, GitHub navigation without API calls, bounded refresh, hidden-tab pause, XSS, borderless.', style);
} finally {
  ws?.close();
  chrome.kill('SIGTERM');
  await new Promise(r => chrome.exitCode !== null ? r() : chrome.once('exit', r));
  server.close();
  await rm(profile, {recursive:true, force:true, maxRetries:5, retryDelay:200});
}
