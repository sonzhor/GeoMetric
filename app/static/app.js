const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const LEVEL_MAP = {
  highly_developed: { label: 'Высоко развитый', color: '#34d399' },
  developed: { label: 'Развитый', color: '#38bdf8' },
  moderately_developed: { label: 'Умеренно развитый', color: '#fbbf24' },
  developing: { label: 'Развивающийся', color: '#fb923c' },
  underdeveloped: { label: 'Слабо развитый', color: '#f87171' },
};

const IND_LABELS = {
  population_density: 'Плотность населения',
  green_space_ratio: 'Зелёные зоны',
  infrastructure_index: 'Инфраструктура',
  transport_access: 'Транспорт',
  economic_activity: 'Экономика',
};

// ---------- Map (Leaflet) ----------
let map = null;
let mapMarker = null;
let mapPoint = null; // {lat, lon}

function initMap() {
  if (map) {
    setTimeout(() => map.invalidateSize(), 100);
    return;
  }
  map = L.map('map', { zoomControl: true }).setView([55.75, 37.62], 5);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OSM &copy; CARTO',
    maxZoom: 18,
  }).addTo(map);

  map.on('click', (e) => {
    mapPoint = { lat: e.latlng.lat, lon: e.latlng.lng };
    if (mapMarker) map.removeLayer(mapMarker);
    mapMarker = L.marker([mapPoint.lat, mapPoint.lon]).addTo(map);
    $('#map-coords').textContent =
      `${mapPoint.lat.toFixed(5)}, ${mapPoint.lon.toFixed(5)}`;
  });
}

// ---------- Tabs ----------
$$('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    $$('.tab').forEach((b) => b.classList.remove('active'));
    $$('.panel').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    $(`#panel-${btn.dataset.tab}`).classList.add('active');
    if (btn.dataset.tab === 'map') initMap();
  });
});

$$('.quick-cities button').forEach((btn) => {
  btn.addEventListener('click', () => { $('#city').value = btn.dataset.city; });
});

$('#radius').addEventListener('input', (e) => {
  $('#radius-val').textContent = e.target.value;
});

function setLoading(on) {
  const btn = $('#analyze-btn');
  btn.disabled = on;
  $('.btn-text').classList.toggle('hidden', on);
  $('.btn-loader').classList.toggle('hidden', !on);
}

function showError(msg) {
  $('#error').classList.remove('hidden');
  $('#error-msg').textContent = msg;
  $('#result').classList.add('hidden');
  $('#compare-result').classList.add('hidden');
}

function formatInd(key, val) {
  if (key === 'population_density') return `${Number(val).toLocaleString('ru-RU')} чел/км²`;
  if (typeof val === 'number' && val <= 1) return `${(val * 100).toFixed(1)}%`;
  return val;
}

