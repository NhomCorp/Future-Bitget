"""Local Demo scan tick or supervised cycle from frontend policy.

Examples:
  python -m trader.demo_scan_cli tick --policy policy.json --limits limits.json --json
  python -m trader.demo_scan_cli cycle --policy policy.json --limits limits.json --place-orders --i-confirm-demo --json
  python -m trader.demo_scan_cli loop --policy policy.json --limits limits.json --poll-seconds 8 --max-ticks 3 --json

Default is local paper intents only. ``--proposal`` (intent ticket) wins over
``--agent-config``. Agent errors become ``NO_TRADE`` and do not invent orders.
Demo POST requires both ``--place-orders`` and ``--i-confirm-demo``, and only
for symbols in the frontend allowlist. Live is refused. ``tick`` does not start
the protect clock. ``cycle``/``loop`` GET a fresh snapshot, append equity
(session-start bootstrap on the first UTC day), protect, then scan if due.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_proposal.adapter import NetworkProposalProvider, ProviderConfig, ProviderError
from ai_proposal.provider import StaticPaperProvider
from executor.p1_adapter import P1IntegrationError, P1IntegrationStore
from trader.bitget_readonly import LiveModeDisabled, MissingReadOnlyCredentials, ReadOnlyBitgetAdapter
from trader.zone_store import ZoneStore, ZoneStoreError
from trading.demo_cycle import (
    DEFAULT_MAX_AGE_SECONDS,
    DemoCycleError,
    ProtectDispatchOptions,
    run_allowlist_cycle,
    run_cycle,
    run_loop,
)
from trading.demo_dispatch import (
    DemoDispatchError,
    make_demo_poster,
    make_order_query,
    make_path_poster,
    make_tpsl_poster,
)
from trading.equity_store import DEFAULT_PATH as DEFAULT_EQUITY_STORE
from trading.equity_store import EquityStore, EquityStoreError
from trading.decision_context import enrich_decision_features
from trading.frontend_mandate import (
    FRONTEND_MANDATE_ID,
    FrontendMandateError,
    ScanLimits,
    scan_limits_from_policy,
    build_scan_snapshot,
    policy_to_mandate,
    proposal_from_intent,
    use_allowlist_scope,
)
from trading.mandate import MandateError
from trading.paper_agent import PaperAgent
from trading.paper_scan import LocalNoTradeProvider, ScanDispatchOptions, tick


DEFAULT_STORE = "trader/data/zones.sqlite3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Frontend Demo scan tick/cycle; POST only with --place-orders --i-confirm-demo"
    )
    parser.add_argument("command", choices=("tick", "cycle", "loop"))
    parser.add_argument("--policy", required=True, help="frontend policy JSON")
    parser.add_argument("--limits", required=True, help="user-entered scan limits JSON")
    parser.add_argument("--proposal", help="optional intent/proposal JSON; default is local NO_TRADE")
    parser.add_argument("--agent-config", help="optional AI provider JSON; ignored when --proposal is set")
    parser.add_argument("--features", help="optional snapshot features JSON; ignored by cycle/loop")
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--equity-store", default=DEFAULT_EQUITY_STORE)
    parser.add_argument("--max-age-seconds", type=int, default=DEFAULT_MAX_AGE_SECONDS)
    parser.add_argument("--now", help="ISO-8601 evaluation time; default is current UTC")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--place-orders", action="store_true")
    parser.add_argument("--i-confirm-demo", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=8.0)
    parser.add_argument("--max-ticks", type=int, default=1)
    return parser


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _live_blocked(environ: Any | None = None) -> bool:
    env = os.environ if environ is None else environ
    mode = str(env.get("BITGET_ENV", "demo")).strip().lower()
    return str(env.get("GROK_TRADER_ALLOW_LIVE", "")).strip() == "1" or mode in {"live", "production", "prod"}


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _output(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
        return
    posted = " post=yes" if value.get("exchange_post") else ""
    print(
        f"due={value.get('due')} ran={value.get('ran')} "
        f"action={value.get('action')} reason={value.get('reason_code')} "
        f"next={value.get('next_due_at') or '—'}{posted}"
    )


def _dispatch_options(
    args: argparse.Namespace,
    *,
    environ: Any | None,
    poster: Any | None,
) -> ScanDispatchOptions | None:
    if not args.i_confirm_demo and not args.place_orders:
        return None
    place = bool(args.place_orders and args.i_confirm_demo)
    built = poster
    tpsl = None
    query = None
    if place and built is None:
        built = make_demo_poster(environ=environ)
        tpsl = make_tpsl_poster(environ=environ)
        query = make_order_query(environ=environ)
    return ScanDispatchOptions(
        confirm_demo=bool(args.i_confirm_demo),
        dry_run=not place,
        poster=built,
        tpsl_poster=tpsl,
        query=query,
        environ=environ,
    )


def _protect_dispatch_options(
    args: argparse.Namespace,
    *,
    environ: Any | None,
    poster: Any | None,
    path_poster: Any | None,
    adapter: Any | None,
) -> ProtectDispatchOptions:
    place = bool(args.place_orders and args.i_confirm_demo)
    built = poster
    paths = path_poster
    client = adapter
    if place and built is None:
        built = make_demo_poster(environ=environ)
        paths = paths or make_path_poster(environ=environ)
        client = client or ReadOnlyBitgetAdapter(environ=environ)
    return ProtectDispatchOptions(
        confirm_demo=bool(args.i_confirm_demo),
        dry_run=not place,
        poster=built,
        path_poster=paths,
        environ=environ,
        adapter=client,
    )


def _annotate(payload: dict[str, Any], mandate: Any, limits: ScanLimits | None, agent_meta: dict[str, Any]) -> dict[str, Any]:
    payload["mandate_id"] = FRONTEND_MANDATE_ID
    payload["mandate_version"] = mandate.version
    payload["allowed_symbols"] = list(mandate.allowed_symbols)
    payload["zone_id"] = mandate.zone_id
    payload["symbol"] = "" if limits is None else limits.symbol
    payload["agent"] = agent_meta
    return payload


def _ensure_autonomous_zone(store: P1IntegrationStore, mandate: Any, snapshot: Any) -> None:
    try:
        store.zone_store.get_zone(mandate.zone_id)
        return
    except Exception:
        pass
    store.zone_store.create_zone(
        {
            "symbol": snapshot.symbol,
            "side": snapshot.side,
            "ref_price": format(snapshot.ref_price, "f"),
            "zone_loss_limit_usdt": format(mandate.loss_budget, "f"),
            "sl_pct": format(snapshot.sl_pct, "f"),
            "opened_by": "ai",
        },
        zone_id=mandate.zone_id,
        state="ACTIVE",
    )


def _empty_agent() -> dict[str, Any]:
    return {
        "called": False,
        "error": "",
        "label": "",
        "model": "",
        "ok": False,
        "provider": "",
    }


def _agent_view(config: ProviderConfig, *, called: bool, ok: bool, error: str = "") -> dict[str, Any]:
    return {
        "called": called,
        "error": error[:80],
        "label": config.label,
        "model": config.model,
        "ok": ok,
        "provider": config.provider,
    }


def _intent_provider(args: argparse.Namespace, snapshot: Any, mandate: Any) -> Any:
    raw = _load_json(args.proposal)
    if not isinstance(raw, dict):
        raise FrontendMandateError("proposal must be a JSON object")
    if raw.get("proposal_id") and raw.get("opportunity_id"):
        from ai_proposal.schema import ProposalDraft

        return snapshot, StaticPaperProvider(ProposalDraft.from_dict(raw)), _empty_agent()
    draft = proposal_from_intent(
        snapshot,
        raw,
        policy_version=f"policy-{mandate.version}",
        now=args.now,
    )
    return snapshot, StaticPaperProvider(draft), _empty_agent()


class _RecordingAIProvider:
    """Call the network adapter only when PaperAgent asks. Errors stay NO_TRADE."""

    def __init__(self, inner: NetworkProposalProvider, config: ProviderConfig):
        self._inner = inner
        self.meta = _agent_view(config, called=False, ok=False)

    def propose(self, snapshot: Any) -> Any:
        self.meta["called"] = True
        try:
            _bound, draft = self._inner.decide(snapshot)
        except ProviderError as exc:
            self.meta["ok"] = False
            self.meta["error"] = exc.code[:80]
            raise
        self.meta["ok"] = True
        self.meta["error"] = ""
        return draft


def _ai_provider(
    args: argparse.Namespace,
    snapshot: Any,
    mandate: Any,
    *,
    transport: Any | None,
) -> tuple[Any, Any, dict[str, Any]]:
    raw = _load_json(args.agent_config)
    if not isinstance(raw, dict):
        raise FrontendMandateError("agent-config must be a JSON object")
    try:
        config = ProviderConfig.from_mapping(raw)
    except ProviderError as exc:
        raise FrontendMandateError(exc.code) from exc
    recorder = _RecordingAIProvider(
        NetworkProposalProvider(
            config,
            policy_version=f"policy-{mandate.version}",
            leverage=format(mandate.max_leverage, "f"),
            transport=transport,
            now=args.now,
        ),
        config,
    )
    return snapshot, recorder, recorder.meta


def _provider(
    args: argparse.Namespace,
    snapshot: Any,
    mandate: Any,
    *,
    transport: Any | None,
) -> tuple[Any, Any, dict[str, Any]]:
    if args.proposal:
        return _intent_provider(args, snapshot, mandate)
    if args.agent_config:
        return _ai_provider(args, snapshot, mandate, transport=transport)
    return snapshot, LocalNoTradeProvider(), _empty_agent()


def run(
    argv: list[str] | None = None,
    *,
    environ: Any | None = None,
    poster: Any | None = None,
    path_poster: Any | None = None,
    store: P1IntegrationStore | None = None,
    agent_transport: Any | None = None,
    adapter: Any | None = None,
    equity_store: EquityStore | None = None,
    sleep: Any | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if _live_blocked(environ):
        payload = {"error": "LiveModeDisabled", "message": "demo scan refuses GROK_TRADER_ALLOW_LIVE"}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    if args.place_orders and not args.i_confirm_demo:
        payload = {"error": "PostDisabled", "message": "--place-orders requires --i-confirm-demo"}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2

    owned = store is None
    owned_equity = equity_store is None and args.command in {"cycle", "loop"}
    zones: ZoneStore | None = None
    ledger = equity_store
    try:
        policy = _load_json(args.policy)
        raw_limits = _load_json(args.limits)
        if not isinstance(raw_limits, dict):
            raise FrontendMandateError("limits must be a JSON object")
        if args.proposal and raw_limits.get("size") in (None, ""):
            raw_proposal = _load_json(args.proposal)
            if isinstance(raw_proposal, dict) and raw_proposal.get("size") not in (None, ""):
                raw_limits = {**raw_limits, "size": raw_proposal["size"]}
                if raw_proposal.get("price") not in (None, ""):
                    raw_limits = {**raw_limits, "ref_price": raw_proposal["price"]}
        allowlist_mode = (
            args.command in {"cycle", "loop"}
            and use_allowlist_scope(raw_limits)
            and not args.proposal
        )
        now = args.now or _now_utc()
        if allowlist_mode:
            from decimal import Decimal
            from trading.frontend_mandate import normalize_allowlist, scan_risk_from_policy

            approved = normalize_allowlist(policy)
            if not approved:
                raise FrontendMandateError("WHITELIST_EMPTY")
            sl_pct, loss_budget, max_order_risk, max_size = scan_risk_from_policy(policy, raw_limits)
            limits = ScanLimits(
                symbol=approved[0],
                side="long",
                ref_price=Decimal("1"),
                sl_pct=sl_pct,
                loss_budget=loss_budget,
                max_order_risk=max_order_risk,
                max_size=max_size,
            )
        else:
            limits = scan_limits_from_policy(policy, raw_limits)
        mandate = policy_to_mandate(policy, limits, now=now)
        features = {} if args.command in {"cycle", "loop"} else (_load_json(args.features) if args.features else {})
        if not isinstance(features, dict):
            raise FrontendMandateError("features must be a JSON object")
        if args.command == "tick":
            features = enrich_decision_features(
                features,
                symbol=limits.symbol,
                side=limits.side,
                now=now,
                adapter=adapter,
            )
        snapshot = build_scan_snapshot(mandate, limits, now=now, features=features)
        snapshot, provider, agent_meta = _provider(
            args, snapshot, mandate, transport=agent_transport
        )
        if store is None:
            Path(args.store).parent.mkdir(parents=True, exist_ok=True)
            zones = ZoneStore(args.store)
            store = P1IntegrationStore(zones)
        store.save_mandate(mandate.to_dict())
        if not allowlist_mode:
            _ensure_autonomous_zone(store, mandate, snapshot)
        agent = PaperAgent(provider, store)
        if args.command == "tick":
            result = tick(
                agent,
                snapshot,
                mandate,
                now=now,
                dispatch=_dispatch_options(args, environ=environ, poster=poster),
            )
            _output(_annotate(result.to_dict(), mandate, limits, agent_meta), args.as_json)
            return 0
        client = adapter if adapter is not None else ReadOnlyBitgetAdapter(environ=environ)
        if ledger is None:
            Path(args.equity_store).parent.mkdir(parents=True, exist_ok=True)
            ledger = EquityStore(args.equity_store)
        if allowlist_mode:

            def _job_mandate(job: ScanLimits):
                built = policy_to_mandate(
                    policy,
                    job,
                    now=now,
                    mandate_id=f"{FRONTEND_MANDATE_ID}-{job.symbol}-{job.side}",
                )
                _ensure_autonomous_zone(store, built, build_scan_snapshot(built, job, now=now))
                return built

            cycle_call = {
                "adapter": client,
                "store": store,
                "equity_store": ledger,
                "agent": agent,
                "policy": policy,
                "limits": raw_limits,
                "mandate_builder": _job_mandate,
                "max_age_seconds": args.max_age_seconds,
                "scan_dispatch": _dispatch_options(args, environ=environ, poster=poster),
                "protect_dispatch": _protect_dispatch_options(
                    args,
                    environ=environ,
                    poster=poster,
                    path_poster=path_poster,
                    adapter=client,
                ),
            }
            if args.command == "loop":
                payload = {}
                ticks = max(1, int(args.max_ticks))
                for index in range(ticks):
                    payload = run_allowlist_cycle(now=args.now or _now_utc(), **cycle_call)
                    if index + 1 < ticks:
                        (sleep or time.sleep)(args.poll_seconds)
            else:
                payload = run_allowlist_cycle(now=now, **cycle_call)
            _output(_annotate(payload, mandate, None, agent_meta), args.as_json)
            return 0
        cycle_kwargs = {
            "adapter": client,
            "store": store,
            "equity_store": ledger,
            "agent": agent,
            "mandate": mandate,
            "limits": limits,
            "max_age_seconds": args.max_age_seconds,
            "scan_dispatch": _dispatch_options(args, environ=environ, poster=poster),
            "protect_dispatch": _protect_dispatch_options(
                args,
                environ=environ,
                poster=poster,
                path_poster=path_poster,
                adapter=client,
            ),
        }
        if args.command == "loop":
            results = run_loop(
                now_fn=lambda: args.now or _now_utc(),
                sleep=sleep or time.sleep,
                poll_seconds=args.poll_seconds,
                max_ticks=args.max_ticks,
                **cycle_kwargs,
            )
            payload = results[-1].to_dict() if results else {"error": "DemoCycleError", "message": "empty loop"}
        else:
            payload = run_cycle(now=now, **cycle_kwargs).to_dict()
        _output(_annotate(payload, mandate, limits, agent_meta), args.as_json)
        return 0
    except (
        ZoneStoreError,
        P1IntegrationError,
        MandateError,
        FrontendMandateError,
        DemoCycleError,
        EquityStoreError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        LiveModeDisabled,
        MissingReadOnlyCredentials,
        DemoDispatchError,
    ) as exc:
        payload = {"error": type(exc).__name__, "message": str(exc)[:80]}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"ERROR {payload['error']}: {payload['message']}", file=sys.stderr)
        return 2
    finally:
        if owned_equity and ledger is not None:
            ledger.close()
        if owned:
            if store is not None:
                store.close()
            if zones is not None:
                zones.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
