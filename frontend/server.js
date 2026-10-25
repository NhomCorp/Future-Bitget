"use strict";

const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const HOST = "127.0.0.1";
const PORT = 3007;
const ROOT = path.resolve(__dirname);
const REPO_ROOT = path.resolve(ROOT, "..");
const MAX_BODY = 32 * 1024;
const MAX_TIMEOUT_MS = 60_000;
const SNAPSHOT_TIMEOUT_MS = 45_000;
const SNAPSHOT_MAX_STDOUT = 512 * 1024;
const FILL_LIMIT = 20;
const PAIR_SCREEN_LIMIT_DEFAULT = 12;
const PAIR_SCREEN_LIMIT_MAX = 20;
const PAIR_SCREEN_TIMEOUT_MS = 45_000;
const PAIR_SCREEN_MAX_STDOUT = 512 * 1024;
const STYLE_TIMEOUT_MS = 15_000;
const STYLE_MAX_STDOUT = 256 * 1024;
const STYLE_BODY = 16 * 1024;
const STYLE_KINDS = new Set(["preference", "note", "no_trade"]);
const STYLE_ID_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const DEMO_SCAN_TIMEOUT_MS = 90_000;
const DEMO_SCAN_MAX_STDOUT = 256 * 1024;
const DEMO_SCAN_BODY = 64 * 1024;
const DEMO_KILL_TIMEOUT_MS = 60_000;
const DEMO_KILL_MAX_STDOUT = 256 * 1024;
const DEMO_KILL_BODY = 16 * 1024;
const SYMBOL_RE = /^[A-Z0-9_-]{1,32}$/;
const CONNECT_KEYS = ["BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSPHRASE"];
const LOCAL_ORIGINS = new Set([
  `http://${HOST}:${PORT}`,
  `http://127.0.0.1:${PORT}`,
  `http://localhost:${PORT}`,
]);
const PRIVATE_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"]);
const TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function send(res, status, body, headers) {
  res.writeHead(status, { "Cache-Control": "no-store", ...headers });
  res.end(body);
}

function sendJson(res, status, payload) {
  send(res, status, JSON.stringify(payload), { "Content-Type": "application/json; charset=utf-8" });
}

function redact(text, secret) {
  const raw = String(text || "");
  if (!secret) return raw;
  return raw.split(secret).join("[key]");
}

function readJsonBody(req, limit) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) {
        req.destroy();
        reject(new Error("payload too large"));
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"));
      } catch {
        reject(new Error("invalid json"));
      }
    });
    req.on("error", reject);
  });
}

function parseEnvFile(contents) {
  const values = {};
  for (const raw of String(contents || "").split(/\r?\n/)) {
    let line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("export ")) line = line.slice(7).trim();
    const eq = line.indexOf("=");
    if (eq < 1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === "'" || value[0] === '"')) {
      value = value.slice(1, -1);
    }
    if (key) values[key] = value;
  }
  return values;
}

function envFileCandidates() {
  const cwdEnv = path.resolve(process.cwd(), ".env");
  const rootEnv = path.join(REPO_ROOT, ".env");
  if (path.normalize(cwdEnv) === path.normalize(rootEnv)) return [cwdEnv];
  return [cwdEnv, rootEnv];
}

function readEnvLookup() {
  let fileValues = {};
  let envFile = "missing";
  for (const candidate of envFileCandidates()) {
    try {
      if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) continue;
      fileValues = parseEnvFile(fs.readFileSync(candidate, "utf8"));
      envFile = "present";
      break;
    } catch {
      continue;
    }
  }
  return {
    envFile,
    lookup(name) {
      const fromProcess = process.env[name];
      if (fromProcess !== undefined && String(fromProcess).trim()) return fromProcess;
      return fileValues[name];
    },
  };
}

function presence(value) {
  return String(value || "").trim() ? "present" : "missing";
}

function bitgetEnvStatus(value) {
  const mode = String(value || "").trim().toLowerCase();
  if (!mode) return "missing";
  if (mode === "demo") return "demo";
  if (mode === "live" || mode === "production" || mode === "prod") return "live";
  return "other";
}

function localHostOk(req) {
  const host = String(req.headers.host || "").toLowerCase();
  return host === `${HOST}:${PORT}` || host === `127.0.0.1:${PORT}` || host === `localhost:${PORT}`;
}

function localOriginOk(req) {
  const origin = String(req.headers.origin || "").trim();
  if (origin) return LOCAL_ORIGINS.has(origin);
  const referer = String(req.headers.referer || "").trim();
  if (!referer) return false;
  try {
    const url = new URL(referer);
    return LOCAL_ORIGINS.has(`${url.protocol}//${url.host}`);
  } catch {
    return false;
  }
}

function localRequestOk(req) {
  return localHostOk(req) && localOriginOk(req);
}

function isPrivateHostname(hostname) {
  const host = String(hostname || "").trim().toLowerCase().replace(/^\[|\]$/g, "");
  if (!host || PRIVATE_HOSTS.has(host)) return true;
  if (host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal")) return true;
  if (/^10\./.test(host) || /^127\./.test(host) || /^169\.254\./.test(host) || /^192\.168\./.test(host)) return true;
  const match172 = host.match(/^172\.(\d+)\./);
  if (match172) {
    const second = Number(match172[1]);
    if (second >= 16 && second <= 31) return true;
  }
  if (host === "::" || host.startsWith("fe80:") || host.startsWith("fc") || host.startsWith("fd")) return true;
  return false;
}

function isPublicHttpsUrl(value) {
  let parsed;
  try {
    parsed = new URL(String(value || "").trim());
  } catch {
    return false;
  }
  if (parsed.protocol !== "https:") return false;
  if (parsed.username || parsed.password) return false;
  if (parsed.port && parsed.port !== "443") return false;
  return !isPrivateHostname(parsed.hostname);
}

function isAllowedOpenAiUrl(value) {
  return isPublicHttpsUrl(value);
}

function connectStatusPayload() {
  const { envFile, lookup } = readEnvLookup();
  const credentials = {};
  for (const name of CONNECT_KEYS) {
    credentials[name] = presence(lookup(name));
  }
  return {
    ok: true,
    mode: "demo",
    env_file: envFile,
    bitget_env: bitgetEnvStatus(lookup("BITGET_ENV")),
    credentials,
    live_guard: String(lookup("GROK_TRADER_ALLOW_LIVE") || "").trim() === "1" ? "on" : "off",
    get_bitget: "connected",
  };
}

function handleConnectStatus(req, res) {
  if (req.method !== "GET") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  sendJson(res, 200, connectStatusPayload());
}

function resolveEnvFilePath() {
  for (const candidate of envFileCandidates()) {
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
    } catch {
      continue;
    }
  }
  return path.join(REPO_ROOT, ".env");
}

