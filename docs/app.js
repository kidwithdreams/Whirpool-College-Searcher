// Public backend address only. API credentials must stay on the server.
const API_BASE = 'https://whirlpool-campus-profiler.rozasadykovas.chatgpt.site';
const shell = document.querySelector('#searchShell');
const trigger = document.querySelector('#searchTrigger');
const panel = document.querySelector('#searchPanel');
const backdrop = document.querySelector('#searchBackdrop');
const closeButton = document.querySelector('#closeSearch');
const input = document.querySelector('#universityInput');
const help = document.querySelector('#searchHelp');
const form = document.querySelector('#universitySearch');
const result = document.querySelector('#searchResult');
const generateButton = form.querySelector('.generate-button');
const modeButtons = document.querySelectorAll('[data-search-mode]');
const panelKicker = document.querySelector('#panelKicker');
const searchTitle = document.querySelector('#searchTitle');
const inputLabel = document.querySelector('#searchInputLabel');
const quickTagButtons = [...document.querySelectorAll('[data-search-tag]')];
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const FAVORITES_KEY = 'whirpool-favorites-v1';
const shellParent = shell.parentNode;
const shellNextSibling = shell.nextSibling;
let originRect;
let openedAt = 0;
let searchMode = 'profile';
let lastProfile = null;
let lastAdvice = null;

const searchCopy = {
  profile: {
    kicker: 'Campus profiler',
    title: 'Where do you want to study?',
    label: 'University name',
    placeholder: 'Try Nazarbayev University',
    button: 'Generate Profile',
    help: 'We will assemble a live visual profile in about 30 seconds.',
    tags: ['Nazarbayev University', 'Harvard', 'Oxford']
  },
  advisor: {
    kicker: 'Admissions advisor',
    title: 'Find universities that fit you.',
    label: 'Your scores and preferred region',
    placeholder: 'My SAT is 1350, GPA 3.8, IELTS 6.5 — where can I study in Europe?',
    button: 'Get Recommendations',
    help: 'Tell us your scores, preferred region, and any subject or budget preferences.',
    tags: [
      'SAT 1350 · GPA 3.8 · IELTS 6.5 · Europe',
      'GPA 3.6 · IELTS 7.0 · Germany · Computer Science',
      'IB 36 · IELTS 7.0 · Netherlands · Business'
    ]
  },
  favorites: {
    kicker: 'Saved universities',
    title: 'Your favorites.',
    label: '',
    placeholder: '',
    button: '',
    help: '',
    tags: []
  }
};