// ---------- Analyze ----------
async function analyze() {
  const activeTab = $('.tab.active').dataset.tab;
  const radius = $('#radius').value;

  $('#error').classList.add('hidden');
  $('#result').classList.add('hidden');
  $('#compare-result').classList.add('hidden');
  setLoading(true);

  try {
    if (activeTab === 'compare') {
      await doCompare(radius);
    } else {
      let url;
      if (activeTab === 'city') {
        const city = $('#city').value.trim();
        if (!city) throw new Error('Введите название города');
        url = `/analyze?city=${encodeURIComponent(city)}&radius_km=${radius}`;
      } else if (activeTab === 'coords') {
        const lat = $('#lat').value, lon = $('#lon').value;
        if (lat === '' || lon === '') throw new Error('Укажите широту и долготу');
        url = `/analyze?lat=${lat}&lon=${lon}&radius_km=${radius}`;
      } else if (activeTab === 'map') {
        if (!mapPoint) throw new Error('Кликните на карту, чтобы выбрать точку');
        url = `/analyze?lat=${mapPoint.lat}&lon=${mapPoint.lon}&radius_km=${radius}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка запроса');
      renderResult(data);
    }
  } catch (err) {
    showError(err.message || 'Не удалось выполнить запрос');
  } finally {
    setLoading(false);
  }
}

async function doCompare(radius) {
  const lines = $('#compare-list').value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  if (lines.length < 2) throw new Error('Нужно минимум 2 локации');
  if (lines.length > 5) throw new Error('Максимум 5 локаций');

  const res = await fetch('/analyze/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ locations: lines, radius_km: Number(radius) }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Ошибка сравнения');
  renderCompare(data);
}

function renderResult(data) {
  const pred = data.prediction;
  const score = pred.development_score;
  const level = LEVEL_MAP[pred.development_level] || { label: pred.development_level, color: '#94a3b8' };

  $('#result').classList.remove('hidden');
  $('#result-title').textContent =
    data.input_type === 'city' ? data.query : 'Точка на карте';
  $('#result-coords').textContent =
    `${data.coordinates.lat}, ${data.coordinates.lon} · радиус ${data.radius_km} км`;

  $('#score-value').textContent = score;
  $('#level-label').textContent = level.label;
  $('#level-label').style.color = level.color;
  const fill = $('#level-fill');
  fill.style.width = `${score}%`;
  fill.style.background = `linear-gradient(90deg, ${level.color}, ${level.color}aa)`;

  const grid = $('#indicators');
  grid.innerHTML = '';
  Object.entries(data.indicators).forEach(([k, v]) => {
    const el = document.createElement('div');
    el.className = 'ind-item';
    el.innerHTML = `<div class="name">${IND_LABELS[k] || k}</div><div class="val">${formatInd(k, v)}</div>`;
    grid.appendChild(el);
  });

  const factors = $('#factors');
  factors.innerHTML = '';
  const maxImp = Math.max(...pred.top_contributing_factors.map((f) => f.importance), 0.01);
  pred.top_contributing_factors.forEach((f) => {
    const el = document.createElement('div');
    el.className = 'factor';
    const pct = Math.round((f.importance / maxImp) * 100);
    el.innerHTML = `
      <div class="factor-name">${IND_LABELS[f.feature] || f.feature}</div>
      <div class="factor-bar-bg"><div class="factor-bar" style="width:${pct}%"></div></div>
      <div class="factor-pct">${(f.importance * 100).toFixed(0)}%</div>`;
    factors.appendChild(el);
  });

  $('#raw-json').textContent = JSON.stringify(data, null, 2);
}

function renderCompare(data) {
  $('#compare-result').classList.remove('hidden');
  const best = data.best;
  $('#compare-summary').textContent =
    `Лучший результат: ${typeof best.query === 'string' ? best.query : JSON.stringify(best.query)} ` +
    `(${best.score}) · разброс score: ${data.score_delta}`;

  const rows = data.results.map((r, i) => {
    const q = typeof r.query === 'string' ? r.query : `${r.coordinates.lat.toFixed(3)}, ${r.coordinates.lon.toFixed(3)}`;
    const level = LEVEL_MAP[r.prediction.development_level];
    const isBest = i === best.index;
    return `<tr class="${isBest ? 'best' : ''}">
      <td>${q}${isBest ? '<span class="badge-best">best</span>' : ''}</td>
      <td class="score-cell">${r.prediction.development_score}</td>
      <td style="color:${level ? level.color : '#94a3b8'}">${level ? level.label : r.prediction.development_level}</td>
      <td>${r.indicators.infrastructure_index}</td>
      <td>${r.indicators.economic_activity}</td>
      <td>${r.indicators.green_space_ratio}</td>
    </tr>`;
  }).join('');

  $('#compare-table').innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Локация</th>
          <th>Score</th>
          <th>Уровень</th>
          <th>Инфра</th>
          <th>Экономика</th>
          <th>Зелень</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  $('#compare-raw').textContent = JSON.stringify(data, null, 2);
}

$('#analyze-btn').addEventListener('click', analyze);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') analyze();
});