function quoteEnvValue(value) {
  const text = String(value ?? "");
  if (!text) return "";
  if (/[\s#"']/.test(text)) return `"${text.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  return text;
}

function upsertEnvValues(filePath, updates) {
  let source = "";
  try {
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      source = fs.readFileSync(filePath, "utf8");
    }
  } catch {
    source = "";
  }
  const lines = source ? source.split(/\r?\n/) : [];
  const seen = new Set();
  const next = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return line;
    let body = trimmed.startsWith("export ") ? trimmed.slice(7).trim() : trimmed;
    const eq = body.indexOf("=");
    if (eq < 1) return line;
    const key = body.slice(0, eq).trim();
    if (!Object.prototype.hasOwnProperty.call(updates, key)) return line;
    seen.add(key);
    const prefix = trimmed.startsWith("export ") ? "export " : "";
    return `${prefix}${key}=${quoteEnvValue(updates[key])}`;
  });
  for (const [key, value] of Object.entries(updates)) {
    if (seen.has(key)) continue;
    next.push(`${key}=${quoteEnvValue(value)}`);
  }
  const text = `${next.filter((line, index) => !(index === next.length - 1 && line === "")).join("\n").replace(/\s+$/, "")}\n`;
  fs.writeFileSync(filePath, text, { encoding: "utf8" });
}

async function handleConnectCredentials(req, res) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  let body;
  try {
    body = await readJsonBody(req, MAX_BODY);
  } catch {
    sendJson(res, 400, { ok: false, error: "invalid json" });
    return;
  }
  if (String(body.confirm_demo || "").trim() !== "1") {
    sendJson(res, 400, { ok: false, error: "cần xác nhận Demo key" });
    return;
  }
  const apiKey = String(body.api_key || "").trim();
  const apiSecret = String(body.api_secret || "").trim();
  const passphrase = String(body.passphrase || "").trim();
  if (!apiKey || !apiSecret || !passphrase) {
    sendJson(res, 400, { ok: false, error: "thiếu API key, secret hoặc passphrase" });
    return;
  }
  if ([apiKey, apiSecret, passphrase].some((item) => item.length > 256)) {
    sendJson(res, 400, { ok: false, error: "giá trị quá dài" });
    return;
  }
  const current = connectStatusPayload();
  if (current.bitget_env === "live") {
    sendJson(res, 409, { ok: false, error: "BITGET_ENV đang live; UI Demo không ghi đè. Sửa .env thủ công." });
    return;
  }
  try {
    const filePath = resolveEnvFilePath();
    upsertEnvValues(filePath, {
      BITGET_ENV: "demo",
      BITGET_API_KEY: apiKey,
      BITGET_API_SECRET: apiSecret,
      BITGET_PASSPHRASE: passphrase,
    });
    sendJson(res, 200, connectStatusPayload());
  } catch {
    sendJson(res, 500, { ok: false, error: "không ghi được .env" });
  }
}

function joinUrl(base, suffix) {
  const trimmed = String(base || "").replace(/\/+$/, "");
  if (!trimmed) return suffix;
  if (trimmed.endsWith(suffix) || trimmed.endsWith(`/${suffix}`)) return trimmed;
  return `${trimmed}/${suffix}`;
}

async function checkGemini(model, apiKey, timeoutMs) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey,
    },
    body: JSON.stringify({
      contents: [{ parts: [{ text: "ping" }] }],
      generationConfig: { maxOutputTokens: 8 },
    }),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let message = `HTTP ${response.status}`;
  try {
    const parsed = JSON.parse(text);
    if (parsed?.error?.message) message = parsed.error.message;
  } catch {
    if (!response.ok && text) message = text.slice(0, 200);
  }
  return { ok: response.ok, httpStatus: response.status, error: response.ok ? "" : redact(message, apiKey) };
}

async function checkOpenAi(baseUrl, model, apiKey, timeoutMs) {
  const url = joinUrl(baseUrl, "chat/completions");
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: "ping" }],
      max_tokens: 8,
    }),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let message = `HTTP ${response.status}`;
  try {
    const parsed = JSON.parse(text);
    if (parsed?.error?.message) message = parsed.error.message;
  } catch {
    if (!response.ok && text) message = text.slice(0, 200);
  }
  return { ok: response.ok, httpStatus: response.status, error: response.ok ? "" : redact(message, apiKey) };
}

function redactKnownSecrets(text, lookup, extraSecrets) {
  let out = String(text || "");
  for (const name of CONNECT_KEYS) {
    out = redact(out, lookup(name));
  }
  for (const secret of extraSecrets || []) {
    out = redact(out, secret);
  }
  return out;
}

