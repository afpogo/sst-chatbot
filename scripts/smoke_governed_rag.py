from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from app.audience_access.contracts import DataClassification  # noqa: E402
from app.governed_rag.contracts import GovernedMemoryRecord  # noqa: E402
from app.governed_rag.contracts import RagStatus  # noqa: E402
from app.governed_rag.contracts import RetrievalScope  # noqa: E402
from app.governed_rag.fakes import InMemoryGovernedMemorySource  # noqa: E402
from app.governed_rag.fakes import RecordingGroundedAnswerProvider  # noqa: E402
from app.governed_rag.policy import POLICY_VERSION  # noqa: E402
from app.governed_rag.retriever import LexicalRetriever  # noqa: E402
from app.governed_rag.runtime import GovernedRagRuntime  # noqa: E402


def memory(record_id: str, **overrides) -> GovernedMemoryRecord:
    values = {
        "record_id": record_id,
        "source_id": f"source-{record_id}",
        "source": "user_memory",
        "title": f"Memoria {record_id}",
        "content": "retrieval gobernado con citas y provenance",
        "tenant_id": "tenant-a",
        "user_id": "user-a",
        "application_id": "sst",
        "classification": DataClassification.PRIVATE,
        "required_entitlements": frozenset({"memory.read"}),
        "active": True,
        "indexable": True,
        "provenance": f"memory:{record_id}:v1",
    }
    values.update(overrides)
    return GovernedMemoryRecord(**values)


def run_smoke() -> dict[str, object]:
    source = InMemoryGovernedMemorySource(
        (
            memory("authorized-a"),
            memory("authorized-b", source="curated_workspace"),
            memory("foreign", tenant_id="tenant-b"),
            memory("secret", content="retrieval token=never-send-this"),
        )
    )
    provider = RecordingGroundedAnswerProvider()
    runtime = GovernedRagRuntime(
        source=source,
        retriever=LexicalRetriever(),
        provider=provider,
    )
    retrieval_scope = RetrievalScope(
        tenant_id="tenant-a",
        user_id="user-a",
        application_id="sst",
        entitlements=frozenset({"memory.read"}),
        allowed_classifications=frozenset({DataClassification.PRIVATE}),
        allowed_sources=frozenset({"user_memory", "curated_workspace"}),
        policy_version=POLICY_VERSION,
    )
    result = runtime.answer(
        question="Como funciona retrieval gobernado con citas?",
        scope=retrieval_scope,
        correlation_id="smoke-governed-rag",
    )
    assert result.status is RagStatus.COMPLETED
    assert len(result.citations) == 2
    outbound = provider.calls[0]["context"]
    serialized_outbound = json.dumps([item.model_dump() for item in outbound])
    assert "tenant-b" not in serialized_outbound
    assert "never-send-this" not in serialized_outbound

    denied = runtime.answer(
        question="token=never-send-this",
        scope=retrieval_scope,
        correlation_id="smoke-governed-rag-denied",
    )
    assert denied.status is RagStatus.DENIED
    assert denied.decision_code == "sensitive_question_detected"
    assert len(provider.calls) == 1
    return {
        "ok": True,
        "mode": "deterministic-fakes",
        "status": result.status.value,
        "decision_code": result.decision_code,
        "citation_count": len(result.citations),
        "cross_tenant_forwarded": False,
        "secret_forwarded": False,
        "sensitive_question_provider_call": False,
    }


def main() -> int:
    print(json.dumps(run_smoke(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
