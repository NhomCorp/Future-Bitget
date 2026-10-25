"""Load and merge ``profile/user_style.yaml`` for Demo AI context.

Stdlib only. Preferences are strategy input, not hard limits.
Entries that mention mandate/risk keywords are skipped, not applied.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
import json
import re

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "profile" / "user_style.yaml"
VN = timezone(timedelta(hours=7))
FORBIDDEN = (
    "leverage",
    "granted_capital",
    "max_zones",
    "daily_loss",
    "drawdown",
    "max_order_risk",
    "loss limit",
    "loss_limit",
    "zone_loss",
)
WRITE_FORBIDDEN = FORBIDDEN + ("margin",)
KINDS = frozenset({"no_trade", "preference", "note"})
CHANNELS = frozenset({"manual", "mcp_chat"})
STATUSES = frozenset({"active", "retired"})
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SYMBOL_RE = re.compile(r"^[A-Z0-9_-]{1,32}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
EVENT_RE = re.compile(r"^[A-Z0-9_-]{1,32}$")
NEW_FILE_HEADER = """# Profile phong cách do người dùng xác nhận.
# Spec: ../specs/user-style-profile.md
# File append-only: không sửa/xóa entry cũ; thay đổi bằng version mới.
# Không ghi risk limit, leverage, margin, vốn hoặc max_zones tại đây.
entries:
"""


def _parse_dt(value: str | None) -> datetime | None:
    if not value or value == "null":
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _scalar(raw: str) -> Any:
    text = raw.strip()
    if text in {"", "null", "None"}:
        return None
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text[:1] in {"[", "{"}:
        return json.loads(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def parse_style_yaml(text: str) -> list[dict[str, Any]]:
    """Parse the constrained profile YAML (list of entry mappings)."""
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    nested_key: str | None = None
    nested: dict[str, Any] | None = None
    seen_entries = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not seen_entries:
            if line.strip() == "entries:":
                seen_entries = True
            continue
        if line.startswith("  - "):
            if current is not None:
                if nested_key is not None and nested is not None:
                    current[nested_key] = nested
                entries.append(current)
            body = line[4:]
            key, _, rest = body.partition(":")
            current = {key.strip(): _scalar(rest)}
            nested_key = None
            nested = None
            continue
        if current is None:
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if indent >= 6 and nested_key is not None:
            if nested is None:
                nested = {}
            nested[key] = _scalar(rest)
            continue
        if nested_key is not None and nested is not None:
            current[nested_key] = nested
            nested_key = None
            nested = None
        if rest == "":
            nested_key = key
            nested = {}
            continue
        current[key] = _scalar(rest)
    if current is not None:
        if nested_key is not None and nested is not None:
            current[nested_key] = nested
        entries.append(current)
    return entries


def _mentions_hard_limit(entry: Mapping[str, Any]) -> bool:
    blob = json.dumps(entry, ensure_ascii=False).lower()
    return any(token in blob for token in FORBIDDEN)


def _in_effect(entry: Mapping[str, Any], now: datetime) -> bool:
    start = _parse_dt(str(entry.get("effective_from") or "") or None)
    end = _parse_dt(entry.get("effective_to") if entry.get("effective_to") not in {None, "null"} else None)
    if start is None or start > now:
        return False
    if end is not None and end <= now:
        return False
    return str(entry.get("status") or "") == "active"


def merge_active_entries(
    entries: list[Mapping[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Highest version per id, then active + in-effect, preferences first by priority."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    latest: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        ident = str(entry.get("id") or "").strip()
        kind = str(entry.get("kind") or "").strip()
        if not ident or kind not in KINDS or entry.get("source") != "user":
            continue
        if _mentions_hard_limit(entry):
            continue
        try:
            version = int(entry.get("version") or 0)
        except (TypeError, ValueError):
            continue
        prev = latest.get(ident)
        if prev is None or int(prev.get("version") or 0) < version:
            latest[ident] = entry
    active: list[dict[str, Any]] = []
    for entry in latest.values():
        if not _in_effect(entry, moment):
            continue
        tags = entry.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        scope = entry.get("scope") or ["all"]
        if not isinstance(scope, list):
            scope = ["all"]
        try:
            priority = int(entry.get("priority") or 0)
        except (TypeError, ValueError):
            priority = 0
        item = {
            "id": str(entry.get("id")),
            "kind": str(entry.get("kind")),
            "priority": priority,
            "rule": str(entry.get("rule") or "").strip(),
            "scope": [str(item) for item in scope],
            "tags": [str(item) for item in tags],
        }
        if item["kind"] == "no_trade":
            item["condition"] = dict(entry.get("condition") or {})
        if item["rule"]:
            active.append(item)
    kind_rank = {"no_trade": 0, "preference": 1, "note": 2}
    active.sort(key=lambda row: (kind_rank.get(row["kind"], 9), -int(row["priority"]), row["id"]))
    return active


def load_user_style(
    path: Path | str | None = None,
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe context block. Missing/invalid file → empty rules, not an exception."""
    target = Path(path) if path else DEFAULT_PATH
    moment: datetime | None
    if isinstance(now, str) and now.strip():
        moment = _parse_dt(now)
    else:
        moment = now  # type: ignore[assignment]
    if not target.is_file():
        return {"status": "missing", "path": str(target), "rules": []}
    try:
        entries = parse_style_yaml(target.read_text(encoding="utf-8"))
        rules = merge_active_entries(entries, now=moment)
    except (OSError, json.JSONDecodeError, ValueError):
        return {"status": "invalid", "path": str(target), "rules": []}
    return {
        "status": "ok",
        "count": len(rules),
        "rules": rules,
        "disclaimer": "Strategy preference only. Does not override mandate or risk engine.",
    }


