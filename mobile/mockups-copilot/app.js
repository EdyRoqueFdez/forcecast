const state = {
  screen: 'vote',
  category: 'Code',
  theme: localStorage.getItem('fc-copilot-theme') || 'dark',
  language: localStorage.getItem('fc-copilot-language') || 'en',
  query: '',
  votedModel: null,
};

const models = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', avatar: 'G4', color: '', elo: 1842, delta: '+12', context: '128K', price: '$5', tags: ['Code', 'Writing'] },
  { id: 'claude-35', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', avatar: 'C3', color: 'blue', elo: 1798, delta: '+5', context: '200K', price: '$3', tags: ['Code', 'Creative'] },
  { id: 'gemini-15', name: 'Gemini 1.5 Pro', provider: 'Google', avatar: 'G', color: 'blue', elo: 1720, delta: '+8', context: '2M', price: '$1.25', tags: ['Analysis', 'Writing'] },
  { id: 'mixtral', name: 'Mixtral 8x7B', provider: 'Mistral AI', avatar: 'M', color: 'gold', elo: 1488, delta: '-7', context: '32K', price: '$0.24', tags: ['Open', 'Code'] },
  { id: 'llama', name: 'Llama 3.1 405B', provider: 'Meta', avatar: 'L', color: 'gold', elo: 1456, delta: '+2', context: '128K', price: '$0.90', tags: ['Open', 'Analysis'] },
];

const copy = {
  en: {
    vote: { title: 'Which model is better?', subtitle: 'Your signal shapes the community ranking.', prompt: 'Choose the model you trust for this task.', skip: 'Skip', unknown: "I don't know", saved: 'Vote saved. Your signal now counts.' },
    rankings: { title: 'Rankings', subtitle: 'Community-ranked AI models by category.', weekly: '7D TREND', elo: 'ELO' },
    models: { title: 'Models', subtitle: 'Browse approved models and compare their signal.', search: 'Search models...', all: 'All' },
    profile: { title: 'Your profile', since: 'Member since Sep 2026', votes: 'Votes cast', categories: 'Categories', streak: 'Day streak', recent: 'Recent votes' },
    nav: { vote: 'Vote', rankings: 'Rankings', models: 'Models', profile: 'Profile' },
    details: { context: 'Context', price: 'Price', elo: 'ELO', categories: 'Categories', close: 'Close' },
  },
  es: {
    vote: { title: '¿Qué modelo es mejor?', subtitle: 'Tu señal da forma al ranking de la comunidad.', prompt: 'Elige el modelo en el que confías para esta tarea.', skip: 'Saltar', unknown: 'No lo sé', saved: 'Voto guardado. Tu señal ya cuenta.' },
    rankings: { title: 'Rankings', subtitle: 'Modelos de IA rankeados por la comunidad.', weekly: 'TENDENCIA 7D', elo: 'ELO' },
    models: { title: 'Modelos', subtitle: 'Explora modelos aprobados y compara su señal.', search: 'Buscar modelos...', all: 'Todos' },
    profile: { title: 'Tu perfil', since: 'Miembro desde septiembre de 2026', votes: 'Votos emitidos', categories: 'Categorías', streak: 'Racha de días', recent: 'Votos recientes' },
    nav: { vote: 'Votar', rankings: 'Rankings', models: 'Modelos', profile: 'Perfil' },
    details: { context: 'Contexto', price: 'Precio', elo: 'ELO', categories: 'Categorías', close: 'Cerrar' },
  },
};

const t = (path) => path.split('.').reduce((value, key) => value?.[key], copy[state.language]) || path;
const icon = (name) => ({ vote: 'ϟ', rankings: '▥', models: '◈', profile: '◉', search: '⌕', theme: '◐' }[name] || '·');

function modelAvatar(model, sizeClass = '') {
  return `<div class="avatar ${model.color || ''} ${sizeClass}">${model.avatar}</div>`;
}

function topbar() {
  return `<header class="app-topbar">
    <div class="brand"><span class="brand-mark">ϟ</span><span>Forcecast</span></div>
    <div class="topbar-actions">
      <button data-action="search" aria-label="Search models">${icon('search')}</button>
      <button data-action="theme" aria-label="Toggle theme">${icon('theme')}</button>
    </div>
  </header>`;
}