function readAgentConfig(body) {
  const agent = body && body.agent;
  if (!agent || typeof agent !== "object" || Array.isArray(agent)) return null;
  const provider = String(agent.provider || "").trim();
  const model = String(agent.model || "").trim();
  const apiKey = String(agent.api_key || "").trim();
  const label = String(agent.label || "").trim().slice(0, 64);
  const timeout = Number(agent.request_timeout);
  const requestTimeout = Number.isFinite(timeout) ? timeout : 30;
  if (!["gemini", "openai_compatible"].includes(provider) || !model || !apiKey) {
    return { error: "thiếu provider, model hoặc key" };
  }
  if (requestTimeout < 1 || requestTimeout > 60) {
    return { error: "timeout AI không hợp lệ" };
  }
  if (provider === "openai_compatible" && !isAllowedOpenAiUrl(String(agent.base_url || "").trim())) {
    return { error: "base_url không được phép" };
  }
  const config = {
    provider,
    model,
    api_key: apiKey,
    request_timeout: requestTimeout,
    label,
  };
  if (provider === "openai_compatible") config.base_url = String(agent.base_url || "").trim();
  return { config };
}

function snapshotError(lookup, value) {
  return redactKnownSecrets(String(value || "snapshot failed"), lookup).slice(0, 80);
}

function pairScreenError(lookup, value) {
  return redactKnownSecrets(String(value || "pair screen failed"), lookup).slice(0, 80);
}

function clampPairLimit(value) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1) return PAIR_SCREEN_LIMIT_DEFAULT;
  return Math.min(number, PAIR_SCREEN_LIMIT_MAX);
}

function publicPairCandidate(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const symbol = pickText(row.symbol);
  if (!symbol || !SYMBOL_RE.test(symbol.toUpperCase())) return null;
  const item = { symbol: symbol.toUpperCase() };
  const last = pickFinite(row.last);
  const mark = pickFinite(row.mark);
  const volume = pickFinite(row.volume24h);
  const change = pickFinite(row.change24h);
  const reason = pickText(row.reason);
  if (last) item.last = last;
  if (mark) item.mark = mark;
  if (volume) item.volume24h = volume;
  if (change) item.change24h = change;
  if (reason) item.reason = reason.slice(0, 80);
  return item;
}

function publicPairScreen(parsed, lookup) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: pairScreenError(lookup, "cli invalid") };
  }
  if (parsed.ok !== true) {
    return { ok: false, error: pairScreenError(lookup, parsed.error || parsed.message) };
  }
  return {
    ok: true,
    product_type: pickText(parsed.product_type) || "USDT-FUTURES",
    as_of: pickText(parsed.as_of) || "",
    candidates: publicRows(parsed.candidates, publicPairCandidate).slice(0, PAIR_SCREEN_LIMIT_MAX),
  };
}

function pickFinite(value) {
  if (value === null || value === undefined || value === "") return null;
  const text = String(value).trim();
  if (!text) return null;
  const number = Number(text);
  return Number.isFinite(number) ? text : null;
}

function pickText(value) {
  const text = String(value == null ? "" : value).trim();
  return text || null;
}

function publicTicker(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const ticker = {};
  const symbol = pickText(raw.symbol);
  const last = pickFinite(raw.last);
  const mark = pickFinite(raw.mark);
  const funding = pickFinite(raw.funding);
  if (symbol) ticker.symbol = symbol.toUpperCase();
  if (last) ticker.last = last;
  if (mark) ticker.mark = mark;
  if (funding) ticker.funding = funding;
  return Object.keys(ticker).length ? ticker : null;
}

function publicRows(list, mapRow) {
  if (!Array.isArray(list)) return [];
  return list.map(mapRow).filter(Boolean);
}

function publicPosition(row) {
  if (!row || typeof row !== "object") return null;
  const symbol = pickText(row.symbol);
  const size = pickFinite(row.size);
  if (!symbol || !size) return null;
  const item = { symbol: symbol.toUpperCase(), size };
  const side = pickText(row.side);
  const available = pickFinite(row.available);
  const leverage = pickFinite(row.leverage);
  const marginMode = pickText(row.margin_mode);
  const entry = pickFinite(row.entry_price);
  const mark = pickFinite(row.mark_price);
  const liq = pickFinite(row.liquidation_price);
  const pnl = pickFinite(row.unrealized_pnl);
  if (side) item.side = side.toLowerCase();
  if (available) item.available = available;
  if (leverage) item.leverage = leverage;
  if (marginMode) item.margin_mode = marginMode.toLowerCase();
  if (entry) item.entry_price = entry;
  if (mark) item.mark_price = mark;
  if (liq) item.liquidation_price = liq;
  if (pnl) item.unrealized_pnl = pnl;
  return item;
}

function publicOrder(row) {
  if (!row || typeof row !== "object") return null;
  const symbol = pickText(row.symbol);
  if (!symbol) return null;
  const item = { symbol: symbol.toUpperCase() };
  const side = pickText(row.side);
  const posSide = pickText(row.pos_side);
  const tradeSide = pickText(row.trade_side);
  const price = pickFinite(row.price);
  const size = pickFinite(row.size);
  const orderType = pickText(row.order_type);
  const status = pickText(row.status);
  if (side) item.side = side.toLowerCase();
  if (posSide) item.pos_side = posSide.toLowerCase();
  if (tradeSide) item.trade_side = tradeSide.toLowerCase();
  if (price) item.price = price;
  if (size) item.size = size;
  if (orderType) item.order_type = orderType.toLowerCase();
  if (status) item.status = status.toLowerCase();
  return item;
}

function publicAsset(row) {
  if (!row || typeof row !== "object") return null;
  const coin = pickText(row.margin_coin);
  const equity = pickFinite(row.equity);
  const available = pickFinite(row.available);
  const pnl = pickFinite(row.unrealized_pnl);
  if (!coin && !equity && !available) return null;
  const item = {};
  if (coin) item.margin_coin = coin.toUpperCase();
  if (equity) item.equity = equity;
  if (available) item.available = available;
  if (pnl) item.unrealized_pnl = pnl;
  return item;
}

