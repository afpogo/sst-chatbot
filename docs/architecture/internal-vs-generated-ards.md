# Internal ARDS/SDD Vs Generated ARDS/SDD

## Internal ARDS/SDD
Internal ARDS/SDD is the knowledge system used to build, govern, and evolve this repository and the future SST agent application.

It contains:
- architecture decisions;
- specs and templates;
- POC rules;
- generation policies;
- validation scripts;
- examples approved by the product team.

This content can feed retrievers, planners, and validators. It should not be exposed directly as the user's generated package.

## Generated ARDS/SDD
Generated ARDS/SDD is the output created for the user through the web application.

It contains a project-specific structure such as:
- `AGENTS.md`;
- `docs/00-overview.md`;
- `docs/adr/0001-adopt-ards-sdd.md`;
- `specs/00-index.yaml`;
- `specs/templates/*.yaml`;
- `scripts/check.py`.

The generated package should be downloadable and should only include files approved by backend validation.

The generated workspace should start generic and become user-specific:

- generic baseline: required skeleton and default governance references;
- user specialization: validated files synced from an external documentation source repository.

This allows fast onboarding and later domain-specific adaptation without breaking core governance constraints.

Generated ARDS/SDD can also exist before download as a user workspace. That workspace may be logical, physical, or hybrid depending on how SST stores generated files and metadata.

For chatbot indexing, generated documents should be considered only when:
- sync and validation are complete,
- ownership is explicit (`workspace_id`, `account_id`, `source_tier`),
- the manifest marks the file as retrievable and not archived/sensitive.

## How The Agent Should Use Both
The agent should use internal ARDS/SDD as retrieval context. It should then produce a structured generation intent, not raw filesystem writes.

Recommended flow:

```text
user request
  -> retriever over internal ARDS/SDD catalog
  -> agent planner
  -> structured generation intent
  -> backend validator
  -> deterministic generator
  -> downloadable generated ARDS/SDD bundle
```

This keeps internal governance separate from the user's generated artifact.

## User Signup Implication
When a user is created, SST can provision a generated ARDS/SDD workspace for that user. The internal ARDS/SDD provides templates and rules; the generated workspace is owned by the user/account and can later be downloaded, indexed, or evolved through agent interactions.
