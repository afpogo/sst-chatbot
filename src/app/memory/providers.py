from __future__ import annotations

from typing import Protocol

from app.memory.types import AuditMetadata
from app.memory.types import OperationalRecord
from app.memory.types import PhaseName


class AgentProviderPort(Protocol):
    def execute(
        self,
        *,
        phase_name: PhaseName,
        input_records: tuple[OperationalRecord, ...],
    ) -> OperationalRecord:
        ...


class FakeAgentProvider:
    def execute(
        self,
        *,
        phase_name: PhaseName,
        input_records: tuple[OperationalRecord, ...],
    ) -> OperationalRecord:
        if not input_records:
            raise ValueError("fake provider requires at least one input record")

        first = input_records[0]
        return OperationalRecord(
            id=f"agent-result-{phase_name}-{first.id}",
            record_type="agent_execution",
            tenant_id=first.tenant_id,
            scope=first.scope,
            user_id=first.user_id,
            correlation_id=first.correlation_id,
            idempotency_key=f"agent-result:{phase_name}:{first.id}",
            producer="fake-agent-provider",
            capability_id=first.capability_id,
            phase_name=phase_name,
            source_record_ids=tuple(record.id for record in input_records),
            status="completed",
            audit_metadata=AuditMetadata(
                origin_service="sst-chatbot",
                created_by="fake-agent-provider",
                reason="deterministic provider adapter test result",
            ),
            payload={
                "phase_name": phase_name,
                "input_record_ids": [record.id for record in input_records],
                "authority": "proposal_only",
            },
        )
