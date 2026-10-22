(() => {
  'use strict';

  const STORAGE_KEY = 'future-bitget-zone-desk-v1';
  const STORAGE_SCHEMA = 4;
  const VIEWS = ['ket-noi', 'cau-hinh-ai', 'tong-quan', 'mandate', 'quyen-ai', 'ban-zone', 'phong-cach', 'nhat-ky'];
  const AUTONOMY_LABELS = {
    PROPOSAL_ONLY: 'Chỉ ghi proposal',
    MANAGED_ZONE: 'Quản lý zone đã mở',
    AUTONOMOUS_WITHIN_MANDATE: 'Tự chủ trong mandate'
  };
  const MAX_GEMINI_KEYS = 20;
  const EMPTY_TICKER = { symbol: '', last: '', mark: '', funding: '' };
  const EMPTY_INTENT = { side: 'long', price: '', size: '' };
  const BOOK_TABS = ['positions', 'orders', 'assets'];
  const state = {
    zones: [], selectedId: null, observations: {}, policy: null, policyVersions: [],
    agentConfig: null, agentConfigVersions: [], agentLastCheck: null,
    ticker: { ...EMPTY_TICKER }, intentDraft: { ...EMPTY_INTENT }, overviewTab: 'positions',
    storageAvailable: true, view: 'ban-zone'
  };
  const $ = (selector) => document.querySelector(selector);
  const elements = {
    zoneList: $('#zone-list'), zoneCount: $('#zone-count'), emptyState: $('#empty-state'),
    detailEmpty: $('#detail-empty'), detailContent: $('#detail-content'), detailSummary: $('#detail-summary'),
    selectedId: $('#selected-id'), observationResult: $('#observation-result'), notice: $('#notice'),
    policyForm: $('#policy-form'), policyError: $('#policy-error'), policyVersion: $('#policy-version'), policyHistory: $('#policy-history'),
    mandateAutonomyReadout: $('#mandate-autonomy-readout'),
    autonomyForm: $('#autonomy-form'), autonomyError: $('#autonomy-error'), autonomyVersion: $('#autonomy-version'),
    autonomyGate: $('#autonomy-gate'), autonomyFieldset: $('#autonomy-fieldset'), autonomySubmit: $('#autonomy-submit'),
    autonomyAgentReadout: $('#autonomy-agent-readout'), zoneAgentReadout: $('#zone-agent-readout'),
    agentConfigForm: $('#agent-config-form'), agentConfigError: $('#agent-config-error'),
    agentConfigVersion: $('#agent-config-version'), agentConfigHistory: $('#agent-config-history'),
    agentBaseUrlField: $('#agent-base-url-field'), geminiKeysBlock: $('#gemini-keys-block'),
    geminiKeyRows: $('#gemini-key-rows'), addGeminiKey: $('#add-gemini-key'),
    openaiKeyBlock: $('#openai-key-block'), openaiApiKey: $('#openai-api-key'),
    agentCheckLive: $('#agent-check-live'), agentCheckStatus: $('#agent-check-status'),
    zoneGate: $('#zone-gate'), createSubmit: $('#create-submit'),
    zoneSymbol: $('#zone-symbol'), createForm: $('#create-form'), createError: $('#create-error'), syncForm: $('#sync-form'),
    syncError: $('#sync-error'), activateButton: $('#activate-button'), localState: $('#local-state'),
    overviewSymbol: $('#overview-symbol'), overviewLast: $('#overview-last'), overviewMark: $('#overview-mark'),
    overviewFunding: $('#overview-funding'), overviewEquity: $('#overview-equity'), overviewEquityNote: $('#overview-equity-note'),
    intentForm: $('#intent-form'), intentSymbol: $('#intent-symbol'), intentOrderType: $('#intent-order-type'),
    intentPrice: $('#intent-price'), intentSize: $('#intent-size'), intentLeverage: $('#intent-leverage'),
    intentMargin: $('#intent-margin'), intentError: $('#intent-error'),
    connectStatus: $('#connect-status'), connectBanner: $('#connect-banner'), connectRefresh: $('#connect-refresh')
  };
  let connectStatusRequest = 0;

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

  function isHttpUrl(value) {
    try {
      const parsed = new URL(String(value || '').trim());
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }

  function isGeminiKeys(keys) {
    if (!Array.isArray(keys) || keys.length < 1 || keys.length > MAX_GEMINI_KEYS) return false;
    const labels = [];
    for (const item of keys) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) return false;
      if (typeof item.label !== 'string' || typeof item.key !== 'string') return false;
      const label = item.label.trim();
      const key = item.key.trim();
      if (!label || label.length > 64 || !key) return false;
      labels.push(label.toLowerCase());
    }
    return new Set(labels).size === labels.length;
  }

  function isAgentConfig(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const base = Boolean(
      Number.isInteger(value.version) && value.version > 0
      && ['gemini', 'openai_compatible'].includes(value.provider)
      && typeof value.model === 'string' && value.model.trim() && value.model.length <= 128
      && typeof value.base_url === 'string'
      && (value.provider === 'openai_compatible' ? isHttpUrl(value.base_url) : value.base_url === '')
      && typeof value.request_timeout === 'string'
      && Number.isFinite(Number(value.request_timeout)) && Number(value.request_timeout) > 0
    );
    if (!base) return false;
    if (value.provider === 'gemini') {
      return isGeminiKeys(value.gemini_keys) && value.gemini_key_strategy === 'random'
        && (value.api_key === '' || value.api_key == null);
    }
    return typeof value.api_key === 'string' && value.api_key.trim()
      && Array.isArray(value.gemini_keys) && value.gemini_keys.length === 0
      && value.gemini_key_strategy === '';
  }

  function normaliseAgentConfig(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    if (!isAgentConfig(value)) return null;
    const config = { ...value };
    delete config.max_output_tokens;
    return config;
  }

  function normaliseLastCheck(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    if (typeof value.ok !== 'boolean') return null;
    if (!['gemini', 'openai_compatible'].includes(value.provider)) return null;
    if (typeof value.model !== 'string' || !value.model.trim() || value.model.length > 128) return null;
    if (typeof value.at !== 'string' || !value.at) return null;
    return {
      ok: value.ok,
      provider: value.provider,
      model: value.model.trim(),
      label: typeof value.label === 'string' ? value.label.trim().slice(0, 64) : '',
      at: value.at,
      error: typeof value.error === 'string' ? value.error.slice(0, 200) : ''
    };
  }

  function pickGeminiApiKey(config) {
    if (!config || config.provider !== 'gemini' || !isGeminiKeys(config.gemini_keys)) return null;
    return config.gemini_keys[Math.floor(Math.random() * config.gemini_keys.length)];
  }

  function agentReadout(config) {
    if (!config) return 'Agent: chưa cấu hình';
    if (config.provider === 'gemini') {
      return `Agent: ${config.provider} · ${config.model} · v${config.version} · ${config.gemini_keys.length} key, xoay ngẫu nhiên`;
    }
    return `Agent: ${config.provider} · ${config.model} · v${config.version} · đã có key`;
  }

  function formatCheckAt(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  function lastCheckText(check) {
    const labelText = check.label ? ` · nhãn ${check.label}` : '';
    const when = formatCheckAt(check.at);
    const whenText = when ? ` · ${when}` : '';
    if (check.ok) return `Check live gần nhất: OK${labelText} · ${check.provider} · ${check.model}${whenText}`;
    const error = check.error ? ` · ${check.error}` : '';
    return `Check live gần nhất: lỗi${labelText} · ${check.provider} · ${check.model}${error}${whenText}`;
  }

  function renderLastCheck(pending = false) {
    const el = elements.agentCheckStatus;
    if (pending) {
      el.hidden = false;
      el.classList.remove('is-error');
      el.classList.add('is-pending');
      el.textContent = 'Đang ping provider…';
      return;
    }
    el.classList.remove('is-pending');
    const check = state.agentLastCheck;
    if (!check) {
      el.hidden = true;
      el.textContent = '';
      el.classList.remove('is-error');
      return;
    }
    el.hidden = false;
    el.classList.toggle('is-error', !check.ok);
    el.textContent = lastCheckText(check);
  }

  function agentSaveNotice(config) {
    if (config.provider === 'gemini') {
      return `Đã lưu cấu hình AI v${config.version}: ${config.provider} · ${config.model} · ${config.gemini_keys.length} key, xoay ngẫu nhiên. Chỉ lưu máy này.`;
    }
    return `Đã lưu cấu hình AI v${config.version}: ${config.provider} · ${config.model}. Chỉ lưu máy này.`;
  }

  function asLocalText(value) {
    return typeof value === 'string' ? value : '';
  }

  function normaliseTicker(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return { ...EMPTY_TICKER };
    return {
      symbol: asLocalText(value.symbol).trim().toUpperCase(),
      last: asLocalText(value.last).trim(),
      mark: asLocalText(value.mark).trim(),
      funding: asLocalText(value.funding).trim()
    };
  }

  function normaliseIntentDraft(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return { ...EMPTY_INTENT };
    return {
      side: value.side === 'short' ? 'short' : 'long',
      price: asLocalText(value.price).trim(),
      size: asLocalText(value.size).trim()
    };
  }

  function setFieldValue(element, value) {
    if (!element || document.activeElement === element || element.value === value) return;
    element.value = value;
  }

  function readStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || ![1, 2, 3, 4].includes(data.version) || !Array.isArray(data.zones) || !data.observations || typeof data.observations !== 'object' || Array.isArray(data.observations)) {
        throw new Error('invalid stored data');
      }
      const validZones = data.zones.every((zone) => zone && typeof zone.zone_id === 'string' && typeof zone.symbol === 'string' && typeof zone.side === 'string' && typeof zone.state === 'string' && typeof zone.config === 'object');
      if (!validZones) throw new Error('invalid stored zone');
      state.zones = data.zones;
      state.observations = data.observations;
      state.policy = normalisePolicy(data.policy);
      state.policyVersions = Array.isArray(data.policyVersions) ? data.policyVersions.map(normalisePolicy).filter(Boolean) : (state.policy ? [state.policy] : []);
      if (state.policy && !state.policyVersions.some((policy) => policy.version === state.policy.version)) state.policyVersions.push(state.policy);
      state.agentConfig = normaliseAgentConfig(data.agentConfig);
      state.agentConfigVersions = Array.isArray(data.agentConfigVersions) ? data.agentConfigVersions.map(normaliseAgentConfig).filter(Boolean) : (state.agentConfig ? [state.agentConfig] : []);
      if (state.agentConfig && !state.agentConfigVersions.some((item) => item.version === state.agentConfig.version)) state.agentConfigVersions.push(state.agentConfig);
      state.agentLastCheck = normaliseLastCheck(data.agentLastCheck);
      if (state.zones.length) state.selectedId = state.zones[0].zone_id;
      state.ticker = normaliseTicker(data.ticker);
      state.intentDraft = normaliseIntentDraft(data.intentDraft);
      state.overviewTab = BOOK_TABS.includes(data.overviewTab) ? data.overviewTab : 'positions';
    } catch {
      state.zones = [];
      state.observations = {};
      state.policy = null;
      state.policyVersions = [];
      state.agentConfig = null;
      state.agentConfigVersions = [];
      state.agentLastCheck = null;
      state.ticker = { ...EMPTY_TICKER };
      state.intentDraft = { ...EMPTY_INTENT };
      state.overviewTab = 'positions';
      state.storageAvailable = false;
      showNotice('Dữ liệu demo lưu trên trình duyệt không hợp lệ hoặc không đọc được. Đã bỏ qua dữ liệu đó.', true);
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        version: STORAGE_SCHEMA, zones: state.zones, observations: state.observations,
        policy: state.policy, policyVersions: state.policyVersions,
        agentConfig: state.agentConfig, agentConfigVersions: state.agentConfigVersions,
        agentLastCheck: state.agentLastCheck,
        ticker: state.ticker, intentDraft: state.intentDraft, overviewTab: state.overviewTab
      }));
      state.storageAvailable = true;
      elements.localState.textContent = 'Lưu trong trình duyệt';
      const versionText = state.policy ? `Policy v${state.policy.version}` : 'Chưa lưu policy';
      elements.policyVersion.textContent = versionText;
      elements.autonomyVersion.textContent = versionText;
      elements.agentConfigVersion.textContent = state.agentConfig ? `Agent v${state.agentConfig.version}` : 'Chưa cấu hình';
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

  function currentView() {
    const hash = window.location.hash.replace(/^#\/?/, '');
    return VIEWS.includes(hash) ? hash : 'ban-zone';
  }

  function setView(view) {
    const next = VIEWS.includes(view) ? view : 'ban-zone';
    state.view = next;
    if (window.location.hash !== `#/${next}`) window.location.hash = `#/${next}`;
    document.querySelectorAll('[data-view-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.viewPanel !== next;
    });
    document.querySelectorAll('.nav-link').forEach((link) => {
      const active = link.dataset.view === next;
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (next === 'ket-noi') loadConnectStatus();
  }

  function presenceLabel(value) {
    if (value === 'present') return { text: 'Đã có', kind: 'ok' };
    if (value === 'missing') return { text: 'Thiếu', kind: 'warn' };
    return { text: 'Không đọc được', kind: 'warn' };
  }

  function pillMarkup(text, kind) {
    const cls = kind === 'ok' ? 'pill-active' : kind === 'bad' ? 'pill-stopping' : 'pill-preview';
    return `<span class="pill ${cls}">${escapeHTML(text)}</span>`;
  }

  function connectRow(labelHtml, value) {
    return `<div class="connect-row"><dt>${labelHtml}</dt><dd>${value}</dd></div>`;
  }

  function renderConnectStatus(data, pending = false) {
    const list = elements.connectStatus;
    const banner = elements.connectBanner;
    elements.connectRefresh.disabled = pending;
    if (pending) {
      banner.hidden = true;
      banner.textContent = '';
      banner.className = 'connect-banner';
      list.innerHTML = connectRow('Đang đọc', '<span class="pill pill-preview">…</span>');
      return;
    }
    if (!data || data.ok !== true) {
      banner.hidden = false;
      banner.className = 'connect-banner is-error';
      banner.textContent = 'Không đọc được env. Chạy npm start rồi mở lại trang. Key vẫn điền trong .env, không nhập trên web.';
      list.innerHTML = [
        connectRow('Chế độ UI', pillMarkup('Demo / dry-run', 'ok')),
        connectRow('GET Bitget', pillMarkup('Chưa nối', 'warn'))
      ].join('');
      return;
    }
    const envFile = presenceLabel(data.env_file);
    const creds = data.credentials && typeof data.credentials === 'object' ? data.credentials : {};
    const apiKey = presenceLabel(creds.BITGET_API_KEY);
    const apiSecret = presenceLabel(creds.BITGET_API_SECRET);
    const passphrase = presenceLabel(creds.BITGET_PASSPHRASE);
    const envMode = data.bitget_env === 'demo'
      ? { text: 'Demo', kind: 'ok' }
      : data.bitget_env === 'live'
        ? { text: 'Live — bị chặn', kind: 'bad' }
        : data.bitget_env === 'missing'
          ? { text: 'Thiếu (mặc định Demo)', kind: 'warn' }
          : { text: 'Khác', kind: 'warn' };
    const liveGuard = data.live_guard === 'on'
      ? { text: 'Đang bật — không dùng live', kind: 'bad' }
      : { text: 'Tắt', kind: 'ok' };
    const missingCreds = [apiKey, apiSecret, passphrase].some((item) => item.kind !== 'ok');
    const warnings = [];
    if (data.bitget_env === 'live') warnings.push('BITGET_ENV đang live; adapter Demo sẽ từ chối.');
    if (data.live_guard === 'on') warnings.push('GROK_TRADER_ALLOW_LIVE đang bật; frontend local không dùng live.');
    if (missingCreds) warnings.push('Thiếu key chỉ-đọc. Điền .env rồi bấm Đọc lại env.');
    if (warnings.length) {
      banner.hidden = false;
      banner.className = `connect-banner ${data.bitget_env === 'live' || data.live_guard === 'on' ? 'is-error' : ''}`;
      banner.textContent = warnings.join(' ');
    } else {
      banner.hidden = false;
      banner.className = 'connect-banner is-ok';
      banner.textContent = 'Đủ key chỉ-đọc cho Demo. GET Bitget vẫn chưa nối.';
    }
    list.innerHTML = [
      connectRow('Chế độ UI', pillMarkup('Demo / dry-run', 'ok')),
      connectRow('File <code>.env</code>', pillMarkup(envFile.text, envFile.kind)),
      connectRow('<code>BITGET_ENV</code>', pillMarkup(envMode.text, envMode.kind)),
      connectRow('<code>BITGET_API_KEY</code>', pillMarkup(apiKey.text, apiKey.kind)),
      connectRow('<code>BITGET_API_SECRET</code>', pillMarkup(apiSecret.text, apiSecret.kind)),
      connectRow('<code>BITGET_PASSPHRASE</code>', pillMarkup(passphrase.text, passphrase.kind)),
      connectRow('<code>GROK_TRADER_ALLOW_LIVE</code>', pillMarkup(liveGuard.text, liveGuard.kind)),
      connectRow('GET Bitget', pillMarkup('Chưa nối', 'warn'))
    ].join('');
  }

  function loadConnectStatus() {
    const requestId = ++connectStatusRequest;
    renderConnectStatus(null, true);
    fetch('/api/connect-status', { method: 'GET', cache: 'no-store' })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data) => {
        if (requestId !== connectStatusRequest) return;
        renderConnectStatus(data);
      })
      .catch(() => {
        if (requestId !== connectStatusRequest) return;
        renderConnectStatus(null);
      });
  }

  function policyFromForm(form) {
    const grantedCapital = parseFinite(form.get('granted_capital'), 'Vốn được cấp', { required: true, positive: true });
    const autonomy = state.policy?.ai_autonomy || 'MANAGED_ZONE';
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

  function readGeminiKeysFromForm() {
    const rows = [...elements.geminiKeyRows.querySelectorAll('.key-row')];
    const keys = [];
    for (const row of rows) {
      const label = String(row.querySelector('.gemini-key-label')?.value || '').trim();
      const key = String(row.querySelector('.gemini-key-value')?.value || '').trim();
      if (!label && !key) continue;
      if (!label) throw new Error('Mỗi Gemini key cần một nhãn.');
      if (label.length > 64) throw new Error('Nhãn key tối đa 64 ký tự.');
      if (!key) throw new Error(`Nhãn "${label}" chưa có API key.`);
      keys.push({ label, key });
    }
    if (!keys.length) throw new Error('Thêm ít nhất một Gemini key có nhãn.');
    if (keys.length > MAX_GEMINI_KEYS) throw new Error(`Tối đa ${MAX_GEMINI_KEYS} Gemini key.`);
    const labels = keys.map((item) => item.label.toLowerCase());
    if (new Set(labels).size !== labels.length) throw new Error('Nhãn Gemini key không được trùng.');
    return keys;
  }

  function readAgentDraftFromForm(form) {
    const provider = String(form.get('provider') || '').trim();
    if (!['gemini', 'openai_compatible'].includes(provider)) throw new Error('Chọn provider.');
    const model = String(form.get('model') || '').trim();
    if (!model) throw new Error('Nhập tên model.');
    if (model.length > 128) throw new Error('Tên model tối đa 128 ký tự.');
    const rawBaseUrl = String(form.get('base_url') || '').trim();
    let baseUrl = '';
    let apiKey = '';
    let geminiKeys = [];
    let geminiStrategy = '';
    if (provider === 'openai_compatible') {
      if (!rawBaseUrl) throw new Error('Nhập base URL cho OpenAI-compatible.');
      if (!isHttpUrl(rawBaseUrl)) throw new Error('Base URL phải bắt đầu bằng http:// hoặc https://.');
      baseUrl = rawBaseUrl;
      apiKey = String(form.get('api_key') || '').trim();
      if (!apiKey) throw new Error('Nhập API key cho OpenAI-compatible.');
    } else {
      geminiKeys = readGeminiKeysFromForm();
      geminiStrategy = 'random';
    }
    const timeout = parseFinite(form.get('request_timeout'), 'Request timeout', { required: true, positive: true });
    const draft = {
      provider,
      model,
      base_url: baseUrl,
      request_timeout: timeout,
      api_key: apiKey,
      gemini_keys: geminiKeys,
      gemini_key_strategy: geminiStrategy,
      source: 'manual'
    };
    if (provider === 'gemini' && !pickGeminiApiKey(draft)) {
      throw new Error('Gemini cần ít nhất một key hợp lệ.');
    }
    return draft;
  }

  function agentConfigFromForm(form) {
    return {
      ...readAgentDraftFromForm(form),
      version: state.agentConfig ? state.agentConfig.version + 1 : 1,
      created_at: new Date().toISOString()
    };
  }

  function redactSecrets(text, secrets) {
    let out = String(text || '');
    secrets.filter(Boolean).forEach((secret) => {
      out = out.split(secret).join('…');
    });
    return out;
  }

  function joinProviderUrl(base, suffix) {
    const trimmed = String(base || '').replace(/\/+$/, '');
    if (!trimmed) return suffix;
    if (trimmed.endsWith(suffix) || trimmed.endsWith(`/${suffix}`)) return trimmed;
    return `${trimmed}/${suffix}`;
  }

  function liveCheckSecrets(draft, picked) {
    return [picked?.key, draft.api_key].filter(Boolean);
  }

  async function parseProviderError(response, secrets) {
    const text = await response.text();
    let message = `HTTP ${response.status}`;
    try {
      const parsed = JSON.parse(text);
      if (parsed?.error?.message) message = parsed.error.message;
    } catch {
      if (text) message = text.slice(0, 200);
    }
    return redactSecrets(message, secrets);
  }

  async function checkDirect(draft, picked, timeoutMs) {
    const secrets = liveCheckSecrets(draft, picked);
    const signal = AbortSignal.timeout(timeoutMs);
    if (draft.provider === 'gemini') {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(draft.model)}:generateContent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': picked.key },
        body: JSON.stringify({ contents: [{ parts: [{ text: 'ping' }] }], generationConfig: { maxOutputTokens: 8 } }),
        signal
      });
      if (!response.ok) throw new Error(await parseProviderError(response, secrets));
      return { ok: true, httpStatus: response.status, label: picked.label };
    }
    const response = await fetch(joinProviderUrl(draft.base_url, 'chat/completions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${draft.api_key}` },
      body: JSON.stringify({ model: draft.model, messages: [{ role: 'user', content: 'ping' }], max_tokens: 8 }),
      signal
    });
    if (!response.ok) throw new Error(await parseProviderError(response, secrets));
    return { ok: true, httpStatus: response.status, label: '' };
  }

  async function checkViaProxy(draft, picked, timeoutMs) {
    const response = await fetch('/api/ai-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: draft.provider,
        model: draft.model,
        base_url: draft.base_url,
        api_key: picked?.key || draft.api_key,
        label: picked?.label || '',
        timeout_ms: timeoutMs
      })
    });
    if (response.status === 404) return null;
    const payload = await response.json();
    if (!payload || typeof payload !== 'object') throw new Error('Phản hồi check không hợp lệ.');
    if (!payload.ok) throw new Error(redactSecrets(payload.error || `HTTP ${payload.httpStatus || response.status}`, liveCheckSecrets(draft, picked)));
    return { ok: true, httpStatus: payload.httpStatus, label: payload.label || picked?.label || '' };
  }

  async function checkProviderLive(draft) {
    const picked = draft.provider === 'gemini' ? pickGeminiApiKey(draft) : { label: '', key: draft.api_key };
    if (!picked?.key) throw new Error('Thiếu API key để check live.');
    const timeoutMs = Math.min(Math.max(Number(draft.request_timeout) * 1000, 1000), 60000);
    try {
      const proxied = await checkViaProxy(draft, picked, timeoutMs);
      if (proxied) return { ...proxied, picked };
    } catch (error) {
      if (error && error.message === 'Phản hồi check không hợp lệ.') throw error;
      if (error && !/failed to fetch|network|404/i.test(String(error.message))) throw error;
    }
    const direct = await checkDirect(draft, picked, timeoutMs);
    return { ...direct, picked };
  }

  function syncGeminiKeyRemoveButtons() {
    const rows = elements.geminiKeyRows.querySelectorAll('.key-row');
    rows.forEach((row) => {
      const button = row.querySelector('.gemini-key-remove');
      if (button) button.disabled = rows.length <= 1;
    });
    elements.addGeminiKey.disabled = rows.length >= MAX_GEMINI_KEYS;
  }

  function addGeminiKeyRow(label = '', key = '') {
    if (elements.geminiKeyRows.querySelectorAll('.key-row').length >= MAX_GEMINI_KEYS) return;
    const row = document.createElement('div');
    row.className = 'key-row';
    const labelField = document.createElement('label');
    labelField.className = 'field';
    labelField.innerHTML = '<span>Nhãn</span>';
    const labelInput = document.createElement('input');
    labelInput.className = 'gemini-key-label';
    labelInput.autocomplete = 'off';
    labelInput.placeholder = 'nhãn';
    labelInput.value = label;
    labelField.appendChild(labelInput);
    const keyField = document.createElement('label');
    keyField.className = 'field';
    keyField.innerHTML = '<span>API key</span>';
    const keyInput = document.createElement('input');
    keyInput.className = 'gemini-key-value';
    keyInput.type = 'text';
    keyInput.spellcheck = false;
    keyInput.autocomplete = 'off';
    keyInput.value = key;
    keyField.appendChild(keyInput);
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'button button-ghost gemini-key-remove';
    remove.textContent = 'Xóa';
    row.append(labelField, keyField, remove);
    elements.geminiKeyRows.appendChild(row);
    syncGeminiKeyRemoveButtons();
  }

  function renderGeminiKeyRows(keys) {
    elements.geminiKeyRows.replaceChildren();
    const list = Array.isArray(keys) && keys.length ? keys : [{ label: '', key: '' }];
    list.forEach((item) => addGeminiKeyRow(item.label || '', item.key || ''));
  }

  function syncAgentProviderFields() {
    const provider = String(elements.agentConfigForm.elements.provider.value || 'gemini');
    const isOpenAi = provider === 'openai_compatible';
    elements.agentBaseUrlField.hidden = !isOpenAi;
    elements.openaiKeyBlock.hidden = !isOpenAi;
    elements.geminiKeysBlock.hidden = isOpenAi;
    if (!isOpenAi && !elements.geminiKeyRows.querySelector('.key-row')) renderGeminiKeyRows();
  }

  function renderAgentConfig() {
    const config = state.agentConfig;
    const form = elements.agentConfigForm;
    const configKey = config ? `${config.version}:${config.created_at}` : 'none';
    elements.agentConfigVersion.textContent = config ? `Agent v${config.version}` : 'Chưa cấu hình';
    const readout = agentReadout(config);
    elements.autonomyAgentReadout.textContent = readout;
    elements.zoneAgentReadout.textContent = readout;
    elements.agentConfigHistory.innerHTML = state.agentConfigVersions.length > 1
      ? `<span>Lịch sử:</span> ${state.agentConfigVersions.map((item) => `<span class="policy-version-chip">v${escapeHTML(item.version)}${item.version === config?.version ? ' · hiện tại' : ''}</span>`).join('')}`
      : '';
    if (form.dataset.configKey === configKey) {
      syncAgentProviderFields();
      renderLastCheck();
      return;
    }
    form.dataset.configKey = configKey;
    if (!config) {
      form.reset();
      form.elements.request_timeout.value = '30';
      renderGeminiKeyRows();
      syncAgentProviderFields();
      renderLastCheck();
      return;
    }
    form.elements.provider.value = config.provider;
    form.elements.model.value = config.model;
    form.elements.base_url.value = config.base_url;
    form.elements.request_timeout.value = config.request_timeout;
    elements.openaiApiKey.value = config.api_key || '';
    renderGeminiKeyRows(config.provider === 'gemini' ? config.gemini_keys : []);
    syncAgentProviderFields();
    renderLastCheck();
  }

  function policyFromAutonomyForm(form) {
    if (!state.policy) throw new Error('Lưu Mandate trước khi chọn quyền AI.');
    const autonomy = String(form.get('ai_autonomy') || '').trim();
    if (!['PROPOSAL_ONLY', 'MANAGED_ZONE', 'AUTONOMOUS_WITHIN_MANDATE'].includes(autonomy)) {
      throw new Error('Chọn quyền AI.');
    }
    return {
      ...state.policy,
      version: state.policy.version + 1,
      created_at: new Date().toISOString(),
      ai_autonomy: autonomy,
      source: 'manual'
    };
  }

  function renderAutonomy() {
    const policy = state.policy;
    const versionText = policy ? `Policy v${policy.version}` : 'Chưa lưu policy';
    elements.autonomyVersion.textContent = versionText;
    elements.autonomyFieldset.disabled = !policy;
    elements.autonomySubmit.disabled = !policy;
    elements.autonomyGate.hidden = Boolean(policy);
    elements.autonomyGate.textContent = 'Lưu Mandate trước khi chọn quyền AI.';
    if (policy) {
      const radio = elements.autonomyForm.elements.ai_autonomy;
      if (radio) radio.value = policy.ai_autonomy;
    }
  }

  function renderPolicy() {
    const policy = state.policy;
    const form = elements.policyForm;
    const policyKey = policy ? `${policy.version}:${policy.created_at}` : 'none';
    const versionText = policy ? `Policy v${policy.version}` : 'Chưa lưu policy';
    elements.policyVersion.textContent = versionText;
    elements.mandateAutonomyReadout.textContent = policy
      ? `Quyền AI hiện tại: ${AUTONOMY_LABELS[policy.ai_autonomy] || policy.ai_autonomy} · đổi ở trang Quyền AI.`
      : 'Quyền AI: chưa chọn · lưu Mandate trước, rồi mở trang Quyền AI.';
    elements.zoneSymbol.innerHTML = policy && policy.symbol_allowlist.length
      ? policy.symbol_allowlist.map((symbol) => `<option value="${escapeHTML(symbol)}">${escapeHTML(symbol)}</option>`).join('')
      : '<option value="">Lưu policy trước</option>';
    const canCreate = Boolean(policy);
    elements.zoneSymbol.disabled = !canCreate;
    elements.createSubmit.disabled = !canCreate;
    elements.createForm.querySelectorAll('input, select').forEach((field) => { field.disabled = !canCreate; });
    elements.zoneGate.hidden = canCreate;
    elements.policyHistory.innerHTML = state.policyVersions.length > 1
      ? `<span>Lịch sử:</span> ${state.policyVersions.map((item) => `<span class="policy-version-chip">v${escapeHTML(item.version)}${item.version === policy?.version ? ' · hiện tại' : ''}</span>`).join('')}`
      : '';
    renderAutonomy();
    renderAgentConfig();
    renderOverview();
    if (form.dataset.policyKey === policyKey) return;
    form.dataset.policyKey = policyKey;
    if (!policy) {
      form.reset();
      return;
    }
    form.elements.granted_capital.value = policy.granted_capital || '';
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

  function localEquity() {
    return null;
  }

  function renderOverview() {
    const policy = state.policy;
    const allowlist = policy?.symbol_allowlist || [];
    if (state.ticker.symbol && !allowlist.includes(state.ticker.symbol)) {
      state.ticker.symbol = '';
      persist();
    }
    const symbolOptions = ['<option value="">—</option>'].concat(
      allowlist.map((symbol) => `<option value="${escapeHTML(symbol)}">${escapeHTML(symbol)}</option>`)
    );
    if (elements.overviewSymbol.innerHTML !== symbolOptions.join('')) {
      elements.overviewSymbol.innerHTML = symbolOptions.join('');
    }
    elements.overviewSymbol.disabled = allowlist.length === 0;
    setFieldValue(elements.overviewSymbol, state.ticker.symbol);
    setFieldValue(elements.overviewLast, state.ticker.last);
    setFieldValue(elements.overviewMark, state.ticker.mark);
    setFieldValue(elements.overviewFunding, state.ticker.funding);
    const equity = localEquity();
    elements.overviewEquity.textContent = equity === null ? '—' : formatNumber(equity);
    elements.overviewEquityNote.textContent = equity === null ? 'Chưa có equity local' : 'Equity local, không lấy từ sàn';
    const symbol = state.ticker.symbol || '—';
    elements.intentSymbol.textContent = symbol;
    elements.intentOrderType.value = policy?.entry_order_type || 'limit';
    setFieldValue(elements.intentPrice, state.intentDraft.price);
    setFieldValue(elements.intentSize, state.intentDraft.size);
    const side = elements.intentForm.elements.intent_side;
    if (side && document.activeElement?.name !== 'intent_side') side.value = state.intentDraft.side;
    elements.intentLeverage.textContent = policy?.max_leverage ? `${formatNumber(policy.max_leverage)}×` : '—';
    elements.intentMargin.textContent = policy?.margin_mode || '—';
    document.querySelectorAll('[data-book-tab]').forEach((tab) => {
      const active = tab.dataset.bookTab === state.overviewTab;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll('[data-book-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.bookPanel !== state.overviewTab;
    });
  }

  function readOverviewInputs() {
    state.ticker = {
      symbol: String(elements.overviewSymbol.value || '').trim().toUpperCase(),
      last: String(elements.overviewLast.value || '').trim(),
      mark: String(elements.overviewMark.value || '').trim(),
      funding: String(elements.overviewFunding.value || '').trim()
    };
    const sideValue = String(elements.intentForm.elements.intent_side?.value || 'long');
    state.intentDraft = {
      side: sideValue === 'short' ? 'short' : 'long',
      price: String(elements.intentPrice.value || '').trim(),
      size: String(elements.intentSize.value || '').trim()
    };
  }

  function persistOverview() {
    hideError(elements.intentError);
    readOverviewInputs();
    persist();
    renderOverview();
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
    setView(currentView());
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

  elements.agentConfigForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.agentConfigError);
    try {
      const config = agentConfigFromForm(new FormData(elements.agentConfigForm));
      const previous = state.agentConfig;
      state.agentConfig = config;
      state.agentConfigVersions.push(config);
      if (!persist()) {
        state.agentConfig = previous;
        state.agentConfigVersions.pop();
        render();
        return;
      }
      elements.agentConfigForm.dataset.configKey = '';
      render();
      showNotice(agentSaveNotice(config));
    } catch (error) {
      elements.agentConfigError.textContent = error.message;
      elements.agentConfigError.hidden = false;
    }
  });
  elements.agentConfigForm.elements.provider.addEventListener('change', () => {
    syncAgentProviderFields();
  });
  elements.agentCheckLive.addEventListener('click', async () => {
    hideError(elements.agentConfigError);
    let draft;
    try {
      draft = readAgentDraftFromForm(new FormData(elements.agentConfigForm));
    } catch (error) {
      elements.agentConfigError.textContent = error.message;
      elements.agentConfigError.hidden = false;
      return;
    }
    elements.agentCheckLive.disabled = true;
    elements.agentCheckLive.textContent = 'Đang check…';
    renderLastCheck(true);
    try {
      const result = await checkProviderLive(draft);
      const label = result.picked?.label || result.label || '';
      state.agentLastCheck = {
        ok: true,
        provider: draft.provider,
        model: draft.model,
        label,
        at: new Date().toISOString(),
        error: ''
      };
      persist();
      renderLastCheck();
      const labelText = label ? ` · nhãn ${label}` : '';
      showNotice(`Check live OK${labelText} · ${draft.provider} · ${draft.model}. Không tạo version mới.`);
    } catch (error) {
      const raw = error && error.message ? String(error.message) : '';
      const message = error && error.name === 'TimeoutError'
        ? 'Check live timeout.'
        : /failed to fetch/i.test(raw)
          ? 'Không gọi được provider. Chạy npm start rồi check lại.'
          : (raw || 'Check live lỗi.');
      state.agentLastCheck = {
        ok: false,
        provider: draft.provider,
        model: draft.model,
        label: '',
        at: new Date().toISOString(),
        error: message
      };
      persist();
      renderLastCheck();
      elements.agentConfigError.textContent = message;
      elements.agentConfigError.hidden = false;
    } finally {
      elements.agentCheckLive.disabled = false;
      elements.agentCheckLive.textContent = 'Check live';
    }
  });
  elements.addGeminiKey.addEventListener('click', () => {
    addGeminiKeyRow();
  });
  elements.geminiKeyRows.addEventListener('click', (event) => {
    const button = event.target.closest('.gemini-key-remove');
    if (!button || button.disabled) return;
    button.closest('.key-row')?.remove();
    if (!elements.geminiKeyRows.querySelector('.key-row')) addGeminiKeyRow();
    syncGeminiKeyRemoveButtons();
  });

  elements.autonomyForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.autonomyError);
    try {
      const policy = policyFromAutonomyForm(new FormData(elements.autonomyForm));
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
      showNotice(`Đã lưu policy v${policy.version} với quyền ${AUTONOMY_LABELS[policy.ai_autonomy]}. Frontend không tự giao dịch.`);
    } catch (error) {
      elements.autonomyError.textContent = error.message;
      elements.autonomyError.hidden = false;
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

  elements.connectRefresh.addEventListener('click', () => {
    loadConnectStatus();
  });

  $('#reset-button').addEventListener('click', () => {
    if (!window.confirm('Xóa toàn bộ zone, observation, policy, cấu hình AI và ticker demo đã lưu trên trình duyệt này?')) return;
    state.zones = [];
    state.observations = {};
    state.policy = null;
    state.policyVersions = [];
    state.agentConfig = null;
    state.agentConfigVersions = [];
    state.agentLastCheck = null;
    state.selectedId = null;
    state.ticker = { ...EMPTY_TICKER };
    state.intentDraft = { ...EMPTY_INTENT };
    state.overviewTab = 'positions';
    elements.agentConfigForm.dataset.configKey = '';
    persist();
    render();
    elements.syncForm.reset();
    elements.intentForm.reset();
    showNotice('Đã xóa dữ liệu demo trên trình duyệt này.');
  });

  [elements.overviewLast, elements.overviewMark, elements.overviewFunding, elements.intentPrice, elements.intentSize].forEach((element) => {
    element.addEventListener('input', () => {
      hideError(elements.intentError);
      readOverviewInputs();
      persist();
    });
    element.addEventListener('change', persistOverview);
  });
  elements.overviewSymbol.addEventListener('change', persistOverview);
  elements.intentForm.addEventListener('change', persistOverview);
  elements.intentForm.addEventListener('submit', (event) => {
    event.preventDefault();
  });
  document.querySelectorAll('[data-book-tab]').forEach((tab) => {
    tab.addEventListener('click', () => {
      const next = tab.dataset.bookTab;
      if (!BOOK_TABS.includes(next)) return;
      state.overviewTab = next;
      persist();
      renderOverview();
    });
  });

  window.addEventListener('storage', (event) => {
    if (event.key !== STORAGE_KEY) return;
    state.zones = [];
    state.observations = {};
    state.policy = null;
    state.policyVersions = [];
    state.agentConfig = null;
    state.agentConfigVersions = [];
    state.agentLastCheck = null;
    state.selectedId = null;
    state.ticker = { ...EMPTY_TICKER };
    state.intentDraft = { ...EMPTY_INTENT };
    state.overviewTab = 'positions';
    elements.agentConfigForm.dataset.configKey = '';
    readStorage();
    render();
  });

  window.addEventListener('hashchange', () => {
    readOverviewInputs();
    persist();
    setView(currentView());
  });

  readStorage();
  if (!window.location.hash) window.location.hash = '#/ban-zone';
  render();
})();