function publicFill(row) {
  if (!row || typeof row !== "object") return null;
  const symbol = pickText(row.symbol);
  if (!symbol) return null;
  const item = { symbol: symbol.toUpperCase() };
  const side = pickText(row.side);
  const posSide = pickText(row.pos_side);
  const tradeSide = pickText(row.trade_side);
  const price = pickFinite(row.price);
  const size = pickFinite(row.size);
  const fee = pickFinite(row.fee);
  const profit = pickFinite(row.profit);
  const tradeScope = pickText(row.trade_scope);
  const tradeId = pickText(row.trade_id);
  const orderId = pickText(row.order_id);
  const clientOid = pickText(row.client_oid);
  const filledAt = pickText(row.filled_at);
  if (side) item.side = side.toLowerCase();
  if (posSide) item.pos_side = posSide.toLowerCase();
  if (tradeSide) item.trade_side = tradeSide.toLowerCase();
  if (price) item.price = price;
  if (size) item.size = size;
  if (fee) item.fee = fee;
  if (profit) item.profit = profit;
  if (tradeScope) item.trade_scope = tradeScope.toLowerCase();
  if (tradeId) item.trade_id = tradeId.slice(0, 64);
  if (orderId) item.order_id = orderId.slice(0, 64);
  if (clientOid) item.client_oid = clientOid.slice(0, 64);
  if (filledAt) item.filled_at = filledAt.slice(0, 40);
  return item;
}

function publicSnapshot(parsed, lookup) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: snapshotError(lookup, "cli invalid") };
  }
  if (parsed.ok !== true) {
    return { ok: false, error: snapshotError(lookup, parsed.error || parsed.message) };
  }
  const assets = publicRows(parsed.assets, publicAsset);
  const payload = {
    ok: true,
    product_type: pickText(parsed.product_type) || "USDT-FUTURES",
    as_of: pickText(parsed.as_of) || "",
    equity: pickFinite(parsed.equity),
    ticker: publicTicker(parsed.ticker),
    positions: publicRows(parsed.positions, publicPosition),
    pending_orders: publicRows(parsed.pending_orders, publicOrder),
    fills: publicRows(parsed.fills, publicFill).slice(0, FILL_LIMIT),
    assets,
  };
  if (payload.equity == null) {
    const usdt = assets.find((row) => row.margin_coin === "USDT" && row.equity);
    payload.equity = usdt ? usdt.equity : (assets[0] && assets[0].equity) || null;
  }
  return payload;
}

function runBitgetSnapshotCli(symbol) {
  return new Promise((resolve) => {
    const python = process.env.PYTHON || "python";
    const args = ["-m", "trader.bitget_snapshot_cli", "snapshot"];
    if (symbol) args.push("--symbol", symbol);
    const child = spawn(python, args, { cwd: REPO_ROOT, windowsHide: true, env: process.env });
    let stdout = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "timeout" });
    }, SNAPSHOT_TIMEOUT_MS);

    function finish(payload) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(payload);
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      if (stdout.length > SNAPSHOT_MAX_STDOUT) {
        child.kill();
        finish({ ok: false, error: "cli output too large" });
      }
    });
    child.stderr.on("data", () => {});
    child.on("error", () => {
      finish({ ok: false, error: "cli unavailable" });
    });
    child.on("close", () => {
      const { lookup } = readEnvLookup();
      let parsed;
      try {
        parsed = JSON.parse(redactKnownSecrets(stdout, lookup).trim() || "{}");
      } catch {
        finish({ ok: false, error: snapshotError(lookup, "cli failed") });
        return;
      }
      finish(publicSnapshot(parsed, lookup));
    });
  });
}

async function handleBitgetSnapshot(req, res) {
  if (req.method !== "GET") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  const current = connectStatusPayload();
  if (current.live_guard === "on") {
    sendJson(res, 409, { ok: false, error: "GROK_TRADER_ALLOW_LIVE đang bật; GET Demo bị chặn" });
    return;
  }
  if (current.bitget_env === "live") {
    sendJson(res, 409, { ok: false, error: "BITGET_ENV đang live; GET Demo bị chặn" });
    return;
  }
  let symbol = "";
  try {
    symbol = String(new URL(req.url || "/", `http://${HOST}:${PORT}`).searchParams.get("symbol") || "").trim().toUpperCase();
  } catch {
    sendJson(res, 400, { ok: false, error: "symbol không hợp lệ" });
    return;
  }
  if (symbol && !SYMBOL_RE.test(symbol)) {
    sendJson(res, 400, { ok: false, error: "symbol không hợp lệ" });
    return;
  }
  try {
    const payload = await runBitgetSnapshotCli(symbol);
    sendJson(res, payload.ok ? 200 : 502, payload);
  } catch {
    sendJson(res, 500, { ok: false, error: "snapshot failed" });
  }
}

function runPairScreenCli(limit) {
  return new Promise((resolve) => {
    const python = process.env.PYTHON || "python";
    const args = ["-m", "trader.pair_screen_cli", "screen", "--limit", String(limit)];
    const child = spawn(python, args, {
      cwd: REPO_ROOT,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "timeout" });
    }, PAIR_SCREEN_TIMEOUT_MS);

    function finish(payload) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(payload);
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      if (stdout.length > PAIR_SCREEN_MAX_STDOUT) {
        child.kill();
        finish({ ok: false, error: "cli output too large" });
      }
    });
    child.stderr.on("data", () => {});
    child.on("error", () => {
      finish({ ok: false, error: "cli unavailable" });
    });
    child.on("close", () => {
      const { lookup } = readEnvLookup();
      let parsed;
      try {
        parsed = JSON.parse(redactKnownSecrets(stdout, lookup).trim() || "{}");
      } catch {
        finish({ ok: false, error: pairScreenError(lookup, "cli failed") });
        return;
      }
      finish(publicPairScreen(parsed, lookup));
    });
  });
}

