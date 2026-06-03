/* Radar de Viagens — Dashboard JS (vanilla ES2020, sem dependências) */

const TYPE_ICONS = {
  flight: '✈',
  hotel: '🏨',
  cruise_repositioning: '🚢',
  package: '📦',
};

const TYPE_LABELS = {
  flight: 'Voo',
  hotel: 'Hotel',
  cruise_repositioning: 'Cruzeiro',
  package: 'Pacote',
};

let allDeals = [];
let activeFilter = 'all';
let activeSort = 'score';

async function loadData() {
  try {
    const [topRes, flightsRes, hotelsRes, cruisesRes, packagesRes] = await Promise.all([
      fetch('data/top_deals.json'),
      fetch('data/flights_latest.json'),
      fetch('data/hotels_latest.json'),
      fetch('data/cruises_latest.json'),
      fetch('data/packages_latest.json'),
    ]);

    const top = await topRes.json();
    const flights = flightsRes.ok ? (await flightsRes.json()).deals || [] : [];
    const hotels  = hotelsRes.ok  ? (await hotelsRes.json()).deals  || [] : [];
    const cruises = cruisesRes.ok ? (await cruisesRes.json()).deals || [] : [];
    const pkgs    = packagesRes.ok? (await packagesRes.json()).deals|| [] : [];

    allDeals = [...flights, ...hotels, ...cruises, ...pkgs];

    // Preenche resumo
    document.getElementById('stat-total').textContent  = top.total_deals_found ?? allDeals.length;
    document.getElementById('stat-discount').textContent = (top.stats?.best_discount ?? 0).toFixed(1) + '%';
    document.getElementById('stat-cruises').textContent  = top.stats?.cruises_found ?? 0;
    document.getElementById('stat-sources').textContent  = top.sources_consulted ?? '—';

    // Timestamp
    if (top.generated_at) {
      const d = new Date(top.generated_at);
      document.getElementById('last-updated').textContent =
        'Atualizado: ' + d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    }

    renderDeals();
  } catch (err) {
    document.getElementById('deals-grid').innerHTML =
      `<div id="empty">⚠ Não foi possível carregar os dados. Tente novamente mais tarde.<br><small>${err.message}</small></div>`;
  }
}

function formatBRL(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}

function renderDeals() {
  const grid = document.getElementById('deals-grid');
  let deals = [...allDeals];

  // Filtro por tipo
  if (activeFilter !== 'all') {
    deals = deals.filter(d =>
      activeFilter === 'cruise' ? d.type.includes('cruise') : d.type === activeFilter
    );
  }

  // Ordenação
  deals.sort((a, b) => {
    if (activeSort === 'score')    return (b.score ?? 0) - (a.score ?? 0);
    if (activeSort === 'price')    return (a.total_3pax_brl ?? 0) - (b.total_3pax_brl ?? 0);
    if (activeSort === 'discount') return (b.discount_pct ?? 0) - (a.discount_pct ?? 0);
    if (activeSort === 'date')     return (a.outbound_date ?? '').localeCompare(b.outbound_date ?? '');
    return 0;
  });

  if (deals.length === 0) {
    grid.innerHTML = '<div id="empty">Nenhuma oferta encontrada para este filtro.</div>';
    return;
  }

  grid.innerHTML = deals.map(deal => cardHTML(deal)).join('');
}

function cardHTML(deal) {
  const icon    = TYPE_ICONS[deal.type] ?? '🎯';
  const typeLabel = TYPE_LABELS[deal.type] ?? deal.type;
  const label   = (deal.label ?? 'FAIR').toLowerCase();
  const badgeClass = `badge-${label}`;
  const discountText = deal.discount_pct > 0 ? ` −${deal.discount_pct}%` : '';
  const barWidth = Math.min(Math.max(deal.discount_pct ?? 0, 0), 80);

  let meta = `<div class="deal-meta">`;
  if (deal.source) meta += `Fonte: ${deal.source}<br>`;
  if (deal.outbound_date) {
    meta += `📅 ${deal.outbound_date}`;
    if (deal.return_date) meta += ` → ${deal.return_date}`;
    if (deal.nights) meta += ` (${deal.nights} noites)`;
    meta += `<br>`;
  }
  if (deal.airline) meta += `✈ ${deal.airline}`;
  if (deal.stops !== undefined && deal.type === 'flight') meta += ` · ${deal.stops === 0 ? 'Direto' : deal.stops + ' escala(s)'}`;
  if (deal.airline) meta += `<br>`;
  if (deal.ship) meta += `🚢 ${deal.ship} · ${deal.departure_port ?? ''} → ${deal.arrival_port ?? ''}<br>`;
  if (deal.hotel_name) meta += `🏨 ${deal.hotel_name}${ deal.hotel_stars ? ` · ${deal.hotel_stars}★` : ''}<br>`;
  meta += `</div>`;

  return `
  <div class="deal-card ${label}">
    <div class="deal-card-body">
      <div class="deal-header">
        <span class="deal-type-icon">${icon}</span>
        <span class="deal-badge ${badgeClass}">${deal.label ?? 'FAIR'}${discountText}</span>
        <span style="margin-left:auto;font-size:11px;color:#718096;">${typeLabel}</span>
      </div>
      <div class="deal-title">${deal.title ?? ''}</div>
      <div class="deal-price">${formatBRL(deal.total_3pax_brl ?? 0)}</div>
      <div class="deal-price-sub">para 3 passageiros${deal.price_brl ? ` · ${formatBRL(deal.price_brl)} /pax` : ''}</div>
      <div class="deal-discount-bar">
        <div class="deal-discount-fill" style="width:${barWidth}%"></div>
      </div>
      ${meta}
      <a class="deal-cta" href="${deal.booking_url ?? '#'}" target="_blank" rel="noopener">Ver Oferta →</a>
    </div>
  </div>`;
}

// ── FILTROS E ORDENAÇÃO ──────────────────────────
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderDeals();
  });
});

document.getElementById('sort-select').addEventListener('change', e => {
  activeSort = e.target.value;
  renderDeals();
});

// ── INIT ─────────────────────────────────────────
loadData();