function setSearchMode(mode) {
  searchMode = ['advisor', 'favorites'].includes(mode) ? mode : 'profile';
  const copy = searchCopy[searchMode];
  modeButtons.forEach(button => {
    const active = button.dataset.searchMode === searchMode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  panelKicker.textContent = copy.kicker;
  searchTitle.textContent = copy.title;
  inputLabel.textContent = copy.label;
  input.placeholder = copy.placeholder;
  generateButton.textContent = copy.button;
  form.hidden = searchMode === 'favorites';
  help.classList.remove('error');
  help.textContent = copy.help;
  quickTagButtons.forEach((button, index) => {
    const value = copy.tags[index] || '';
    button.hidden = !value;
    button.dataset.searchTag = value;
    button.textContent = value;
  });
  result.className = 'search-result';
  result.innerHTML = '';
  shell.classList.remove('has-results');
  if (searchMode === 'favorites') loadFavorites();
}

function openSearch() {
  if (shell.dataset.state === 'open') return;
  originRect = shell.getBoundingClientRect();
  document.body.appendChild(shell);
  panel.hidden = false;
  shell.classList.add('is-open');
  shell.dataset.state = 'open';
  openedAt = performance.now();
  trigger.setAttribute('aria-expanded', 'true');
  backdrop.classList.add('visible');
  backdrop.setAttribute('aria-hidden', 'false');
  document.body.classList.add('dialog-open');

  const finalRect = shell.getBoundingClientRect();
  if (!prefersReducedMotion) {
    const dx = originRect.left - finalRect.left;
    const dy = originRect.top - finalRect.top;
    const sx = Math.max(originRect.width / finalRect.width, 0.6);
    const sy = Math.max(originRect.height / finalRect.height, 0.18);
    shell.animate([
      { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(${sx}, ${sy})`, opacity: 0.86 },
      { transform: 'translate(-50%, -50%) scale(1)', opacity: 1 }
    ], { duration: 460, easing: 'cubic-bezier(.16,1,.3,1)', fill: 'both' });
  }
  window.setTimeout(() => input.focus(), prefersReducedMotion ? 0 : 380);
}

function closeSearch() {
  if (shell.dataset.state !== 'open') return;
  const animation = prefersReducedMotion ? null : shell.animate([
    { transform: 'translate(-50%, -50%) scale(1)', opacity: 1 },
    { transform: 'translate(-50%, -50%) scale(.84)', opacity: 0 }
  ], { duration: 220, easing: 'cubic-bezier(.4,0,1,1)', fill: 'both' });

  const finish = () => {
    shell.getAnimations().forEach(item => item.cancel());
    shell.classList.remove('is-open');
    shell.classList.remove('has-results');
    shell.dataset.state = 'closed';
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    backdrop.classList.remove('visible');
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('dialog-open');
    shellParent.insertBefore(shell, shellNextSibling);
    trigger.focus({ preventScroll: true });
  };
  if (animation) animation.finished.then(finish).catch(finish);
  else finish();
}

function getFavorites() {
  try {
    const value = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function setFavorites(favorites) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
}

async function loadFavorites() {
  shell.classList.add('has-results');
  const favorites = getFavorites();
  result.className = 'search-result success favorites-result';
  result.innerHTML = favorites.length ? `
    <div class="favorites-list">${favorites.map(item => `
      <article class="favorite-card">
        <h3>${escapeHtml(item.university_name)}</h3>
        <p>${escapeHtml(item.location || 'Location will be added after profiling')}</p>
        <p>${escapeHtml(item.summary || 'Saved from your recommendation list.')}</p>
        <div class="favorite-actions">
          <button type="button" data-open-favorite="${escapeHtml(item.university_name)}">Explore →</button>
          <button type="button" data-remove-favorite="${escapeHtml(item.university_name)}">Remove</button>
        </div>
      </article>`).join('')}</div>`
    : '<div class="favorite-card"><h3>No favorites yet</h3><p>Save a university from a profile or recommendation list and it will appear here on this device.</p></div>';
}

async function saveFavorite(item, button) {
  try {
    const favorites = getFavorites().filter(saved => saved.university_name !== item.university_name);
    setFavorites([{ ...item, added_at: new Date().toISOString() }, ...favorites]);
    if (button) {
      button.classList.add('saved');
      button.textContent = '♥ Saved';
    }
  } catch (error) {
    help.classList.add('error');
    help.textContent = error.message;
  }
}

document.querySelectorAll('[data-open-search]').forEach(button => button.addEventListener('click', openSearch));
trigger.addEventListener('click', openSearch);
closeButton.addEventListener('click', closeSearch);
backdrop.addEventListener('click', () => {
  if (performance.now() - openedAt > 700) closeSearch();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && shell.dataset.state === 'open') closeSearch();
});

modeButtons.forEach(button => button.addEventListener('click', () => setSearchMode(button.dataset.searchMode)));

quickTagButtons.forEach(button => {
  button.addEventListener('click', () => {
    input.value = button.dataset.searchTag;
    input.classList.remove('invalid');
    help.classList.remove('error');
    help.textContent = searchCopy[searchMode].help;
    input.focus();
  });
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) {
    input.classList.add('invalid');
    help.classList.add('error');
    help.textContent = searchMode === 'advisor'
      ? 'Add your scores and preferred study region.'
      : 'Enter a university name or choose one of the suggestions.';
    input.focus();
    return;
  }
  const advisorRequest = searchMode === 'advisor' || /\b(?:sat|gpa|ielts|toefl|ib)\b|куда\s+(?:я\s+)?могу\s+поступить|подбери.*университет|where\s+can\s+i\s+(?:apply|study)/i.test(query);
  if (advisorRequest && searchMode !== 'advisor') setSearchMode('advisor');
  input.classList.remove('invalid');
  help.classList.remove('error');
  help.textContent = advisorRequest
    ? 'Comparing your profile with university admission patterns.'
    : 'Checking official, campus, and student sources.';
  result.className = 'search-result loading';
  result.innerHTML = '<span class="skeleton"></span><span class="skeleton"></span><span class="skeleton"></span>';
  generateButton.disabled = true;
  generateButton.textContent = advisorRequest ? 'Matching…' : 'Profiling…';

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 29500);
  try {
    const response = await fetch(API_BASE + (advisorRequest ? '/api/advice' : '/api/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(advisorRequest ? { query } : { university_name: query }),
      signal: controller.signal
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const requestError = new Error(payload.detail || 'The profile could not be generated.');
      requestError.code = payload.code;
      throw requestError;
    }

    shell.classList.add('has-results');
    if (payload.type === 'recommendations') {
      result.className = 'search-result success advisor-result';
      result.innerHTML = renderAdviceResult(payload);
      help.textContent = `${payload.recommendations.length} universities matched to your profile.`;
    } else {
      result.className = 'search-result success profile-result';
      result.innerHTML = renderSearchResult(payload);
      help.textContent = `${payload.images.length} visual sources checked. Confidence ${payload.confidence_score}%.`;
      applyProfileToPage(payload);
    }
  } catch (error) {
    const timedOut = error && error.name === 'AbortError';
    result.className = 'search-result error';
    result.innerHTML = `<strong>${timedOut ? 'The 30-second search window expired.' : 'We could not generate this result.'}</strong><span>${escapeHtml(timedOut ? 'Please try again—the source services may be busy.' : error.message)}</span>`;
    help.classList.add('error');
    help.textContent = 'No profile data was changed.';
  } finally {
    window.clearTimeout(timeout);
    generateButton.disabled = false;
    generateButton.textContent = searchCopy[searchMode].button;
  }
});

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : '#';
  } catch {
    return '#';
  }
}

function categorySlug(value) {
  return String(value).toLowerCase().replace(/\s+/g, '-');
}

function renderAdviceResult(advice) {
  lastAdvice = advice;
  const applicant = advice.applicant || {};
  const recommendations = Array.isArray(advice.recommendations) ? advice.recommendations : [];
  const cards = recommendations.map((item, index) => {
    const fit = ['Reach', 'Target', 'Safer'].includes(item.fit) ? item.fit : 'Target';
    return `
      <article class="recommendation-card">
        <header>
          <div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.country)}</p></div>
          <span class="fit-badge fit-${fit.toLowerCase()}">${fit}</span>
        </header>
        <p>${escapeHtml(item.reason)}</p>
        <p><strong>Check:</strong> ${escapeHtml(item.requirements || 'Official program requirements')}</p>
        <div class="favorite-actions">
          <button type="button" data-recommendation="${escapeHtml(item.name)}">Explore →</button>
          <button type="button" data-save-recommendation="${index}">♡ Save</button>
        </div>
      </article>`;
  }).join('');
  return `
    <div class="advisor-summary">
      <div><small>${escapeHtml(applicant.region || 'Recommended region')}</small><strong>Your university shortlist</strong></div>
      <div class="applicant-scores" aria-label="Applicant scores">
        <span>SAT ${escapeHtml(applicant.sat || '—')}</span>
        <span>GPA ${escapeHtml(applicant.gpa || '—')}</span>
        <span>IELTS ${escapeHtml(applicant.ielts || '—')}</span>
      </div>
    </div>
    <div class="recommendation-grid">${cards}</div>
    <p class="advisor-disclaimer">${escapeHtml(advice.disclaimer || 'Recommendations are indicative. Always verify current program requirements and deadlines on official university websites.')}</p>`;
}

function renderSearchResult(profile) {
  lastProfile = profile;
  const admissions = profile.admissions || {};
  const images = profile.images.slice(0, 6).map(image => `
    <a class="result-image" href="${escapeHtml(safeUrl(image.source_url))}" target="_blank" rel="noreferrer">
      <img src="${escapeHtml(safeUrl(image.url))}" alt="${escapeHtml(`${image.category} at ${profile.university_name}`)}" loading="lazy">
      <span>${escapeHtml(image.category)} · ${image.is_verified ? 'Verified' : 'Unverified'}</span>
    </a>`).join('');
  return `
    <div class="result-heading">
      <div><small>${escapeHtml(profile.location)}</small><strong>${escapeHtml(profile.university_name)}</strong></div>
      <b>${profile.confidence_score}%</b>
    </div>
    <p>${escapeHtml(profile.summary)}</p>
    <div class="result-stats">
      <span><small>City center</small>${escapeHtml(profile.stats.distance_to_city_center)}</span>
      <span><small>Climate</small>${escapeHtml(profile.stats.climate)}</span>
      <span><small>Living cost</small>${escapeHtml(profile.stats.avg_living_cost)}</span>
    </div>
    <div class="result-stats admission-stats" aria-label="Typical admission profile">
      <span><small>GPA · guidance</small>${escapeHtml(admissions.average_gpa || 'Not published')}</span>
      <span><small>SAT · guidance</small>${escapeHtml(admissions.average_sat || 'Not published')}</span>
      <span><small>IELTS · guidance</small>${escapeHtml(admissions.ielts || 'Check program')}</span>
    </div>
    <p class="admission-note">${escapeHtml(admissions.note || 'Indicative values only—requirements vary by program and applicant type.')}</p>
    ${images ? `<div class="result-images">${images}</div>` : '<p class="result-note">No usable campus images were returned by the selected sources.</p>'}
    <button class="favorite-button" type="button" data-save-current>♡ Add to favorites</button>
    <button class="view-profile-button" type="button" data-view-profile>View full profile ↓</button>`;
}

result.addEventListener('click', event => {
  const exploreButton = event.target.closest('[data-recommendation], [data-open-favorite]');
  if (exploreButton) {
    const university = exploreButton.dataset.recommendation || exploreButton.dataset.openFavorite;
    setSearchMode('profile');
    input.value = university;
    input.focus();
    return;
  }
  const saveCurrentButton = event.target.closest('[data-save-current]');
  if (saveCurrentButton && lastProfile) {
    saveFavorite({ university_name: lastProfile.university_name, location: lastProfile.location, summary: lastProfile.summary }, saveCurrentButton);
    return;
  }
  const saveRecommendationButton = event.target.closest('[data-save-recommendation]');
  if (saveRecommendationButton && lastAdvice) {
    const item = lastAdvice.recommendations[Number(saveRecommendationButton.dataset.saveRecommendation)];
    if (item) saveFavorite({ university_name: item.name, location: item.country, summary: item.reason }, saveRecommendationButton);
    return;
  }
  const removeButton = event.target.closest('[data-remove-favorite]');
  if (removeButton) {
    const favorites = getFavorites().filter(item => item.university_name !== removeButton.dataset.removeFavorite);
    setFavorites(favorites);
    loadFavorites();
  }
});

function setSummaryLogo(universityName, imageUrl) {
  const logo = document.querySelector('.summary-logo');
  const initials = universityName.split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
  const safeImageUrl = safeUrl(imageUrl);

  logo.replaceChildren();
  if (safeImageUrl !== '#') {
    const image = document.createElement('img');
    image.src = safeImageUrl;
    image.alt = `Main building of ${universityName}`;
    image.loading = 'eager';
    image.referrerPolicy = 'no-referrer';
    image.addEventListener('load', () => {
      logo.classList.remove('is-loading');
      logo.classList.add('has-photo');
    }, { once: true });
    image.addEventListener('error', () => {
      logo.classList.remove('has-photo', 'is-loading');
      logo.textContent = initials;
    }, { once: true });
    logo.classList.add('is-loading');
    logo.appendChild(image);
    return;
  }

  logo.classList.remove('has-photo', 'is-loading');
  logo.textContent = initials;
}

function applyProfileToPage(profile) {
  const usableImages = (profile.images || []).filter(image => safeUrl(image.url) !== '#');
  const mainBuildingImage = usableImages
    .filter(image => image.category === 'Campus')
    .sort((a, b) => Number(b.is_verified) - Number(a.is_verified) || Number(b.confidence || 0) - Number(a.confidence || 0))[0]
    || usableImages.sort((a, b) => Number(b.is_verified) - Number(a.is_verified) || Number(b.confidence || 0) - Number(a.confidence || 0))[0];
  setSummaryLogo(profile.university_name, mainBuildingImage?.url);
  document.querySelector('.summary-caption').textContent = 'Live verified profile';
  document.querySelector('.summary-meta h3').textContent = profile.university_name;
  document.querySelector('.summary-meta div > p:last-child').textContent = profile.location;
  document.querySelector('.summary-text').textContent = profile.summary;
  document.querySelector('.confidence-panel strong').textContent = `${profile.confidence_score}%`;

  const facts = document.querySelectorAll('.summary-facts div');
  const admissions = profile.admissions || {};
  const values = [
    ['GPA · guidance', admissions.average_gpa || 'Not published'],
    ['SAT · guidance', admissions.average_sat || 'Not published'],
    ['IELTS · guidance', admissions.ielts || 'Check program']
  ];
  facts.forEach((fact, index) => {
    fact.querySelector('span').textContent = values[index][0];
    fact.querySelector('strong').textContent = values[index][1];
  });
  let admissionsNote = document.querySelector('#profileAdmissionsNote');
  if (!admissionsNote) {
    admissionsNote = document.createElement('p');
    admissionsNote.id = 'profileAdmissionsNote';
    admissionsNote.className = 'admission-note';
    document.querySelector('.summary-facts').after(admissionsNote);
  }
  admissionsNote.textContent = admissions.note || 'Confirm current requirements with the program.';

  if (profile.images.length) {
    document.querySelector('#galleryGrid').innerHTML = profile.images.map((image, index) => `
      <article class="photo-card ${index === 0 ? 'photo-card-large' : ''}" data-category="${escapeHtml(categorySlug(image.category))}">
        <img src="${escapeHtml(safeUrl(image.url))}" alt="${escapeHtml(`${image.category} at ${profile.university_name}`)}" loading="lazy">
        <div class="photo-content">
          <div><p>${escapeHtml(image.category)}</p><h3>${escapeHtml(image.source_name)}</h3></div>
          <span class="status ${image.is_verified ? 'verified' : 'unverified'}">${image.is_verified ? 'Verified' : 'Unverified'}</span>
        </div>
        <div class="photo-meta">
          <a href="${escapeHtml(safeUrl(image.source_url))}" target="_blank" rel="noreferrer">View source <span aria-hidden="true">↗</span></a>
          <time datetime="${escapeHtml(image.date)}">${escapeHtml(image.date)}</time>
        </div>
      </article>`).join('');
    galleryPages.clear();
    applyFilter(activeGalleryFilter);
  }

  document.querySelector('.climate-card .temperature').innerHTML = `${escapeHtml(profile.stats.climate)}<span>Approximate seasonal range</span>`;
  document.querySelector('.cost-card h3').textContent = profile.stats.avg_living_cost.replace('Approx. ', '').replace(' / month', '');
  document.querySelector('.cost-card > div > span').textContent = 'estimated monthly total';

  const viewButton = result.querySelector('[data-view-profile]');
  if (viewButton) viewButton.addEventListener('click', () => {
    closeSearch();
    document.querySelector('#profile').scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  });
}

const filters = document.querySelectorAll('[data-filter]');
const emptyGallery = document.querySelector('#emptyGallery');
const galleryGrid = document.querySelector('#galleryGrid');
const loadMoreGallery = document.querySelector('#loadMoreGallery');
const galleryStatus = document.querySelector('#galleryStatus');
const galleryPages = new Map();
const galleryRequests = new Map();
const busyGalleryFilters = new Set();
let activeGalleryFilter = 'all';

const galleryFilterNames = {
  all: 'images',
  dormitories: 'dormitories',
  sports: 'sports facilities',
  laboratories: 'laboratories',
  'student-life': 'student life',
  campus: 'campuses',
  city: 'university cities'
};

function updateLoadMoreButton() {
  const busy = busyGalleryFilters.has(activeGalleryFilter);
  loadMoreGallery.disabled = busy;
  loadMoreGallery.querySelector('span').textContent = busy
    ? 'Loading 5 photos…'
    : `Load 5 more ${galleryFilterNames[activeGalleryFilter] || 'images'}`;
}

function applyFilter(filter, { preserveStatus = false } = {}) {
  activeGalleryFilter = filter;
  let visibleCount = 0;
  filters.forEach(button => {
    const active = button.dataset.filter === filter;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  galleryGrid.querySelectorAll('.photo-card[data-category]').forEach(card => {
    const categories = card.dataset.category.split(' ');
    const visible = filter === 'all' || categories.includes(filter);
    card.hidden = !visible;
    if (visible) visibleCount += 1;
  });
  emptyGallery.hidden = visibleCount !== 0 || busyGalleryFilters.has(filter);
  if (!preserveStatus) {
    galleryStatus.classList.remove('error');
    galleryStatus.textContent = galleryPages.has(filter)
      ? 'Five different universities per load · no Gemini tokens used'
      : 'Loading real university photography…';
  }
  updateLoadMoreButton();
}

function galleryCardMarkup(image, index, featured = false) {
  const layoutClass = featured && index === 0 ? ' photo-card-large' : ' photo-card-loaded';
  return `
    <article class="photo-card${layoutClass}" data-category="${escapeHtml(image.category_slug || categorySlug(image.category))}">
      <img src="${escapeHtml(safeUrl(image.url))}" alt="${escapeHtml(`${image.category} at ${image.university_name}`)}" loading="lazy" referrerpolicy="no-referrer">
      <div class="photo-content">
        <div><p>${escapeHtml(image.category)}</p><h3>${escapeHtml(image.university_name)}</h3></div>
        <span class="status ${image.is_verified ? 'verified' : 'unverified'}">${image.is_verified ? 'Verified' : 'Unverified'}</span>
      </div>
      <div class="photo-meta">
        <a href="${escapeHtml(safeUrl(image.source_url))}" target="_blank" rel="noreferrer">${escapeHtml(image.source_name || 'View source')} <span aria-hidden="true">↗</span></a>
        <time datetime="${escapeHtml(image.date)}">${escapeHtml(image.date)}</time>
      </div>
    </article>`;
}

function updateSampleAvatar(images) {
  if (lastProfile) return;
  const nazarbayevImage = images.find(image =>
    image.university_name?.toLowerCase().includes('nazarbayev') &&
    (image.category_slug === 'campus' || image.category === 'Campus')
  ) || images.find(image => image.university_name?.toLowerCase().includes('nazarbayev'));
  if (nazarbayevImage) setSummaryLogo('Nazarbayev University', nazarbayevImage.url);
}

async function loadGalleryBatch(filter, { page = (galleryPages.get(filter) || 0) + 1, replace = false, initial = false } = {}) {
  if (galleryRequests.has(filter)) return galleryRequests.get(filter);

  const request = (async () => {
    busyGalleryFilters.add(filter);
    if (filter === activeGalleryFilter) {
      galleryStatus.classList.remove('error');
      galleryStatus.textContent = 'Searching real university visual sources without calling Gemini.';
      applyFilter(filter, { preserveStatus: true });
    }

    try {
      const response = await fetch(`${API_BASE}/api/gallery?category=${encodeURIComponent(filter)}&page=${page}`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'More images could not be loaded.');

      const returnedImages = Array.isArray(payload.images) ? payload.images : [];
      updateSampleAvatar(returnedImages);
      const existingUrls = new Set([...galleryGrid.querySelectorAll('img')].map(image => safeUrl(image.src)));
      const images = returnedImages.filter(image => safeUrl(image.url) !== '#' && !existingUrls.has(safeUrl(image.url)));
      if (!images.length) throw new Error('No new images were found for this category. Try again.');

      if (replace) galleryGrid.replaceChildren();
      galleryGrid.classList.remove('is-loading');
      galleryGrid.setAttribute('aria-busy', 'false');
      const startIndex = galleryGrid.children.length;
      galleryGrid.insertAdjacentHTML('beforeend', images.map((image, index) => galleryCardMarkup(image, index, initial)).join(''));
      galleryPages.set(filter, page);

      const addedCards = [...galleryGrid.children].slice(startIndex);
      addedCards.forEach((card, index) => {
        const image = card.querySelector('img');
        image.addEventListener('error', () => card.remove(), { once: true });
        if (!prefersReducedMotion) card.animate([
          { opacity: 0, transform: 'translateY(18px)' },
          { opacity: 1, transform: 'translateY(0)' }
        ], { duration: 260, delay: index * 45, easing: 'cubic-bezier(0.23, 1, 0.32, 1)', fill: 'both' });
      });

      if (filter === activeGalleryFilter) {
        applyFilter(filter, { preserveStatus: true });
        galleryStatus.classList.remove('error');
        galleryStatus.textContent = initial
          ? 'Live university photography · open any source to verify it'
          : `Added ${images.length} new photos from ${images.length} universities.`;
      }
      return images;
    } catch (error) {
      galleryGrid.classList.remove('is-loading');
      galleryGrid.setAttribute('aria-busy', 'false');
      galleryGrid.querySelectorAll('.gallery-skeleton').forEach(item => item.remove());
      if (filter === activeGalleryFilter) {
        galleryStatus.classList.add('error');
        galleryStatus.textContent = error.message;
      }
      throw error;
    } finally {
      busyGalleryFilters.delete(filter);
      galleryRequests.delete(filter);
      if (filter === activeGalleryFilter) applyFilter(filter, { preserveStatus: true });
    }
  })();

  galleryRequests.set(filter, request);
  return request;
}

filters.forEach(button => button.addEventListener('click', () => {
  const filter = button.dataset.filter;
  applyFilter(filter);
  if (!galleryPages.has(filter)) loadGalleryBatch(filter, { page: 1 }).catch(() => {});
}));
document.querySelector('[data-reset-filter]').addEventListener('click', () => applyFilter('all'));

loadMoreGallery.addEventListener('click', () => loadGalleryBatch(activeGalleryFilter).catch(() => {}));

loadGalleryBatch('all', { page: 1, replace: true, initial: true }).catch(() => {});

const graduateImages = [...document.querySelectorAll('.graduate-image')];
const graduateDots = [...document.querySelectorAll('.graduate-dots span')];
let graduateIndex = 0;
let graduateTimer = null;

function advanceGraduate() {
  const current = graduateImages[graduateIndex];
  graduateIndex = (graduateIndex + 1) % graduateImages.length;
  const next = graduateImages[graduateIndex];
  current.classList.remove('is-active');
  current.classList.add('is-leaving');
  current.setAttribute('aria-hidden', 'true');
  next.classList.remove('is-leaving');
  next.classList.add('is-active');
  next.setAttribute('aria-hidden', 'false');
  graduateDots.forEach((dot, index) => dot.classList.toggle('is-active', index === graduateIndex));
  window.setTimeout(() => current.classList.remove('is-leaving'), 760);
}

if (!prefersReducedMotion && graduateImages.length > 1) {
  const graduateObserver = new IntersectionObserver(entries => {
    const visible = entries.some(entry => entry.isIntersecting);
    if (visible && !graduateTimer) graduateTimer = window.setInterval(advanceGraduate, 3600);
    if (!visible && graduateTimer) {
      window.clearInterval(graduateTimer);
      graduateTimer = null;
    }
  }, { threshold: 0.2 });
  graduateObserver.observe(document.querySelector('#graduateStage'));
}

const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(section => revealObserver.observe(section));

const navLinks = document.querySelectorAll('.nav-glass a');
const sectionObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    navLinks.forEach(link => link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`));
  });
}, { rootMargin: '-35% 0px -55% 0px' });
document.querySelectorAll('main section[id]').forEach(section => sectionObserver.observe(section));

const siteHeader = document.querySelector('#siteHeader');
const heroThemeObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => siteHeader.classList.toggle('on-light', !entry.isIntersecting));
}, { threshold: 0.48 });
heroThemeObserver.observe(document.querySelector('#top'));