async function handlePairScreen(req, res) {
  if (req.method !== "GET") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  const current = connectStatusPayload();
  if (current.live_guard === "on") {
    sendJson(res, 409, { ok: false, error: "GROK_TRADER_ALLOW_LIVE đang bật; GET Demo bị chặn" });
    return;
  }
  if (current.bitget_env === "live") {
    sendJson(res, 409, { ok: false, error: "BITGET_ENV đang live; GET Demo bị chặn" });
    return;
  }
  let limit = PAIR_SCREEN_LIMIT_DEFAULT;
  try {
    limit = clampPairLimit(new URL(req.url || "/", `http://${HOST}:${PORT}`).searchParams.get("limit"));
  } catch {
    sendJson(res, 400, { ok: false, error: "limit không hợp lệ" });
    return;
  }
  try {
    const payload = await runPairScreenCli(limit);
    sendJson(res, payload.ok ? 200 : 502, payload);
  } catch {
    sendJson(res, 500, { ok: false, error: "pair screen failed" });
  }
}

function styleError(value) {
  return String(value || "style failed").slice(0, 80);
}

function publicStyleCondition(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const condition = {};
  if (Array.isArray(raw.event_in)) {
    const events = raw.event_in
      .map((item) => pickText(item))
      .filter(Boolean)
      .map((item) => item.toUpperCase())
      .slice(0, 16);
    if (events.length) condition.event_in = events;
  }
  const windowMin = Number(raw.window_min);
  if (Number.isInteger(windowMin) && windowMin >= 1 && windowMin <= 240) {
    condition.window_min = windowMin;
  }
  return Object.keys(condition).length ? condition : null;
}

function publicStyleEntry(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const id = pickText(row.id);
  const kind = pickText(row.kind);
  if (!id || !STYLE_KINDS.has(kind) || !STYLE_ID_RE.test(id) || id.length > 64) return null;
  const version = Number(row.version);
  const priority = Number(row.priority);
  const item = {
    id,
    kind,
    version: Number.isInteger(version) && version > 0 ? version : 0,
    status: pickText(row.status) || "",
    channel: pickText(row.channel) || "",
    applied: row.applied === true,
    blocked: row.blocked === true,
    priority: Number.isInteger(priority) ? priority : 0,
    rule: String(row.rule || "").slice(0, 500),
    scope: Array.isArray(row.scope)
      ? row.scope.map((item) => pickText(item)).filter(Boolean).slice(0, 16)
      : ["all"],
    tags: Array.isArray(row.tags)
      ? row.tags.map((item) => pickText(item)).filter(Boolean).slice(0, 16)
      : [],
  };
  const condition = publicStyleCondition(row.condition);
  if (condition) item.condition = condition;
  return item;
}

function publicStylePayload(parsed) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: styleError("cli invalid") };
  }
  if (parsed.ok !== true) {
    return { ok: false, error: styleError(parsed.error || parsed.message) };
  }
  const entries = publicRows(parsed.entries, publicStyleEntry);
  const payload = {
    ok: true,
    status: pickText(parsed.status) || "ok",
    count: entries.filter((row) => row.applied).length,
    entries,
    disclaimer: "Strategy preference only. Does not override mandate or risk engine.",
  };
  if (parsed.saved && typeof parsed.saved === "object") {
    const saved = publicStyleEntry({ ...parsed.saved, rule: parsed.saved.rule || "saved", applied: false });
    if (saved) {
      payload.saved = {
        id: saved.id,
        version: saved.version,
        status: saved.status,
        kind: saved.kind,
      };
    }
  }
  return payload;
}

function runStyleCli(args, filePath) {
  return new Promise((resolve) => {
    const python = process.env.PYTHON || "python";
    const child = spawn(python, ["-m", "trader.style_cli", ...args], {
      cwd: REPO_ROOT,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "timeout" });
    }, STYLE_TIMEOUT_MS);

    function finish(payload) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (filePath) {
        try {
          fs.unlinkSync(filePath);
        } catch {
          /* ignore */
        }
      }
      resolve(payload);
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      if (stdout.length > STYLE_MAX_STDOUT) {
        child.kill();
        finish({ ok: false, error: "cli output too large" });
      }
    });
    child.stderr.on("data", () => {});
    child.on("error", () => {
      finish({ ok: false, error: "cli unavailable" });
    });
    child.on("close", () => {
      let parsed;
      try {
        parsed = JSON.parse(String(stdout || "").trim() || "{}");
      } catch {
        finish({ ok: false, error: styleError("cli failed") });
        return;
      }
      finish(publicStylePayload(parsed));
    });
  });
}

function styleDraftFromBody(body) {
  const id = pickText(body && body.id);
  const kind = pickText(body && body.kind);
  if (!id || !STYLE_ID_RE.test(id) || id.length > 64) return { error: "id phải là kebab-case" };
  if (!STYLE_KINDS.has(kind)) return { error: "kind không hợp lệ" };
  const rule = String((body && body.rule) || "").trim();
  if (!rule) return { error: "thiếu rule" };
  const draft = {
    id,
    kind,
    rule: rule.slice(0, 500),
    scope: body && body.scope,
    tags: body && body.tags,
    priority: body && body.priority,
  };
  if (kind === "no_trade") draft.condition = body && body.condition;
  return { draft };
}

async function handleUserStyle(req, res) {
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  if (req.method === "GET") {
    try {
      const payload = await runStyleCli(["list"]);
      sendJson(res, payload.ok ? 200 : 502, payload);
    } catch {
      sendJson(res, 500, { ok: false, error: "style list failed" });
    }
    return;
  }
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  let body;
  try {
    body = await readJsonBody(req, STYLE_BODY);
  } catch {
    sendJson(res, 400, { ok: false, error: "invalid json" });
    return;
  }
  const action = pickText(body && body.action);
  if (action === "retire") {
    const id = pickText(body && body.id);
    if (!id || !STYLE_ID_RE.test(id)) {
      sendJson(res, 400, { ok: false, error: "id không hợp lệ" });
      return;
    }
    try {
      const payload = await runStyleCli(["retire", "--id", id]);
      sendJson(res, payload.ok ? 200 : 400, payload);
    } catch {
      sendJson(res, 500, { ok: false, error: "style retire failed" });
    }
    return;
  }
  if (action !== "add") {
    sendJson(res, 400, { ok: false, error: "action không hợp lệ" });
    return;
  }
  const parsed = styleDraftFromBody(body);
  if (parsed.error) {
    sendJson(res, 400, { ok: false, error: parsed.error });
    return;
  }
  let filePath;
  try {
    filePath = path.join(require("os").tmpdir(), `fb-style-${process.pid}-${Date.now()}.json`);
    fs.writeFileSync(filePath, JSON.stringify(parsed.draft), { encoding: "utf8" });
    const payload = await runStyleCli(["add", "--file", filePath], filePath);
    filePath = null;
    sendJson(res, payload.ok ? 200 : 400, payload);
  } catch {
    if (filePath) {
      try {
        fs.unlinkSync(filePath);
      } catch {
        /* ignore */
      }
    }
    sendJson(res, 500, { ok: false, error: "style save failed" });
  }
}

