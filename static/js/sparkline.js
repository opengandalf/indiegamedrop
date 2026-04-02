/**
 * Tiny inline sparkline charts for game cards.
 * Canvas-based, lightweight. Shows 7-day review/follower trend.
 */

/**
 * Draw a sparkline on a canvas element.
 * @param {HTMLCanvasElement} canvas - The canvas to draw on.
 * @param {number[]} data - Array of data points.
 * @param {string} color - Line colour (default: green for uptrend, red for downtrend).
 */
function drawSparkline(canvas, data, color) {
  if (!canvas || !data || data.length < 2) return;

  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 2;

  // Determine colour from trend if not specified
  if (!color) {
    const trend = data[data.length - 1] - data[0];
    color = trend >= 0 ? '#3fb950' : '#f85149';
  }

  // Normalize data to canvas height
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((val, i) => ({
    x: padding + (i / (data.length - 1)) * (width - padding * 2),
    y: height - padding - ((val - min) / range) * (height - padding * 2),
  }));

  // Clear
  ctx.clearRect(0, 0, width, height);

  // Draw line
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';

  points.forEach((point, i) => {
    if (i === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();

  // Fill area under the line
  ctx.lineTo(points[points.length - 1].x, height);
  ctx.lineTo(points[0].x, height);
  ctx.closePath();
  ctx.fillStyle = color.replace(')', ', 0.15)').replace('rgb', 'rgba');
  if (color.startsWith('#')) {
    ctx.fillStyle = color + '26'; // ~15% opacity hex
  }
  ctx.fill();
}

/**
 * Initialize sparklines on the page.
 * Looks for elements with data-sparkline attribute and fetches game data.
 * @param {string} baseURL - Base URL for data fetching (currently unused).
 */
function initSparklines(baseURL) {
  const elements = document.querySelectorAll('[data-sparkline]');
  elements.forEach(el => {
    const appId = el.getAttribute('data-sparkline');
    if (!appId) return;

    // Create canvas inside the container
    const canvas = document.createElement('canvas');
    canvas.width = 60;
    canvas.height = 20;
    canvas.className = 'sparkline-canvas';
    el.appendChild(canvas);

    // For now, generate sample trend data (will be replaced with real data)
    const sampleData = generateSampleTrend(7);
    drawSparkline(canvas, sampleData);
  });
}

/**
 * Generate sample trend data for demo purposes.
 * Will be replaced by real snapshot data when available.
 * @param {number} points - Number of data points to generate.
 * @returns {number[]} Array of trend values.
 */
function generateSampleTrend(points) {
  const data = [100];
  for (let i = 1; i < points; i++) {
    const change = (Math.random() - 0.3) * 10;
    data.push(Math.max(0, data[i - 1] + change));
  }
  return data;
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() { initSparklines(''); }, 500);
});
