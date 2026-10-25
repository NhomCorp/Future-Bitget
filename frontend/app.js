(() => {
  'use strict';

  const STORAGE_KEY = 'future-bitget-zone-desk-v1';
  const STORAGE_SCHEMA = 5;
  const VIEWS = ['tong-quan', 'ban-zone', 'ket-noi', 'cau-hinh-ai', 'phong-cach', 'mandate', 'de-xuat-cap', 'quyen-ai', 'nhat-ky'];
  const NAV_AUTONOMY = { PROPOSAL_ONLY: 'proposal', MANAGED_ZONE: 'zone', AUTONOMOUS_WITHIN_MANDATE: 'tự chủ' };
  const DEFAULT_VIEW = 'tong-quan';
  const AUTONOMY_LABELS = {
    PROPOSAL_ONLY: 'Chỉ ghi proposal',
    MANAGED_ZONE: 'Quản lý zone đã mở',
    AUTONOMOUS_WITHIN_MANDATE: 'Tự chủ trong mandate'
  };
  const MAX_GEMINI_KEYS = 20;
  const EMPTY_TICKER = { symbol: '', last: '', mark: '', funding: '' };
  const EMPTY_INTENT = { side: 'long', price: '', size: '' };
  const EMPTY_BITGET = { status: 'idle', error: '', refreshError: '', asOf: '', equity: null, ticker: null, positions: [], orders: [], fills: [], assets: [] };
  const EMPTY_PAIR_SCREEN = { status: 'idle', error: '', asOf: '', count: 0 };
  const EMPTY_STYLE = { status: 'idle', error: '', count: 0, entries: [] };
  const STYLE_KIND_LABELS = { preference: 'Ưu tiên', note: 'Ghi chú', no_trade: 'Không giao dịch' };
  const STYLE_FORBIDDEN = ['leverage', 'granted_capital', 'max_zones', 'daily_loss', 'drawdown', 'max_order_risk', 'loss limit', 'loss_limit', 'zone_loss', 'margin'];
  const EMPTY_DEMO_SCAN = { status: 'idle', error: '', action: '', posted: false, reason: '', agentError: '', protect: '', equity: '', scanned: 0 };
  const DEMO_CYCLE_MS = 8000;
  const SNAPSHOT_POLL_MS = 12000;
  const EMPTY_DEMO_KILL = { status: 'idle', error: '', cancelled: 0, closed: 0, clear: false, reason: '' };
  const BOOK_TABS = ['positions', 'orders', 'fills', 'reconcile', 'assets'];
  const FILL_LIMIT = 20;
  const PAIR_SCREEN_LIMIT = 12;
  const state = {
    zones: [], selectedId: null, observations: {}, policy: null, policyVersions: [],
    agentConfig: null, agentConfigVersions: [], agentLastCheck: null,
    pairCandidates: [], pairScreen: { ...EMPTY_PAIR_SCREEN },
    ticker: { ...EMPTY_TICKER }, intentDraft: { ...EMPTY_INTENT }, overviewTab: 'positions',
    bitget: { ...EMPTY_BITGET }, demoScan: { ...EMPTY_DEMO_SCAN }, demoKill: { ...EMPTY_DEMO_KILL },
    style: { ...EMPTY_STYLE }, styleEditingId: null, storageAvailable: true, view: DEFAULT_VIEW
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
    overviewAvailable: $('#overview-available'), overviewAvailableNote: $('#overview-available-note'),
    overviewUpnl: $('#overview-upnl'), overviewUpnlNote: $('#overview-upnl-note'),
    overviewPositionsCount: $('#overview-positions-count'), overviewOrdersCount: $('#overview-orders-count'),
    overviewFillsCount: $('#overview-fills-count'),
    overviewRefresh: $('#overview-refresh'), overviewSnapshotStatus: $('#overview-snapshot-status'),
    bookPositions: $('#book-positions'), bookOrders: $('#book-orders'), bookFills: $('#book-fills'),
    bookReconcile: $('#book-reconcile'), bookAssets: $('#book-assets'),
    connectStatus: $('#connect-status'), connectBanner: $('#connect-banner'), connectRefresh: $('#connect-refresh'),
    connectKeyForm: $('#connect-key-form'), connectKeyError: $('#connect-key-error'),
    bitgetApiKey: $('#bitget-api-key'), bitgetApiSecret: $('#bitget-api-secret'),
    bitgetPassphrase: $('#bitget-passphrase'), bitgetConfirmDemo: $('#bitget-confirm-demo'),
    mandateAllowlist: $('#mandate-allowlist'),
    pairGate: $('#pair-gate'), pairVersion: $('#pair-version'), pairAllowlist: $('#pair-allowlist'),
    pairAllowlistEmpty: $('#pair-allowlist-empty'), pairScreenButton: $('#pair-screen-button'),
    pairScreenStatus: $('#pair-screen-status'), pairPending: $('#pair-pending'),
    pairApproveSelected: $('#pair-approve-selected'), pairManualForm: $('#pair-manual-form'),
    pairManualSymbol: $('#pair-manual-symbol'), pairError: $('#pair-error'),
    pairRejected: $('#pair-rejected'), pairRejectedEmpty: $('#pair-rejected-empty'),
    demoScanForm: $('#demo-scan-form'), demoScanGate: $('#demo-scan-gate'),
    demoScanLimits: $('#demo-scan-limits'),
    demoCycleRun: $('#demo-cycle-run'), demoCycleStop: $('#demo-cycle-stop'),
    demoScanError: $('#demo-scan-error'), demoScanStatus: $('#demo-scan-status'),
    demoKillForm: $('#demo-kill-form'), demoKillGate: $('#demo-kill-gate'),
    demoKillConfirm: $('#demo-kill-confirm'),
    demoKillSubmit: $('#demo-kill-submit'), demoKillError: $('#demo-kill-error'),
    demoKillStatus: $('#demo-kill-status'),
    styleList: $('#style-list'), styleStatus: $('#style-status'), styleRefresh: $('#style-refresh'),
    styleForm: $('#style-form'), styleError: $('#style-error'), styleKind: $('#style-kind'),
    styleId: $('#style-id'), styleNoTrade: $('#style-no-trade'), styleFormMode: $('#style-form-mode'),
    styleCancel: $('#style-cancel'), styleRetire: $('#style-retire')
  };
  let connectStatusRequest = 0;
  let bitgetSnapshotRequest = 0;
  let pairScreenRequest = 0;
  let styleRequest = 0;
  let snapshotPollTimer = 0;
  let snapshotInFlight = false;
  let overviewFetchStarted = false;
  let demoCycleRunning = false;
  let demoCycleTimer = 0;
  let demoCycleInFlight = false;
  const secretStore = new WeakMap();

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
      && Array.isArray(value.symbol_allowlist)
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
      && (value.position_review_interval == null
        || (Number.isInteger(value.position_review_interval)
          && value.position_review_interval >= 1
          && value.position_review_interval <= 240))
      && isOptionalPositiveDecimal(value.sl_pct)
      && isOptionalPositiveDecimal(value.zone_loss_limit_usdt)
      && isOptionalPositiveDecimal(value.max_order_risk_usdt)
      && isOptionalPositiveDecimal(value.max_size)
    );
  }

  function isOptionalPositiveDecimal(value) {
    return value == null
      || (typeof value === 'string' && Number.isFinite(Number(value)) && Number(value) > 0);
  }

  function policyTradeLimits(policy) {
    if (!policy) return null;
    const slPct = String(policy.sl_pct || '').trim();
    const lossBudget = String(policy.zone_loss_limit_usdt || '').trim();
    const maxOrderRisk = String(policy.max_order_risk_usdt || '').trim();
    const maxSize = String(policy.max_size || '').trim();
    if (!slPct || !lossBudget || !maxOrderRisk || !maxSize) return null;
    if ([slPct, lossBudget, maxOrderRisk, maxSize].some((item) => !(Number(item) > 0))) return null;
    return { sl_pct: slPct, loss_budget: lossBudget, max_order_risk: maxOrderRisk, max_size: maxSize };
  }

  function hasDemoAgent() {
    const draft = state.agentConfig;
    if (!draft) return false;
    if (draft.provider === 'gemini') return Boolean(pickGeminiApiKey(draft)?.key);
    return Boolean(draft.api_key);
  }

  function normalisePolicy(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const policy = { ...value, daily_loss_reference: value.daily_loss_reference || 'day_start_equity' };
    return isPolicy(policy) ? policy : null;
  }

  function isPairCandidate(value) {
    return Boolean(
      value && typeof value === 'object' && !Array.isArray(value)
      && typeof value.symbol === 'string' && /^[A-Z0-9_-]{1,32}$/.test(value.symbol)
      && ['pending', 'approved', 'rejected'].includes(value.status)
      && typeof value.reason === 'string'
      && typeof value.proposedAt === 'string'
      && ['screen', 'manual'].includes(value.source)
    );
  }

  function normalisePairCandidates(value) {
    if (!Array.isArray(value)) return [];
    const seen = new Set();
    const items = [];
    for (const row of value) {
      if (!isPairCandidate(row)) continue;
      const symbol = row.symbol.toUpperCase();
      if (seen.has(symbol)) continue;
      seen.add(symbol);
      items.push({
        symbol,
        status: row.status,
        reason: String(row.reason || '').slice(0, 80),
        last: row.last == null ? '' : String(row.last),
        volume24h: row.volume24h == null ? '' : String(row.volume24h),
        change24h: row.change24h == null ? '' : String(row.change24h),
        proposedAt: row.proposedAt,
        decidedAt: row.decidedAt ? String(row.decidedAt) : '',
        source: row.source
      });
    }
    return items;
  }

  function currentAllowlist() {
    return Array.isArray(state.policy?.symbol_allowlist) ? [...state.policy.symbol_allowlist] : [];
  }

  function nextPolicy(patch, source) {
    if (!state.policy) throw new Error('Lưu Mandate trước khi duyệt cặp.');
    const allowlist = Array.isArray(patch.symbol_allowlist) ? patch.symbol_allowlist : currentAllowlist();
    if (allowlist.some((symbol) => !/^[A-Z0-9_-]{1,32}$/.test(symbol))) {
      throw new Error('Symbol chỉ dùng chữ in hoa, số, gạch ngang hoặc gạch dưới.');
    }
    if (new Set(allowlist).size !== allowlist.length) throw new Error('Symbol không được lặp lại.');
    return {
      ...state.policy,
      ...patch,
      symbol_allowlist: allowlist,
      version: state.policy.version + 1,
      created_at: new Date().toISOString(),
      source
    };
  }

  function savePolicy(policy) {
    const previousPolicy = state.policy;
    const previousVersions = state.policyVersions;
    state.policy = policy;
    state.policyVersions = [...state.policyVersions, policy];
    if (!persist()) {
      state.policy = previousPolicy;
      state.policyVersions = previousVersions;
      render();
      return false;
    }
    render();
    return true;
  }

  function isHttpUrl(value) {
    try {
      const parsed = new URL(String(value || '').trim());
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }

  function isPrivateHostname(hostname) {
    const host = String(hostname || '').trim().toLowerCase().replace(/^\[|\]$/g, '');
    if (!host) return true;
    if (['localhost', '127.0.0.1', '0.0.0.0', '::1', 'metadata.google.internal'].includes(host)) return true;
    if (host.endsWith('.localhost') || host.endsWith('.local') || host.endsWith('.internal')) return true;
    if (/^10\./.test(host) || /^127\./.test(host) || /^169\.254\./.test(host) || /^192\.168\./.test(host)) return true;
    const match172 = host.match(/^172\.(\d+)\./);
    if (match172) {
      const second = Number(match172[1]);
      if (second >= 16 && second <= 31) return true;
    }
    return host === '::' || host.startsWith('fe80:') || host.startsWith('fc') || host.startsWith('fd');
  }

  function isLocalHostname(hostname) {
    const host = String(hostname || '').trim().toLowerCase().replace(/^\[|\]$/g, '');
    return host === 'localhost' || host === '127.0.0.1' || host === '::1' || host.endsWith('.localhost');
  }

  function isPublicHttpsUrl(value) {
    try {
      const parsed = new URL(String(value || '').trim());
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password) return false;
      if (parsed.port && parsed.port !== '443') return false;
      return !isPrivateHostname(parsed.hostname);
    } catch {
      return false;
    }
  }

  function isAllowedOpenAiUrl(value) {
    return isPublicHttpsUrl(value);
  }

  function isDirectCheckUrl(value) {
    try {
      const parsed = new URL(String(value || '').trim());
      if (parsed.username || parsed.password) return false;
      if (isLocalHostname(parsed.hostname) && (parsed.protocol === 'http:' || parsed.protocol === 'https:')) return true;
      return isAllowedOpenAiUrl(value);
    } catch {
      return false;
    }
  }

  function maskSecret(value) {
    const text = String(value || '');
    if (!text) return '';
    if (text.length <= 8) return '•'.repeat(text.length);
    return `${text.slice(0, 4)}${'•'.repeat(text.length - 8)}${text.slice(-4)}`;
  }

  function bindSecretInput(input) {
    if (!input || input.dataset.secretBound === '1') return input;
    input.dataset.secretBound = '1';
    input.dataset.masked = '1';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.addEventListener('focus', () => {
      if (input.dataset.masked !== '1') return;
      input.value = secretStore.get(input) || '';
      input.dataset.masked = '0';
    });
    input.addEventListener('blur', () => {
      const current = String(input.value || '');
      secretStore.set(input, current);
      input.value = maskSecret(current);
      input.dataset.masked = '1';
    });
    return input;
  }

  function setSecretInput(input, value) {
    bindSecretInput(input);
    const text = String(value || '');
    secretStore.set(input, text);
    input.value = maskSecret(text);
    input.dataset.masked = '1';
  }

  function readSecretInput(input) {
    if (!input) return '';
    if (input.dataset.masked === '1') return String(secretStore.get(input) || '').trim();
    return String(input.value || '').trim();
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
      if (!data || ![1, 2, 3, 4, 5].includes(data.version) || !Array.isArray(data.zones) || !data.observations || typeof data.observations !== 'object' || Array.isArray(data.observations)) {
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
      state.pairCandidates = normalisePairCandidates(data.pairCandidates);
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
      state.pairCandidates = [];
      state.pairScreen = { ...EMPTY_PAIR_SCREEN };
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
        agentLastCheck: state.agentLastCheck, pairCandidates: state.pairCandidates,
        ticker: state.ticker, intentDraft: state.intentDraft, overviewTab: state.overviewTab
      }));
      state.storageAvailable = true;
      elements.localState.textContent = 'Lưu trong trình duyệt';
      const versionText = state.policy ? `Policy v${state.policy.version}` : 'Chưa lưu policy';
      elements.policyVersion.textContent = versionText;
      elements.autonomyVersion.textContent = versionText;
      if (elements.pairVersion) elements.pairVersion.textContent = versionText;
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

  function formatTime(value) {
    if (value === null || value === undefined || value === '') return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('vi-VN');
  }

  function bookKey(symbol, side) {
    return `${String(symbol || '').trim().toUpperCase()}:${String(side || '').trim().toLowerCase()}`;
  }

  function currentView() {
    const hash = window.location.hash.replace(/^#\/?/, '');
    return VIEWS.includes(hash) ? hash : DEFAULT_VIEW;
  }

  function navChecklist() {
    const allowlist = currentAllowlist();
    const autonomy = state.policy?.ai_autonomy;
    return {
      'ban-zone': String(state.zones.length),
      'cau-hinh-ai': state.agentConfig ? `v${state.agentConfig.version}` : 'chưa',
      mandate: state.policy ? `v${state.policy.version}` : 'chưa',
      'de-xuat-cap': state.policy ? String(allowlist.length) : '—',
      'quyen-ai': state.policy && NAV_AUTONOMY[autonomy] ? NAV_AUTONOMY[autonomy] : 'chưa',
      'phong-cach': state.style.status === 'ok' ? String(state.style.count) : '—'
    };
  }

  function renderNav(activeView) {
    const checklist = navChecklist();
    document.querySelectorAll('.nav-link').forEach((link) => {
      const view = link.dataset.view;
      const active = view === activeView;
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
      const meta = link.querySelector('[data-nav-meta]');
      if (!meta) {
        link.classList.remove('is-ready', 'is-wait');
        return;
      }
      const text = checklist[meta.dataset.navMeta] || '';
      meta.textContent = text;
      const ready = text !== '' && text !== 'chưa' && text !== '—' && text !== '0';
      link.classList.toggle('is-ready', ready);
      link.classList.toggle('is-wait', text === 'chưa' || text === '0');
    });
  }

  function setView(view) {
    const next = VIEWS.includes(view) ? view : DEFAULT_VIEW;
    state.view = next;
    if (window.location.hash !== `#/${next}`) window.location.hash = `#/${next}`;
    document.querySelectorAll('[data-view-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.viewPanel !== next;
    });
    renderNav(next);
    if (next === 'ket-noi') loadConnectStatus();
    if (next === 'phong-cach') {
      renderStyle();
      if (state.style.status === 'idle' || state.style.status === 'error') loadUserStyle();
    }
    if (next === 'tong-quan') {
      startSnapshotPoll();
      if (!overviewFetchStarted) {
        overviewFetchStarted = true;
        loadBitgetSnapshot();
      }
    } else {
      overviewFetchStarted = false;
      stopSnapshotPoll();
    }
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
      banner.textContent = 'Không đọc được env. Chạy npm start rồi mở lại trang. Key Bitget ghi vào .env qua form bên dưới.';
      list.innerHTML = [
        connectRow('Chế độ UI', pillMarkup('Demo / dry-run', 'ok')),
        connectRow('GET Bitget', pillMarkup('Không đọc được', 'warn'))
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
    if (missingCreds) warnings.push('Thiếu key Demo. Điền form bên dưới hoặc sửa .env rồi bấm Đọc lại env.');
    if (warnings.length) {
      banner.hidden = false;
      banner.className = `connect-banner ${data.bitget_env === 'live' || data.live_guard === 'on' ? 'is-error' : ''}`;
      banner.textContent = warnings.join(' ');
    } else {
      banner.hidden = false;
      banner.className = 'connect-banner is-ok';
      banner.textContent = 'Đủ key chỉ-đọc cho Demo. Tổng quan GET Demo, không gửi lệnh.';
    }
    list.innerHTML = [
      connectRow('Chế độ UI', pillMarkup('Demo / dry-run', 'ok')),
      connectRow('File <code>.env</code>', pillMarkup(envFile.text, envFile.kind)),
      connectRow('<code>BITGET_ENV</code>', pillMarkup(envMode.text, envMode.kind)),
      connectRow('<code>BITGET_API_KEY</code>', pillMarkup(apiKey.text, apiKey.kind)),
      connectRow('<code>BITGET_API_SECRET</code>', pillMarkup(apiSecret.text, apiSecret.kind)),
      connectRow('<code>BITGET_PASSPHRASE</code>', pillMarkup(passphrase.text, passphrase.kind)),
      connectRow('<code>GROK_TRADER_ALLOW_LIVE</code>', pillMarkup(liveGuard.text, liveGuard.kind)),
      connectRow('GET Bitget', data.get_bitget === 'connected'
        ? pillMarkup('GET Demo đã nối', 'ok')
        : pillMarkup('Chưa nối', 'warn'))
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

  function clearBitgetKeyForm() {
    setSecretInput(elements.bitgetApiKey, '');
    setSecretInput(elements.bitgetApiSecret, '');
    setSecretInput(elements.bitgetPassphrase, '');
    elements.bitgetConfirmDemo.checked = false;
  }

  async function saveBitgetCredentials(event) {
    event.preventDefault();
    hideError(elements.connectKeyError);
    const apiKey = readSecretInput(elements.bitgetApiKey);
    const apiSecret = readSecretInput(elements.bitgetApiSecret);
    const passphrase = readSecretInput(elements.bitgetPassphrase);
    if (!apiKey || !apiSecret || !passphrase) {
      elements.connectKeyError.textContent = 'Nhập đủ API key, secret và passphrase.';
      elements.connectKeyError.hidden = false;
      return;
    }
    if (!elements.bitgetConfirmDemo.checked) {
      elements.connectKeyError.textContent = 'Xác nhận đây là Demo key trước khi lưu.';
      elements.connectKeyError.hidden = false;
      return;
    }
    elements.connectKeyForm.querySelector('[type="submit"]').disabled = true;
    try {
      const response = await fetch('/api/connect-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, passphrase, confirm_demo: '1' })
      });
      const payload = await response.json().catch(() => null);
      if (!payload || payload.ok !== true) {
        throw new Error((payload && payload.error) || 'Không ghi được .env. Chạy npm start rồi thử lại.');
      }
      clearBitgetKeyForm();
      renderConnectStatus(payload);
      showNotice('Đã ghi Demo key vào .env trên máy này. Không hiện giá trị. GET Demo từ Tổng quan, không gửi lệnh.');
    } catch (error) {
      elements.connectKeyError.textContent = error && error.message ? String(error.message) : 'Không ghi được .env.';
      elements.connectKeyError.hidden = false;
    } finally {
      elements.connectKeyForm.querySelector('[type="submit"]').disabled = false;
    }
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
    const symbols = currentAllowlist();
    if (symbols.some((symbol) => !/^[A-Z0-9_-]{1,32}$/.test(symbol))) throw new Error('Symbol chỉ dùng chữ in hoa, số, gạch ngang hoặc gạch dưới.');
    if (new Set(symbols).size !== symbols.length) throw new Error('Symbol không được lặp lại.');
    const intervalRaw = String(form.get('position_review_interval') || '').trim();
    const interval = Number(intervalRaw);
    if (!Number.isInteger(interval) || interval < 1 || interval > 240) {
      throw new Error('Chu kỳ quét phải là số nguyên từ 1 đến 240 phút.');
    }
    const slPct = parseFinite(form.get('sl_pct'), 'SL chiến lược', { required: true, positive: true });
    const zoneLoss = parseFinite(form.get('zone_loss_limit_usdt'), 'Giới hạn lỗ zone', { required: true, positive: true });
    const maxOrderRisk = parseFinite(form.get('max_order_risk_usdt'), 'Rủi ro tối đa mỗi lệnh', { required: true, positive: true });
    const maxSize = parseFinite(form.get('max_size'), 'Trần khối lượng', { required: true, positive: true });
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
      position_review_interval: interval,
      sl_pct: slPct,
      zone_loss_limit_usdt: zoneLoss,
      max_order_risk_usdt: maxOrderRisk,
      max_size: maxSize,
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
      const key = readSecretInput(row.querySelector('.gemini-key-value'));
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
      apiKey = readSecretInput(elements.openaiApiKey);
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
    if (!isDirectCheckUrl(draft.base_url)) throw new Error('Base URL không được phép cho Check live.');
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
    const canProxy = draft.provider === 'gemini' || isAllowedOpenAiUrl(draft.base_url);
    if (canProxy) {
      try {
        const proxied = await checkViaProxy(draft, picked, timeoutMs);
        if (proxied) return { ...proxied, picked };
      } catch (error) {
        if (error && error.message === 'Phản hồi check không hợp lệ.') throw error;
        if (error && !/failed to fetch|network|404/i.test(String(error.message))) throw error;
      }
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
    keyInput.className = 'gemini-key-value secret-input';
    keyInput.type = 'text';
    keyInput.spellcheck = false;
    keyInput.autocomplete = 'off';
    setSecretInput(keyInput, key);
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
      setSecretInput(elements.openaiApiKey, '');
      renderGeminiKeyRows();
      syncAgentProviderFields();
      renderLastCheck();
      return;
    }
    form.elements.provider.value = config.provider;
    form.elements.model.value = config.model;
    form.elements.base_url.value = config.base_url;
    form.elements.request_timeout.value = config.request_timeout;
    setSecretInput(elements.openaiApiKey, config.api_key || '');
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
    const allowlist = policy?.symbol_allowlist || [];
    elements.zoneSymbol.innerHTML = allowlist.length
      ? allowlist.map((symbol) => `<option value="${escapeHTML(symbol)}">${escapeHTML(symbol)}</option>`).join('')
      : `<option value="">${policy ? 'Duyệt cặp trước' : 'Lưu policy trước'}</option>`;
    const canCreate = Boolean(policy) && allowlist.length > 0;
    elements.zoneSymbol.disabled = !canCreate;
    elements.createSubmit.disabled = !canCreate;
    elements.createForm.querySelectorAll('input, select').forEach((field) => { field.disabled = !canCreate; });
    elements.zoneGate.hidden = canCreate;
    elements.zoneGate.textContent = policy
      ? 'Duyệt ít nhất một cặp trước khi tạo zone.'
      : 'Lưu Mandate trước khi tạo zone.';
    renderAllowlistChips(elements.mandateAllowlist, allowlist, { removable: false, empty: 'Chưa duyệt cặp nào.' });
    renderPairs();
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
    form.elements.position_review_interval.value = policy.position_review_interval || '';
    if (form.elements.sl_pct) form.elements.sl_pct.value = policy.sl_pct || '';
    if (form.elements.zone_loss_limit_usdt) form.elements.zone_loss_limit_usdt.value = policy.zone_loss_limit_usdt || '';
    if (form.elements.max_order_risk_usdt) form.elements.max_order_risk_usdt.value = policy.max_order_risk_usdt || '';
    if (form.elements.max_size) form.elements.max_size.value = policy.max_size || '';
  }

  function formatCompact(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    if (Math.abs(number) >= 1_000_000_000) return `${(number / 1_000_000_000).toFixed(2)}B`;
    if (Math.abs(number) >= 1_000_000) return `${(number / 1_000_000).toFixed(2)}M`;
    if (Math.abs(number) >= 1_000) return `${(number / 1_000).toFixed(2)}K`;
    return formatNumber(value);
  }

  function renderAllowlistChips(target, symbols, { removable = false, empty = 'Trống', rejected = false } = {}) {
    if (!target) return;
    if (!symbols.length) {
      target.innerHTML = `<span class="pair-empty">${escapeHTML(empty)}</span>`;
      return;
    }
    target.innerHTML = symbols.map((symbol) => {
      const remove = removable
        ? `<button type="button" data-pair-remove="${escapeHTML(symbol)}" aria-label="Gỡ ${escapeHTML(symbol)}">Gỡ</button>`
        : '';
      return `<span class="allowlist-chip${rejected ? ' is-rejected' : ''}">${escapeHTML(symbol)}${remove}</span>`;
    }).join('');
  }

  function renderPairs() {
    const policy = state.policy;
    const allowlist = currentAllowlist();
    const pending = state.pairCandidates.filter((item) => item.status === 'pending');
    const rejected = state.pairCandidates.filter((item) => item.status === 'rejected').map((item) => item.symbol);
    const versionText = policy ? `Policy v${policy.version}` : 'Chưa lưu policy';
    if (elements.pairVersion) elements.pairVersion.textContent = versionText;
    if (elements.pairGate) {
      elements.pairGate.hidden = Boolean(policy);
      elements.pairGate.textContent = 'Lưu Mandate trước khi duyệt cặp.';
    }
    const canEdit = Boolean(policy);
    if (elements.pairScreenButton) elements.pairScreenButton.disabled = !canEdit || state.pairScreen.status === 'loading';
    if (elements.pairApproveSelected) elements.pairApproveSelected.disabled = !canEdit || pending.length === 0;
    if (elements.pairManualForm) {
      elements.pairManualForm.querySelectorAll('input, button').forEach((field) => { field.disabled = !canEdit; });
    }
    renderAllowlistChips(elements.pairAllowlist, allowlist, { removable: canEdit, empty: 'Chưa có cặp được duyệt.' });
    if (elements.pairAllowlistEmpty) elements.pairAllowlistEmpty.hidden = true;
    renderAllowlistChips(elements.pairRejected, rejected, { empty: 'Chưa từ chối cặp nào.', rejected: true });
    if (elements.pairRejectedEmpty) elements.pairRejectedEmpty.hidden = true;
    if (elements.pairPending) {
      elements.pairPending.innerHTML = pending.length
        ? pending.map((item) => {
            const meta = [
              item.volume24h ? `Vol 24h ${formatCompact(item.volume24h)}` : '',
              item.last ? `Last ${formatNumber(item.last)}` : '',
              item.change24h ? `${formatNumber(item.change24h)}%` : ''
            ].filter(Boolean).join(' · ');
            return `<div class="pair-row">
              <input type="checkbox" data-pair-select="${escapeHTML(item.symbol)}" aria-label="Chọn ${escapeHTML(item.symbol)}" />
              <span><strong>${escapeHTML(item.symbol)}</strong><small>${escapeHTML(item.reason || 'Đề xuất chờ duyệt')}</small></span>
              <span class="pair-row-meta">${escapeHTML(meta || '—')}</span>
              <span class="pair-row-actions">
                <button class="button button-secondary" type="button" data-pair-approve="${escapeHTML(item.symbol)}">Duyệt</button>
                <button class="button button-ghost" type="button" data-pair-reject="${escapeHTML(item.symbol)}">Từ chối</button>
              </span>
            </div>`;
          }).join('')
        : bookEmpty('Chưa có ứng viên', canEdit ? 'Bấm Đề xuất cặp để sàng lọc public USDT-M. Không tự vào allowlist.' : 'Lưu Mandate rồi đề xuất cặp.');
    }
    renderPairScreenStatus();
  }

  function renderPairScreenStatus(pending = false) {
    if (!elements.pairScreenStatus) return;
    if (pending || state.pairScreen.status === 'loading') {
      elements.pairScreenStatus.hidden = false;
      elements.pairScreenStatus.className = 'pair-screen-status is-pending';
      elements.pairScreenStatus.textContent = 'Đang GET public ticker…';
      return;
    }
    if (state.pairScreen.status === 'error') {
      elements.pairScreenStatus.hidden = false;
      elements.pairScreenStatus.className = 'pair-screen-status is-error';
      elements.pairScreenStatus.textContent = state.pairScreen.error || 'Không sàng lọc được.';
      return;
    }
    if (state.pairScreen.status === 'ok') {
      elements.pairScreenStatus.hidden = false;
      elements.pairScreenStatus.className = 'pair-screen-status';
      const asOf = state.pairScreen.asOf ? ` · ${formatTime(state.pairScreen.asOf)}` : '';
      elements.pairScreenStatus.textContent = `Đã sàng ${state.pairScreen.count} ứng viên công khai${asOf}. GET Demo, không gửi lệnh.`;
      return;
    }
    elements.pairScreenStatus.hidden = true;
    elements.pairScreenStatus.textContent = '';
  }

  function upsertCandidate(symbol, patch) {
    const key = String(symbol || '').trim().toUpperCase();
    const now = new Date().toISOString();
    const current = state.pairCandidates.find((item) => item.symbol === key);
    const next = {
      symbol: key,
      status: 'pending',
      reason: 'Đề xuất chờ duyệt',
      last: '',
      volume24h: '',
      change24h: '',
      proposedAt: now,
      decidedAt: '',
      source: 'screen',
      ...(current || {}),
      ...patch,
      symbol: key
    };
    state.pairCandidates = [next, ...state.pairCandidates.filter((item) => item.symbol !== key)];
  }

  function mergeScreenCandidates(rows) {
    const allowlist = new Set(currentAllowlist());
    const blocked = new Set(
      state.pairCandidates.filter((item) => item.status === 'rejected' || item.status === 'pending').map((item) => item.symbol)
    );
    let added = 0;
    for (const row of rows) {
      const symbol = String(row?.symbol || '').trim().toUpperCase();
      if (!/^[A-Z0-9_-]{1,32}$/.test(symbol) || allowlist.has(symbol) || blocked.has(symbol)) continue;
      upsertCandidate(symbol, {
        status: 'pending',
        reason: String(row.reason || 'Top khối lượng 24h USDT-M').slice(0, 80),
        last: row.last == null ? '' : String(row.last),
        volume24h: row.volume24h == null ? '' : String(row.volume24h),
        change24h: row.change24h == null ? '' : String(row.change24h),
        proposedAt: new Date().toISOString(),
        decidedAt: '',
        source: 'screen'
      });
      added += 1;
    }
    return added;
  }

  function approveSymbols(symbols) {
    const wanted = [...new Set(symbols.map((symbol) => String(symbol || '').trim().toUpperCase()).filter(Boolean))];
    if (!wanted.length) throw new Error('Chọn ít nhất một cặp để duyệt.');
    if (wanted.some((symbol) => !/^[A-Z0-9_-]{1,32}$/.test(symbol))) {
      throw new Error('Symbol chỉ dùng chữ in hoa, số, gạch ngang hoặc gạch dưới.');
    }
    const allowlist = currentAllowlist();
    const added = wanted.filter((symbol) => !allowlist.includes(symbol));
    if (!added.length) throw new Error('Cặp đã nằm trong allowlist.');
    const now = new Date().toISOString();
    const previousCandidates = state.pairCandidates.map((item) => ({ ...item }));
    const policy = nextPolicy({ symbol_allowlist: [...allowlist, ...added] }, 'pair_approval');
    added.forEach((symbol) => {
      upsertCandidate(symbol, { status: 'approved', decidedAt: now, source: state.pairCandidates.find((item) => item.symbol === symbol)?.source || 'manual' });
    });
    if (!savePolicy(policy)) {
      state.pairCandidates = previousCandidates;
      render();
      return false;
    }
    return added;
  }

  function rejectSymbol(symbol) {
    const key = String(symbol || '').trim().toUpperCase();
    if (!key) return;
    if (currentAllowlist().includes(key)) throw new Error('Gỡ khỏi allowlist trước khi từ chối.');
    upsertCandidate(key, { status: 'rejected', decidedAt: new Date().toISOString() });
    persist();
    render();
  }

  function removeAllowlistSymbol(symbol) {
    const key = String(symbol || '').trim().toUpperCase();
    const allowlist = currentAllowlist().filter((item) => item !== key);
    if (allowlist.length === currentAllowlist().length) return;
    const previousCandidates = state.pairCandidates.map((item) => ({ ...item }));
    const policy = nextPolicy({ symbol_allowlist: allowlist }, 'pair_removal');
    state.pairCandidates = state.pairCandidates.filter((item) => item.symbol !== key);
    if (!savePolicy(policy)) {
      state.pairCandidates = previousCandidates;
      render();
    }
  }

  function loadPairScreen() {
    if (!state.policy) {
      elements.pairError.textContent = 'Lưu Mandate trước khi đề xuất cặp.';
      elements.pairError.hidden = false;
      return;
    }
    hideError(elements.pairError);
    const requestId = ++pairScreenRequest;
    state.pairScreen = { ...EMPTY_PAIR_SCREEN, status: 'loading' };
    if (elements.pairScreenButton) elements.pairScreenButton.disabled = true;
    renderPairScreenStatus(true);
    fetch(`/api/pair-screen?limit=${PAIR_SCREEN_LIMIT}`, { method: 'GET', cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json().catch(() => null);
        if (!data || typeof data !== 'object') throw new Error('cli invalid');
        if (!response.ok || data.ok !== true) throw new Error(data.error || 'pair screen failed');
        return data;
      })
      .then((data) => {
        if (requestId !== pairScreenRequest) return;
        const rows = Array.isArray(data.candidates) ? data.candidates : [];
        const added = mergeScreenCandidates(rows);
        state.pairScreen = {
          status: 'ok',
          error: '',
          asOf: data.as_of || '',
          count: added
        };
        persist();
        render();
        showNotice(added ? `Đã đề xuất ${added} cặp. Chưa vào allowlist — hãy duyệt hoặc từ chối.` : 'Không còn cặp mới trong top khối lượng. GET Demo, không gửi lệnh.');
      })
      .catch((error) => {
        if (requestId !== pairScreenRequest) return;
        state.pairScreen = {
          status: 'error',
          error: String(error && error.message ? error.message : 'pair screen failed').slice(0, 80),
          asOf: '',
          count: 0
        };
        render();
      })
      .finally(() => {
        if (requestId !== pairScreenRequest) return;
        if (elements.pairScreenButton) elements.pairScreenButton.disabled = !state.policy;
      });
  }

  function bookEmpty(title, copy) {
    return `<div class="empty-state"><div class="empty-symbol" aria-hidden="true">○</div><h3>${escapeHTML(title)}</h3><p>${escapeHTML(copy)}</p></div>`;
  }

  function pnlClass(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number === 0) return '';
    return number > 0 ? ' is-up' : ' is-down';
  }

  function usdtAsset(snap) {
    const assets = Array.isArray(snap.assets) ? snap.assets : [];
    return assets.find((row) => String(row.margin_coin || '').toUpperCase() === 'USDT') || assets[0] || null;
  }

  function finiteMetric(value) {
    if (value === null || value === undefined || value === '') return null;
    return Number.isFinite(Number(value)) ? value : null;
  }

  function snapshotUnrealized(snap) {
    const asset = usdtAsset(snap);
    const fromAsset = finiteMetric(asset && asset.unrealized_pnl);
    if (fromAsset != null) return fromAsset;
    const values = (Array.isArray(snap.positions) ? snap.positions : [])
      .map((row) => Number(row.unrealized_pnl))
      .filter((value) => Number.isFinite(value));
    if (!values.length) return null;
    return String(values.reduce((sum, value) => sum + value, 0));
  }

  function renderAccountMetrics(snap) {
    const ready = snap.status === 'ok';
    const dashNote = snap.status === 'loading'
      ? 'Đang GET Demo'
      : snap.status === 'error'
        ? 'GET lỗi, không bịa số'
        : 'Chưa GET Demo';
    if (elements.overviewEquity) {
      elements.overviewEquity.textContent = ready ? formatNumber(snap.equity) : '—';
      elements.overviewEquityNote.textContent = ready
        ? (snap.equity == null || snap.equity === '' ? 'GET xong, không có equity' : 'Equity Demo GET')
        : dashNote;
    }
    const asset = usdtAsset(snap);
    const available = finiteMetric(asset && asset.available);
    if (elements.overviewAvailable) {
      elements.overviewAvailable.textContent = ready ? formatNumber(available) : '—';
      elements.overviewAvailableNote.textContent = ready
        ? (available == null ? 'GET xong, không có available' : 'Available USDT')
        : dashNote;
    }
    const upnl = ready ? snapshotUnrealized(snap) : null;
    if (elements.overviewUpnl) {
      elements.overviewUpnl.textContent = ready ? formatNumber(upnl) : '—';
      elements.overviewUpnl.className = ready ? pnlClass(upnl).trim() : '';
      elements.overviewUpnlNote.textContent = ready
        ? 'Chưa chốt trên Demo. Đã chốt / PnL ngày chưa tách.'
        : dashNote;
    }
    if (elements.overviewPositionsCount) {
      elements.overviewPositionsCount.textContent = ready ? String((snap.positions || []).length) : '—';
    }
    if (elements.overviewOrdersCount) {
      elements.overviewOrdersCount.textContent = ready ? String((snap.orders || []).length) : '—';
    }
    if (elements.overviewFillsCount) {
      elements.overviewFillsCount.textContent = ready ? String((snap.fills || []).length) : '—';
    }
  }

  function bookTable(headers, rows) {
    const head = headers.map((label) => `<th>${escapeHTML(label)}</th>`).join('');
    const body = rows.map((row) => `<tr>${row}</tr>`).join('');
    return `<div class="book-table-wrap"><table class="book-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function reconcileKindClass(kind) {
    if (kind === 'matched') return 'pill-matched';
    if (kind === 'local_only') return 'pill-local-only';
    if (kind === 'exchange_only') return 'pill-exchange-only';
    return 'pill-preview';
  }

  function buildReconcileRows() {
    const positions = Array.isArray(state.bitget.positions) ? state.bitget.positions : [];
    const fills = Array.isArray(state.bitget.fills) ? state.bitget.fills : [];
    const tracked = state.zones.filter((zone) => zone.state === 'ACTIVE' || zone.state === 'STOPPING');
    const preview = state.zones.filter((zone) => zone.state === 'PREVIEW');
    const claimed = new Set();
    const rows = [];
    tracked.forEach((zone) => {
      const key = bookKey(zone.symbol, zone.side);
      const fillCount = fills.filter((row) => String(row.symbol || '').toUpperCase() === String(zone.symbol || '').toUpperCase()).length;
      const fillNote = fillCount ? `${fillCount} fill gần nhất cùng symbol` : 'Không có fill gần nhất cùng symbol';
      if (claimed.has(key)) {
        rows.push({
          kind: 'local_only',
          label: 'Chỉ local',
          zone_id: zone.zone_id,
          zone_state: zone.state,
          symbol: zone.symbol,
          side: zone.side,
          size: '',
          note: `Trùng ${key} với zone khác. ${fillNote}`
        });
        return;
      }
      const position = positions.find((row) => bookKey(row.symbol, row.side) === key);
      if (position) {
        claimed.add(key);
        rows.push({
          kind: 'matched',
          label: 'Khớp',
          zone_id: zone.zone_id,
          zone_state: zone.state,
          symbol: zone.symbol,
          side: zone.side,
          size: position.size || '',
          note: `Vị thế sàn size ${position.size || '—'}. ${fillNote}`
        });
        return;
      }
      rows.push({
        kind: 'local_only',
        label: 'Chỉ local',
        zone_id: zone.zone_id,
        zone_state: zone.state,
        symbol: zone.symbol,
        side: zone.side,
        size: '',
        note: `Zone ${zone.state} không có vị thế sàn. ${fillNote}`
      });
    });
    positions.forEach((row) => {
      const key = bookKey(row.symbol, row.side);
      if (claimed.has(key)) return;
      const fillCount = fills.filter((fill) => String(fill.symbol || '').toUpperCase() === String(row.symbol || '').toUpperCase()).length;
      claimed.add(key);
      rows.push({
        kind: 'exchange_only',
        label: 'Chỉ sàn',
        zone_id: '—',
        zone_state: '—',
        symbol: row.symbol,
        side: row.side,
        size: row.size || '',
        note: fillCount ? `Không có zone ACTIVE/STOPPING. ${fillCount} fill gần nhất cùng symbol` : 'Không có zone local ACTIVE/STOPPING'
      });
    });
    preview.forEach((zone) => {
      rows.push({
        kind: 'preview',
        label: 'Preview',
        zone_id: zone.zone_id,
        zone_state: zone.state,
        symbol: zone.symbol,
        side: zone.side,
        size: '',
        note: 'Zone PREVIEW không kỳ vọng vị thế sàn'
      });
    });
    const knownSymbols = new Set(state.zones.map((zone) => String(zone.symbol || '').toUpperCase()).filter(Boolean));
    const orphanFills = fills.filter((row) => !knownSymbols.has(String(row.symbol || '').toUpperCase()));
    if (orphanFills.length) {
      rows.push({
        kind: 'exchange_only',
        label: 'Fill lẻ',
        zone_id: '—',
        zone_state: '—',
        symbol: orphanFills[0].symbol || '—',
        side: '—',
        size: '',
        note: `${orphanFills.length} fill gần nhất không thuộc symbol zone local`
      });
    }
    return rows;
  }

  function renderBookPanels() {
    const snap = state.bitget;
    const loadingCopy = 'Đang GET Demo. Làm mới mỗi 12 giây, không gửi lệnh.';
    const errorCopy = snap.error || 'Thiếu key, lỗi sàn hoặc Origin lạ. Tab để rỗng, không bịa số.';
    if (snap.status === 'loading') {
      elements.bookPositions.innerHTML = bookEmpty('Đang GET vị thế Demo', loadingCopy);
      elements.bookOrders.innerHTML = bookEmpty('Đang GET lệnh chờ Demo', loadingCopy);
      elements.bookFills.innerHTML = bookEmpty('Đang GET fills Demo', loadingCopy);
      elements.bookReconcile.innerHTML = bookEmpty('Đang GET để đối soát', loadingCopy);
      elements.bookAssets.innerHTML = bookEmpty('Đang GET tài sản Demo', loadingCopy);
      return;
    }
    if (snap.status !== 'ok') {
      const title = snap.status === 'error' ? 'Không lấy được số sàn' : 'Chưa GET Demo';
      const copy = snap.status === 'error' ? errorCopy : 'Mở Tổng quan hoặc bấm làm mới. Lỗi thì tab rỗng, không bịa số.';
      const reconcileCopy = snap.status === 'error' ? errorCopy : 'Mở Tổng quan hoặc bấm làm mới. Đối soát chỉ đọc, không đổi state.';
      elements.bookPositions.innerHTML = bookEmpty(title, copy);
      elements.bookOrders.innerHTML = bookEmpty(title, copy);
      elements.bookFills.innerHTML = bookEmpty(title, copy);
      elements.bookReconcile.innerHTML = bookEmpty(title, reconcileCopy);
      elements.bookAssets.innerHTML = bookEmpty(title, copy);
      return;
    }
    if (!snap.positions.length) {
      elements.bookPositions.innerHTML = bookEmpty('Không có vị thế trên Demo', 'GET thành công. Không bịa số.');
    } else {
      elements.bookPositions.innerHTML = bookTable(
        ['Symbol', 'Side', 'Size', 'Đòn bẩy', 'Entry', 'Mark', 'Thanh lý', 'uPnL'],
        snap.positions.map((row) => [
          `<td>${escapeHTML(row.symbol || '—')}</td>`,
          `<td>${escapeHTML(row.side || '—')}</td>`,
          `<td>${escapeHTML(formatNumber(row.size))}</td>`,
          `<td>${row.leverage ? `${escapeHTML(formatNumber(row.leverage))}×` : '—'}</td>`,
          `<td>${escapeHTML(formatNumber(row.entry_price))}</td>`,
          `<td>${escapeHTML(formatNumber(row.mark_price))}</td>`,
          `<td>${escapeHTML(formatNumber(row.liquidation_price))}</td>`,
          `<td class="${pnlClass(row.unrealized_pnl).trim()}">${escapeHTML(formatNumber(row.unrealized_pnl))}</td>`
        ].join(''))
      );
    }
    if (!snap.orders.length) {
      elements.bookOrders.innerHTML = bookEmpty('Không có lệnh chờ trên Demo', 'GET thành công. Không bịa số.');
    } else {
      elements.bookOrders.innerHTML = bookTable(
        ['Symbol', 'Side', 'Hướng', 'Giá', 'KL', 'Loại', 'Trạng thái'],
        snap.orders.map((row) => [
          `<td>${escapeHTML(row.symbol || '—')}</td>`,
          `<td>${escapeHTML(row.side || '—')}</td>`,
          `<td>${escapeHTML(row.trade_side || row.pos_side || '—')}</td>`,
          `<td>${escapeHTML(formatNumber(row.price))}</td>`,
          `<td>${escapeHTML(formatNumber(row.size))}</td>`,
          `<td>${escapeHTML(row.order_type || '—')}</td>`,
          `<td>${escapeHTML(row.status || '—')}</td>`
        ].join(''))
      );
    }
    if (!snap.assets.length) {
      elements.bookAssets.innerHTML = bookEmpty('Không có tài sản trên Demo', 'GET thành công. Không bịa số.');
    } else {
      elements.bookAssets.innerHTML = bookTable(
        ['Coin', 'Equity', 'Available', 'uPnL'],
        snap.assets.map((row) => [
          `<td>${escapeHTML(row.margin_coin || '—')}</td>`,
          `<td>${escapeHTML(formatNumber(row.equity))}</td>`,
          `<td>${escapeHTML(formatNumber(row.available))}</td>`,
          `<td class="${pnlClass(row.unrealized_pnl).trim()}">${escapeHTML(formatNumber(row.unrealized_pnl))}</td>`
        ].join(''))
      );
    }
    if (!snap.fills.length) {
      elements.bookFills.innerHTML = bookEmpty('Không có fill gần nhất trên Demo', 'GET thành công. Tối đa 20 fill. Không bịa số.');
    } else {
      elements.bookFills.innerHTML = `<p class="book-note">Tối đa ${FILL_LIMIT} fill gần nhất từ GET Demo. Không dùng fill-history.</p>` + bookTable(
        ['Thời điểm', 'Symbol', 'Side', 'Hướng', 'Giá', 'KL', 'Phí', 'PnL', 'Scope'],
        snap.fills.map((row) => [
          `<td>${escapeHTML(formatTime(row.filled_at))}</td>`,
          `<td>${escapeHTML(row.symbol || '—')}</td>`,
          `<td>${escapeHTML(row.side || '—')}</td>`,
          `<td>${escapeHTML(row.trade_side || row.pos_side || '—')}</td>`,
          `<td>${escapeHTML(formatNumber(row.price))}</td>`,
          `<td>${escapeHTML(formatNumber(row.size))}</td>`,
          `<td class="${pnlClass(row.fee).trim()}">${escapeHTML(formatNumber(row.fee))}</td>`,
          `<td class="${pnlClass(row.profit).trim()}">${escapeHTML(formatNumber(row.profit))}</td>`,
          `<td>${escapeHTML(row.trade_scope || '—')}</td>`
        ].join(''))
      );
    }
    const reconcileRows = buildReconcileRows();
    if (!reconcileRows.length) {
      elements.bookReconcile.innerHTML = bookEmpty('Không có zone local và không có vị thế sàn', 'GET thành công. Đối soát chỉ đọc, không đổi state local, không POST.');
    } else {
      elements.bookReconcile.innerHTML = `<p class="book-note">Đối soát zone local với vị thế/fills sàn. Không chạy PaperReconcile, không đổi state, không POST.</p>` + bookTable(
        ['Kết quả', 'Zone', 'State', 'Symbol', 'Side', 'Size sàn', 'Ghi chú'],
        reconcileRows.map((row) => [
          `<td><span class="pill ${reconcileKindClass(row.kind)}">${escapeHTML(row.label)}</span></td>`,
          `<td>${escapeHTML(row.zone_id || '—')}</td>`,
          `<td>${escapeHTML(row.zone_state || '—')}</td>`,
          `<td>${escapeHTML(row.symbol || '—')}</td>`,
          `<td>${escapeHTML(row.side || '—')}</td>`,
          `<td>${escapeHTML(formatNumber(row.size))}</td>`,
          `<td>${escapeHTML(row.note || '—')}</td>`
        ].join(''))
      );
    }
  }

  function applySnapshotTicker(ticker) {
    if (!ticker || typeof ticker !== 'object') return false;
    let changed = false;
    ['last', 'mark', 'funding'].forEach((field) => {
      if (ticker[field] == null || ticker[field] === '') return;
      if (state.ticker[field] === String(ticker[field])) return;
      state.ticker[field] = String(ticker[field]);
      changed = true;
    });
    return changed;
  }

  function stopSnapshotPoll() {
    if (!snapshotPollTimer) return;
    window.clearInterval(snapshotPollTimer);
    snapshotPollTimer = 0;
  }

  function startSnapshotPoll() {
    if (snapshotPollTimer) return;
    snapshotPollTimer = window.setInterval(() => {
      if (document.hidden || state.view !== 'tong-quan') return;
      loadBitgetSnapshot({ quiet: true });
    }, SNAPSHOT_POLL_MS);
  }

  function loadBitgetSnapshot(options = {}) {
    const quiet = Boolean(options.quiet) && state.bitget.status === 'ok';
    if (quiet && snapshotInFlight) return;
    const requestId = ++bitgetSnapshotRequest;
    snapshotInFlight = true;
    const symbol = String(elements.overviewSymbol.value || state.ticker.symbol || '').trim().toUpperCase();
    if (!quiet) {
      state.bitget = { ...EMPTY_BITGET, status: 'loading' };
      renderOverview();
    }
    if (elements.overviewRefresh) elements.overviewRefresh.disabled = true;
    const query = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
    fetch(`/api/bitget-snapshot${query}`, { method: 'GET', cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json().catch(() => null);
        if (!data || typeof data !== 'object') throw new Error('cli invalid');
        if (!response.ok || data.ok !== true) throw new Error(data.error || 'snapshot failed');
        return data;
      })
      .then((data) => {
        if (requestId !== bitgetSnapshotRequest) return;
        state.bitget = {
          status: 'ok',
          error: '',
          refreshError: '',
          asOf: data.as_of || '',
          equity: data.equity == null || data.equity === '' ? null : data.equity,
          ticker: data.ticker && typeof data.ticker === 'object' ? data.ticker : null,
          positions: Array.isArray(data.positions) ? data.positions : [],
          orders: Array.isArray(data.pending_orders) ? data.pending_orders : [],
          fills: Array.isArray(data.fills) ? data.fills.slice(0, FILL_LIMIT) : [],
          assets: Array.isArray(data.assets) ? data.assets : []
        };
        if (applySnapshotTicker(state.bitget.ticker)) persist();
        renderOverview();
      })
      .catch((error) => {
        if (requestId !== bitgetSnapshotRequest) return;
        const message = String(error && error.message ? error.message : 'snapshot failed').slice(0, 80);
        if (quiet) {
          state.bitget = { ...state.bitget, refreshError: message };
        } else {
          state.bitget = { ...EMPTY_BITGET, status: 'error', error: message };
        }
        renderOverview();
      })
      .finally(() => {
        if (requestId !== bitgetSnapshotRequest) return;
        snapshotInFlight = false;
        if (elements.overviewRefresh) elements.overviewRefresh.disabled = false;
      });
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
    const snap = state.bitget;
    renderAccountMetrics(snap);
    if (elements.overviewSnapshotStatus) {
      elements.overviewSnapshotStatus.classList.remove('is-ok', 'is-error');
      if (snap.status === 'loading') {
        elements.overviewSnapshotStatus.textContent = 'Đang GET Demo…';
      } else if (snap.status === 'ok' && snap.refreshError) {
        elements.overviewSnapshotStatus.classList.add('is-error');
        const when = snap.asOf ? ` · ${snap.asOf}` : '';
        elements.overviewSnapshotStatus.textContent = `Làm mới lỗi, giữ số cũ${when}: ${snap.refreshError}`;
      } else if (snap.status === 'ok') {
        elements.overviewSnapshotStatus.classList.add('is-ok');
        const when = snap.asOf ? ` · ${snap.asOf}` : '';
        elements.overviewSnapshotStatus.textContent = `GET Demo xong${when}. Làm mới mỗi 12 giây. Không gửi lệnh.`;
      } else if (snap.status === 'error') {
        elements.overviewSnapshotStatus.classList.add('is-error');
        elements.overviewSnapshotStatus.textContent = `GET Demo lỗi: ${snap.error || 'không lấy được số sàn'}`;
      } else {
        elements.overviewSnapshotStatus.textContent = 'Chưa GET Demo';
      }
    }
    document.querySelectorAll('[data-book-tab]').forEach((tab) => {
      const active = tab.dataset.bookTab === state.overviewTab;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll('[data-book-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.bookPanel !== state.overviewTab;
    });
    renderBookPanels();
    renderDemoScan();
    renderDemoKill();
  }

  function renderDemoScan() {
    if (!elements.demoScanForm) return;
    const policy = state.policy;
    const allowlist = policy?.symbol_allowlist || [];
    const tradeLimits = policyTradeLimits(policy);
    const ready = Boolean(policy) && policy.ai_autonomy === 'AUTONOMOUS_WITHIN_MANDATE' && allowlist.length > 0 && Boolean(tradeLimits) && hasDemoAgent();
    if (elements.demoScanGate) {
      if (!policy) elements.demoScanGate.textContent = 'Lưu Mandate, duyệt ít nhất một cặp, rồi chọn quyền Tự chủ.';
      else if (policy.ai_autonomy !== 'AUTONOMOUS_WITHIN_MANDATE') elements.demoScanGate.textContent = 'Chu kỳ Demo POST cần quyền Tự chủ trong mandate.';
      else if (!allowlist.length) elements.demoScanGate.textContent = 'Allowlist trống — duyệt cặp trước. Không POST.';
      else if (!tradeLimits) elements.demoScanGate.textContent = 'Lưu Mandate với SL, lỗ zone, rủi ro/lệnh và trần khối lượng.';
      else if (!hasDemoAgent()) elements.demoScanGate.textContent = 'Cấu hình AI trước khi Chạy.';
      else elements.demoScanGate.textContent = '';
      elements.demoScanGate.hidden = !elements.demoScanGate.textContent;
    }
    if (elements.demoScanLimits) {
      elements.demoScanLimits.textContent = tradeLimits
        ? `Mandate: SL ${tradeLimits.sl_pct}% · lỗ ${tradeLimits.loss_budget} USDT · risk ${tradeLimits.max_order_risk} USDT · trần ${tradeLimits.max_size}.`
        : 'Hạn mức lấy từ Mandate đã lưu.';
    }
    const busy = state.demoScan.status === 'loading' || demoCycleInFlight;
    if (elements.demoCycleRun) elements.demoCycleRun.disabled = !ready || busy || demoCycleRunning;
    if (elements.demoCycleStop) elements.demoCycleStop.disabled = !demoCycleRunning;
    if (!elements.demoScanStatus) return;
    const scan = state.demoScan;
    if (scan.status === 'idle' && !demoCycleRunning) {
      elements.demoScanStatus.hidden = true;
      return;
    }
    elements.demoScanStatus.hidden = false;
    elements.demoScanStatus.className = 'pair-screen-status';
    if (scan.status === 'loading' || (demoCycleRunning && demoCycleInFlight && scan.status === 'idle')) {
      elements.demoScanStatus.classList.add('is-pending');
      elements.demoScanStatus.textContent = demoCycleRunning ? 'Đang chạy vòng Demo…' : 'Đang chạy 1 chu kỳ Demo…';
    } else if (scan.status === 'error') {
      elements.demoScanStatus.classList.add('is-error');
      elements.demoScanStatus.textContent = scan.error || 'Chu kỳ Demo lỗi';
    } else {
      const post = scan.posted ? 'Đã POST Demo' : 'Không POST';
      const agentNote = scan.agentError ? ` · AI ${scan.agentError}` : '';
      const loopNote = demoCycleRunning ? ' · vòng đang chạy' : '';
      const protectNote = scan.protect ? ` · protect ${scan.protect}` : '';
      const equityNote = scan.equity ? ` · equity ${scan.equity}` : '';
      const scanned = scan.scanned ? ` · ${scan.scanned} cặp` : '';
      elements.demoScanStatus.textContent = `${post} · action ${scan.action || '—'} · ${scan.reason || 'REVIEW_RAN'}${scanned}${agentNote}${protectNote}${equityNote}${loopNote}. ${allowlist.join(', ') || '—'}.`;
    }
  }

  function stopDemoCycle() {
    demoCycleRunning = false;
    if (demoCycleTimer) {
      clearTimeout(demoCycleTimer);
      demoCycleTimer = 0;
    }
    renderDemoScan();
  }

  function scheduleDemoCycle() {
    if (!demoCycleRunning) return;
    if (demoCycleTimer) clearTimeout(demoCycleTimer);
    demoCycleTimer = setTimeout(() => {
      if (!demoCycleRunning) return;
      runDemoScan({ fromLoop: true });
    }, DEMO_CYCLE_MS);
  }

  function startDemoCycle() {
    hideError(elements.demoScanError);
    if (demoCycleRunning) return;
    demoCycleRunning = true;
    renderDemoScan();
    runDemoScan({ fromLoop: true });
  }

  function runDemoScan(event) {
    const fromLoop = Boolean(event && event.fromLoop);
    if (event && typeof event.preventDefault === 'function') event.preventDefault();
    if (fromLoop && demoCycleInFlight) {
      scheduleDemoCycle();
      return;
    }
    hideError(elements.demoScanError);
    const policy = state.policy;
    try {
      if (!policy) throw new Error('Lưu Mandate trước.');
      if (policy.ai_autonomy !== 'AUTONOMOUS_WITHIN_MANDATE') throw new Error('Cần quyền Tự chủ trong mandate.');
      if (!policy.symbol_allowlist?.length) throw new Error('Allowlist trống — duyệt cặp trước.');
      const tradeLimits = policyTradeLimits(policy);
      if (!tradeLimits) throw new Error('Lưu Mandate với SL, lỗ zone, rủi ro/lệnh và trần khối lượng.');
      const draft = state.agentConfig;
      const picked = draft
        ? (draft.provider === 'gemini' ? pickGeminiApiKey(draft) : { label: '', key: draft.api_key })
        : null;
      if (!picked?.key) throw new Error('Cấu hình AI trước khi Chạy.');
      if (draft.provider === 'openai_compatible' && !isAllowedOpenAiUrl(draft.base_url)) {
        throw new Error('Base URL AI không được phép.');
      }
      const limits = {
        scope: 'allowlist',
        sl_pct: tradeLimits.sl_pct,
        loss_budget: tradeLimits.loss_budget,
        max_order_risk: tradeLimits.max_order_risk,
        max_size: tradeLimits.max_size
      };
      const body = {
        policy,
        limits,
        confirm_demo: '1',
        place_orders: true,
        agent: {
          provider: draft.provider,
          model: draft.model,
          base_url: draft.base_url || '',
          api_key: picked.key,
          label: picked.label || '',
          request_timeout: Number(draft.request_timeout) || 30
        }
      };
      state.demoScan = { ...EMPTY_DEMO_SCAN, status: 'loading' };
      demoCycleInFlight = true;
      renderDemoScan();
      fetch('/api/demo-cycle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
        .then(async (response) => {
          const data = await response.json().catch(() => null);
          if (!data || typeof data !== 'object') throw new Error('cli invalid');
          if (!response.ok || data.ok !== true) throw new Error(data.error || 'cycle failed');
          return data;
        })
        .then((data) => {
          const agent = data.agent && typeof data.agent === 'object' ? data.agent : {};
          const protect = data.protect && typeof data.protect === 'object' ? data.protect : {};
          const equity = data.equity && typeof data.equity === 'object' ? data.equity : {};
          state.demoScan = {
            status: 'ok',
            error: '',
            action: data.action || '',
            posted: Boolean(data.exchange_post),
            reason: data.reason_code || '',
            agentError: agent.called && !agent.ok ? String(agent.error || 'PROVIDER_ERROR') : '',
            protect: protect.triggered ? (protect.reason_code || 'TRIGGERED') : (protect.reason_code || ''),
            equity: equity.complete ? 'ok' : ((equity.reason_codes || []).join(',') || 'incomplete'),
            scanned: Number(data.scanned) || (Array.isArray(data.pairs) ? data.pairs.length : 0)
          };
          const posted = data.exchange_post ? 'Đã POST Demo' : 'Không POST';
          const agentNote = agent.called ? (agent.ok ? ' · AI' : ` · AI ${agent.error || 'lỗi'}`) : '';
          const scanned = state.demoScan.scanned ? ` · ${state.demoScan.scanned} cặp` : '';
          showNotice(`${posted} · ${data.action || 'NO_TRADE'} · ${data.reason_code || 'REVIEW_RAN'}${scanned}${agentNote}.`);
        })
        .catch((error) => {
          const message = String(error && error.message ? error.message : 'cycle failed').slice(0, 80);
          state.demoScan = { ...EMPTY_DEMO_SCAN, status: 'error', error: message };
          elements.demoScanError.textContent = message;
          elements.demoScanError.hidden = false;
        })
        .finally(() => {
          demoCycleInFlight = false;
          renderDemoScan();
          if (demoCycleRunning) scheduleDemoCycle();
        });
    } catch (error) {
      demoCycleInFlight = false;
      elements.demoScanError.textContent = error.message;
      elements.demoScanError.hidden = false;
      if (fromLoop) stopDemoCycle();
      else renderDemoScan();
    }
  }

  function renderDemoKill() {
    if (!elements.demoKillForm) return;
    const policy = state.policy;
    const allowlist = policy?.symbol_allowlist || [];
    const symbol = String(state.ticker.symbol || '').trim().toUpperCase();
    const ready = Boolean(allowlist.length && symbol && allowlist.includes(symbol));
    if (elements.demoKillGate) {
      if (!allowlist.length) elements.demoKillGate.textContent = 'Allowlist trống — duyệt cặp trước. Không flatten.';
      else if (!symbol) elements.demoKillGate.textContent = 'Chọn symbol đã duyệt trên thanh ticker.';
      else if (!allowlist.includes(symbol)) elements.demoKillGate.textContent = 'Symbol phải nằm trong allowlist.';
      else elements.demoKillGate.textContent = '';
      elements.demoKillGate.hidden = !elements.demoKillGate.textContent;
    }
    if (elements.demoKillSubmit) elements.demoKillSubmit.disabled = !ready || state.demoKill.status === 'loading';
    if (!elements.demoKillStatus) return;
    const kill = state.demoKill;
    if (kill.status === 'idle') {
      elements.demoKillStatus.hidden = true;
      return;
    }
    elements.demoKillStatus.hidden = false;
    elements.demoKillStatus.className = 'pair-screen-status';
    if (kill.status === 'loading') {
      elements.demoKillStatus.classList.add('is-pending');
      elements.demoKillStatus.textContent = 'Đang flatten Demo…';
    } else if (kill.status === 'error') {
      elements.demoKillStatus.classList.add('is-error');
      elements.demoKillStatus.textContent = kill.error || 'Kill Demo lỗi';
    } else {
      const leftover = kill.clear ? 'sàn sạch' : 'còn leftover';
      elements.demoKillStatus.textContent = `Hủy ${kill.cancelled} · đóng ${kill.closed} · ${leftover} · ${kill.reason || 'KILL_RAN'}.`;
    }
  }

  function runDemoKill(event) {
    event.preventDefault();
    hideError(elements.demoKillError);
    const policy = state.policy;
    const symbol = String(state.ticker.symbol || '').trim().toUpperCase();
    try {
      if (!policy?.symbol_allowlist?.length) throw new Error('Allowlist trống — duyệt cặp trước.');
      if (!symbol || !policy.symbol_allowlist.includes(symbol)) throw new Error('Symbol phải nằm trong allowlist.');
      if (!elements.demoKillConfirm?.checked) throw new Error('Cần xác nhận chạy trên Demo.');
      stopDemoCycle();
      state.demoKill = { ...EMPTY_DEMO_KILL, status: 'loading' };
      renderDemoKill();
      fetch('/api/demo-kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          allowlist: policy.symbol_allowlist,
          confirm_demo: '1',
          place_orders: true
        })
      })
        .then(async (response) => {
          const data = await response.json().catch(() => null);
          if (!data || typeof data !== 'object') throw new Error('cli invalid');
          if (!response.ok || data.ok !== true) throw new Error(data.error || 'kill failed');
          return data;
        })
        .then((data) => {
          state.demoKill = {
            status: 'ok',
            error: '',
            cancelled: Number(data.cancelled) || 0,
            closed: Number(data.closed) || 0,
            clear: Boolean(data.leftover_clear),
            reason: data.reason_code || ''
          };
          showNotice(`Kill Demo · hủy ${state.demoKill.cancelled} · đóng ${state.demoKill.closed} · ${state.demoKill.clear ? 'sàn sạch' : 'còn leftover'}.`);
          renderDemoKill();
          loadBitgetSnapshot();
        })
        .catch((error) => {
          const message = String(error && error.message ? error.message : 'kill failed').slice(0, 80);
          state.demoKill = { ...EMPTY_DEMO_KILL, status: 'error', error: message };
          elements.demoKillError.textContent = message;
          elements.demoKillError.hidden = false;
          renderDemoKill();
        });
    } catch (error) {
      elements.demoKillError.textContent = error.message;
      elements.demoKillError.hidden = false;
    }
  }

  function readOverviewInputs() {
    state.ticker = {
      symbol: String(elements.overviewSymbol.value || '').trim().toUpperCase(),
      last: String(elements.overviewLast.value || '').trim(),
      mark: String(elements.overviewMark.value || '').trim(),
      funding: String(elements.overviewFunding.value || '').trim()
    };
    state.intentDraft = {
      ...state.intentDraft,
      side: state.intentDraft.side === 'short' ? 'short' : 'long'
    };
  }

  function persistOverview() {
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
      ['Leverage tối đa', policy.max_leverage ? `${escapeHTML(formatNumber(policy.max_leverage))}×` : '—'],
      ['Chu kỳ quét', policy.position_review_interval ? `${escapeHTML(String(policy.position_review_interval))} phút` : '—'],
      ['SL Mandate', policy.sl_pct ? `${escapeHTML(formatNumber(policy.sl_pct))}%` : '—'],
      ['Trần KL Mandate', policy.max_size ? escapeHTML(formatNumber(policy.max_size)) : '—']
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

  function styleKindLabel(kind) {
    return STYLE_KIND_LABELS[kind] || kind || '—';
  }

  function syncStyleKindFields() {
    if (!elements.styleNoTrade || !elements.styleKind) return;
    elements.styleNoTrade.hidden = elements.styleKind.value !== 'no_trade';
  }

  function resetStyleForm() {
    state.styleEditingId = null;
    if (!elements.styleForm) return;
    elements.styleForm.reset();
    if (elements.styleId) elements.styleId.readOnly = false;
    if (elements.styleForm.elements.priority) elements.styleForm.elements.priority.value = '50';
    if (elements.styleForm.elements.scope) elements.styleForm.elements.scope.value = 'all';
    if (elements.styleForm.elements.window_min) elements.styleForm.elements.window_min.value = '30';
    if (elements.styleFormMode) elements.styleFormMode.textContent = 'Thói quen mới';
    if (elements.styleRetire) elements.styleRetire.hidden = true;
    syncStyleKindFields();
    if (elements.styleError) hideError(elements.styleError);
  }

  function fillStyleForm(entry) {
    if (!elements.styleForm || !entry) return;
    state.styleEditingId = entry.id;
    elements.styleForm.elements.kind.value = entry.kind || 'preference';
    elements.styleForm.elements.id.value = entry.id || '';
    elements.styleForm.elements.priority.value = String(entry.priority ?? 50);
    elements.styleForm.elements.scope.value = (entry.scope || ['all']).join(', ');
    elements.styleForm.elements.tags.value = (entry.tags || []).join(', ');
    elements.styleForm.elements.rule.value = entry.rule || '';
    const condition = entry.condition || {};
    elements.styleForm.elements.event_in.value = Array.isArray(condition.event_in) ? condition.event_in.join(', ') : '';
    elements.styleForm.elements.window_min.value = condition.window_min != null ? String(condition.window_min) : '30';
    if (elements.styleId) elements.styleId.readOnly = true;
    if (elements.styleFormMode) elements.styleFormMode.textContent = `Sửa ${entry.id} → v${Number(entry.version || 0) + 1}`;
    if (elements.styleRetire) elements.styleRetire.hidden = !entry.applied;
    syncStyleKindFields();
    if (elements.styleError) hideError(elements.styleError);
  }

  function applyStylePayload(data) {
    const entries = Array.isArray(data && data.entries) ? data.entries : [];
    state.style = {
      status: 'ok',
      error: '',
      count: Number.isInteger(data && data.count) ? data.count : entries.filter((row) => row.applied).length,
      entries
    };
  }

  function renderStyleStatus(pending = false) {
    if (!elements.styleStatus) return;
    if (pending || state.style.status === 'loading') {
      elements.styleStatus.hidden = false;
      elements.styleStatus.className = 'pair-screen-status is-pending';
      elements.styleStatus.textContent = 'Đang đọc YAML local…';
      return;
    }
    if (state.style.status === 'error') {
      elements.styleStatus.hidden = false;
      elements.styleStatus.className = 'pair-screen-status is-error';
      elements.styleStatus.textContent = state.style.error || 'Không đọc được phong cách.';
      return;
    }
    if (state.style.status === 'ok') {
      elements.styleStatus.hidden = false;
      elements.styleStatus.className = 'pair-screen-status';
      elements.styleStatus.textContent = `Đang áp dụng ${state.style.count} thói quen. Preference cho AI, không đè Mandate.`;
      return;
    }
    elements.styleStatus.hidden = false;
    elements.styleStatus.className = 'pair-screen-status';
    elements.styleStatus.textContent = 'Chưa đọc file phong cách.';
  }

  function renderStyle() {
    renderStyleStatus();
    if (!elements.styleList) return;
    const entries = state.style.entries || [];
    if (!entries.length) {
      const copy = state.style.status === 'ok'
        ? 'File trống hoặc chưa có bản đang hiệu lực. Thêm ở form dưới.'
        : 'Bấm Đọc lại YAML hoặc mở trang này khi server local đang chạy.';
      elements.styleList.innerHTML = bookEmpty('Chưa có thói quen', copy);
      return;
    }
    elements.styleList.innerHTML = entries.map((entry) => {
      const selected = state.styleEditingId === entry.id ? ' is-selected' : '';
      const retired = entry.status === 'retired' ? ' is-retired' : '';
      const blocked = entry.blocked ? ' is-blocked' : '';
      const pill = entry.blocked ? 'Bỏ qua' : entry.applied ? styleKindLabel(entry.kind) : (entry.status === 'retired' ? 'Đã dừng' : styleKindLabel(entry.kind));
      const pillClass = entry.blocked || entry.status === 'retired' ? 'pill-closed' : entry.kind === 'no_trade' ? 'pill-stopping' : 'pill-active';
      const meta = `v${entry.version} · ưu tiên ${entry.priority} · ${(entry.scope || ['all']).join(', ')}`;
      const actions = [
        `<button class="button button-secondary" type="button" data-style-edit="${escapeHTML(entry.id)}">Sửa</button>`
      ];
      if (entry.applied) {
        actions.push(`<button class="button button-ghost" type="button" data-style-retire="${escapeHTML(entry.id)}">Dừng</button>`);
      }
      return `<article class="style-row${selected}${retired}${blocked}">
        <div class="style-row-head"><span class="pill ${pillClass}">${escapeHTML(pill)}</span><strong class="style-row-id">${escapeHTML(entry.id)}</strong></div>
        <span class="style-row-actions">${actions.join('')}</span>
        <p class="style-row-rule">${escapeHTML(entry.rule || '—')}</p>
        <small class="style-row-id">${escapeHTML(meta)}</small>
      </article>`;
    }).join('');
  }

  function loadUserStyle({ quiet = false } = {}) {
    const requestId = ++styleRequest;
    state.style = { ...state.style, status: 'loading', error: '' };
    if (!quiet) renderStyle();
    fetch('/api/user-style', { method: 'GET', cache: 'no-store' })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        if (requestId !== styleRequest) return;
        if (!ok || !data || data.ok !== true) {
          state.style = { ...EMPTY_STYLE, status: 'error', error: (data && data.error) || 'Không đọc được phong cách.' };
        } else {
          applyStylePayload(data);
        }
        renderNav(state.view);
        renderStyle();
      })
      .catch(() => {
        if (requestId !== styleRequest) return;
        state.style = { ...EMPTY_STYLE, status: 'error', error: 'Không đọc được phong cách.' };
        renderNav(state.view);
        renderStyle();
      });
  }

  function styleDraftFromForm() {
    const form = elements.styleForm;
    const kind = String(form.elements.kind.value || '').trim();
    const id = String(form.elements.id.value || '').trim();
    const rule = String(form.elements.rule.value || '').trim();
    const blob = `${id} ${rule} ${form.elements.event_in.value || ''}`.toLowerCase();
    if (STYLE_FORBIDDEN.some((token) => blob.includes(token))) {
      throw new Error('Không ghi đòn bẩy, margin, vốn hoặc hạn mức rủi ro vào phong cách.');
    }
    const draft = {
      action: 'add',
      id,
      kind,
      rule,
      priority: form.elements.priority.value,
      scope: form.elements.scope.value,
      tags: form.elements.tags.value
    };
    if (kind === 'no_trade') {
      draft.condition = {
        event_in: form.elements.event_in.value,
        window_min: form.elements.window_min.value
      };
    }
    return draft;
  }

  function postUserStyle(body, notice) {
    if (elements.styleError) hideError(elements.styleError);
    return fetch('/api/user-style', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || !data || data.ok !== true) {
          throw new Error((data && data.error) || 'Không lưu được phong cách.');
        }
        applyStylePayload(data);
        resetStyleForm();
        renderNav(state.view);
        renderStyle();
        showNotice(notice);
      })
      .catch((error) => {
        if (elements.styleError) {
          elements.styleError.textContent = error.message || 'Không lưu được phong cách.';
          elements.styleError.hidden = false;
        }
      });
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

  if (elements.styleRefresh) {
    elements.styleRefresh.addEventListener('click', () => loadUserStyle());
  }
  if (elements.styleKind) {
    elements.styleKind.addEventListener('change', syncStyleKindFields);
  }
  if (elements.styleCancel) {
    elements.styleCancel.addEventListener('click', () => {
      resetStyleForm();
      renderStyle();
    });
  }
  if (elements.styleForm) {
    elements.styleForm.addEventListener('submit', (event) => {
      event.preventDefault();
      try {
        const draft = styleDraftFromForm();
        const ident = draft.id;
        postUserStyle(draft, `Đã thêm ${ident} (version mới). AI đọc khi chu kỳ Demo quét.`);
      } catch (error) {
        elements.styleError.textContent = error.message;
        elements.styleError.hidden = false;
      }
    });
  }
  if (elements.styleRetire) {
    elements.styleRetire.addEventListener('click', () => {
      const ident = state.styleEditingId;
      if (!ident) return;
      if (!window.confirm(`Dừng ${ident}? File giữ bản cũ, chỉ thêm version retired.`)) return;
      postUserStyle({ action: 'retire', id: ident }, `Đã dừng ${ident}.`);
    });
  }
  if (elements.styleList) {
    elements.styleList.addEventListener('click', (event) => {
      const edit = event.target.closest('[data-style-edit]');
      const retire = event.target.closest('[data-style-retire]');
      if (edit) {
        const entry = state.style.entries.find((row) => row.id === edit.dataset.styleEdit);
        if (entry) {
          fillStyleForm(entry);
          renderStyle();
        }
        return;
      }
      if (retire) {
        const ident = retire.dataset.styleRetire;
        if (!ident) return;
        if (!window.confirm(`Dừng ${ident}? File giữ bản cũ, chỉ thêm version retired.`)) return;
        postUserStyle({ action: 'retire', id: ident }, `Đã dừng ${ident}.`);
      }
    });
  }

  elements.policyForm.addEventListener('click', (event) => {
    const button = event.target.closest('[data-review-interval]');
    if (!button || !elements.policyForm.contains(button)) return;
    const minutes = Number(button.getAttribute('data-review-interval'));
    if (!Number.isInteger(minutes)) return;
    elements.policyForm.elements.position_review_interval.value = String(minutes);
  });
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

  function pairActionError(error) {
    if (!elements.pairError) return;
    elements.pairError.textContent = error && error.message ? error.message : 'Không cập nhật được allowlist.';
    elements.pairError.hidden = false;
  }

  elements.pairScreenButton.addEventListener('click', () => {
    loadPairScreen();
  });
  elements.pairApproveSelected.addEventListener('click', () => {
    hideError(elements.pairError);
    const selected = [...elements.pairPending.querySelectorAll('[data-pair-select]:checked')].map((input) => input.getAttribute('data-pair-select'));
    try {
      const added = approveSymbols(selected);
      if (added) showNotice(`Đã duyệt ${added.join(', ')} vào allowlist · policy v${state.policy.version}. Không gửi lệnh.`);
    } catch (error) {
      pairActionError(error);
    }
  });
  elements.pairPending.addEventListener('click', (event) => {
    const approve = event.target.closest('[data-pair-approve]');
    const reject = event.target.closest('[data-pair-reject]');
    if (!approve && !reject) return;
    hideError(elements.pairError);
    try {
      if (approve) {
        const added = approveSymbols([approve.getAttribute('data-pair-approve')]);
        if (added) showNotice(`Đã duyệt ${added.join(', ')} vào allowlist · policy v${state.policy.version}. Không gửi lệnh.`);
        return;
      }
      rejectSymbol(reject.getAttribute('data-pair-reject'));
      showNotice('Đã từ chối cặp. Không vào allowlist, không đề xuất lại.');
    } catch (error) {
      pairActionError(error);
    }
  });
  elements.pairAllowlist.addEventListener('click', (event) => {
    const button = event.target.closest('[data-pair-remove]');
    if (!button) return;
    hideError(elements.pairError);
    try {
      const symbol = button.getAttribute('data-pair-remove');
      removeAllowlistSymbol(symbol);
      if (state.policy) showNotice(`Đã gỡ ${symbol} khỏi allowlist · policy v${state.policy.version}.`);
    } catch (error) {
      pairActionError(error);
    }
  });
  elements.pairManualForm.addEventListener('submit', (event) => {
    event.preventDefault();
    hideError(elements.pairError);
    const symbol = String(elements.pairManualSymbol.value || '').trim().toUpperCase();
    try {
      if (!symbol) throw new Error('Nhập symbol để thêm tay.');
      const added = approveSymbols([symbol]);
      if (added) {
        upsertCandidate(symbol, { status: 'approved', source: 'manual', reason: 'Thêm tay', decidedAt: new Date().toISOString() });
        persist();
        render();
        elements.pairManualSymbol.value = '';
        showNotice(`Đã thêm ${added.join(', ')} vào allowlist · policy v${state.policy.version}. Không gửi lệnh.`);
      }
    } catch (error) {
      pairActionError(error);
    }
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
      `Chu kỳ quét: ${policy.position_review_interval || '—'} phút`,
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
  elements.overviewRefresh.addEventListener('click', () => {
    overviewFetchStarted = true;
    loadBitgetSnapshot();
  });
  if (elements.demoScanForm) {
    elements.demoScanForm.addEventListener('submit', (event) => {
      event.preventDefault();
      startDemoCycle();
    });
  }
  if (elements.demoCycleStop) {
    elements.demoCycleStop.addEventListener('click', stopDemoCycle);
  }
  if (elements.demoKillForm) {
    elements.demoKillForm.addEventListener('submit', runDemoKill);
  }
  elements.connectKeyForm.addEventListener('submit', (event) => {
    saveBitgetCredentials(event);
  });
  bindSecretInput(elements.openaiApiKey);
  bindSecretInput(elements.bitgetApiKey);
  bindSecretInput(elements.bitgetApiSecret);
  bindSecretInput(elements.bitgetPassphrase);

  $('#reset-button').addEventListener('click', () => {
    if (!window.confirm('Xóa toàn bộ zone, observation, policy, đề xuất cặp, cấu hình AI và ticker demo đã lưu trên trình duyệt này?')) return;
    state.zones = [];
    state.observations = {};
    state.policy = null;
    state.policyVersions = [];
    state.agentConfig = null;
    state.agentConfigVersions = [];
    state.agentLastCheck = null;
    state.pairCandidates = [];
    state.pairScreen = { ...EMPTY_PAIR_SCREEN };
    state.selectedId = null;
    state.ticker = { ...EMPTY_TICKER };
    state.intentDraft = { ...EMPTY_INTENT };
    state.overviewTab = 'positions';
    state.bitget = { ...EMPTY_BITGET };
    state.demoScan = { ...EMPTY_DEMO_SCAN };
    state.demoKill = { ...EMPTY_DEMO_KILL };
    stopDemoCycle();
    stopSnapshotPoll();
    overviewFetchStarted = false;
    pairScreenRequest += 1;
    elements.agentConfigForm.dataset.configKey = '';
    persist();
    render();
    elements.syncForm.reset();
    showNotice('Đã xóa dữ liệu demo trên trình duyệt này.');
  });

  [elements.overviewLast, elements.overviewMark, elements.overviewFunding].forEach((element) => {
    element.addEventListener('input', () => {
      readOverviewInputs();
      persist();
    });
    element.addEventListener('change', persistOverview);
  });
  elements.overviewSymbol.addEventListener('change', persistOverview);
  document.querySelectorAll('[data-book-tab]').forEach((tab) => {
    tab.addEventListener('click', () => {
      const next = tab.dataset.bookTab;
      if (!BOOK_TABS.includes(next)) return;
      state.overviewTab = next;
      persist();
      renderOverview();
    });
  });
  document.querySelectorAll('[data-overview-jump]').forEach((card) => {
    card.addEventListener('click', () => {
      const next = card.dataset.overviewJump;
      if (!BOOK_TABS.includes(next)) return;
      state.overviewTab = next;
      persist();
      renderOverview();
      const panel = document.getElementById(`book-${next}`);
      if (panel) panel.scrollIntoView({ block: 'nearest' });
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
    state.pairCandidates = [];
    state.pairScreen = { ...EMPTY_PAIR_SCREEN };
    state.selectedId = null;
    state.ticker = { ...EMPTY_TICKER };
    state.intentDraft = { ...EMPTY_INTENT };
    state.overviewTab = 'positions';
    state.bitget = { ...EMPTY_BITGET };
    state.demoScan = { ...EMPTY_DEMO_SCAN };
    state.demoKill = { ...EMPTY_DEMO_KILL };
    overviewFetchStarted = false;
    stopSnapshotPoll();
    pairScreenRequest += 1;
    elements.agentConfigForm.dataset.configKey = '';
    readStorage();
    render();
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden || state.view !== 'tong-quan') return;
    loadBitgetSnapshot({ quiet: true });
  });

  window.addEventListener('hashchange', () => {
    readOverviewInputs();
    persist();
    setView(currentView());
  });

  readStorage();
  if (!window.location.hash) window.location.hash = `#/${DEFAULT_VIEW}`;
  render();
})();