function publicDemoScan(parsed, lookup, extraSecrets) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: redactKnownSecrets("cli invalid", lookup, extraSecrets).slice(0, 80) };
  }
  if (parsed.error) {
    return {
      ok: false,
      error: redactKnownSecrets(parsed.message || parsed.error, lookup, extraSecrets).slice(0, 80),
    };
  }
  const results = Array.isArray(parsed.dispatch_results)
    ? parsed.dispatch_results.map((row) => ({
        result: pickText(row && row.result) || "",
        dispatch: pickText(row && row.dispatch) || "",
        posted: Boolean(row && row.exchange_post),
        reason_code: pickText(row && row.reason_code) || "",
      }))
    : [];
  return {
    ok: true,
    action: pickText(parsed.action) || "NO_TRADE",
    reason_code: pickText(parsed.reason_code) || "",
    exchange_post: Boolean(parsed.exchange_post),
    dry_run: parsed.dry_run !== false && !parsed.exchange_post,
    allowed_symbols: publicRows(parsed.allowed_symbols, (item) => {
      const symbol = pickText(item);
      return symbol && SYMBOL_RE.test(symbol.toUpperCase()) ? symbol.toUpperCase() : null;
    }),
    dispatch_results: results.slice(0, 8),
    mandate_version: Number.isInteger(parsed.mandate_version) ? parsed.mandate_version : null,
    pairs: Array.isArray(parsed.pairs)
      ? parsed.pairs.slice(0, 12).map((row) => ({
          symbol: pickText(row && row.symbol) || "",
          side: pickText(row && row.side) || "",
          action: pickText(row && row.action) || "",
          posted: Boolean(row && row.exchange_post),
          reason_code: pickText(row && row.reason_code) || "",
        }))
      : [],
    scanned: Number.isInteger(parsed.scanned) ? parsed.scanned : 0,
    skipped: publicRows(parsed.skipped, (item) => pickText(item) || null).slice(0, 12),
    symbol: pickText(parsed.symbol) || "",
    agent: {
      called: Boolean(parsed.agent && parsed.agent.called),
      ok: Boolean(parsed.agent && parsed.agent.ok),
      provider: pickText(parsed.agent && parsed.agent.provider) || "",
      model: pickText(parsed.agent && parsed.agent.model) || "",
      label: pickText(parsed.agent && parsed.agent.label) || "",
      error: redactKnownSecrets(pickText(parsed.agent && parsed.agent.error) || "", lookup, extraSecrets).slice(0, 80),
    },
    snapshot_stale: Boolean(parsed.snapshot_stale),
    protect: parsed.protect && typeof parsed.protect === "object"
      ? {
          ran: Boolean(parsed.protect.ran),
          triggered: Boolean(parsed.protect.triggered),
          reason_code: pickText(parsed.protect.reason_code) || "",
        }
      : null,
    protect_kill: parsed.protect_kill && typeof parsed.protect_kill === "object"
      ? {
          posted: Boolean(parsed.protect_kill.exchange_post),
          leftover_clear: Boolean(parsed.protect_kill.leftover_clear),
          reason_code: pickText(parsed.protect_kill.reason_code) || "",
        }
      : null,
    equity: parsed.equity && typeof parsed.equity === "object"
      ? {
          complete: Boolean(parsed.equity.complete),
          stale: Boolean(parsed.equity.stale),
          reason_codes: publicRows(parsed.equity.reason_codes, (item) => pickText(item) || null).slice(0, 8),
        }
      : null,
  };
}

function writeTempJson(dir, name, value) {
  const filePath = path.join(dir, name);
  fs.writeFileSync(filePath, JSON.stringify(value), { encoding: "utf-8" });
  return filePath;
}

function runDemoScanCli(files, flags) {
  return new Promise((resolve) => {
    const python = process.env.PYTHON || "python";
    const args = [
      "-m",
      "trader.demo_scan_cli",
      flags.command || "tick",
      "--policy",
      files.policy,
      "--limits",
      files.limits,
      "--json",
    ];
    if (files.proposal) args.push("--proposal", files.proposal);
    if (files.agent) args.push("--agent-config", files.agent);
    if (files.features) args.push("--features", files.features);
    if (flags.placeOrders) args.push("--place-orders");
    if (flags.confirmDemo) args.push("--i-confirm-demo");
    const child = spawn(python, args, {
      cwd: REPO_ROOT,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "timeout" });
    }, DEMO_SCAN_TIMEOUT_MS);

    function finish(payload) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(payload);
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      if (stdout.length > DEMO_SCAN_MAX_STDOUT) {
        child.kill();
        finish({ ok: false, error: "cli output too large" });
      }
    });
    child.stderr.on("data", () => {});
    child.on("error", () => {
      finish({ ok: false, error: "cli unavailable" });
    });
    child.on("close", () => {
      const { lookup } = readEnvLookup();
      const extra = flags.extraSecrets || [];
      let parsed;
      try {
        parsed = JSON.parse(redactKnownSecrets(stdout, lookup, extra).trim() || "{}");
      } catch {
        finish({ ok: false, error: redactKnownSecrets("cli failed", lookup, extra).slice(0, 80) });
        return;
      }
      finish(publicDemoScan(parsed, lookup, extra));
    });
  });
}

