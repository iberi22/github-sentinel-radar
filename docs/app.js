
// Retire credentials saved by versions prior to token-free navigation.
localStorage.removeItem('sentinel_pat');
localStorage.removeItem('sentinel_repo');

// State Management
let currentLocale = localStorage.getItem('sentinel_locale') || 'en';
let localeData = {};
let radarData = null;
let blocklistData = null;
let verifiedData = null;

// RTL Locales
const RTL_LOCALES = ['ar', 'ur'];
const SUPPORTED_LOCALES = ['en', 'zh', 'hi', 'es', 'fr', 'ar', 'bn', 'pt', 'ru', 'ur'];
let localeRequest = 0;

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function safeURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? escapeHTML(url.href) : '#';
  } catch { return '#'; }
}


async function loadLocale(lang) {
  if (!SUPPORTED_LOCALES.includes(lang)) lang = 'en';
  const request = ++localeRequest;
  try {
    const res = await fetch(`locales/${lang}.json`);
    if (!res.ok) throw new Error(`Locale HTTP ${res.status}`);
    if (res.ok) {
      const data = await res.json();
      if (request !== localeRequest) return;
      localeData = data;
      document.documentElement.lang = lang;
      currentLocale = lang;
      localStorage.setItem('sentinel_locale', lang);
      applyTranslations();

      // Handle RTL
      if (RTL_LOCALES.includes(lang)) {
        document.documentElement.setAttribute('dir', 'rtl');
      } else {
        document.documentElement.setAttribute('dir', 'ltr');
      }
    }
  } catch (e) {
    console.error('Failed to load locale:', e);
    if (lang !== 'en' && request === localeRequest) await loadLocale('en');
  }
}

function applyTranslations() {
  document.getElementById('lang-select').value = currentLocale;

  const map = {
    'app-title': 'app_title',
    'app-tagline': 'tagline',
    'nav-radar': 'nav_radar',
    'nav-sentinel': 'nav_sentinel',
    'nav-directory': 'nav_directory',
    'btn-refresh-text': 'btn_refresh',
    'radar-title': 'radar_title',
    'radar-desc': 'radar_desc',
    'releases-header': 'releases_header',
    'discoveries-header': 'discoveries_header',
    'dna-lang-label': 'languages',
    'dna-topic-label': 'topics',
    'sentinel-title': 'sentinel_title',
    'sentinel-desc': 'sentinel_desc',
    'label-total-blocked': 'total_blocked',
    'directory-title': 'directory_title',
    'directory-desc': 'directory_desc',
    'btn-submit-project': 'btn_submit_project',
    'modal-title': 'modal_title',
    'modal-desc': 'modal_desc',
    'btn-guide-next': 'next_btn',
    'btn-guide-back': 'back_btn',
    'btn-copy-template': 'copy_btn',
    'btn-sentinel-setup': 'sentinel_setup',
    'refresh-help': 'refresh_help',
    'tech-dna-title': 'tech_dna_title',
  };

  for (const [elemId, key] of Object.entries(map)) {
    const el = document.getElementById(elemId);
    if (el && localeData[key]) {
      el.textContent = localeData[key];
    }
  }

  document.getElementById('btn-close-modal').setAttribute('aria-label', localeData.close_btn);
  document.getElementById('btn-open-settings').title = localeData.nav_settings;
  document.getElementById('theme-toggle').title = localeData.theme_label;
  renderGuide();
  renderFeedStatus();
  renderDirectory();
  renderBlocklist(document.getElementById('bot-search').value);
  const searchInput = document.getElementById('bot-search');
  if (searchInput && localeData['search_placeholder']) {
    searchInput.placeholder = localeData['search_placeholder'];
  }
}

