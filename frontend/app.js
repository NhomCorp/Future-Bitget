(() => {
  'use strict';

  const STORAGE_KEY = 'future-bitget-zone-desk-v1';
  const state = { zones: [], selectedId: null, observations: {}, storageAvailable: true };
  const $ = (selector) => document.querySelector(selector);
  const elements = {
    zoneList: $('#zone-list'), zoneCount: $('#zone-count'), emptyState: $('#empty-state'),
    detailEmpty: $('#detail-empty'), detailContent: $('#detail-content'), detailSummary: $('#detail-summary'),
    selectedId: $('#selected-id'), observationResult: $('#observation-result'), notice: $('#notice'),
    createForm: $('#create-form'), createError: $('#create-error'), syncForm: $('#sync-form'),
    syncError: $('#sync-error'), activateButton: $('#activate-button'), localState: $('#local-state')
  };

  function readStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || data.version !== 1 || !Array.isArray(data.zones) || !data.observations || typeof data.observations !== 'object' || Array.isArray(data.observations)) {
        throw new Error('invalid stored data');
      }
      const validZones = data.zones.every((zone) => zone && typeof zone.zone_id === 'string' && typeof zone.symbol === 'string' && typeof zone.side === 'string' && typeof zone.state === 'string' && typeof zone.config === 'object');
      if (!validZones) throw new Error('invalid stored zone');
      state.zones = data.zones;
      state.observations = data.observations;
      if (state.zones.length) state.selectedId = state.zones[0].zone_id;
    } catch {
      state.zones = [];
      state.observations = {};
      state.storageAvailable = false;
      showNotice('Dữ liệu demo lưu trên trình duyệt không hợp lệ hoặc không đọc được. Đã bỏ qua dữ liệu đó.', true);
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, zones: state.zones, observations: state.observations }));
      state.storageAvailable = true;
      elements.localState.textContent = 'Lưu trong trình duyệt';
      return true;
    } catch {
      state.storageAvailable = false;
      elements.localState.textContent = 'Không lưu được dữ liệu';
      showNotice('Không lưu được dữ liệu demo. Hãy kiểm tra dung lượng lưu của trình duyệt.', true);
      return false;
    }
  }

  function showNotice(message, isError = false) {
    elements.notice.textContent = message;
    elements.notice.hidden = false;
    elements.notice.classList.toggle('is-error', isError);
    window.clearTimeout(showNotice.timeout);
    showNotice.timeout = window.setTimeout(() => { elements.notice.hidden = true; }, 5000);
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  }

  function parseFinite(raw, label, { required = false, positive = false } = {}) {
    const text = String(raw ?? '').trim();
    if (!text) {
      if (required) throw new Error(`${label} là trường bắt buộc.`);
      return null;
    }
    const value = Number(text);
    if (!Number.isFinite(value)) throw new Error(`${label} phải là một số hữu hạn.`);
    if (positive && value <= 0) throw new Error(`${label} phải lớn hơn 0.`);
    return text;
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === '') return '—';
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString('en-US', { maximumFractionDigits: 8 }) : '—';
  }

  function statusClass(status) {
    return ({ PREVIEW: 'pill-preview', ACTIVE: 'pill-active', STOPPING: 'pill-stopping', CLOSED: 'pill-closed' })[status] || '';
  }

  function selectedZone() {
    return state.zones.find((zone) => zone.zone_id === state.selectedId) || null;
  }

  function renderZones() {
    elements.zoneCount.textContent = String(state.zones.length);
    elements.emptyState.hidden = state.zones.length > 0;
    elements.zoneList.innerHTML = state.zones.map((zone) => `
      <button type="button" class="zone-row" data-zone-id="${escapeHTML(zone.zone_id)}" aria-current="${zone.zone_id === state.selectedId}">
        <span><span class="zone-symbol">${escapeHTML(zone.symbol)} <span class="pill ${statusClass(zone.state)}">${escapeHTML(zone.state)}</span></span><span class="zone-id">${escapeHTML(zone.zone_id)}</span></span>
        <span class="zone-price">${escapeHTML(formatNumber(zone.ref_price))}</span>
        <span class="zone-row-meta"><span>${escapeHTML(zone.side)} · ref price</span><span>net ${escapeHTML(formatNumber(zone.last_net_pnl))}</span></span>
      </button>`).join('');
    elements.zoneList.querySelectorAll('[data-zone-id]').forEach((button) => button.addEventListener('click', () => {
      state.selectedId = button.dataset.zoneId;
      hideError(elements.syncError);
      render();
    }));
  }

  function renderSummary(zone) {
    const config = zone.config || {};
    const items = [
      ['Trạng thái', `<span class="pill ${statusClass(zone.state)}">${escapeHTML(zone.state)}</span>`],
      ['Hướng', escapeHTML(zone.side)],
      ['Giá tham chiếu', escapeHTML(formatNumber(zone.ref_price))],
      ['Net PnL gần nhất', escapeHTML(formatNumber(zone.last_net_pnl))]
    ];
    elements.detailSummary.innerHTML = items.map(([label, value]) => `<div class="summary-cell"><span class="summary-label">${label}</span><span class="summary-value">${value}</span></div>`).join('');
    elements.selectedId.textContent = zone.zone_id;
    elements.activateButton.disabled = zone.state !== 'PREVIEW';
    elements.activateButton.textContent = zone.state === 'ACTIVE' ? 'Đã kích hoạt' : 'Kích hoạt local';
    elements.activateButton.title = zone.state === 'PREVIEW' ? 'Chuyển zone sang ACTIVE chỉ trong dữ liệu local' : 'Chỉ zone PREVIEW mới có thể kích hoạt';
    const observation = state.observations[zone.zone_id];
    renderObservation(observation, zone);
    if (config.zone_loss_limit_usdt || config.sl_pct) {
      elements.detailSummary.setAttribute('aria-label', `Giới hạn lỗ ${config.zone_loss_limit_usdt || 'không đặt'} USDT, stop-loss ${config.sl_pct || 'không đặt'} phần trăm`);
    }
  }

  function renderObservation(result, zone) {
    if (!result) {
      elements.observationResult.innerHTML = '<p class="observation-empty">Chưa có observation. Ghi một bộ số liệu mô phỏng để xem kết quả tại đây.</p>';
      return;
    }
    const observation = result.observation || {};
    const rows = [
      ['Thời điểm', new Date(result.observed_at || Date.now()).toLocaleString('vi-VN')],
      ['Mark price', formatNumber(observation.mark_price)],
      ['Net PnL', formatNumber(observation.net_pnl)],
      ['Trạng thái', result.state || zone.state]
    ];
    elements.observationResult.innerHTML = rows.map(([label, value]) => `<div class="result-line"><span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong></div>`).join('');
    const triggered = Boolean(result.triggered);
    const message = triggered
      ? `Đã chạm điều kiện mô phỏng: ${escapeHTML(result.reason || 'RISK_TRIGGERED')}. State thành STOPPING. Không có lệnh nào được gửi.`
      : `Không có trigger trong observation này. Kết quả chỉ là mô phỏng local.`;
    elements.observationResult.insertAdjacentHTML('beforeend', `<div class="trigger-result ${triggered ? 'is-triggered' : ''}">${message}</div>`);
  }

  function render() {
    renderZones();
    const zone = selectedZone();
    elements.detailEmpty.hidden = Boolean(zone);
    elements.detailContent.hidden = !zone;
    if (zone) renderSummary(zone);
  }

  function hideError(element) {
    element.hidden = true;
    element.textContent = '';
  }

  elements.createForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.createError);
    const form = new FormData(elements.createForm);
    const symbol = String(form.get('symbol') || '').trim().toUpperCase();
    const side = String(form.get('side') || 'long');
    try {
      if (!symbol || symbol.length > 32) throw new Error('Nhập symbol, tối đa 32 ký tự.');
      if (!/^[A-Z0-9_-]+$/.test(symbol)) throw new Error('Symbol chỉ dùng chữ in hoa, số, gạch ngang hoặc gạch dưới.');
      if (side !== 'long' && side !== 'short') throw new Error('Hướng phải là long hoặc short.');
      const refPrice = parseFinite(form.get('ref_price'), 'Giá tham chiếu', { required: true, positive: true });
      const lossLimit = parseFinite(form.get('zone_loss_limit_usdt'), 'Giới hạn lỗ', { positive: true });
      const slPct = parseFinite(form.get('sl_pct'), 'Stop-loss', { positive: true });
      if (!lossLimit && !slPct) throw new Error('Nhập ít nhất một giới hạn lỗ hoặc stop-loss.');
      const now = new Date().toISOString();
      const zone = {
        zone_id: `zone-${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
        symbol, side, state: 'PREVIEW', created_at: now, updated_at: now,
        ref_price: refPrice, last_mark_price: null, last_net_pnl: null,
        config: { symbol, side, ref_price: refPrice, zone_loss_limit_usdt: lossLimit, sl_pct: slPct, policy_version: 'zone-risk-policy.p1' }
      };
      state.zones.unshift(zone);
      state.selectedId = zone.zone_id;
      persist();
      render();
      elements.createForm.reset();
      showNotice(`Đã tạo zone ${zone.zone_id} ở trạng thái PREVIEW.`);
    } catch (error) {
      elements.createError.textContent = error.message;
      elements.createError.hidden = false;
    }
  });

  elements.activateButton.addEventListener('click', () => {
    const zone = selectedZone();
    if (!zone || zone.state !== 'PREVIEW') return;
    zone.state = 'ACTIVE';
    zone.updated_at = new Date().toISOString();
    persist();
    render();
    showNotice(`Đã kích hoạt ${zone.zone_id} trong dữ liệu local. Không có lệnh được gửi.`);
  });

  elements.syncForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.syncError);
    const zone = selectedZone();
    if (!zone || !state.zones.some((item) => item.zone_id === zone.zone_id)) {
      elements.syncError.textContent = 'Không tìm thấy zone đang chọn. Hãy chọn lại trong sổ theo dõi.';
      elements.syncError.hidden = false;
      return;
    }
    const form = new FormData(elements.syncForm);
    try {
      const mark = parseFinite(form.get('mark_price'), 'Mark price');
      const realized = parseFinite(form.get('realized_pnl'), 'Realized PnL', { required: true });
      const unrealized = parseFinite(form.get('unrealized_pnl'), 'Unrealized PnL', { required: true });
      const fees = parseFinite(form.get('fees'), 'Fees', { required: true });
      const paid = parseFinite(form.get('funding_paid'), 'Funding đã trả', { required: true });
      const received = parseFinite(form.get('funding_received'), 'Funding đã nhận', { required: true });
      const net = Number(realized) + Number(unrealized) - Number(fees) - Number(paid) + Number(received);
      if (!Number.isFinite(net)) throw new Error('Net PnL phải là số hữu hạn.');
      const config = zone.config || {};
      const riskReasons = [];
      if (config.zone_loss_limit_usdt && net <= -Number(config.zone_loss_limit_usdt)) riskReasons.push('LOSS_BUDGET');
      let stopPrice = null;
      if (mark !== null && config.sl_pct) {
        const ref = Number(zone.ref_price);
        const sl = Number(config.sl_pct) / 100;
        stopPrice = ref * (zone.side === 'long' ? 1 - sl : 1 + sl);
        if ((zone.side === 'long' && Number(mark) <= stopPrice) || (zone.side === 'short' && Number(mark) >= stopPrice)) riskReasons.push('PRICE_SL');
      }
      const reason = riskReasons.length > 1 ? 'BOTH' : (riskReasons[0] || null);
      const wasTriggered = Boolean(reason && zone.state === 'ACTIVE');
      if (wasTriggered) zone.state = 'STOPPING';
      const now = new Date().toISOString();
      zone.updated_at = now;
      zone.last_mark_price = mark;
      zone.last_net_pnl = String(net);
      const result = {
        zone_id: zone.zone_id, state: zone.state, triggered: wasTriggered, reason,
        observed_at: now, source: 'mock',
        risk: { net_pnl: String(net), stop_price: stopPrice === null ? null : String(stopPrice), reasons: riskReasons },
        observation: { mark_price: mark, realized_pnl: realized, unrealized_pnl: unrealized, fees, funding_paid: paid, funding_received: received, net_pnl: String(net) }
      };
      state.observations[zone.zone_id] = result;
      persist();
      render();
      showNotice(wasTriggered ? `Observation đã ghi. Trigger ${reason}, state chuyển STOPPING trong mô phỏng.` : 'Đã ghi observation mock trong trình duyệt.');
    } catch (error) {
      elements.syncError.textContent = error.message;
      elements.syncError.hidden = false;
    }
  });

  $('#reset-button').addEventListener('click', () => {
    if (!window.confirm('Xóa toàn bộ zone và observation demo đã lưu trên trình duyệt này?')) return;
    state.zones = [];
    state.observations = {};
    state.selectedId = null;
    persist();
    render();
    elements.syncForm.reset();
    showNotice('Đã xóa dữ liệu demo trên trình duyệt này.');
  });

  window.addEventListener('storage', (event) => {
    if (event.key !== STORAGE_KEY) return;
    state.zones = [];
    state.observations = {};
    state.selectedId = null;
    readStorage();
    render();
  });

  readStorage();
  render();
})();
