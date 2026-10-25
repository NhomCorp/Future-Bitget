"""Offline tests for the standalone P3 proposal-only boundary."""
from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ai_proposal import (
    AppendOnlyProposalLog,
    DecisionOpportunitySnapshot,
    HardLimits,
    ProposalDraft,
    RESULT_ACCEPTED,
    RESULT_REJECTED,
    no_trade_proposal,
    propose,
)


def snapshot() -> DecisionOpportunitySnapshot:
    return DecisionOpportunitySnapshot(
        opportunity_id="opp-001",
        snapshot_at="2026-10-21T09:00:00Z",
        feature_as_of="2026-10-21T08:59:00Z",
        symbol="ETHUSDT",
        side="long",
        state="READY",
        ref_price=Decimal("2400.00"),
        sl_pct=Decimal("0.05"),
        loss_budget=Decimal("26.24"),
        size=Decimal("0.03"),
        exposure=Decimal("72.00"),
        hard_limits=HardLimits(
            allowed_symbols=("BTCUSDT", "ETHUSDT"),
            allowed_sides=("long", "short"),
            allowed_states=("READY", "PAUSED"),
            max_size=Decimal("0.15"),
            max_exposure=Decimal("393.65"),
        ),
        features={"regime": "range", "score": Decimal("0.2")},
    )


def candidate(snap: DecisionOpportunitySnapshot, **overrides) -> ProposalDraft:
    values = dict(
        proposal_id="prop-001",
        opportunity_id=snap.opportunity_id,
        decision_timestamp="2026-10-21T09:01:00Z",
        feature_as_of=snap.feature_as_of,
        model_version="adapter-test-1",
        policy_version="policy-test-1",
        action="OPEN",
        rationale="snapshot is eligible",
        symbol=snap.symbol,
        side=snap.side,
        state=snap.state,
        ref_price=snap.ref_price,
        sl_pct=snap.sl_pct,
        loss_budget=snap.loss_budget,
        size=snap.size,
        exposure=snap.exposure,
    )
    values.update(overrides)
    return ProposalDraft(**values)


class ProposalTests(unittest.TestCase):
    def test_accept_valid_proposal(self) -> None:
        snap = snapshot()
        record = propose(snap, lambda received: candidate(received))
        self.assertEqual(record.result, RESULT_ACCEPTED)
        self.assertIsNotNone(record.proposal)
        self.assertEqual(record.proposal.model_version, "adapter-test-1")
        self.assertEqual(record.proposal.policy_version, "policy-test-1")
        self.assertEqual(record.proposal.feature_as_of, "2026-10-21T08:59:00Z")

    def test_reject_proposal_over_hard_limit(self) -> None:
        snap = snapshot()
        record = propose(snap, lambda received: candidate(received, size=Decimal("0.16")))
        self.assertEqual(record.result, RESULT_REJECTED)
        self.assertTrue(any(error.code == "SIZE_HARD_LIMIT" for error in record.validation_errors))

    def test_reject_immutable_fields(self) -> None:
        snap = snapshot()
        record = propose(
            snap,
            lambda received: candidate(
                received,
                loss_budget=Decimal("1"),
                sl_pct=Decimal("0.01"),
                ref_price=Decimal("2500"),
                symbol="BTCUSDT",
                side="short",
                state="PAUSED",
                size=Decimal("0.04"),
                exposure=Decimal("73"),
            ),
        )
        self.assertEqual(record.result, RESULT_REJECTED)
        codes = {error.code for error in record.validation_errors}
        self.assertTrue({"LOSS_BUDGET_IMMUTABLE", "SL_PCT_IMMUTABLE", "REF_PRICE_IMMUTABLE", "SYMBOL_IMMUTABLE", "SIDE_IMMUTABLE", "STATE_IMMUTABLE", "SIZE_IMMUTABLE", "EXPOSURE_IMMUTABLE"} <= codes)

    def test_open_may_set_size_when_snapshot_is_empty(self) -> None:
        data = snapshot().to_dict()
        data["size"] = "0"
        data["exposure"] = "0"
        snap = DecisionOpportunitySnapshot.from_dict(data)
        record = propose(
            snap,
            lambda received: candidate(
                received,
                size=Decimal("0.03"),
                exposure=Decimal("0.03") * received.ref_price,
            ),
        )
        self.assertEqual(record.result, RESULT_ACCEPTED)

    def test_reduce_may_use_smaller_size(self) -> None:
        snap = snapshot()
        record = propose(snap, lambda received: candidate(received, action="REDUCE", size=Decimal("0.01")))
        self.assertEqual(record.result, RESULT_ACCEPTED)
        record = propose(snap, lambda received: candidate(received, action="REDUCE", size=Decimal("0.16")))
        self.assertEqual(record.result, RESULT_REJECTED)
        self.assertTrue(any(error.code == "REDUCE_SIZE_INVALID" for error in record.validation_errors))

    def test_no_trade_is_explicit(self) -> None:
        record = no_trade_proposal(
            snapshot(),
            proposal_id="prop-no-trade",
            model_version="rules-only-1",
            policy_version="policy-test-1",
            rationale="risk filter is neutral; do not open",
            decision_timestamp="2026-10-21T09:02:00Z",
        )
        self.assertEqual(record.result, RESULT_ACCEPTED)
        self.assertIsNotNone(record.proposal)
        self.assertEqual(record.proposal.action, "NO_TRADE")
        self.assertEqual(record.validation_errors, ())

    def test_append_only_replay_preserves_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = AppendOnlyProposalLog(Path(directory) / "proposals.jsonl")
            first = propose(snapshot(), lambda received: candidate(received))
            second = no_trade_proposal(
                snapshot(),
                proposal_id="prop-no-trade",
                model_version="rules-only-1",
                policy_version="policy-test-1",
                rationale="no action",
                decision_timestamp="2026-10-21T09:02:00Z",
            )
            log.append(first)
            log.append(second)
            before = log.path.read_text(encoding="utf-8")
            replayed = log.replay()
            after = log.path.read_text(encoding="utf-8")
            self.assertEqual([record.result for record in replayed], [RESULT_ACCEPTED, RESULT_ACCEPTED])
            self.assertEqual(replayed[0].to_dict(), first.to_dict())
            self.assertEqual(replayed[1].proposal.action, "NO_TRADE")
            self.assertEqual(before, after)
            self.assertEqual(len(before.splitlines()), 2)
            for line in before.splitlines():
                json.loads(line)


if __name__ == "__main__":
    unittest.main()
