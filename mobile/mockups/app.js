/**
 * Forcecast Mobile Mockups — App Engine
 *
 * Vanilla JS template engine + i18n + theme toggle + screen router.
 * Zero dependencies. Works with static HTML mockups.
 *
 * Usage:
 *   FC.init({ lang: 'en', theme: 'dark' });
 *   FC.router.navigate('vote');
 *   FC.i18n.t('vote.title');
 *   FC.theme.toggle();
 */

const FC = (() => {
  // ─── i18n ───────────────────────────────────────────────
  const translations = {
    en: {
      app: { name: 'Forcecast', tagline: 'Community-driven AI rankings' },
      nav: { vote: 'Vote', rankings: 'Rankings', models: 'Models', profile: 'Profile' },
      vote: {
        title: 'Which model is better?',
        category: 'Category',
        skip: 'Skip',
        dontKnow: "Don't Know",
        match: '{current} / {total}',
        voted: 'Vote saved!',
      },
      rankings: {
        title: 'Rankings',
        subtitle: 'Community-ranked AI models by category',
        noVotes: 'No votes in this category yet',
      },
      models: {
        title: 'Models',
        subtitle: 'Browse all AI models',
        search: 'Search models...',
        context: 'Context',
        maxOut: 'Max Output',
        price: 'Price',
        perMillion: '/1M tokens',
      },
      profile: {
        title: 'Your Profile',
        votesCast: 'Votes Cast',
        categoriesExplored: 'Categories',
        streak: 'Day Streak',
        recentVotes: 'Recent Votes',
      },
      elo: {
        elite: 'Elite',
        strong: 'Strong',
        average: 'Average',
        emerging: 'Emerging',
      },
      errors: {
        network: 'No internet connection',
        networkDesc: 'Check your connection and try again.',
        server: 'Something went wrong',
        serverDesc: "We couldn't load the data. Please try again.",
        retry: 'Retry',
        goBack: 'Go Back',
      },
      toast: {
        voteSaved: 'Vote saved',
        voteSavedDesc: 'Your vote has been recorded.',
        connectionLost: 'Connection lost',
        connectionLostDesc: 'Your vote will be saved when you\'re back online.',
      },
    },
    es: {
      app: { name: 'Forcecast', tagline: 'Rankings de IA impulsados por la comunidad' },
      nav: { vote: 'Votar', rankings: 'Rankings', models: 'Modelos', profile: 'Perfil' },
      vote: {
        title: '¿Qué modelo es mejor?',
        category: 'Categoría',
        skip: 'Saltar',
        dontKnow: 'No Sé',
        match: '{current} / {total}',
        voted: '¡Voto guardado!',
      },
      rankings: {
        title: 'Rankings',
        subtitle: 'Modelos de IA rankeados por categoría',
        noVotes: 'Aún no hay votos en esta categoría',
      },
      models: {
        title: 'Modelos',
        subtitle: 'Explorar todos los modelos de IA',
        search: 'Buscar modelos...',
        context: 'Contexto',
        maxOut: 'Salida Máx',
        price: 'Precio',
        perMillion: '/1M tokens',
      },
      profile: {
        title: 'Tu Perfil',
        votesCast: 'Votos Emitidos',
        categoriesExplored: 'Categorías',
        streak: 'Racha de Días',
        recentVotes: 'Votos Recientes',
      },
      elo: {
        elite: 'Élite',
        strong: 'Fuerte',
        average: 'Promedio',
        emerging: 'Emergente',
      },
      errors: {
        network: 'Sin conexión a internet',
        networkDesc: 'Revisa tu conexión e intenta de nuevo.',
        server: 'Algo salió mal',
        serverDesc: 'No pudimos cargar los datos. Intenta de nuevo.',
        retry: 'Reintentar',
        goBack: 'Volver',
      },
      toast: {
        voteSaved: 'Voto guardado',
        voteSavedDesc: 'Tu voto ha sido registrado.',
        connectionLost: 'Conexión perdida',
        connectionLostDesc: 'Tu voto se guardará cuando vuelvas a estar en línea.',
      },
    },
  };

  let currentLang = 'en';

  function t(key, params = {}) {
    const keys = key.split('.');
    let value = translations[currentLang];
    for (const k of keys) {
      value = value?.[k];
    }
    if (typeof value !== 'string') return key;
    return Object.entries(params).reduce(
      (str, [k, v]) => str.replace(new RegExp(`\\{${k}\\}`, 'g'), v),
      value
    );
  }

  function setLang(lang) {
    if (!translations[lang]) return;
    currentLang = lang;
    document.documentElement.setAttribute('lang', lang);
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const params = el.getAttribute('data-i18n-params');
      el.textContent = t(key, params ? JSON.parse(params) : {});
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
  }

  // ─── Theme ──────────────────────────────────────────────
  const THEMES = {
    dark: 'dark',
    light: 'light',
    'jedi-dark': 'jedi-dark',
    'jedi-light': 'jedi-light',
  };

  let currentTheme = 'dark';

  function setTheme(theme) {
    if (!THEMES[theme]) return;
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('fc-theme', theme); } catch {}
  }

  function toggleTheme() {
    const cycle = ['dark', 'light', 'jedi-dark', 'jedi-light'];
    const idx = cycle.indexOf(currentTheme);
    setTheme(cycle[(idx + 1) % cycle.length]);
  }

  function getEloTier(rating) {
    if (rating >= 1800) return 'elite';
    if (rating >= 1600) return 'strong';
    if (rating >= 1400) return 'average';
    return 'emerging';
  }

  // ─── Template Engine ────────────────────────────────────
  function render(template, data) {
    return template.replace(/\{\{(.+?)\}\}/g, (_, expr) => {
      const trimmed = expr.trim();
      if (trimmed.startsWith('#')) {
        // Block: {{#items}}...{{/items}}
        return '';
      }
      return resolve(trimmed, data) ?? '';
    });
  }

  function resolve(expr, data) {
    return expr.split('.').reduce((obj, key) => obj?.[key], data);
  }

  function renderList(template, items, data = {}) {
    return items.map((item, i) => {
      const merged = { ...data, item, index: i };
      return render(template, merged);
    }).join('');
  }

  // ─── Router ─────────────────────────────────────────────
  let currentScreen = 'vote';
  const listeners = [];

  function navigate(screen) {
    currentScreen = screen;
    document.querySelectorAll('.fc-screen').forEach((el) => {
      el.style.display = el.id === `screen-${screen}` ? 'block' : 'none';
    });
    document.querySelectorAll('.fc-bottom-nav__item, .fc-navbar__link').forEach((el) => {
      el.classList.toggle('fc-bottom-nav__item--active', el.dataset.screen === screen);
      el.classList.toggle('fc-navbar__link--active', el.dataset.screen === screen);
    });
    listeners.forEach((fn) => fn(screen));
  }

  function onNavigate(fn) {
    listeners.push(fn);
  }

  // ─── Toast ──────────────────────────────────────────────
  function showToast(variant, title, message, duration = 3000) {
    const container = document.querySelector('.fc-toast-container');
    if (!container) return;

    const icons = {
      success: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
      error: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
      warning: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
      info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    };

    const toast = document.createElement('div');
    toast.className = `fc-toast fc-toast--${variant}`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <svg class="fc-toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[variant]}</svg>
      <div class="fc-toast__content">
        <span class="fc-toast__title">${title}</span>
        ${message ? `<span class="fc-toast__message">${message}</span>` : ''}
      </div>
      <button class="fc-toast__close" aria-label="Dismiss" onclick="this.closest('.fc-toast').remove()">×</button>
    `;
    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add('fc-toast--exiting');
        setTimeout(() => toast.remove(), 200);
      }, duration);
    }
  }

  // ─── Init ───────────────────────────────────────────────
  function init(opts = {}) {
    const { lang = 'en', theme = 'dark' } = opts;

    // Restore theme from localStorage
    const saved = (() => { try { return localStorage.getItem('fc-theme'); } catch { return null; } })();
    setTheme(saved || theme);
    setLang(lang);

    // Bind nav clicks
    document.querySelectorAll('[data-screen]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        navigate(el.dataset.screen);
      });
    });

    // Theme toggle button
    document.querySelectorAll('[data-action="toggle-theme"]').forEach((el) => {
      el.addEventListener('click', () => toggleTheme());
    });

    // Language toggle
    document.querySelectorAll('[data-action="toggle-lang"]').forEach((el) => {
      el.addEventListener('click', () => {
        setLang(currentLang === 'en' ? 'es' : 'en');
      });
    });

    // Default screen
    navigate(currentScreen);
  }

  // ─── Public API ─────────────────────────────────────────
  return {
    init,
    i18n: { t, setLang, getLang: () => currentLang },
    theme: { set: setTheme, toggle: toggleTheme, get: () => currentTheme },
    router: { navigate, onNavigate, current: () => currentScreen },
    toast: { show: showToast },
    render,
    renderList,
    getEloTier,
  };
})();

// Auto-init if DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => FC.init());
} else {
  FC.init();
}
