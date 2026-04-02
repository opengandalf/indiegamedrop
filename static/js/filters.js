/**
 * Client-side filtering for IndieGameDrop list pages.
 * Handles search, genre, platform, price, rating, review-count, and sort options.
 */

let allGames = [];
let currentSort = '';
let gridId = '';

/**
 * Format a number with commas (e.g. 253546 → "253,546").
 */
function fmtNum(n) {
  return (n || 0).toLocaleString('en-GB');
}

/**
 * Initialize a filtered page.
 * @param {string} dataUrl - URL to fetch JSON data from.
 * @param {string} containerId - ID of the game grid container.
 * @param {string} defaultSort - Default sort field.
 */
function initFilteredPage(dataUrl, containerId, defaultSort) {
  gridId = containerId;
  currentSort = defaultSort;

  fetch(dataUrl)
    .then(r => r.json())
    .then(games => {
      allGames = games || [];
      if (allGames.length === 0) {
        const emptyState = document.getElementById('empty-state');
        if (emptyState) emptyState.style.display = 'block';
        return;
      }
      populateGenreFilter(allGames);

      // Set the sort dropdown to default if it exists as an option
      const sortSelect = document.getElementById('sort-filter');
      if (sortSelect && defaultSort) {
        const opt = sortSelect.querySelector(`option[value="${defaultSort}"]`);
        if (opt) sortSelect.value = defaultSort;
      }

      attachFilterListeners();
      applyFilters();
    })
    .catch(() => {
      const emptyState = document.getElementById('empty-state');
      if (emptyState) emptyState.style.display = 'block';
    });
}

/**
 * Populate the genre dropdown from game data.
 */
function populateGenreFilter(games) {
  const genreSet = new Set();
  games.forEach(g => {
    (g.genres || []).forEach(genre => genreSet.add(genre));
  });

  const select = document.getElementById('genre-filter');
  if (!select) return;

  Array.from(genreSet).sort().forEach(genre => {
    const opt = document.createElement('option');
    opt.value = genre;
    opt.textContent = genre;
    select.appendChild(opt);
  });
}

/**
 * Count how many non-default filters are currently active.
 */
function countActiveFilters() {
  const ids = ['genre-filter', 'platform-filter', 'price-filter', 'rating-filter', 'reviews-filter'];
  let count = 0;
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el && el.value) count++;
  });
  const searchEl = document.getElementById('search-input');
  if (searchEl && searchEl.value.trim()) count++;
  return count;
}

/**
 * Update the active-filter badge and clear-filters button visibility.
 */
function updateFilterUI(filteredCount) {
  const activeCount = countActiveFilters();

  // Badge on mobile toggle
  const badge = document.getElementById('filter-badge');
  if (badge) {
    if (activeCount > 0) {
      badge.textContent = activeCount;
      badge.style.display = 'inline-flex';
    } else {
      badge.style.display = 'none';
    }
  }

  // Toggle button label
  const toggleLabel = document.querySelector('#filters-toggle .toggle-label');
  if (toggleLabel) {
    toggleLabel.textContent = activeCount > 0 ? `Filters (${activeCount})` : 'Filters';
  }

  // Summary row
  const summaryEl = document.getElementById('filter-summary');
  const countEl = document.getElementById('results-count');
  const clearBtn = document.getElementById('clear-filters');

  if (summaryEl) {
    summaryEl.style.display = (activeCount > 0) ? 'flex' : 'none';
  }
  if (countEl) {
    countEl.textContent = `${filteredCount} game${filteredCount !== 1 ? 's' : ''} shown`;
  }
  if (clearBtn) {
    clearBtn.style.display = activeCount > 0 ? 'inline-block' : 'none';
  }
}

/**
 * Attach event listeners to filter controls.
 */
function attachFilterListeners() {
  const filterIds = ['genre-filter', 'platform-filter', 'price-filter', 'rating-filter', 'reviews-filter'];
  filterIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', applyFilters);
  });

  const sortFilter = document.getElementById('sort-filter');
  if (sortFilter) {
    sortFilter.addEventListener('change', function() {
      currentSort = this.value;
      applyFilters();
    });
  }

  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }

  // Mobile toggle
  const toggleBtn = document.getElementById('filters-toggle');
  const dropdowns = document.getElementById('filter-dropdowns');
  if (toggleBtn && dropdowns) {
    toggleBtn.addEventListener('click', function() {
      const expanded = this.getAttribute('aria-expanded') === 'true';
      this.setAttribute('aria-expanded', String(!expanded));
      dropdowns.classList.toggle('open', !expanded);
    });
  }

  // Clear filters button
  const clearBtn = document.getElementById('clear-filters');
  if (clearBtn) {
    clearBtn.addEventListener('click', clearAllFilters);
  }
}

/**
 * Reset all filters to their defaults.
 */
function clearAllFilters() {
  const filterIds = ['genre-filter', 'platform-filter', 'price-filter', 'rating-filter', 'reviews-filter'];
  filterIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';
  applyFilters();
}

/**
 * Apply all active filters and re-render.
 */