def now_vn_iso() -> str:
    return datetime.now(VN).replace(microsecond=0).isoformat()


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    if '"' not in text and "\n" not in text:
        return f'"{text}"'
    if "'" not in text and "\n" not in text:
        return f"'{text}'"
    return json.dumps(text, ensure_ascii=False)


def _mentions_write_forbidden(entry: Mapping[str, Any]) -> bool:
    blob = json.dumps(entry, ensure_ascii=False).lower()
    return any(token in blob for token in WRITE_FORBIDDEN)


def latest_by_id(entries: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for entry in entries:
        ident = str(entry.get("id") or "").strip()
        if not ident:
            continue
        try:
            version = int(entry.get("version") or 0)
        except (TypeError, ValueError):
            continue
        prev = latest.get(ident)
        if prev is None or int(prev.get("version") or 0) < version:
            latest[ident] = dict(entry)
    return latest


def read_style_entries(path: Path | str | None = None) -> tuple[list[dict[str, Any]] | None, str | None]:
    target = Path(path) if path else DEFAULT_PATH
    if not target.is_file():
        return [], None
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return None, "không đọc được file phong cách"
    if "entries:" not in text:
        return None, "file phong cách không hợp lệ"
    try:
        entries = parse_style_yaml(text)
    except (json.JSONDecodeError, ValueError):
        return None, "file phong cách không parse được"
    seen: set[tuple[str, int]] = set()
    for entry in entries:
        ident = str(entry.get("id") or "").strip()
        try:
            version = int(entry.get("version") or 0)
        except (TypeError, ValueError):
            return None, "file phong cách có version không hợp lệ"
        key = (ident, version)
        if not ident or version < 1 or key in seen:
            return None, "file phong cách trùng id/version"
        seen.add(key)
    return entries, None


def list_style_entries(
    path: Path | str | None = None,
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_PATH
    moment: datetime | None
    if isinstance(now, str) and now.strip():
        moment = _parse_dt(now)
    else:
        moment = now
    if moment is None:
        moment = datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    entries, error = read_style_entries(target)
    if error:
        return {"ok": False, "error": error, "path": str(target), "entries": []}
    rows: list[dict[str, Any]] = []
    for entry in latest_by_id(entries or []).values():
        try:
            version = int(entry.get("version") or 0)
            priority = int(entry.get("priority") or 0)
        except (TypeError, ValueError):
            continue
        kind = str(entry.get("kind") or "").strip()
        if kind not in KINDS:
            continue
        scope = entry.get("scope") if isinstance(entry.get("scope"), list) else ["all"]
        tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
        blocked = _mentions_hard_limit(entry) or _mentions_write_forbidden(entry)
        applied = (not blocked) and _in_effect(entry, moment)
        row = {
            "id": str(entry.get("id")),
            "version": version,
            "kind": kind,
            "status": str(entry.get("status") or ""),
            "channel": str(entry.get("channel") or ""),
            "applied": applied,
            "blocked": blocked,
            "priority": priority,
            "rule": str(entry.get("rule") or "").strip(),
            "scope": [str(item) for item in scope][:16],
            "tags": [str(item) for item in tags][:16],
            "effective_from": str(entry.get("effective_from") or ""),
            "effective_to": entry.get("effective_to"),
        }
        if kind == "no_trade" and isinstance(entry.get("condition"), dict):
            row["condition"] = dict(entry.get("condition") or {})
        rows.append(row)
    kind_rank = {"no_trade": 0, "preference": 1, "note": 2}
    rows.sort(
        key=lambda row: (
            0 if row["applied"] else 1,
            kind_rank.get(row["kind"], 9),
            -int(row["priority"]),
            row["id"],
        )
    )
    return {
        "ok": True,
        "status": "ok" if target.is_file() else "missing",
        "path": str(target),
        "count": sum(1 for row in rows if row["applied"]),
        "entries": rows,
        "disclaimer": "Strategy preference only. Does not override mandate or risk engine.",
    }


def _clean_scope(raw: Any) -> list[str] | None:
    if raw in (None, "", "all", ["all"]):
        return ["all"]
    items = raw if isinstance(raw, list) else str(raw).split(",")
    out: list[str] = []
    for item in items:
        token = str(item).strip().upper()
        if not token or token == "ALL":
            return ["all"]
        if not SYMBOL_RE.fullmatch(token):
            return None
        if token not in out:
            out.append(token)
    return out or ["all"]


def _clean_tags(raw: Any) -> list[str] | None:
    if raw in (None, ""):
        return []
    items = raw if isinstance(raw, list) else str(raw).split(",")
    out: list[str] = []
    for item in items:
        token = str(item).strip().lower()
        if not token:
            continue
        if not TAG_RE.fullmatch(token):
            return None
        if token not in out:
            out.append(token)
        if len(out) > 16:
            return None
    return out


def _clean_condition(kind: str, raw: Any) -> dict[str, Any] | None:
    if kind != "no_trade":
        return {}
    if not isinstance(raw, Mapping):
        return None
    events_raw = raw.get("event_in")
    if isinstance(events_raw, str):
        events = [part.strip().upper() for part in events_raw.split(",") if part.strip()]
    elif isinstance(events_raw, list):
        events = [str(part).strip().upper() for part in events_raw if str(part).strip()]
    else:
        return None
    if not events or any(not EVENT_RE.fullmatch(item) for item in events):
        return None
    try:
        window = int(raw.get("window_min"))
    except (TypeError, ValueError):
        return None
    if window < 1 or window > 240:
        return None
    return {"event_in": events, "window_min": window}


def build_style_entry(
    draft: Mapping[str, Any],
    existing: list[Mapping[str, Any]],
    *,
    action: str = "add",
    now: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    ident = str(draft.get("id") or "").strip()
    if not ID_RE.fullmatch(ident) or len(ident) > 64:
        return None, "id phải là kebab-case, tối đa 64 ký tự"
    latest = latest_by_id(existing).get(ident)
    stamp = now or now_vn_iso()
    if action == "retire":
        if latest is None:
            return None, "không thấy thói quen để dừng"
        if str(latest.get("status") or "") != "active":
            return None, "thói quen này đã dừng"
        try:
            version = int(latest.get("version") or 0) + 1
        except (TypeError, ValueError):
            return None, "version hiện tại không hợp lệ"
        entry = dict(latest)
        entry.update(
            {
                "version": version,
                "source": "user",
                "channel": "manual",
                "status": "retired",
                "effective_from": stamp,
                "effective_to": stamp,
            }
        )
        return entry, None
    if action != "add":
        return None, "action không hợp lệ"
    kind = str(draft.get("kind") or "").strip()
    if kind not in KINDS:
        return None, "kind chỉ nhận preference, note hoặc no_trade"
    rule = str(draft.get("rule") or "").strip()
    if not rule or len(rule) > 500 or "#" in rule or "\n" in rule:
        return None, "rule bắt buộc, tối đa 500 ký tự, không chứa # hoặc xuống dòng"
    scope = _clean_scope(draft.get("scope"))
    if scope is None:
        return None, "scope chỉ nhận all hoặc symbol hợp lệ"
    tags = _clean_tags(draft.get("tags"))
    if tags is None:
        return None, "tags không hợp lệ"
    try:
        priority = int(draft.get("priority") if draft.get("priority") not in {None, ""} else 50)
    except (TypeError, ValueError):
        return None, "priority phải là số nguyên"
    if priority < 0 or priority > 999:
        return None, "priority trong khoảng 0–999"
    condition = _clean_condition(kind, draft.get("condition") if kind == "no_trade" else {})
    if kind == "no_trade" and condition is None:
        return None, "no_trade cần condition event_in và window_min"
    version = 1
    if latest is not None:
        try:
            version = int(latest.get("version") or 0) + 1
        except (TypeError, ValueError):
            return None, "version hiện tại không hợp lệ"
    entry: dict[str, Any] = {
        "id": ident,
        "version": version,
        "kind": kind,
        "source": "user",
        "channel": "manual",
        "status": "active",
        "effective_from": stamp,
        "effective_to": None,
        "scope": scope,
        "priority": priority,
        "rule": rule,
        "tags": tags,
    }
    if kind == "no_trade":
        entry["condition"] = condition
    if _mentions_write_forbidden(entry):
        return None, "không ghi đòn bẩy, margin, vốn hoặc hạn mức rủi ro vào phong cách"
    return entry, None


def format_entry_yaml(entry: Mapping[str, Any]) -> str:
    keys = (
        "id",
        "version",
        "kind",
        "source",
        "channel",
        "status",
        "effective_from",
        "effective_to",
        "scope",
        "priority",
        "rule",
    )
    lines = [f"  - {keys[0]}: {_yaml_scalar(entry.get(keys[0]))}"]
    for key in keys[1:]:
        lines.append(f"    {key}: {_yaml_scalar(entry.get(key))}")
    if entry.get("kind") == "no_trade" and isinstance(entry.get("condition"), dict):
        lines.append("    condition:")
        for key, value in entry["condition"].items():
            lines.append(f"      {key}: {_yaml_scalar(value)}")
    lines.append(f"    tags: {_yaml_scalar(list(entry.get('tags') or []))}")
    return "\n".join(lines) + "\n"


def append_style_entry(
    draft: Mapping[str, Any],
    *,
    path: Path | str | None = None,
    action: str = "add",
    now: str | None = None,
) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_PATH
    entries, error = read_style_entries(target)
    if error:
        return {"ok": False, "error": error}
    entry, reason = build_style_entry(draft, entries or [], action=action, now=now)
    if entry is None:
        return {"ok": False, "error": reason or "entry không hợp lệ"}
    block = format_entry_yaml(entry)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file():
            target.write_text(NEW_FILE_HEADER + block, encoding="utf-8")
        else:
            current = target.read_text(encoding="utf-8")
            if not current.endswith("\n"):
                current += "\n"
            if "entries:" not in current:
                return {"ok": False, "error": "file phong cách không hợp lệ"}
            target.write_text(current + "\n" + block, encoding="utf-8")
    except OSError:
        return {"ok": False, "error": "không ghi được file phong cách"}
    packed = list_style_entries(target)
    packed["saved"] = {
        "id": entry["id"],
        "version": entry["version"],
        "status": entry["status"],
        "kind": entry.get("kind"),
    }
    return packed
