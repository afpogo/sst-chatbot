from __future__ import annotations

from app.memory.providers import AgentProviderPort
from app.memory.store import RecordStore
from app.memory.types import AuditMetadata
from app.memory.types import OperationalRecord
from app.memory.types import PhaseDefinition
from app.memory.types import PhaseName
from app.memory.types import PhaseRunResult
from app.memory.types import ValidationIssue
from app.memory.types import ValidationResult
from app.memory.validation import validate_record

DEFAULT_PHASES: dict[PhaseName, PhaseDefinition] = {
    "capture": PhaseDefinition(name="capture", allowed_next=("classify",)),
    "classify": PhaseDefinition(name="classify", allowed_next=("local_validate",)),
    "local_validate": PhaseDefinition(
        name="local_validate",
        allowed_next=("draft_intent", "reject_local_record"),
    ),
    "draft_intent": PhaseDefinition(
        name="draft_intent",
        allowed_next=("prepare_handoff", "reject_local_record"),
    ),
    "prepare_handoff": PhaseDefinition(
        name="prepare_handoff",
        allowed_next=("run_provider_adapter", "reject_local_record"),
        requires_human_review=True,
    ),
    "run_provider_adapter": PhaseDefinition(
        name="run_provider_adapter",
        allowed_next=("collect_observation", "reject_local_record"),
        emits=("phase_run", "agent_execution"),
    ),
    "collect_observation": PhaseDefinition(
        name="collect_observation",
        allowed_next=("select_visibility",),
    ),
    "select_visibility": PhaseDefinition(
        name="select_visibility",
        allowed_next=("archive_local_record", "reject_local_record"),
    ),
    "archive_local_record": PhaseDefinition(name="archive_local_record", allowed_next=()),
    "reject_local_record": PhaseDefinition(name="reject_local_record", allowed_next=()),
}


class PhaseRunner:
    def __init__(
        self,
        store: RecordStore,
        provider: AgentProviderPort | None = None,
    ) -> None:
        self.store = store
        self.provider = provider

    def run(
        self,
        phase_name: PhaseName,
        input_records: tuple[OperationalRecord, ...],
        *,
        human_reviewed: bool = False,
    ) -> PhaseRunResult:
        definition = DEFAULT_PHASES[phase_name]
        validation = self._validate_inputs(definition, input_records, human_reviewed)

        first = input_records[0]
        phase_run = OperationalRecord(
            id=f"phase-run-{phase_name}-{first.id}",
            record_type="phase_run",
            tenant_id=first.tenant_id,
            scope=first.scope,
            user_id=first.user_id,
            correlation_id=first.correlation_id,
            idempotency_key=f"phase:{phase_name}:{first.id}",
            producer="sst-chatbot",
            capability_id=first.capability_id,
            phase_name=phase_name,
            source_record_ids=tuple(record.id for record in input_records),
            status="completed" if validation.accepted else "rejected",
            audit_metadata=AuditMetadata(
                origin_service="sst-chatbot",
                created_by="phase-runner",
                reason=f"run {phase_name} phase",
            ),
            payload={
                "allowed_next": list(definition.allowed_next),
                "requires_human_review": definition.requires_human_review,
                "authority": "local_proposal_runtime_only",
            },
        )
        self.store.append(phase_run)

        emitted: list[OperationalRecord] = [phase_run]
        if validation.accepted and phase_name == "run_provider_adapter":
            if self.provider is None:
                raise ValueError("run_provider_adapter phase requires a provider adapter")
            agent_record = self.provider.execute(
                phase_name=phase_name,
                input_records=input_records,
            )
            self.store.append(agent_record)
            emitted.append(agent_record)

        return PhaseRunResult(
            phase_run=phase_run,
            emitted_records=tuple(emitted),
            validation=validation,
        )

    def _validate_inputs(
        self,
        definition: PhaseDefinition,
        input_records: tuple[OperationalRecord, ...],
        human_reviewed: bool,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if not input_records:
            issues.append(
                ValidationIssue(
                    code="missing_input_records",
                    message="phase requires at least one input record",
                )
            )

        for record in input_records:
            record_result = validate_record(record)
            issues.extend(record_result.issues)

        if definition.requires_human_review and not human_reviewed:
            issues.append(
                ValidationIssue(
                    code="human_review_required",
                    message=f"{definition.name} phase requires explicit human review before handoff preparation",
                    severity="manual-review",
                )
            )

        required = set(definition.required_record_types)
        if required:
            actual = {record.record_type for record in input_records}
            missing = required.difference(actual)
            for record_type in sorted(missing):
                issues.append(
                    ValidationIssue(
                        code="missing_required_record_type",
                        message=f"{definition.name} requires {record_type}",
                    )
                )

        return ValidationResult(accepted=not issues, issues=tuple(issues))