function applyFilters() {
  const genreVal    = (document.getElementById('genre-filter')    || {}).value || '';
  const platformVal = (document.getElementById('platform-filter') || {}).value || '';
  const priceVal    = (document.getElementById('price-filter')    || {}).value || '';
  const ratingVal   = (document.getElementById('rating-filter')   || {}).value || '';
  const reviewsVal  = (document.getElementById('reviews-filter')  || {}).value || '';
  const searchVal   = ((document.getElementById('search-input')   || {}).value || '').toLowerCase().trim();
  const sortVal     = (document.getElementById('sort-filter')     || {}).value || currentSort;
  if (sortVal) currentSort = sortVal;

  let filtered = [...allGames];

  // Search filter (name + developer)
  if (searchVal) {
    filtered = filtered.filter(g => {
      const name = (g.name || '').toLowerCase();
      const dev  = (g.developer || '').toLowerCase();
      return name.includes(searchVal) || dev.includes(searchVal);
    });
  }

  // Genre filter
  if (genreVal) {
    filtered = filtered.filter(g => (g.genres || []).includes(genreVal));
  }

  // Platform filter
  if (platformVal) {
    filtered = filtered.filter(g => (g.platforms || []).includes(platformVal));
  }

  // Price filter
  if (priceVal) {
    filtered = filtered.filter(g => {
      const price = g.price_usd || 0;
      switch (priceVal) {
        case 'free':  return price === 0;
        case '0-5':   return price > 0 && price <= 5;
        case '5-10':  return price > 5 && price <= 10;
        case '10-20': return price > 10 && price <= 20;
        case '20+':   return price > 20;
        default:      return true;
      }
    });
  }

  // Rating filter
  if (ratingVal) {
    const minRating = parseInt(ratingVal, 10);
    filtered = filtered.filter(g => (g.review_percentage || 0) >= minRating);
  }

  // Review count filter
  if (reviewsVal) {
    const minReviews = parseInt(reviewsVal, 10);
    filtered = filtered.filter(g => (g.review_count || 0) >= minReviews);
  }

  // Sort
  if (currentSort) {
    filtered = sortGames(filtered, currentSort);
  }

  renderGames(filtered);
  updateFilterUI(filtered.length);
}

/**
 * Sort games by the given sort key.
 */
function sortGames(games, sortKey) {
  const copy = [...games];
  switch (sortKey) {
    case 'name_az':
      return copy.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    case 'newest':
      return copy.sort((a, b) => {
        // release_date is a string like "Jun 7, 2019" — parse to Date for comparison
        const da = new Date(a.release_date || 0);
        const db = new Date(b.release_date || 0);
        return db - da;
      });
    case 'review_count':
      return copy.sort((a, b) => (b.review_count || 0) - (a.review_count || 0));
    case 'review_percentage':
      return copy.sort((a, b) => (b.review_percentage || 0) - (a.review_percentage || 0));
    default:
      // Numeric field sort (gem_score, rising_score, price_usd, etc.)
      return copy.sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        // Handle "price_usd" ascending (cheaper first) as a special case
        if (sortKey === 'price_usd') return (av || 0) - (bv || 0);
        return (bv || 0) - (av || 0);
      });
  }
}

/**
 * Render game cards into the grid.
 */
function renderGames(games) {
  const container = document.getElementById(gridId);
  if (!container) return;

  const emptyState = document.getElementById('empty-state');

  if (games.length === 0) {
    container.innerHTML = '';
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  if (emptyState) emptyState.style.display = 'none';

  // Determine baseURL — find a script tag with known path
  const scripts = document.querySelectorAll('script[src]');
  let baseURL = '/';
  scripts.forEach(s => {
    const idx = s.src.indexOf('js/filters.js');
    if (idx > -1) {
      const origin = new URL(s.src).origin;
      baseURL = s.src.substring(origin.length, idx);
    }
  });

  container.innerHTML = games.map(game => {
    const reviewPct = game.review_percentage || 0;
    let reviewClass = 'positive';
    if (reviewPct < 70) reviewClass = 'mixed';
    if (reviewPct < 40) reviewClass = 'negative';

    const price = game.price_usd === 0
      ? '<span class="price-tag free">Free</span>'
      : `<span class="price-tag">$${(game.price_usd || 0).toFixed(2)}</span>`;

    const genres = (game.genres || []).slice(0, 3)
      .map(g => `<span class="tag">${g}</span>`).join('');

    const changeHtml = game.rising_score
      ? `<span class="change-indicator up">Rising: ${game.rising_score.toFixed(2)}</span>`
      : (game.gem_score
        ? `<span class="change-indicator up">Gem: ${game.gem_score.toFixed(2)}</span>`
        : '');

    return `
      <div class="game-card" data-genres="${(game.genres || []).join(',')}" data-price="${game.price_usd || 0}">
        <a href="${baseURL}game/?slug=${game.slug}">
          <img src="${game.header_image_url}" alt="${game.name}" loading="lazy"
               onerror="this.src='https://cdn.akamai.steamstatic.com/steam/apps/0/header.jpg'">
        </a>
        <div class="card-body">
          <h3 class="card-title"><a href="${baseURL}game/?slug=${game.slug}">${game.name}</a></h3>
          <div class="card-meta">
            <span class="review-score ${reviewClass}">${reviewPct.toFixed(0)}%</span>
            <span>${fmtNum(game.review_count)} reviews</span>
            ${price}
          </div>
          ${changeHtml ? `<div class="card-meta">${changeHtml}</div>` : ''}
          <div class="tags">${genres}</div>
        </div>
      </div>`;
  }).join('');
}