function bottomNav() {
  const labels = ['vote', 'rankings', 'models', 'profile'];
  return `<nav class="bottom-nav" aria-label="Primary navigation">${labels.map((screen) => `
    <button class="nav-item ${state.screen === screen ? 'active' : ''}" data-screen="${screen}">
      <span>${icon(screen)}</span><span>${t(`nav.${screen}`)}</span>
    </button>`).join('')}</nav>`;
}

function voteScreen() {
  const first = models[0];
  const second = models[1];
  return `<main class="screen">
    <span class="section-kicker">Daily signal / 07 of 50</span>
    <h1 class="screen-title">${t('vote.title')}</h1>
    <p class="screen-subtitle">${t('vote.subtitle')}</p>
    <div class="chips">${['Code', 'Writing', 'Analysis', 'Creative', 'Math'].map((category) => `<button class="chip ${state.category === category ? 'active' : ''}" data-category="${category}">${category}</button>`).join('')}</div>
    <div class="progress-row"><span>${t('vote.prompt')}</span><span>14%</span></div><div class="progress"><span></span></div>
    <p class="vote-prompt">${state.category} / community comparison</p>
    <div class="vote-card">${contender(first)}<div class="vs">VS</div>${contender(second)}</div>
    <div class="footer-actions"><button class="ghost-button" data-action="skip">${t('vote.skip')}</button><button class="ghost-button" data-action="skip">${t('vote.unknown')}</button></div>
  </main>`;
}

function contender(model) {
  const selected = state.votedModel === model.id;
  return `<article class="contender ${selected ? 'selected' : ''}">${modelAvatar(model)}<h3>${model.name}</h3><p>${model.provider}</p><div class="stat-line"><span><strong>${model.context}</strong>ctx</span><span><strong>${model.price}</strong>/1M</span></div><span class="elo">◆ ${model.elo}</span><button class="vote-button" data-vote="${model.id}">${selected ? 'Selected' : 'Vote'}</button></article>`;
}

function rankingsScreen() {
  return `<main class="screen"><span class="section-kicker">Signal / public</span><h1 class="screen-title">${t('rankings.title')}</h1><p class="screen-subtitle">${t('rankings.subtitle')}</p><div class="tabs">${['Code', 'Writing', 'Analysis', 'All'].map((tab) => `<button class="tab ${state.category === tab || (tab === 'Code' && !['Writing', 'Analysis'].includes(state.category)) ? 'active' : ''}" data-category="${tab}">${tab}</button>`).join('')}</div><div class="rank-list">${models.map((model, index) => `<article class="rank-item"> <span class="rank-number ${index < 2 ? 'top' : ''}">${index + 1}</span>${modelAvatar(model, 'small')}<div class="item-copy"><strong>${model.name}</strong><span>${model.provider}</span></div><span class="item-score">${model.elo}</span><span class="delta ${model.delta.startsWith('-') ? 'down' : ''}">${model.delta}</span></article>`).join('')}</div></main>`;
}

function modelsScreen() {
  const filtered = models.filter((model) => `${model.name} ${model.provider} ${model.tags.join(' ')}`.toLowerCase().includes(state.query.toLowerCase()));
  return `<main class="screen"><span class="section-kicker">Catalog / approved</span><h1 class="screen-title">${t('models.title')}</h1><p class="screen-subtitle">${t('models.subtitle')}</p><input class="search" data-search value="${state.query}" placeholder="${t('models.search')}" aria-label="${t('models.search')}"><div class="tabs"><button class="tab active">${t('models.all')}</button><button class="tab">OpenAI</button><button class="tab">Anthropic</button><button class="tab">Open</button></div><div class="model-list">${filtered.length ? filtered.map(modelItem).join('') : `<p class="screen-subtitle">No models match your search.</p>`}</div></main>`;
}

function modelItem(model) {
  return `<article class="model-item" data-model="${model.id}">${modelAvatar(model)}<div class="item-copy"><strong>${model.name}</strong><span>${model.provider}</span><div class="model-tags">${model.tags.map((tag) => `<span class="tag">${tag}</span>`).join('')}</div></div><span class="item-score">${model.elo}</span></article>`;
}

