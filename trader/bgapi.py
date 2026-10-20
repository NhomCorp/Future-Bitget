"""Bitget v2 REST helper (USDT-M futures).
- pub(): public GET (no key)
- get(): signed GET with READ-ONLY key (BITGET_API_KEY/SECRET/PASSPHRASE) – same signing as ../bg.py
- post(): signed POST with TRADE key (BITGET_TRADE_API_KEY/SECRET/PASSPHRASE). dry_run=True -> never sends,
  returns/prints the exact body that would be signed. Secrets are never printed or logged.
Every request/response is appended to logs/YYYYMMDD.jsonl (no headers, no secrets)."""
import os, time, hmac, hashlib, base64, json, urllib.request, urllib.error, datetime as dt
API = "https://api.bitget.com"
HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, "logs")
PT = "USDT-FUTURES"

class ApiError(RuntimeError):
    pass

def _log(rec):
    os.makedirs(LOGDIR, exist_ok=True)
    rec = dict(t=dt.datetime.now().astimezone().isoformat(timespec="milliseconds"), **rec)
    with open(os.path.join(LOGDIR, f"{dt.datetime.now():%Y%m%d}.jsonl"), "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

def _http(method, rp, headers, body=None, timeout=15):
    req = urllib.request.Request(API + rp, data=body.encode() if body else None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        txt = e.read().decode()[:500]
        try: return json.loads(txt)
        except Exception: return {"code": f"http{e.code}", "msg": txt}

def sign(secret, ts, method, rp, body=""):
    return base64.b64encode(hmac.new(secret.encode(), (ts + method + rp + body).encode(), hashlib.sha256).digest()).decode()

def _q(params):
    if not params: return ""
    if isinstance(params, str): return params
    return "&".join(f"{k}={v}" for k, v in params.items() if v is not None and v != "")

def _unwrap(path, d, raise_err=True):
    if d.get("code") != "00000":
        if raise_err: raise ApiError(f"{path}: {d.get('code')} {d.get('msg')}")
        return None
    return d.get("data")

def pub(path, params=None, raise_err=True, log=False):
    q = _q(params); rp = path + ("?" + q if q else "")
    d = _http("GET", rp, {"locale": "en-US"})
    if log: _log(dict(kind="pub", method="GET", path=rp, code=d.get("code"), resp=_short(d)))
    return _unwrap(path, d, raise_err)

def _short(d, n=4000):
    s = json.dumps(d, ensure_ascii=False, default=str)
    return d if len(s) <= n else s[:n] + "…"

def read_keys():
    k = [os.environ.get(x) for x in ("BITGET_API_KEY", "BITGET_API_SECRET", "BITGET_PASSPHRASE")]
    if not all(k): raise ApiError("Thiếu key chỉ-đọc BITGET_API_KEY/BITGET_API_SECRET/BITGET_PASSPHRASE")
    return k

def trade_keys():
    k = [os.environ.get(x) for x in ("BITGET_TRADE_API_KEY", "BITGET_TRADE_API_SECRET", "BITGET_TRADE_PASSPHRASE")]
    return k if all(k) else None

def get(path, params=None, raise_err=True):
    K, S, P = read_keys()
    q = _q(params); rp = path + ("?" + q if q else ""); ts = str(int(time.time() * 1000))
    h = {"ACCESS-KEY": K, "ACCESS-SIGN": sign(S, ts, "GET", rp), "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": P,
         "Content-Type": "application/json", "locale": "en-US"}
    d = _http("GET", rp, h)
    _log(dict(kind="private", method="GET", path=rp, code=d.get("code"), msg=d.get("msg"), resp=_short(d)))
    return _unwrap(path, d, raise_err)

# hard guard so tests / this session can never send a live POST by accident
LIVE_POST_ALLOWED = os.environ.get("GROK_TRADER_ALLOW_LIVE") == "1"

def post(path, body, dry_run=True, tag=""):
    """Signed POST with the TRADE key. dry_run -> nothing sent; returns {'dry_run':True,...}."""
    bs = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    keys = trade_keys()
    if dry_run:
        rec = dict(kind="post", dry_run=True, method="POST", path=path, body=body, tag=tag,
                   prehash_format="timestamp + 'POST' + path + body", trade_key_present=bool(keys))
        _log(rec)
        return {"dry_run": True, "path": path, "body": body, "body_str": bs}
    if not keys:
        raise ApiError("Không có BITGET_TRADE_API_KEY/SECRET/PASSPHRASE → không thể gửi lệnh thật. Dùng --dry-run.")
    if not LIVE_POST_ALLOWED:
        raise ApiError("Gửi lệnh thật bị khoá: đặt env GROK_TRADER_ALLOW_LIVE=1 để mở khoá (chỉ khi bạn chắc chắn).")
    K, S, P = keys; ts = str(int(time.time() * 1000))
    h = {"ACCESS-KEY": K, "ACCESS-SIGN": sign(S, ts, "POST", path, bs), "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": P,
         "Content-Type": "application/json", "locale": "en-US"}
    d = _http("POST", path, h, bs)
    _log(dict(kind="post", dry_run=False, method="POST", path=path, body=body, tag=tag, code=d.get("code"), msg=d.get("msg"), resp=_short(d)))
    return d
