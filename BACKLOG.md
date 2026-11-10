# WealthFlow Coding-Agent Training Backlog

This is the single project backlog for the Train WealthFlow Coding Agent project.
All items start as pending and are independently trackable.

## Phase 1 - Audit and design

### TWF-01 - Inspect task ledger/report structures and available conversation data
Status: pending
Acceptance: Written summary of the actual task ledger/report structures and the available conversation data, with source locations identified.

### TWF-02 - Identify qualifying task statuses and event types
Status: pending
Acceptance: Enumerate task statuses and event types; define in writing which combinations qualify as training examples and which are excluded; definition must be unambiguous.

### TWF-03 - Design formats for investigation/QA and implementation/patch examples
Status: pending
Acceptance: Specify a concrete versioned format for investigation/QA examples; specify a concrete versioned format for implementation/patch examples (request, context, diff, verification evidence); document both in this backlog or a linked note.

### TWF-04 - Confirm compatibility with current Agent2 training format
Status: pending
Acceptance: Review existing Agent2 training format; confirm the new example formats are compatible or document exactly how incompatible examples are kept separate; outcome recorded in this backlog.

## Phase 2 - Dataset extraction

### TWF-05 - Build an extractor for completed coding-agent task ledgers
Status: pending
Acceptance: Extractor code exists and produces structured examples from completed task ledgers; runs without error on a sample ledger.

### TWF-06 - Extract user requests, agent answers, implementation diffs, and verification evidence
Status: pending
Acceptance: Extracted examples contain user request, agent answer, implementation diff (where applicable), and verification evidence (where applicable); validated on a sample.

### TWF-07 - Exclude incomplete, failed, rejected, and unverified tasks
Status: pending
Acceptance: Filtering rules implemented and tested; incomplete, failed, rejected, and unverified tasks are demonstrably excluded from output.

### TWF-08 - Exclude secrets and sensitive personal/financial information
Status: pending
Acceptance: Privacy filtering implemented and tested; sample containing a secret/sensitive value shows it removed or redacted from output.

### TWF-09 - Deduplicate examples and validate their structure
Status: pending
Acceptance: Deduplication implemented; duplicate sample inputs produce a single example; all output examples pass a structure validation step.

## Phase 3 - Review and curation

### TWF-10 - Generate a reviewable dataset and report
Status: pending
Acceptance: A reviewable dataset file and a human-readable report are generated; report lists example counts and sources.

### TWF-11 - Allow manual approval or rejection of individual examples
Status: pending
Acceptance: Approval/rejection mechanism exists for individual examples; an example can be marked approved or rejected and the state persisted.

### TWF-12 - Preserve source task IDs for traceability
Status: pending
Acceptance: Every curated example carries its source task ID; traceability demonstrated by mapping an example back to its source ledger.

### TWF-13 - Ensure rejected examples never enter training datasets
Status: pending
Acceptance: Rejected examples are demonstrably absent from all downstream training dataset outputs; verified by test or manual check.

## Phase 4 - Dataset preparation

### TWF-14 - Create separate datasets for investigation and implementation
Status: pending
Acceptance: Two distinct dataset outputs exist (investigation/QA and implementation/patch); each contains only its own example type.

### TWF-15 - Create deterministic training/held-out splits to prevent data leakage
Status: pending
Acceptance: Split logic is deterministic (seeded); same input yields same split; no example appears in both training and held-out sets.

### TWF-16 - Add dataset quality checks and statistics
Status: pending
Acceptance: Quality checks run on the prepared datasets and produce statistics (counts, sizes, coverage); failures are reported.

### TWF-17 - Preserve the existing Git-based patch dataset pipeline unchanged
Status: pending
Acceptance: The existing Git-based patch dataset pipeline is untouched and still runs successfully after the new work.

## Phase 5 - Testing

### TWF-18 - Add automated tests for extraction, filtering, privacy, deduplication, approval, and splitting
Status: pending
Acceptance: Automated tests cover extraction, filtering, privacy, deduplication, approval, and splitting; all tests pass.

### TWF-19 - Run a dry-run against available real task history
Status: pending
Acceptance: A dry-run against real task history completes; results and any issues are recorded in this backlog.

### TWF-20 - Review sample outputs and correct any quality issues
Status: pending
Acceptance: Sample outputs reviewed; identified quality issues corrected and re-verified; outcome recorded in this backlog.

## Phase 6 - Training integration

### TWF-21 - Integrate approved datasets into the appropriate training workflow
Status: pending
Acceptance: Approved datasets wired into the existing Agent2 training workflow; end-to-end demonstrated without breaking existing functionality.

### TWF-22 - Keep training configuration separate for each example type
Status: pending
Acceptance: Investigation and implementation types use separate clearly named training configurations; no shared config that could mix types.

### TWF-23 - Ensure existing Agent2 training/export workflow remains functional
Status: pending
Acceptance: Pre-existing Agent2 training/export workflow runs successfully after integration; no behavior change for existing datasets.

### TWF-24 - Document the complete workflow
Status: pending
Acceptance: End-to-end workflow document exists (extraction, curation, preparation, training, export); covers prerequisites, commands, configuration, failure modes; committed to the repository.

## Rules (apply to all items)
- Do not modify the existing training pipeline during backlog-only work.
- Do not start model training until Phase 6 items are approved and ready.
- Do not create a new parallel backlog; this file is the single project backlog.
- Follow project file-size and architecture conventions.
- Every item is independently trackable with a clear completion criterion.
- All new items start as pending.
