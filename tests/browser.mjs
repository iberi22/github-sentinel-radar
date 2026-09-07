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
    window.__dispatches = [];
    window.__status = 204;
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (url, options) => {
      if (String(url).startsWith('https://api.github.com/')) {
        window.__dispatches.push({url, options});
        if (window.__status === 0) throw new TypeError('simulated network error');
        return new Response(null, {status: window.__status});
      }
      return originalFetch(url, options);
    };
  ` });
  await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/docs/index.html` });
  await evaluate(`new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      if (typeof localeData !== 'undefined' && localeData.app_title && typeof radarData !== 'undefined' && radarData) { clearInterval(timer); resolve(true); }
      if (Date.now() - started > 15000) {clearInterval(timer); reject(Error('App failed to load'));}
    }, 50);
  })`);
  const locales = ['en', 'zh', 'hi', 'es', 'fr', 'ar', 'bn', 'pt', 'ru', 'ur'];
  const keys = Object.keys(JSON.parse(await readFile(join(root, 'docs/locales/en.json')))).sort();
  for (const lang of locales) {
    const dictionary = JSON.parse(await readFile(join(root, `docs/locales/${lang}.json`)));
    assert.deepEqual(Object.keys(dictionary).sort(), keys);
    assert.ok(Object.values(dictionary).every(x => typeof x === 'string' && x.length));
    const state = await evaluate(`(async () => {await loadLocale('${lang}'); return {lang: document.documentElement.lang, dir: document.documentElement.dir, button: document.getElementById('btn-refresh-text').textContent, save: document.getElementById('btn-save-settings').textContent};})()`);
    assert.equal(state.lang, lang);
    assert.equal(state.dir, ['ar', 'ur'].includes(lang) ? 'rtl' : 'ltr');
    assert.equal(state.button, dictionary.btn_refresh);
    assert.equal(state.save, dictionary.save_btn);
  }
  assert.equal(await evaluate(`(async () => {await loadLocale('../../invalid'); return document.documentElement.lang;})()`), 'en');
  const theme = await evaluate(`(() => {const before = document.documentElement.classList.contains('dark'); document.getElementById('theme-toggle').click(); return {changed: before !== document.documentElement.classList.contains('dark'), saved: localStorage.getItem('sentinel_theme')};})()`);
  assert.ok(theme.changed); assert.ok(['dark', 'light'].includes(theme.saved));
  assert.equal(await evaluate(`(() => {document.getElementById('btn-dispatch-radar').click(); return document.getElementById('modal-settings').classList.contains('hidden');})()`), false);
  await evaluate(`document.getElementById('input-token').value='test-only-token'; document.getElementById('input-repo').value='test-owner/test-repo'; document.getElementById('btn-save-settings').click();`);
  for (const status of [204, 200, 401, 403, 404, 422, 0]) {
    const state = await evaluate(`(async () => {
      window.__status=${status}; document.getElementById('btn-dispatch-radar').click();
      await new Promise(r => setTimeout(r, 10));
      return {request: window.__dispatches.at(-1), toast: document.getElementById('toast-msg').textContent, disabled: document.getElementById('btn-dispatch-radar').disabled};
    })()`);
    assert.equal(state.request.url, 'https://api.github.com/repos/test-owner/test-repo/actions/workflows/radar.yml/dispatches');
    assert.equal(state.request.options.headers.Authorization, 'Bearer test-only-token');
    assert.deepEqual(JSON.parse(state.request.options.body), {ref:'main', inputs:{force:true}});
    assert.equal(state.disabled, false);
    const en = JSON.parse(await readFile(join(root, 'docs/locales/en.json')));
    assert.equal(state.toast, status >= 200 && status < 300 ? en.toast_success : en.toast_error);
  }
  assert.equal(await evaluate(`(() => {document.getElementById('input-token').value=''; document.getElementById('btn-save-settings').click(); return localStorage.getItem('sentinel_pat');})()`), null);
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
  console.log('PASS: 10 locales and RTL; invalid locale fallback; theme; 7 dispatch outcomes; token deletion; XSS; local data fallback; borderless.', style);
} finally {
  ws?.close();
  chrome.kill('SIGTERM');
  await new Promise(r => chrome.exitCode !== null ? r() : chrome.once('exit', r));
  server.close();
  await rm(profile, {recursive:true, force:true, maxRetries:5, retryDelay:200});
}