function publicDemoKill(parsed, lookup) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, error: redactKnownSecrets("cli invalid", lookup).slice(0, 80) };
  }
  if (parsed.error) {
    return {
      ok: false,
      error: redactKnownSecrets(parsed.message || parsed.error, lookup).slice(0, 80),
    };
  }
  return {
    ok: true,
    symbol: pickText(parsed.symbol) || "",
    cancelled: Number.isInteger(parsed.cancelled) ? parsed.cancelled : 0,
    closed: Number.isInteger(parsed.closed) ? parsed.closed : 0,
    leftover_clear: Boolean(parsed.leftover_clear),
    exchange_post: Boolean(parsed.exchange_post),
    dry_run: parsed.dry_run !== false && !parsed.exchange_post,
    reason_code: pickText(parsed.reason_code) || "",
  };
}

function runDemoKillCli(symbol, allowlist, flags) {
  return new Promise((resolve) => {
    const python = process.env.PYTHON || "python";
    const args = [
      "-m",
      "trader.demo_kill_cli",
      "run",
      "--symbol",
      symbol,
      "--allowlist",
      allowlist.join(","),
      "--json",
    ];
    if (flags.placeOrders) args.push("--place-orders");
    if (flags.confirmDemo) args.push("--i-confirm-demo");
    const child = spawn(python, args, {
      cwd: REPO_ROOT,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });
    let stdout = "";
    let settled = false;
    const timer = setTimeout(() => {
      child.kill();
      finish({ ok: false, error: "timeout" });
    }, DEMO_KILL_TIMEOUT_MS);

    function finish(payload) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(payload);
    }

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
      if (stdout.length > DEMO_KILL_MAX_STDOUT) {
        child.kill();
        finish({ ok: false, error: "cli output too large" });
      }
    });
    child.stderr.on("data", () => {});
    child.on("error", () => {
      finish({ ok: false, error: "cli unavailable" });
    });
    child.on("close", () => {
      const { lookup } = readEnvLookup();
      let parsed;
      try {
        parsed = JSON.parse(redactKnownSecrets(stdout, lookup).trim() || "{}");
      } catch {
        finish({ ok: false, error: redactKnownSecrets("cli failed", lookup).slice(0, 80) });
        return;
      }
      finish(publicDemoKill(parsed, lookup));
    });
  });
}

async function handleDemoKill(req, res) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  const current = connectStatusPayload();
  if (current.live_guard === "on") {
    sendJson(res, 409, { ok: false, error: "GROK_TRADER_ALLOW_LIVE đang bật; Demo kill bị chặn" });
    return;
  }
  if (current.bitget_env === "live") {
    sendJson(res, 409, { ok: false, error: "BITGET_ENV đang live; Demo kill bị chặn" });
    return;
  }
  let body;
  try {
    body = await readJsonBody(req, DEMO_KILL_BODY);
  } catch {
    sendJson(res, 400, { ok: false, error: "invalid json" });
    return;
  }
  if (String(body.confirm_demo || "").trim() !== "1") {
    sendJson(res, 400, { ok: false, error: "cần xác nhận Demo" });
    return;
  }
  const allowlist = Array.isArray(body.allowlist)
    ? body.allowlist.map((item) => String(item || "").trim().toUpperCase()).filter((item) => SYMBOL_RE.test(item))
    : [];
  if (!allowlist.length) {
    sendJson(res, 400, { ok: false, error: "allowlist trống; không POST" });
    return;
  }
  const symbol = pickText(body.symbol);
  if (!symbol || !SYMBOL_RE.test(symbol) || !allowlist.includes(symbol)) {
    sendJson(res, 400, { ok: false, error: "symbol ngoài allowlist" });
    return;
  }
  try {
    const payload = await runDemoKillCli(symbol, allowlist, {
      placeOrders: Boolean(body.place_orders),
      confirmDemo: true,
    });
    sendJson(res, payload.ok ? 200 : 502, payload);
  } catch {
    sendJson(res, 500, { ok: false, error: "demo kill failed" });
  }
}

async function handleDemoScan(req, res, command) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  const current = connectStatusPayload();
  if (current.live_guard === "on") {
    sendJson(res, 409, { ok: false, error: "GROK_TRADER_ALLOW_LIVE đang bật; Demo scan bị chặn" });
    return;
  }
  if (current.bitget_env === "live") {
    sendJson(res, 409, { ok: false, error: "BITGET_ENV đang live; Demo scan bị chặn" });
    return;
  }
  let body;
  try {
    body = await readJsonBody(req, DEMO_SCAN_BODY);
  } catch {
    sendJson(res, 400, { ok: false, error: "invalid json" });
    return;
  }
  if (String(body.confirm_demo || "").trim() !== "1") {
    sendJson(res, 400, { ok: false, error: "cần xác nhận Demo" });
    return;
  }
  const policy = body.policy && typeof body.policy === "object" ? body.policy : null;
  const limits = body.limits && typeof body.limits === "object" ? body.limits : null;
  if (!policy || !limits) {
    sendJson(res, 400, { ok: false, error: "thiếu policy hoặc limits" });
    return;
  }
  const allowlist = Array.isArray(policy.symbol_allowlist) ? policy.symbol_allowlist : [];
  if (!allowlist.length) {
    sendJson(res, 400, { ok: false, error: "allowlist trống; không POST" });
    return;
  }
  const allowlistScope = String(limits.scope || "").trim().toLowerCase() === "allowlist" || command === "cycle";
  const symbol = pickText(limits.symbol);
  if (!allowlistScope) {
    if (!symbol || !SYMBOL_RE.test(symbol) || !allowlist.map((item) => String(item).toUpperCase()).includes(symbol)) {
      sendJson(res, 400, { ok: false, error: "symbol ngoài allowlist" });
      return;
    }
  }
  const placeOrders = Boolean(body.place_orders);
  let agentConfig = null;
  if (body.agent != null) {
    const parsedAgent = readAgentConfig(body);
    if (!parsedAgent || parsedAgent.error) {
      sendJson(res, 400, { ok: false, error: (parsedAgent && parsedAgent.error) || "agent không hợp lệ" });
      return;
    }
    agentConfig = parsedAgent.config;
  }
  let dir;
  try {
    dir = fs.mkdtempSync(path.join(require("os").tmpdir(), "fb-demo-scan-"));
    const files = {
      policy: writeTempJson(dir, "policy.json", policy),
      limits: writeTempJson(dir, "limits.json", limits),
    };
    if (body.proposal && typeof body.proposal === "object") {
      files.proposal = writeTempJson(dir, "proposal.json", body.proposal);
    } else if (agentConfig) {
      files.agent = writeTempJson(dir, "agent.json", agentConfig);
    }
    if (command !== "cycle" && body.features && typeof body.features === "object") {
      files.features = writeTempJson(dir, "features.json", body.features);
    }
    const payload = await runDemoScanCli(files, {
      command: command === "cycle" ? "cycle" : "tick",
      placeOrders,
      confirmDemo: true,
      extraSecrets: agentConfig ? [agentConfig.api_key] : [],
    });
    sendJson(res, payload.ok ? 200 : 502, payload);
  } catch {
    sendJson(res, 500, { ok: false, error: "demo scan failed" });
  } finally {
    if (dir) {
      try {
        fs.rmSync(dir, { recursive: true, force: true });
      } catch {
        /* ignore */
      }
    }
  }
}

