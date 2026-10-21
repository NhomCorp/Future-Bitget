"""Append-only JSONL proposal journal with deterministic replay."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .schema import ProposalRecord


class AppendOnlyProposalLog:
    """Write proposal records once and replay them without mutation."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, record: ProposalRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = record.to_dict()
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()

    def replay(self) -> tuple[ProposalRecord, ...]:
        if not self.path.exists():
            return ()
        records: list[ProposalRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    records.append(ProposalRecord.from_dict(data))
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"invalid proposal record at line {line_number}") from exc
        return tuple(records)

    def __iter__(self) -> Iterable[ProposalRecord]:
        return iter(self.replay())
