from __future__ import annotations

from typing import Protocol

from app.memory.types import OperationalRecord
from app.memory.types import RecordType
from app.memory.validation import require_valid_record


class RecordStore(Protocol):
    def append(self, record: OperationalRecord) -> OperationalRecord:
        ...

    def get(self, record_id: str) -> OperationalRecord | None:
        ...

    def list_records(self) -> tuple[OperationalRecord, ...]:
        ...

    def find_by_correlation(self, correlation_id: str) -> tuple[OperationalRecord, ...]:
        ...

    def find_by_idempotency(self, idempotency_key: str) -> OperationalRecord | None:
        ...


class InMemoryRecordStore:
    def __init__(self) -> None:
        self._records: dict[str, OperationalRecord] = {}
        self._idempotency_index: dict[str, str] = {}

    def append(self, record: OperationalRecord) -> OperationalRecord:
        require_valid_record(record)

        existing_id = self._idempotency_index.get(record.idempotency_key)
        if existing_id:
            existing = self._records[existing_id]
            if _same_idempotent_operation(existing, record):
                return existing
            raise ValueError(f"idempotency_key conflict for record {existing_id}")
        if record.id in self._records:
            raise ValueError(f"record already exists: {record.id}")

        self._records[record.id] = record
        self._idempotency_index[record.idempotency_key] = record.id
        return record

    def get(self, record_id: str) -> OperationalRecord | None:
        return self._records.get(record_id)

    def list_records(self) -> tuple[OperationalRecord, ...]:
        return tuple(self._records.values())

    def find_by_correlation(self, correlation_id: str) -> tuple[OperationalRecord, ...]:
        return tuple(
            record
            for record in self._records.values()
            if record.correlation_id == correlation_id
        )

    def find_by_idempotency(self, idempotency_key: str) -> OperationalRecord | None:
        record_id = self._idempotency_index.get(idempotency_key)
        if not record_id:
            return None
        return self._records[record_id]

    def find_by_type(self, record_type: RecordType) -> tuple[OperationalRecord, ...]:
        return tuple(
            record
            for record in self._records.values()
            if record.record_type == record_type
        )


def _same_idempotent_operation(
    existing: OperationalRecord,
    incoming: OperationalRecord,
) -> bool:
    return (
        existing.record_type == incoming.record_type
        and existing.tenant_id == incoming.tenant_id
        and existing.scope == incoming.scope
        and existing.user_id == incoming.user_id
        and existing.correlation_id == incoming.correlation_id
        and existing.capability_id == incoming.capability_id
        and existing.payload == incoming.payload
        and existing.body == incoming.body
        and existing.body_hash == incoming.body_hash
    )