async function handleAiCheck(req, res) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  if (!localRequestOk(req)) {
    sendJson(res, 403, { ok: false, error: "chỉ nhận từ frontend local" });
    return;
  }
  let body;
  try {
    body = await readJsonBody(req, MAX_BODY);
  } catch {
    sendJson(res, 400, { ok: false, error: "invalid json" });
    return;
  }
  const provider = String(body.provider || "").trim();
  const model = String(body.model || "").trim();
  const apiKey = String(body.api_key || "").trim();
  const label = String(body.label || "").trim();
  const timeoutMs = Math.min(Math.max(Number(body.timeout_ms) || 30000, 1000), MAX_TIMEOUT_MS);
  if (!["gemini", "openai_compatible"].includes(provider) || !model || !apiKey) {
    sendJson(res, 400, { ok: false, error: "thiếu provider, model hoặc key" });
    return;
  }
  if (provider === "openai_compatible" && !isAllowedOpenAiUrl(String(body.base_url || "").trim())) {
    sendJson(res, 400, { ok: false, error: "base_url không được phép" });
    return;
  }
  try {
    const result = provider === "gemini"
      ? await checkGemini(model, apiKey, timeoutMs)
      : await checkOpenAi(String(body.base_url || "").trim(), model, apiKey, timeoutMs);
    sendJson(res, 200, { ok: result.ok, httpStatus: result.httpStatus, label, error: result.error });
  } catch (error) {
    const timedOut = error && (error.name === "TimeoutError" || error.name === "AbortError");
    sendJson(res, 200, {
      ok: false,
      httpStatus: 0,
      label,
      error: timedOut ? "timeout" : "không gọi được provider",
    });
  }
}

const server = http.createServer((req, res) => {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url || "/", `http://${HOST}:${PORT}`).pathname);
  } catch {
    send(res, 400, "Bad request");
    return;
  }

  if (pathname === "/api/ai-check") {
    handleAiCheck(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "check failed" });
    });
    return;
  }

  if (pathname === "/api/connect-status") {
    try {
      handleConnectStatus(req, res);
    } catch {
      sendJson(res, 500, { ok: false, error: "status failed" });
    }
    return;
  }

  if (pathname === "/api/connect-credentials") {
    handleConnectCredentials(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "save failed" });
    });
    return;
  }

  if (pathname === "/api/bitget-snapshot") {
    handleBitgetSnapshot(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "snapshot failed" });
    });
    return;
  }

  if (pathname === "/api/pair-screen") {
    handlePairScreen(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "pair screen failed" });
    });
    return;
  }

  if (pathname === "/api/user-style") {
    handleUserStyle(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "style failed" });
    });
    return;
  }

  if (pathname === "/api/demo-scan") {
    handleDemoScan(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "demo scan failed" });
    });
    return;
  }

  if (pathname === "/api/demo-cycle") {
    handleDemoScan(req, res, "cycle").catch(() => {
      sendJson(res, 500, { ok: false, error: "demo cycle failed" });
    });
    return;
  }

  if (pathname === "/api/demo-kill") {
    handleDemoKill(req, res).catch(() => {
      sendJson(res, 500, { ok: false, error: "demo kill failed" });
    });
    return;
  }

  if (pathname === "/") {
    pathname = "/index.html";
  }

  const filePath = path.normalize(path.join(ROOT, pathname));
  if (!filePath.startsWith(`${ROOT}${path.sep}`) && filePath !== ROOT) {
    send(res, 403, "Forbidden");
    return;
  }

  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      send(res, 404, "Not found");
      return;
    }

    const type = TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": type,
      "Cache-Control": "no-store",
    });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`Cổng ${PORT} đang bị chiếm. Đóng process cũ rồi chạy lại npm start.`);
    process.exit(1);
  }
  throw err;
});

function openLocalFrontend(url) {
  if (process.env.FRONTEND_NO_OPEN === "1") return;
  const child = process.platform === "win32"
    ? spawn("cmd", ["/c", "start", "", url], { detached: true, stdio: "ignore", windowsHide: true })
    : spawn(process.platform === "darwin" ? "open" : "xdg-open", [url], { detached: true, stdio: "ignore" });
  child.on("error", () => {});
  child.unref();
}

server.listen(PORT, HOST, () => {
  const url = `http://localhost:${PORT}`;
  console.log(`Frontend local: ${url}`);
  openLocalFrontend(url);
});