async function fetchDataFile(name) {
  let response;
  try { response = await fetch(`data/${name}.json?v=${Date.now()}`, { cache: 'no-store', signal: AbortSignal.timeout(10000) }); } catch {}
  if (!response?.ok) response = await fetch(`../data/${name}.json?v=${Date.now()}`, { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  return response;
}

async function fetchLocalData() {
  try {
    const [rRes, bRes, vRes] = await Promise.all([
      fetchDataFile('radar'),
      fetchDataFile('blocklist'),
      fetchDataFile('verified_projects')
    ]);

    if (!rRes.ok) throw new Error(`Feed HTTP ${rRes.status}`);
    radarData = await rRes.json();
    if (bRes.ok) blocklistData = await bRes.json();
    if (vRes.ok) verifiedData = await vRes.json();

    renderRadar();
    renderFeedStatus();
    renderBlocklist();
    renderDirectory();
  } catch (e) {
    console.error('Data loading error:', e);
    feedStatus = 'load_error';
    renderFeedStatus();
  }
}

function renderRadar() {
  if (!radarData) return;

  // DNA
  const langContainer = document.getElementById('dna-languages');
  const topicContainer = document.getElementById('dna-topics');
  langContainer.innerHTML = '';
  topicContainer.innerHTML = '';

  (radarData.profile_dna?.top_languages || []).forEach(l => {
    langContainer.innerHTML += `<span class="bg-surface-mutedLight dark:bg-surface-mutedDark px-2.5 py-1 rounded-lg font-mono text-[11px]">${escapeHTML(l)}</span>`;
  });

  (radarData.profile_dna?.top_topics || []).forEach(t => {
    topicContainer.innerHTML += `<span class="bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 px-2.5 py-1 rounded-lg font-mono text-[11px]">#${escapeHTML(t)}</span>`;
  });

  // Releases
  const relContainer = document.getElementById('releases-list');
  const releases = radarData.releases || [];
  document.getElementById('releases-count').textContent = releases.length;
  relContainer.innerHTML = '';

  releases.forEach(r => {
    relContainer.innerHTML += `
      <div class="surface-card bg-surface-cardLight dark:bg-surface-cardDark p-4 rounded-2xl shadow-sm space-y-2">
        <div class="flex items-center justify-between">
          <a href="${safeURL(r.html_url)}" target="_blank" rel="noopener noreferrer" class="font-bold text-xs hover:text-indigo-500 transition">${escapeHTML(r.repo)}</a>
          <span class="font-mono text-[10px] bg-slate-100 dark:bg-surface-mutedDark px-2 py-0.5 rounded-md text-slate-500">${escapeHTML(r.tag_name)}</span>
        </div>
        <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">${escapeHTML(r.body_snippet)}</p>
        <span class="text-[10px] text-slate-400 block">${escapeHTML(r.published_at.slice(0, 10))}</span>
      </div>
    `;
  });

  // Discoveries
  const discContainer = document.getElementById('discoveries-list');
  const discoveries = radarData.discoveries || [];
  document.getElementById('discoveries-count').textContent = discoveries.length;
  discContainer.innerHTML = '';

  discoveries.forEach(d => {
    discContainer.innerHTML += `
      <div class="surface-card bg-surface-cardLight dark:bg-surface-cardDark p-4 rounded-2xl shadow-sm space-y-2">
        <div class="flex items-center justify-between">
          <a href="${safeURL(d.html_url)}" target="_blank" rel="noopener noreferrer" class="font-bold text-xs hover:text-indigo-500 transition">${escapeHTML(d.full_name)}</a>
          <span class="font-mono text-[10px] text-amber-500">★ ${escapeHTML(d.stars)}</span>
        </div>
        <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">${escapeHTML(d.description)}</p>
        <div class="flex items-center gap-2 pt-1">
          <span class="text-[10px] bg-slate-100 dark:bg-surface-mutedDark px-2 py-0.5 rounded text-slate-500">${escapeHTML(d.language)}</span>
        </div>
      </div>
    `;
  });
}

function renderBlocklist(filter = '') {
  if (!blocklistData) return;
  const bots = blocklistData.bots || [];
  document.getElementById('metric-blocked-count').textContent = bots.length;

  const container = document.getElementById('bots-table');
  container.innerHTML = '';

  const filtered = bots.filter(b => b.username.toLowerCase().includes(filter.toLowerCase()));

  filtered.forEach(b => {
    container.innerHTML += `
      <div class="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-surface-mutedLight/60 dark:bg-surface-mutedDark/60 rounded-2xl gap-3 text-xs">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl bg-red-500/10 text-red-500 flex items-center justify-center font-bold">🚫</div>
          <div>
            <p class="font-bold text-slate-800 dark:text-slate-200">@${escapeHTML(b.username)}</p>
            <p class="text-[11px] text-slate-400">${escapeHTML(b.reason)}</p>
          </div>
        </div>
        <div class="flex items-center gap-4 text-slate-400 text-[11px] self-end sm:self-center">
          <span>${escapeHTML(b.blocked_at.slice(0, 10))}</span>
          <a href="https://github.com/${escapeHTML(b.username)}" target="_blank" rel="noopener noreferrer" class="text-indigo-500 hover:underline">${escapeHTML(localeData.view_profile || 'Profile ↗')}</a>
        </div>
      </div>
    `;
  });
}

function renderDirectory() {
  if (!verifiedData) return;
  const container = document.getElementById('projects-grid');
  container.innerHTML = '';

  (verifiedData.projects || []).forEach(p => {
    container.innerHTML += `
      <div class="surface-card bg-surface-cardLight dark:bg-surface-cardDark p-5 rounded-3xl shadow-sm space-y-3 flex flex-col justify-between">
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <h4 class="font-bold text-sm">${escapeHTML(p.name)}</h4>
            <span class="text-[10px] bg-emerald-500/10 text-emerald-500 font-semibold px-2 py-0.5 rounded-full">${escapeHTML(localeData.verified_label || 'Verified')}</span>
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400">${escapeHTML(p.description)}</p>
        </div>
        <div class="space-y-3 pt-2">
          <div class="flex flex-wrap gap-1">
            ${(p.stack || []).map(s => `<span class="text-[10px] bg-surface-mutedLight dark:bg-surface-mutedDark px-2 py-0.5 rounded text-slate-500">${escapeHTML(s)}</span>`).join('')}
          </div>
          <div class="flex items-center justify-between pt-2 text-xs">
            <span class="text-slate-400">${escapeHTML(localeData.by_label || 'By')} ${escapeHTML(p.owner)}</span>
            <div class="flex gap-2">
              ${p.pages_url ? `<a href="${safeURL(p.pages_url)}" target="_blank" rel="noopener noreferrer" class="text-indigo-500 hover:underline">${escapeHTML(localeData.site_label || 'Site ↗')}</a>` : ''}
              <a href="${safeURL(p.repo_url)}" target="_blank" rel="noopener noreferrer" class="text-slate-500 hover:underline">${escapeHTML(localeData.repo_link_label || 'Repo ↗')}</a>
            </div>
          </div>
        </div>
      </div>
    `;
  });
}

// GitHub owns authentication. Pages only links to the workflow and reads public files.
let site = null;
let guideStep = 0;
let guideTrigger = null;
let feedStatus = '';
let refreshTimer = null;
let refreshChecking = false;
let pendingRefresh = null;
try { pendingRefresh = JSON.parse(sessionStorage.getItem('sentinel_refresh')); } catch {}
if (!pendingRefresh || !Number.isFinite(pendingRefresh.until)) pendingRefresh = null;

function validRepository(value) {
  return typeof value === 'string' && /^[A-Za-z0-9-]+\/[A-Za-z0-9_.-]+$/.test(value);
}

async function loadSite() {
  try {
    const response = await fetch('site.json', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('No deployment metadata');
    const config = await response.json();
    if (!validRepository(config.repository) || typeof config.default_branch !== 'string' || !config.default_branch) {
      throw new Error('Invalid deployment metadata');
    }
    site = config;
  } catch {
    const owner = location.hostname.endsWith('.github.io') ? location.hostname.split('.')[0] : null;
    const name = location.pathname.split('/').filter(Boolean)[0] || `${owner}.github.io`;
    // Local preview has a known source; custom domains require build metadata.
    const repository = owner ? `${owner}/${name}` :
      ['localhost', '127.0.0.1'].includes(location.hostname) ? 'iberi22/github-sentinel-radar' : null;
    if (!validRepository(repository)) {
      feedStatus = 'setup_error'; renderFeedStatus(); return;
    }
    site = {repository, default_branch: 'main'};
  }
  document.getElementById('btn-dispatch-radar').href = workflowURL();
  document.getElementById('btn-dispatch-radar').removeAttribute('aria-disabled');
  document.getElementById('btn-submit-project').href = `https://github.com/${site.repository}/pulls`;
  document.getElementById('btn-sentinel-setup').href = `https://github.com/${site.repository}/blob/${encodeURIComponent(site.default_branch)}/DEPLOYMENT.md#sentinel`;
  renderGuide();
}

function workflowURL() {
  return `https://github.com/${site.repository}/actions/workflows/radar.yml`;
}

function renderFeedStatus() {
  const status = document.getElementById('feed-status');
  if (!status) return;
  const key = pendingRefresh ? 'waiting_feed' : feedStatus || (radarData?.last_updated ? 'feed_ready' : 'feed_empty');
  status.textContent = localeData[key] || '';
  const date = document.getElementById('feed-updated');
  const timestamp = Date.parse(radarData?.last_updated);
  date.textContent = Number.isFinite(timestamp) ? new Date(timestamp).toLocaleString(currentLocale) : '';
  date.dateTime = Number.isFinite(timestamp) ? new Date(timestamp).toISOString() : '';
}

function finishRefresh(status) {
  clearTimeout(refreshTimer);
  refreshTimer = null;
  pendingRefresh = null;
  sessionStorage.removeItem('sentinel_refresh');
  feedStatus = status;
  renderFeedStatus();
}

async function checkFeedUpdate() {
  clearTimeout(refreshTimer);
  refreshTimer = null;
  if (!pendingRefresh) return;
  if (Date.now() >= pendingRefresh.until) { finishRefresh('wait_finished'); return; }
  if (document.hidden || refreshChecking) return;
  refreshChecking = true;
  const request = pendingRefresh;
  try {
    const response = await fetchDataFile('radar');
    if (!response.ok) throw new Error(`Feed HTTP ${response.status}`);
    const data = await response.json();
    if (pendingRefresh !== request) return;
    if (data.last_updated && data.last_updated !== request.baseline) {
      radarData = data;
      renderRadar();
      finishRefresh('feed_updated');
      return;
    }
  } catch {
    // Transient network failures do not report a successful refresh.
  } finally {
    refreshChecking = false;
    if (pendingRefresh && !document.hidden) refreshTimer = setTimeout(checkFeedUpdate, 20000);
  }
}

function requestRefresh(event) {
  if (!site) { event.preventDefault(); return; }
  // Normal link navigation preserves GitHub login, popup handling and keyboard access.
  pendingRefresh = {baseline: radarData?.last_updated || null, until: Date.now() + 5 * 60000};
  sessionStorage.setItem('sentinel_refresh', JSON.stringify(pendingRefresh));
  feedStatus = '';
  renderFeedStatus();
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(checkFeedUpdate, 20000);
}

document.getElementById('btn-dispatch-radar').addEventListener('click', requestRefresh);
window.addEventListener('focus', checkFeedUpdate);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { clearTimeout(refreshTimer); refreshTimer = null; }
  else checkFeedUpdate();
});

function renderGuide() {
  const title = document.getElementById('guide-step-title');
  if (!title) return;
  document.getElementById('guide-progress').textContent = `${guideStep + 1} / 3`;
  document.getElementById('guide-repository').textContent = site?.repository || '';
  title.textContent = localeData[`step_${guideStep + 1}_title`] || '';
  document.getElementById('guide-step-body').textContent = localeData[`step_${guideStep + 1}_body`] || '';
  const link = document.getElementById('guide-action');
  link.textContent = localeData[`step_${guideStep + 1}_action`] || '';
  link.removeAttribute('href');
  if (site) link.href = [
    `https://github.com/${site.repository}`,
    `https://github.com/${site.repository}/settings/pages`,
    workflowURL()
  ][guideStep];
  document.getElementById('btn-guide-back').disabled = guideStep === 0;
  document.getElementById('btn-guide-next').textContent = localeData[guideStep === 2 ? 'done_btn' : 'next_btn'] || '';
}

function closeGuide() {
  document.getElementById('modal-settings').close();
  guideTrigger?.focus();
}
document.getElementById('btn-open-settings').addEventListener('click', event => {
  guideTrigger = event.currentTarget;
  guideStep = 0;
  renderGuide();
  document.getElementById('modal-settings').showModal();
});
document.getElementById('btn-close-modal').addEventListener('click', closeGuide);
document.getElementById('btn-guide-next').addEventListener('click', () => {
  if (guideStep === 2) closeGuide();
  else { guideStep++; renderGuide(); }
});
document.getElementById('btn-guide-back').addEventListener('click', () => {
  guideStep = Math.max(0, guideStep - 1); renderGuide();
});
document.getElementById('guide-action').addEventListener('click', event => {
  if (!site) event.preventDefault();
  else if (guideStep === 2) requestRefresh(event);
});

// Theme Toggle
const themeToggleBtn = document.getElementById('theme-toggle');
themeToggleBtn.addEventListener('click', () => {
  if (document.documentElement.classList.contains('dark')) {
    document.documentElement.classList.remove('dark');
    localStorage.setItem('sentinel_theme', 'light');
  } else {
    document.documentElement.classList.add('dark');
    localStorage.setItem('sentinel_theme', 'dark');
  }
});

// Tab Navigation
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => {
      t.classList.remove('active', 'bg-white', 'dark:bg-surface-cardDark', 'text-indigo-600', 'dark:text-indigo-400', 'shadow-sm');
      t.classList.add('text-slate-500', 'dark:text-slate-400');
    });
    tab.classList.add('active', 'bg-white', 'dark:bg-surface-cardDark', 'text-indigo-600', 'dark:text-indigo-400', 'shadow-sm');
    tab.classList.remove('text-slate-500', 'dark:text-slate-400');

    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(tab.dataset.tab).classList.remove('hidden');
  });
});

// Search filter for bots
document.getElementById('bot-search').addEventListener('input', (e) => {
  renderBlocklist(e.target.value);
});

// Init
document.getElementById('lang-select').addEventListener('change', (e) => {
  loadLocale(e.target.value);
});

// Initial Theme Check
if (localStorage.getItem('sentinel_theme') === 'dark' || (!localStorage.getItem('sentinel_theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
} else {
  document.documentElement.classList.remove('dark');
}

(async () => {
  await Promise.all([loadLocale(currentLocale), loadSite(), fetchLocalData()]);
  renderFeedStatus();
  checkFeedUpdate();
})();