function profileScreen() {
  return `<main class="screen"><span class="section-kicker">Account / reputation</span><h1 class="screen-title">${t('profile.title')}</h1><section class="profile-hero">${modelAvatar({ avatar: 'U', color: '' })}<h2>Forcecaster</h2><p>${t('profile.since')}</p><div class="badges"><span class="badge">TOP 10%</span><span class="badge gold">7-DAY STREAK</span></div></section><div class="stat-grid"><div class="stat-card"><strong>47</strong><span>${t('profile.votes')}</span></div><div class="stat-card"><strong>5</strong><span>${t('profile.categories')}</span></div><div class="stat-card"><strong>7</strong><span>${t('profile.streak')}</span></div></div><div class="section-label">${t('profile.recent')}</div><div class="recent">${[['G4', 'GPT-4o vs Claude 3.5', 'Code · 2 min ago', 'GPT-4o'], ['C3', 'Claude vs Gemini 1.5', 'Writing · 15 min ago', 'Claude'], ['G4', 'GPT-4o vs Llama 3.1', 'Code · 3 hours ago', 'GPT-4o']].map((vote, index) => `<article class="recent-item">${modelAvatar({ avatar: vote[0], color: index === 1 ? 'blue' : '' })}<div class="item-copy"><strong>${vote[1]}</strong><span>${vote[2]}</span></div><span class="recent-result">${vote[3]}</span></article>`).join('')}</div></main>`;
}

function render() {
  document.documentElement.dataset.theme = state.theme;
  const content = { vote: voteScreen, rankings: rankingsScreen, models: modelsScreen, profile: profileScreen }[state.screen]();
  document.getElementById('app').innerHTML = `${topbar()}${content}${bottomNav()}`;
  bindEvents();
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 2600);
}

function showModel(model) {
  document.getElementById('dialog-content').innerHTML = `<div class="dialog-model-head">${modelAvatar(model)}<div><h2>${model.name}</h2><p>${model.provider} · approved</p></div></div><div class="detail-grid"><div class="detail-cell"><span>${t('details.elo')}</span><strong>${model.elo}</strong></div><div class="detail-cell"><span>${t('details.context')}</span><strong>${model.context}</strong></div><div class="detail-cell"><span>${t('details.price')}</span><strong>${model.price} / 1M</strong></div><div class="detail-cell"><span>${t('details.categories')}</span><strong>${model.tags.join(' · ')}</strong></div></div><button class="primary-button" data-action="close-dialog">${t('details.close')}</button>`;
  document.getElementById('model-dialog').showModal();
  document.querySelectorAll('[data-action="close-dialog"]').forEach((button) => button.addEventListener('click', () => document.getElementById('model-dialog').close()));
}

function bindEvents() {
  document.querySelectorAll('[data-screen]').forEach((button) => button.addEventListener('click', () => { state.screen = button.dataset.screen; render(); }));
  document.querySelectorAll('[data-category]').forEach((button) => button.addEventListener('click', () => { state.category = button.dataset.category; render(); }));
  document.querySelectorAll('[data-vote]').forEach((button) => button.addEventListener('click', () => { state.votedModel = button.dataset.vote; showToast(t('vote.saved')); render(); }));
  document.querySelectorAll('[data-action="theme"]').forEach((button) => button.addEventListener('click', () => { state.theme = state.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('fc-copilot-theme', state.theme); render(); }));
  document.querySelectorAll('[data-action="language"]').forEach((button) => button.addEventListener('click', () => { state.language = state.language === 'en' ? 'es' : 'en'; localStorage.setItem('fc-copilot-language', state.language); render(); }));
  document.querySelectorAll('[data-action="skip"]').forEach((button) => button.addEventListener('click', () => showToast('Skipped for now')));
  document.querySelectorAll('[data-action="search"]').forEach((button) => button.addEventListener('click', () => { state.screen = 'models'; render(); document.querySelector('[data-search]')?.focus(); }));
  document.querySelectorAll('[data-model]').forEach((item) => item.addEventListener('click', () => showModel(models.find((model) => model.id === item.dataset.model))));
  document.querySelector('[data-search]')?.addEventListener('input', (event) => { state.query = event.target.value; render(); const input = document.querySelector('[data-search]'); input?.focus(); input?.setSelectionRange(state.query.length, state.query.length); });
}

render();
