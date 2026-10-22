(() => {
  'use strict';

  const STORAGE_KEY = 'future-bitget-zone-desk-v1';
  const state = { zones: [], selectedId: null, observations: {}, policy: null, policyVersions: [], storageAvailable: true };
  const $ = (selector) => document.querySelector(selector);
  const elements = {
    zoneList: $('#zone-list'), zoneCount: $('#zone-count'), emptyState: $('#empty-state'),
    detailEmpty: $('#detail-empty'), detailContent: $('#detail-content'), detailSummary: $('#detail-summary'),
    selectedId: $('#selected-id'), observationResult: $('#observation-result'), notice: $('#notice'),
    policyForm: $('#policy-form'), policyError: $('#policy-error'), policyVersion: $('#policy-version'), policyHistory: $('#policy-history'),
    zoneSymbol: $('#zone-symbol'), createForm: $('#create-form'), createError: $('#create-error'), syncForm: $('#sync-form'),
    syncError: $('#sync-error'), activateButton: $('#activate-button'), localState: $('#local-state')
  };

  function isPolicy(value) {
    return Boolean(
      value && typeof value === 'object' && !Array.isArray(value)
      && Number.isInteger(value.version) && value.version > 0
      && typeof value.granted_capital === 'string'
      && Number.isFinite(Number(value.granted_capital)) && Number(value.granted_capital) > 0
      && value.capital_currency === 'USDT'
      && ['PROPOSAL_ONLY', 'MANAGED_ZONE', 'AUTONOMOUS_WITHIN_MANDATE'].includes(value.ai_autonomy)
      && typeof value.daily_loss_limit_pct === 'string'
      && Number.isFinite(Number(value.daily_loss_limit_pct)) && Number(value.daily_loss_limit_pct) > 0
      && ['FREEZE_ENTRY', 'EMERGENCY_FLATTEN'].includes(value.daily_loss_action)
      && Number.isInteger(value.max_consecutive_losses) && value.max_consecutive_losses > 0
      && typeof value.loss_streak_cooldown === 'string' && value.loss_streak_cooldown.trim()
      && value.loss_streak_scope === 'subaccount'
      && value.allow_average_down === false
      && typeof value.drawdown_limit === 'string'
      && Number.isFinite(Number(value.drawdown_limit)) && Number(value.drawdown_limit) > 0
      && ['pct', 'usdt'].includes(value.drawdown_unit)
      && ['equity_peak', 'day_start', 'policy_start'].includes(value.drawdown_reference)
      && typeof value.max_leverage === 'string'
      && Number.isFinite(Number(value.max_leverage)) && Number(value.max_leverage) > 0
      && Array.isArray(value.symbol_allowlist) && value.symbol_allowlist.length > 0
      && value.symbol_allowlist.every((symbol) => typeof symbol === 'string' && /^[A-Z0-9_-]{1,32}$/.test(symbol))
      && new Set(value.symbol_allowlist).size === value.symbol_allowlist.length
      && value.daily_loss_scope === 'subaccount'
      && value.daily_loss_reference === 'day_start_equity'
      && value.daily_reset_time_utc === '00:00'
      && value.drawdown_scope === 'subaccount'
      && value.margin_mode === 'isolated'
      && value.entry_order_type === 'limit'
      && value.dca_order_type === 'limit'
      && value.take_profit_order_type === 'limit'
      && value.strategic_stop_order_type === 'market_reduce_only'
      && value.emergency_order_type === 'market_reduce_only'
      && value.kill_switch_order_type === 'market_reduce_only'
    );
  }

  function normalisePolicy(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const policy = { ...value, daily_loss_reference: value.daily_loss_reference || 'day_start_equity' };
    return isPolicy(policy) ? policy : null;
  }

  function readStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || ![1, 2, 3].includes(data.version) || !Array.isArray(data.zones) || !data.observations || typeof data.observations !== 'object' || Array.isArray(data.observations)) {
        throw new Error('invalid stored data');
      }
      const validZones = data.zones.every((zone) => zone && typeof zone.zone_id === 'string' && typeof zone.symbol === 'string' && typeof zone.side === 'string' && typeof zone.state === 'string' && typeof zone.config === 'object');
      if (!validZones) throw new Error('invalid stored zone');
      state.zones = data.zones;
      state.observations = data.observations;
      state.policy = normalisePolicy(data.policy);
      state.policyVersions = Array.isArray(data.policyVersions) ? data.policyVersions.map(normalisePolicy).filter(Boolean) : (state.policy ? [state.policy] : []);
      if (state.policy && !state.policyVersions.some((policy) => policy.version === state.policy.version)) state.policyVersions.push(state.policy);
      if (state.zones.length) state.selectedId = state.zones[0].zone_id;
    } catch {
      state.zones = [];
      state.observations = {};
      state.policy = null;
      state.policyVersions = [];
      state.storageAvailable = false;
      showNotice('Dữ liệu demo lưu trên trình duyệt không hợp lệ hoặc không đọc được. Đã bỏ qua dữ liệu đó.', true);
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 3, zones: state.zones, observations: state.observations, policy: state.policy, policyVersions: state.policyVersions }));
      state.storageAvailable = true;
      elements.localState.textContent = 'Lưu trong trình duyệt';
      elements.policyVersion.textContent = state.policy ? `Policy v${state.policy.version}` : 'Chưa lưu policy';
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

  function policyFromForm(form) {
    const grantedCapital = parseFinite(form.get('granted_capital'), 'Vốn được cấp', { required: true, positive: true });
    const autonomy = String(form.get('ai_autonomy') || '').trim();
    if (!['PROPOSAL_ONLY', 'MANAGED_ZONE', 'AUTONOMOUS_WITHIN_MANDATE'].includes(autonomy)) {
      throw new Error('Chọn quyền AI.');
    }
    const dailyLoss = parseFinite(form.get('daily_loss_limit_pct'), 'Daily loss limit', { required: true, positive: true });
    const dailyLossAction = String(form.get('daily_loss_action') || '').trim();
    if (!['FREEZE_ENTRY', 'EMERGENCY_FLATTEN'].includes(dailyLossAction)) throw new Error('Chọn hành động khi chạm daily loss.');
    const streakRaw = String(form.get('max_consecutive_losses') || '').trim();
    const streak = Number(streakRaw);
    if (!Number.isInteger(streak) || streak < 1) throw new Error('Chuỗi lỗ tối đa phải là số nguyên dương.');
    const cooldown = String(form.get('loss_streak_cooldown') || '').trim();
    if (!cooldown) throw new Error('Nhập cooldown sau chuỗi lỗ.');
    const drawdown = parseFinite(form.get('drawdown_limit'), 'Drawdown limit', { required: true, positive: true });
    const maxLeverage = parseFinite(form.get('max_leverage'), 'Leverage tối đa', { required: true, positive: true });
    const reference = String(form.get('drawdown_reference') || '').trim();
    if (!reference) throw new Error('Chọn mốc tính drawdown.');
    const symbols = String(form.get('symbol_allowlist') || '')
      .split(',')
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);
    if (!symbols.length) throw new Error('Nhập ít nhất một symbol được phép.');
    if (symbols.some((symbol) => !/^[A-Z0-9_-]{1,32}$/.test(symbol))) throw new Error('Symbol chỉ dùng chữ in hoa, số, gạch ngang hoặc gạch dưới.');
    if (new Set(symbols).size !== symbols.length) throw new Error('Symbol không được lặp lại.');
    return {
      version: state.policy ? state.policy.version + 1 : 1,
      created_at: new Date().toISOString(),
      granted_capital: grantedCapital,
      capital_currency: 'USDT',
      ai_autonomy: autonomy,
      daily_loss_limit_pct: dailyLoss,
      daily_loss_action: dailyLossAction,
      daily_loss_scope: 'subaccount',
      daily_loss_reference: 'day_start_equity',
      daily_reset_time_utc: '00:00',
      max_consecutive_losses: streak,
      loss_streak_scope: 'subaccount',
      loss_streak_cooldown: cooldown,
      allow_average_down: false,
      drawdown_limit: drawdown,
      drawdown_unit: String(form.get('drawdown_unit') || 'pct'),
      drawdown_scope: 'subaccount',
      drawdown_reference: reference,
      max_leverage: maxLeverage,
      symbol_allowlist: symbols,
      margin_mode: 'isolated',
      entry_order_type: 'limit',
      dca_order_type: 'limit',
      take_profit_order_type: 'limit',
      strategic_stop_order_type: 'market_reduce_only',
      emergency_order_type: 'market_reduce_only',
      kill_switch_order_type: 'market_reduce_only',
      source: 'manual'
    };
  }

  function renderPolicy() {
    const policy = state.policy;
    const form = elements.policyForm;
    const policyKey = policy ? `${policy.version}:${policy.created_at}` : 'none';
    elements.policyVersion.textContent = policy ? `Policy v${policy.version}` : 'Chưa lưu policy';
    elements.zoneSymbol.innerHTML = policy && policy.symbol_allowlist.length
      ? policy.symbol_allowlist.map((symbol) => `<option value="${escapeHTML(symbol)}">${escapeHTML(symbol)}</option>`).join('')
      : '<option value="">Lưu policy trước</option>';
    elements.zoneSymbol.disabled = !policy;
    elements.policyHistory.innerHTML = state.policyVersions.length > 1
      ? `<span>Lịch sử:</span> ${state.policyVersions.map((item) => `<span class="policy-version-chip">v${escapeHTML(item.version)}${item.version === policy?.version ? ' · hiện tại' : ''}</span>`).join('')}`
      : '';
    if (form.dataset.policyKey === policyKey) return;
    form.dataset.policyKey = policyKey;
    if (!policy) {
      form.reset();
      return;
    }
    form.elements.granted_capital.value = policy.granted_capital || '';
    form.elements.ai_autonomy.value = policy.ai_autonomy || 'MANAGED_ZONE';
    form.elements.daily_loss_limit_pct.value = policy.daily_loss_limit_pct || '';
    form.elements.daily_loss_action.value = policy.daily_loss_action || 'FREEZE_ENTRY';
    form.elements.max_consecutive_losses.value = policy.max_consecutive_losses || '';
    form.elements.loss_streak_cooldown.value = policy.loss_streak_cooldown || '';
    form.elements.drawdown_limit.value = policy.drawdown_limit || '';
    form.elements.drawdown_unit.value = policy.drawdown_unit || 'pct';
    form.elements.drawdown_reference.value = policy.drawdown_reference || '';
    form.elements.max_leverage.value = policy.max_leverage || '';
    form.elements.symbol_allowlist.value = (policy.symbol_allowlist || []).join(', ');
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
    const policy = config.policy_snapshot || {};
    const drawdownText = policy.drawdown_limit
      ? `${formatNumber(policy.drawdown_limit)} ${policy.drawdown_unit === 'usdt' ? 'USDT' : '%'} · ${policy.drawdown_reference || 'chưa chọn mốc'}`
      : '—';
    const items = [
      ['Trạng thái', `<span class="pill ${statusClass(zone.state)}">${escapeHTML(zone.state)}</span>`],
      ['Hướng', escapeHTML(zone.side)],
      ['Giá tham chiếu', escapeHTML(formatNumber(zone.ref_price))],
      ['Net PnL gần nhất', escapeHTML(formatNumber(zone.last_net_pnl))],
      ['Giới hạn lỗ zone', `${escapeHTML(formatNumber(config.zone_loss_limit_usdt))} USDT`],
      ['Rủi ro tối đa / lệnh', `${escapeHTML(formatNumber(config.max_order_risk_usdt))} USDT`],
      ['Policy', policy.version ? `v${escapeHTML(policy.version)}` : '—'],
      ['Vốn được cấp', policy.granted_capital ? `${escapeHTML(formatNumber(policy.granted_capital))} USDT` : '—'],
      ['Quyền AI', policy.ai_autonomy ? escapeHTML(policy.ai_autonomy) : '—'],
      ['Daily loss', policy.daily_loss_limit_pct ? `${escapeHTML(formatNumber(policy.daily_loss_limit_pct))}% · ${escapeHTML(policy.daily_loss_action || 'chưa chọn')}` : '—'],
      ['Chuỗi lỗ', policy.max_consecutive_losses ? `${escapeHTML(String(policy.max_consecutive_losses))} · ${escapeHTML(policy.loss_streak_cooldown || 'chưa có cooldown')}` : '—'],
      ['Drawdown', escapeHTML(drawdownText)],
      ['Leverage tối đa', policy.max_leverage ? `${escapeHTML(formatNumber(policy.max_leverage))}×` : '—']
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
    renderPolicy();
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

  elements.policyForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.policyError);
    try {
      const policy = policyFromForm(new FormData(elements.policyForm));
      const previousPolicy = state.policy;
      state.policy = policy;
      state.policyVersions.push(policy);
      if (!persist()) {
        state.policy = previousPolicy;
        state.policyVersions.pop();
        render();
        return;
      }
      render();
      showNotice(`Đã lưu policy v${policy.version}. Áp dụng cho zone tạo sau; không có lệnh nào được gửi.`);
    } catch (error) {
      elements.policyError.textContent = error.message;
      elements.policyError.hidden = false;
    }
  });

  elements.createForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.createError);
    const form = new FormData(elements.createForm);
    const symbol = String(form.get('symbol') || '').trim().toUpperCase();
    const side = String(form.get('side') || 'long');
    try {
      if (!state.policy) throw new Error('Lưu policy subaccount trước khi tạo zone.');
      if (!state.policy.symbol_allowlist.includes(symbol)) throw new Error('Symbol phải nằm trong allowlist của policy hiện tại.');
      if (side !== 'long' && side !== 'short') throw new Error('Hướng phải là long hoặc short.');
      const refPrice = parseFinite(form.get('ref_price'), 'Giá tham chiếu', { required: true, positive: true });
      const lossLimit = parseFinite(form.get('zone_loss_limit_usdt'), 'Giới hạn lỗ zone', { required: true, positive: true });
      const maxOrderRisk = parseFinite(form.get('max_order_risk_usdt'), 'Rủi ro tối đa mỗi lệnh', { required: true, positive: true });
      const slPct = parseFinite(form.get('sl_pct'), 'Stop-loss chiến lược', { positive: true });
      if (Number(maxOrderRisk) > Number(lossLimit)) throw new Error('Rủi ro mỗi lệnh không được lớn hơn giới hạn lỗ zone.');
      const now = new Date().toISOString();
      const policySnapshot = JSON.parse(JSON.stringify(state.policy));
      const zone = {
        zone_id: `zone-${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
        symbol, side, state: 'PREVIEW', created_at: now, updated_at: now,
        ref_price: refPrice, last_mark_price: null, last_net_pnl: null,
        config: {
          symbol, side, ref_price: refPrice, zone_loss_limit_usdt: lossLimit,
          max_order_risk_usdt: maxOrderRisk, sl_pct: slPct,
          policy_version: policySnapshot.version, policy_snapshot: policySnapshot, opened_by: 'user',
          margin_mode: policySnapshot.margin_mode, max_leverage: policySnapshot.max_leverage,
          order_types: { entry: 'limit', dca: 'limit', take_profit: 'limit', emergency: 'market_reduce_only' }
        }
      };
      const previousSelectedId = state.selectedId;
      state.zones.unshift(zone);
      state.selectedId = zone.zone_id;
      if (!persist()) {
        state.zones.shift();
        state.selectedId = previousSelectedId;
        render();
        return;
      }
      render();
      elements.createForm.reset();
      showNotice(`Đã tạo zone ${zone.zone_id} theo policy v${policySnapshot.version}.`);
    } catch (error) {
      elements.createError.textContent = error.message;
      elements.createError.hidden = false;
    }
  });

  elements.activateButton.addEventListener('click', () => {
    const zone = selectedZone();
    if (!zone || zone.state !== 'PREVIEW') return;
    if (!zone.config || !zone.config.policy_snapshot) {
      showNotice('Zone chưa có policy snapshot. Không thể kích hoạt zone này.', true);
      return;
    }
    const policy = zone.config.policy_snapshot;
    const confirmation = [
      `Kích hoạt ${zone.zone_id} theo policy v${zone.config.policy_version}?`,
      `Zone loss: ${zone.config.zone_loss_limit_usdt} USDT`,
      `Risk/lệnh: ${zone.config.max_order_risk_usdt} USDT`,
      `Vốn được cấp: ${policy.granted_capital || '—'} USDT`,
      `Quyền AI: ${policy.ai_autonomy || '—'}`,
      `Daily loss: ${policy.daily_loss_limit_pct}% · ${policy.daily_loss_action || 'chưa chọn'}`,
      `Chuỗi lỗ: ${policy.max_consecutive_losses || '—'} · cooldown ${policy.loss_streak_cooldown || '—'}`,
      `Drawdown: ${policy.drawdown_limit} ${policy.drawdown_unit === 'usdt' ? 'USDT' : '%'} từ ${policy.drawdown_reference}`,
      `Leverage tối đa: ${policy.max_leverage}×`,
      'Chỉ là trạng thái local Demo/dry-run, không gửi lệnh.'
    ].join('\n');
    if (!window.confirm(confirmation)) return;
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
    state.policy = null;
    state.policyVersions = [];
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
    state.policy = null;
    state.policyVersions = [];
    state.selectedId = null;
    readStorage();
    render();
  });

  readStorage();
  render();
})();
