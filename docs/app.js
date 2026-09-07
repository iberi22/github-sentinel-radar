
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
    'btn-save-settings': 'save_btn',
    'tech-dna-title': 'tech_dna_title',
    'token-label': 'token_label',
    'repo-label': 'repo_label',
  };

  for (const [elemId, key] of Object.entries(map)) {
    const el = document.getElementById(elemId);
    if (el && localeData[key]) {
      el.textContent = localeData[key];
    }
  }

  document.getElementById('input-token').placeholder = localeData.token_placeholder;
  document.getElementById('input-repo').placeholder = localeData.repo_placeholder;
  document.getElementById('btn-close-modal').setAttribute('aria-label', localeData.close_btn);
  document.getElementById('btn-open-settings').title = localeData.nav_settings;
  document.getElementById('theme-toggle').title = localeData.theme_label;
  renderDirectory();
  renderBlocklist(document.getElementById('bot-search').value);
  const searchInput = document.getElementById('bot-search');
  if (searchInput && localeData['search_placeholder']) {
    searchInput.placeholder = localeData['search_placeholder'];
  }
}

async function fetchDataFile(name) {
  let response;
  try { response = await fetch(`data/${name}.json`, { cache: 'no-store' }); } catch {}
  if (!response?.ok) response = await fetch(`../data/${name}.json`, { cache: 'no-store' });
  return response;
}

async function fetchLocalData() {
  try {
    const [rRes, bRes, vRes] = await Promise.all([
      fetchDataFile('radar'),
      fetchDataFile('blocklist'),
      fetchDataFile('verified_projects')
    ]);

    if (rRes.ok) radarData = await rRes.json();
    if (bRes.ok) blocklistData = await bRes.json();
    if (vRes.ok) verifiedData = await vRes.json();

    renderRadar();
    renderBlocklist();
    renderDirectory();
  } catch (e) {
    console.error('Data loading error:', e);
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

// On-Demand Dispatch Logic
document.getElementById('btn-dispatch-radar').addEventListener('click', async () => {
  const token = localStorage.getItem('sentinel_pat');
  const repo = localStorage.getItem('sentinel_repo') || 'iberi22/github-sentinel-radar';

  if (!token) {
    document.getElementById('modal-settings').classList.remove('hidden');
    return;
  }

  if (!/^[A-Za-z0-9-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
    showToast(localeData.toast_error || 'Invalid repository.', 'error');
    return;
  }
  const button = document.getElementById('btn-dispatch-radar');
  if (button.disabled) return;
  button.disabled = true;
  const btnText = document.getElementById('btn-refresh-text');
  btnText.textContent = localeData['btn_updating'] || 'Dispatching...';

  try {
    const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/radar.yml/dispatches`, {
      method: 'POST',
      signal: AbortSignal.timeout(20000),
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2026-03-10'
      },
      body: JSON.stringify({ ref: 'main', inputs: { force: true } })
    });

    if (res.ok) {
      showToast(localeData['toast_success'] || 'Dispatched successfully!', 'success');
    } else {
      showToast(localeData['toast_error'] || 'Error dispatching job.', 'error');
    }
  } catch (e) {
    showToast(localeData['toast_error'] || 'Network error.', 'error');
  } finally {
    button.disabled = false;
    btnText.textContent = localeData['btn_refresh'] || 'Update Feed ⚡';
  }
});

function showToast(msg, type) {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toast-msg');
  toastMsg.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 5000);
}

// Settings Modal Handlers
document.getElementById('btn-open-settings').addEventListener('click', () => {
  document.getElementById('input-token').value = localStorage.getItem('sentinel_pat') || '';
  document.getElementById('input-repo').value = localStorage.getItem('sentinel_repo') || '';
  document.getElementById('modal-settings').classList.remove('hidden');
});

document.getElementById('btn-close-modal').addEventListener('click', () => {
  document.getElementById('modal-settings').classList.add('hidden');
});

document.getElementById('btn-save-settings').addEventListener('click', () => {
  const token = document.getElementById('input-token').value.trim();
  const repo = document.getElementById('input-repo').value.trim();
  if (token) localStorage.setItem('sentinel_pat', token);
  else localStorage.removeItem('sentinel_pat');
  if (repo) localStorage.setItem('sentinel_repo', repo);
  else localStorage.removeItem('sentinel_repo');
  document.getElementById('modal-settings').classList.add('hidden');
  showToast(localeData.save_btn || 'Saved', 'success');
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

loadLocale(currentLocale);
fetchLocalData();
