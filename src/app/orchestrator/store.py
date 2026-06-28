from __future__ import annotations

import hashlib
import json
from typing import Protocol

from app.orchestrator.types import HandoffReceipt


class HandoffStore(Protocol):
    def append(self, receipt: HandoffReceipt) -> HandoffReceipt:
        ...

    def find_by_idempotency(self, idempotency_key: str) -> HandoffReceipt | None:
        ...

    def list_receipts(self) -> tuple[HandoffReceipt, ...]:
        ...


class InMemoryHandoffStore:
    def __init__(self) -> None:
        self._receipts: dict[str, HandoffReceipt] = {}
        self._idempotency_index: dict[str, str] = {}

    def append(self, receipt: HandoffReceipt) -> HandoffReceipt:
        existing_id = self._idempotency_index.get(receipt.idempotency_key)
        if existing_id:
            return self._receipts[existing_id]

        self._receipts[receipt.receipt_id] = receipt
        self._idempotency_index[receipt.idempotency_key] = receipt.receipt_id
        return receipt

    def find_by_idempotency(self, idempotency_key: str) -> HandoffReceipt | None:
        receipt_id = self._idempotency_index.get(idempotency_key)
        if not receipt_id:
            return None
        return self._receipts[receipt_id]

    def list_receipts(self) -> tuple[HandoffReceipt, ...]:
        return tuple(self._receipts.values())


def payload_fingerprint(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        value = payload.model_dump()
    else:
        value = payload
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
