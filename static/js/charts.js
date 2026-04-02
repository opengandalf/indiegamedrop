/**
 * Chart.js wrapper for IndieGameDrop.
 * Renders line charts for game profiles and bar charts for data explorer.
 */

/** @type {Object} Default dataset styling for Chart.js */
const chartDefaults = {
  borderColor: '#58a6ff',
  backgroundColor: 'rgba(88, 166, 255, 0.1)',
  pointRadius: 3,
  pointBackgroundColor: '#58a6ff',
  tension: 0.3,
  fill: true,
};

/** @type {Object} Shared Chart.js options (dark theme, no legend) */
const chartOptions = {
  responsive: true,
  plugins: {
    legend: { display: false },
  },
  scales: {
    x: {
      grid: { color: '#30363d' },
      ticks: { color: '#8b949e' },
    },
    y: {
      grid: { color: '#30363d' },
      ticks: { color: '#8b949e' },
      beginAtZero: true,
    },
  },
};

/**
 * Render a line chart on the given canvas ID.
 * @param {string} canvasId - Canvas element ID.
 * @param {string[]} labels - X-axis labels.
 * @param {number[]} data - Data points.
 * @param {string} [label] - Dataset label.
 * @param {string} [color] - Line colour override.
 * @returns {Chart|null} Chart instance or null if canvas not found.
 */
function renderLineChart(canvasId, labels, data, label, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const borderColor = color || chartDefaults.borderColor;
  const bgColor = color ? color.replace(')', ', 0.1)').replace('rgb', 'rgba') : chartDefaults.backgroundColor;

  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label || 'Value',
        data: data,
        borderColor: borderColor,
        backgroundColor: bgColor,
        pointRadius: chartDefaults.pointRadius,
        pointBackgroundColor: borderColor,
        tension: chartDefaults.tension,
        fill: chartDefaults.fill,
      }],
    },
    options: chartOptions,
  });
}

/**
 * Render a bar chart on the given canvas ID.
 * @param {string} canvasId - Canvas element ID.
 * @param {string[]} labels - X-axis labels.
 * @param {number[]} data - Data points.
 * @param {string} [label] - Dataset label.
 * @param {string} [color] - Bar colour override.
 * @returns {Chart|null} Chart instance or null if canvas not found.
 */
function renderBarChart(canvasId, labels, data, label, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const bgColor = color || chartDefaults.borderColor;

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label || 'Count',
        data: data,
        backgroundColor: bgColor + '99',
        borderColor: bgColor,
        borderWidth: 1,
      }],
    },
    options: {
      ...chartOptions,
      plugins: {
        ...chartOptions.plugins,
        legend: { display: false },
      },
    },
  });
}

/**
 * Render all charts for a game profile page.
 * Expects game.history to be an array of { date, review_count, ccu_estimate, review_percentage }.
 * @param {Object} game - Game data with history array.
 */
function renderGameCharts(game) {
  const history = game.history || [];
  if (history.length === 0) return;

  const labels = history.map(h => h.date);

  // Review count chart
  const reviewData = history.map(h => h.review_count || 0);
  renderLineChart('chart-reviews', labels, reviewData, 'Reviews', '#58a6ff');

  // CCU chart
  const ccuData = history.map(h => h.ccu_estimate || 0);
  renderLineChart('chart-ccu', labels, ccuData, 'Players', '#3fb950');

  // Review score trend
  const scoreData = history.map(h => h.review_percentage || 0);
  renderLineChart('chart-score', labels, scoreData, 'Review %', '#d29922');
}
