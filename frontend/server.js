"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");

const HOST = "127.0.0.1";
const PORT = 3007;
const ROOT = path.resolve(__dirname);
const REPO_ROOT = path.resolve(ROOT, "..");
const MAX_BODY = 32 * 1024;
const MAX_TIMEOUT_MS = 60_000;
const CONNECT_KEYS = ["BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSPHRASE"];

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

function handleConnectStatus(req, res) {
  if (req.method !== "GET") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
    return;
  }
  const { envFile, lookup } = readEnvLookup();
  const credentials = {};
  for (const name of CONNECT_KEYS) {
    credentials[name] = presence(lookup(name));
  }
  sendJson(res, 200, {
    ok: true,
    mode: "demo",
    env_file: envFile,
    bitget_env: bitgetEnvStatus(lookup("BITGET_ENV")),
    credentials,
    live_guard: String(lookup("GROK_TRADER_ALLOW_LIVE") || "").trim() === "1" ? "on" : "off",
    get_bitget: "not_connected",
  });
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

async function handleAiCheck(req, res) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method not allowed" });
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

server.listen(PORT, HOST, () => {
  console.log(`Frontend local: http://localhost:${PORT}`);
});
